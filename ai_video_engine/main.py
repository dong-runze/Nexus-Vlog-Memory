"""
main.py
FastAPI 应用入口。
- 配置 CORS 中间件允许前端跨域请求
- 注册核心 API 路由：generate-clip（单节点）、stitch-vlog（全局拼接）
- 异步任务处理架构：POST 返回 taskId，GET 查询状态
- 启动时校验环境变量
"""

import uuid
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from core.config import settings
from models.task import Task, TaskType
from schemas.response import (
    ApiResponse,
    ResponseCode,
    TaskStatusResponse,
    VideoStitchTaskStatusResponse,
)
from services.task_processor import task_processor
from services.task_store import rate_limiter, task_store
from services.gemini_agent import generate_vlog_script, VlogScriptResponse, translate_to_video_prompt, validate_landmark_context
from services.firestore_client import get_all_landmarks, save_landmark
from services.gcs_client import generate_signed_url, upload_video
from services.video_generator import generate_5s_video
from services.vision_agent import detect_weather_from_image
import re
import os
import io
import json

# 公开路径（不需要身份验证）
PUBLIC_PATHS = {"/api/v1/health", "/api/v1/download-vlog", "/api/v1/generate-clip", "/api/v1/stitch-vlog", "/api/v1/upload-image", "/api/v1/validate-video-prompt", "/docs", "/openapi.json", "/redoc"}

app = FastAPI(
    title="AI Video Engine",
    description="AI 驱动的游乐园 DIY 交互地图 Vlog 生成器后端",
    version="0.3.0",
)


# ======================== 请求/响应模型 ========================


class StitchVlogRequest(BaseModel):
    """POST /api/v1/stitch-vlog 的请求体。"""
    video_urls: list[str]
    room_code: str = "master"
    location_id: str = "USS"  # [Multi-location] 景点标识符
    landmark_names: list[str] | None = None  # 与 video_urls 等长，用于字幕叠加
    video_blob_names: list[str] | None = None  # GCS blob 路径，用于重新生成有效下载链接


class StitchVlogResponse(BaseModel):
    """POST /api/v1/stitch-vlog 的响应体。"""
    task_id: str
    message: str


class GenerateVlogScriptRequest(BaseModel):
    """POST /api/v1/generate-vlog-script 的请求体。"""
    landmarks: list[str] = Field(..., description="用户选择的地标节点名称列表")
    theme: str = Field("默认", description="Vlog 的整体氛围主题")
    location_name: str = Field("", description="当前景点名称，用于地理上下文强绑定")


class ValidateLandmarkRequest(BaseModel):
    """POST /api/v1/validate-landmark 的请求体。"""
    landmark_name: str
    location_name: str

class GenerateClipRequest(BaseModel):
    """POST /api/v1/generate-clip 的请求体。"""
    user_prompt: str
    landmark_id: str = ""
    image_url: str = ""  # 可选：用于天气视觉识别
    location_id: str = "USS"  # [Multi-location] 景点标识符，默认 USS
    room_code: str = "master"  # [Multi-location] 沙盒房间码，默认 master


# ======================== 中间件：身份验证 ========================


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """API Key 身份验证中间件 (旧版，目前已全部放开)"""
    path = request.url.path
    method = request.method
    
    # OPTIONS 预检请求直接放行（让 CORS 中间件处理）
    if method == "OPTIONS":
        return await call_next(request)
    
    # 临时全面放开鉴权，以便测试生成脚本接口
    # auth_header = request.headers.get("X-API-Key")
    # if not auth_header or auth_header != settings.API_KEY:
    #     return JSONResponse(
    #         status_code=200,
    #         content={"code": ResponseCode.UNAUTHORIZED, "message": "无效的 API Key", "data": None}
    #     )

    return await call_next(request)


# ======================== 中间件：限流 ========================


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """接口限流中间件"""
    # OPTIONS 预检请求直接放行
    if request.method == "OPTIONS":
        return await call_next(request)
    
    client_id = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_id):
        return JSONResponse(
            status_code=200,
            content={"code": ResponseCode.RATE_LIMITED, "message": "请求过于频繁，请稍后再试", "data": None}
        )

    response = await call_next(request)
    return response


# ======================== CORS 中间件 (必须在所有自定义中间件之后添加) ========================
# FastAPI 中间件执行顺序是 LIFO（后进先出），最后添加的中间件最先执行。
# 把 CORS 放在最后，确保它能处理所有响应（包括其他中间件返回的响应）。

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================== 健康检查 ========================


@app.get("/api/v1/health")
async def health_check():
    """健康检查端点，同时返回环境变量校验状态。"""
    missing = settings.validate()
    return ApiResponse.success({
        "status": "ok" if not missing else "warning",
        "missing_config": missing,
    })


# ======================== 图片上传 (GCS) ========================


@app.post("/api/v1/upload-image", summary="上传图片到 GCS")
async def api_upload_image(
    file: UploadFile = File(...),
    location_id: str = Form("unknown"),
    room_code: str = Form("master"),
):
    try:
        from services.gcs_client import upload_image_bytes

        content_type = file.content_type or "image/jpeg"
        if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {content_type}")

        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(content_type, "jpg")
        import uuid as _uuid
        blob_name = f"images/{location_id}/{room_code}/img_{_uuid.uuid4().hex}.{ext}"

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="上传的文件为空")

        print(f"[UploadImage] {file.filename} → {blob_name} ({len(file_bytes)/1024:.0f} KB)")
        public_url = await upload_image_bytes(file_bytes, blob_name, content_type)
        return ApiResponse.success(data={"image_url": public_url, "blob_name": blob_name})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UploadImage] 失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")


# ======================== 视频提示词安全卫士 ========================


class ValidateVideoPromptRequest(BaseModel):
    prompt: str


@app.post("/api/v1/validate-video-prompt", summary="视频提示词安全校验")
async def api_validate_video_prompt(request: ValidateVideoPromptRequest):
    try:
        from services.gemini_agent import validate_and_enhance_video_prompt
        result = await validate_and_enhance_video_prompt(request.prompt)
        return ApiResponse.success(data=result)
    except Exception as e:
        print(f"[PromptGuard] 校验失败（降级放行）: {e}")
        return ApiResponse.success(data={"status": "safe", "message": "", "suggested_prompt": ""})


# ======================== Vlog 剧本生成 (Gemini 结构化输出) ========================


@app.post(
    "/api/v1/generate-vlog-script",
    summary="基于 Gemini 2.5 Flash 生成 Vlog 交错剧本",
    description="接收前端传来的打卡地标列表与主题，调用 Gemini 大模型生成旁白与生图(视频)提示词交错排列的结构化 JSON 数据"
)
async def api_generate_vlog_script(request: GenerateVlogScriptRequest):
    """
    生成图文交错结构化剧本接口（同步等待返回）。
    
    使用 Google GenAI SDK 和 gemini-2.5-pro 模型。
    """
    if not request.landmarks:
        raise HTTPException(
            status_code=400,
            detail="地标列表不能为空"
        )
    
    try:
        # 直接调用 gemini 服务生成剧本
        script_response = await generate_vlog_script(
            landmarks=request.landmarks,
            theme=request.theme,
            location_name=request.location_name,
        )
        return ApiResponse.success(data=script_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"剧本生成失败: {str(e)}"
        )


@app.post(
    "/api/v1/generate-clip",
    summary="生成 5s AI 视频片段",
    description="翻译提示词 → 天气识别增强 → Vertex AI Veo 生成视频 → 上传 GCS → Firestore 持久化 → 返回签名链接"
)
async def api_generate_clip(request: GenerateClipRequest):
    """
    完整的视频片段生成管线（同步模式，等待结果再返回）。
    GCS Blob 路径：{location_id}/{room_code}/clips/clip_{landmark_id}_{clip_id}.mp4
    """
    user_prompt = request.user_prompt
    landmark_id = request.landmark_id
    image_url = request.image_url
    location_id = request.location_id or "USS"
    room_code = request.room_code or "master"
    local_path = None

    print(f"[GenerateClip] location={location_id}, room={room_code}, landmark={landmark_id}")

    try:
        # 步骤 1：翻译提示词
        print(f"[GenerateClip] 开始翻译提示词: '{user_prompt[:60]}'")
        english_prompt = await translate_to_video_prompt(user_prompt)

        # 步骤 2：实时调用天气 Agent，识别图片中的天气和时间段
        weather_info = {"weather_en": "", "weather_zh": "", "time_en": "", "time_zh": ""}
        if image_url:
            print(f"[GenerateClip] 天气识别: {image_url[:60]}")
            weather_info = await detect_weather_from_image(image_url)

        # 步骤 3：如果天气识别成功，将天气/时间信息强制追加到视频提示词末尾
        weather_suffix = ""
        if weather_info.get("weather_en") or weather_info.get("time_en"):
            parts = [p for p in [weather_info["weather_en"], weather_info["time_en"]] if p]
            weather_suffix = ", ".join(parts)
            english_prompt = f"{english_prompt}, {weather_suffix}"
            print(f"[GenerateClip] 提示词已强化: '{english_prompt[:100]}'")

        # 步骤 4：隐式注入宏观地点上下文，构建最终喂给视频大模型的提示词
        # ⚠️ final_generation_prompt 仅用于视频生成，绝不存入数据库
        # english_prompt（不含地点前缀）才是写入 Firestore 的版本，保持用户输入的纯粹性
        final_generation_prompt = f"In {location_id}, {english_prompt}"
        print(f"[GenerateClip] 最终生成提示词 (含地点前缀): '{final_generation_prompt[:120]}'")

        clip_id = str(uuid.uuid4())[:8]
        filename = f"clip_{landmark_id}_{clip_id}.mp4" if landmark_id else f"clip_{clip_id}.mp4"
        local_path = await generate_5s_video(final_generation_prompt, filename, image_url=image_url)

        # 步骤 5：上传至 GCS（路径含 location_id / room_code）
        blob_name = f"{location_id}/{room_code}/clips/{filename}"
        print(f"[GenerateClip] 上传至 GCS: {blob_name}")
        blob_name = await upload_video(local_path, blob_name)

        # 步骤 6：生成签名链接
        signed_url = generate_signed_url(blob_name, expiration_minutes=60)

        # 步骤 7：持久化到 Firestore，将天气识别结果追加到双语标签列表
        updated_features_en: list[str] = []
        updated_features_zh: list[str] = []
        if landmark_id:
            firestore_update = {
                "videoBlobName": blob_name,
                "userVideoPrompt": user_prompt,
                "translatedVideoPrompt": english_prompt,
            }
            if weather_info.get("weather_en"):
                # 从 Firestore 获取当前地标，读取现有标签再追加（传入正确的 location_id + room_code）
                existing_landmarks = await get_all_landmarks(room_code, location_id)
                existing = next((x for x in existing_landmarks if x.get("id") == landmark_id), {})
                existing_en = existing.get("featuresEn") or existing.get("features") or []
                existing_zh = existing.get("featuresZh") or []
                updated_features_en = list(existing_en) + [f"{weather_info['weather_en']}, {weather_info['time_en']}"]
                updated_features_zh = list(existing_zh) + [f"{weather_info['weather_zh']}，{weather_info['time_zh']}"]
                firestore_update["featuresEn"] = updated_features_en
                firestore_update["featuresZh"] = updated_features_zh
            await save_landmark(landmark_id, firestore_update, room_code, location_id)
            print(f"[GenerateClip] Firestore 更新完成: landmark_id={landmark_id}, location={location_id}")

        # 步骤 8：清理本地临时文件
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

        return ApiResponse.success(data={
            "videoUrl": signed_url,
            "blobName": blob_name,
            "translatedPrompt": english_prompt,
            "weatherInfo": weather_info,
            "updatedFeaturesEn": updated_features_en,
            "updatedFeaturesZh": updated_features_zh,
        })

    except Exception as e:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass
        print(f"[GenerateClip] 视频生成失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"视频生成失败: {str(e)}"
        )




@app.post(
    "/api/v1/validate-landmark",
    summary="地标地理仲裁校验",
    description="调用 Gemini 判断地标是否属于指定地点，支持自动纠错"
)
async def api_validate_landmark(request: ValidateLandmarkRequest):
    """地标地理校验接口：valid / corrected / invalid"""
    try:
        result = await validate_landmark_context(
            landmark_name=request.landmark_name,
            location_name=request.location_name,
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"地标校验失败: {str(e)}"
        )


# ======================== 地标数据云端存取 (Firestore) ========================


@app.get(
    "/api/v1/landmarks",
    summary="获取所有地标数据",
    description="从 Firestore 读取并返回所有持久化的地标数据，为有 videoBlobName 的地标动态注入签名链接"
)
async def api_get_all_landmarks(room_code: str = "master", location_id: str = "USS"):
    """获取所有地标数据（按 room_code + location_id 隔离）"""
    try:
        landmarks = await get_all_landmarks(room_code, location_id)

        # 如果地标有 videoBlobName，动态生成限时60分钟的签名链接
        for lm in landmarks:
            blob_name = lm.get("videoBlobName")
            if blob_name:
                try:
                    lm["videoUrl"] = generate_signed_url(blob_name, expiration_minutes=60)
                except Exception as sign_err:
                    print(f"[GCS] 无法为 {blob_name} 生成签名链接: {sign_err}")

        return ApiResponse.success(data=landmarks)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取地标数据失败: {str(e)}"
        )


@app.post(
    "/api/v1/landmarks",
    summary="保存单个地标数据",
    description="接收地标详细 JSON，更新或插入到 Firestore"
)
async def api_save_landmark(request: Request):
    """保存或更新单个地标数据"""
    try:
        data = await request.json()
        
        # 前端需保证传入 JSON 时带有 id
        landmark_id = data.get("id")
        if not landmark_id:
             raise HTTPException(status_code=400, detail="请求体必须包含 id 字段")
             
        # 获取 room_code 和 location_id
        room_code = data.get("room_code", "master")
        location_id = data.get("location_id", "USS")
             
        # 中文拦截与翻译：如果 user_video_prompt 包含中文字符，翻译为纯英文
        user_prompt = data.get("user_video_prompt")
        # 如果 user_video_prompt_zh 有值，优先翻译它
        user_prompt_zh = data.get("user_video_prompt_zh")
        content_to_translate = user_prompt_zh if user_prompt_zh else user_prompt
        
        if content_to_translate and re.search(r'[\u4e00-\u9fff]', content_to_translate):
            translated_prompt = await translate_to_video_prompt(content_to_translate)
            data["translated_video_prompt"] = translated_prompt
            print(f"[Translation] Translated prompt for {landmark_id}: {translated_prompt}")

        saved_data = await save_landmark(landmark_id, data, room_code, location_id)
        return ApiResponse.success(data=saved_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"\u4fdd\u5b58\u5730\u6807\u6570\u636e\u5931\u8d25: {str(e)}"
        )


@app.delete(
    "/api/v1/landmarks/{landmark_id}",
    summary="\u5220\u9664\u5730\u6807\u6570\u636e",
    description="\u652f\u6301\u6c99\u76d2\u673a\u5236\u7684\u5220\u9664\uff1amaster\u76f4\u63a5\u5220\u9664\uff0c\u5176\u4ed6room_code\u6807\u8bb0\u4e3a\u5893\u7891"
)
async def api_delete_landmark(landmark_id: str, room_code: str = "master", location_id: str = "USS"):
    """\u5220\u9664\u6216\u6807\u8bb0\u5220\u9664\u5355\u4e2a\u5730\u6807\u6570\u636e"""
    try:
        from services.firestore_client import delete_landmark
        result = await delete_landmark(landmark_id, room_code, location_id)
        return ApiResponse.success(data=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"\u5220\u9664\u5730\u6807\u6570\u636e\u5931\u8d25: {str(e)}"
        )


# ======================== AI \u660e\u4fe1\u7247\u5bfc\u51fa\u4e0e\u5bfc\u5165 (EXIF \u9690\u5199\u672f) ========================


@app.get(
    "/api/v1/export-postcard",
    summary="\u5bfc\u51fa AI \u660e\u4fe1\u7247",
    description="\u5c06\u6307\u5b9a\u623f\u95f4\u548c\u5730\u70b9\u7684\u6240\u6709\u5730\u6807\u6570\u636e\u9690\u5199\u81f3 JPEG \u56fe\u7247\u7684 EXIF UserComment \u5b57\u6bb5\u5e76\u8fd4\u56de\u4e0b\u8f7d"
)
async def api_export_postcard(
    location_id: str = Query(..., description="\u5730\u70b9 ID"),
    room_code: str = Query("master", description="\u623f\u95f4\u4ee3\u7801")
):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import piexif
        from services.image_generator import generate_ai_postcard_base

        # \u2460 \u83b7\u53d6\u5730\u6807\u6570\u636e\uff0c\u4e8c\u6b21\u8fc7\u6ee4\u5f7b\u5e95\u5254\u9664\u5893\u7891\uff08belt-and-suspenders\uff09
        landmarks_raw = await get_all_landmarks(room_code, location_id)
        landmarks = [lm for lm in landmarks_raw if not lm.get("is_deleted")]
        if not landmarks:
            raise HTTPException(status_code=404, detail=f"\u5730\u70b9 '{location_id}' \u623f\u95f4 '{room_code}' \u4e2d\u6ca1\u6709\u6709\u6548\u5730\u6807\u6570\u636e\uff0c\u65e0\u6cd5\u751f\u6210\u660e\u4fe1\u7247\u3002")

        print(f"[Postcard] \u5bfc\u51fa\u8fc7\u6ee4: \u539f\u59cb {len(landmarks_raw)} \u6761 \u2192 \u6709\u6548 {len(landmarks)} \u6761")

        payload_json = json.dumps(landmarks, ensure_ascii=False)
        payload_bytes = payload_json.encode("utf-8")

        # \u2461 \u8c03\u7528 Imagen 3 \u751f\u6210 AI \u827a\u672f\u5e95\u56fe\uff0c\u5931\u8d25\u65f6\u964d\u7ea7\u5230 Pillow \u5360\u4f4d\u56fe
        location_display = location_id.replace("_", " ").title()
        base_image_bytes: bytes | None = None

        try:
            base_image_bytes = await generate_ai_postcard_base(location_display)
            print(f"[Postcard] Imagen \u751f\u6210\u6210\u529f\uff0c\u5b57\u8282\u6570: {len(base_image_bytes)}")
        except Exception as img_err:
            print(f"[Postcard] \u26a0\ufe0f Imagen \u751f\u6210\u5e95\u56fe\u5931\u8d25\uff08\u964d\u7ea7 Pillow\uff09: {img_err}")

        if base_image_bytes:
            img = Image.open(io.BytesIO(base_image_bytes)).convert("RGB")
            img = img.resize((800, 600), Image.LANCZOS)
        else:
            # --- Pillow \u964d\u7ea7\u5e95\u56fe ---
            img = Image.new("RGB", (800, 600), color=(15, 23, 42))
            draw_fb = ImageDraw.Draw(img)
            for y in range(600):
                r_v = int(15 + (30 - 15) * y / 600)
                g_v = int(23 + (41 - 23) * y / 600)
                b_v = int(42 + (82 - 42) * y / 600)
                draw_fb.line([(0, y), (800, y)], fill=(r_v, g_v, b_v))
            try:
                fb_font = ImageFont.truetype("arial.ttf", 44)
                fb_sub  = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                fb_font = fb_sub = ImageFont.load_default()
            bbox_fb = draw_fb.textbbox((0, 0), location_display, font=fb_font)
            tw_fb = bbox_fb[2] - bbox_fb[0]
            draw_fb.text(((800 - tw_fb) / 2, 230), location_display, fill=(248, 248, 255), font=fb_font)
            draw_fb.text(((800 - tw_fb) / 2 - 10, 295), f"{len(landmarks)} landmarks", fill=(148, 163, 184), font=fb_sub)

        # \u2462 \u53f3\u4e0b\u89d2\u534a\u900f\u660e\u7cbe\u7f8e\u6c34\u5370\u6807\u7b7e
        draw = ImageDraw.Draw(img, "RGBA")
        try:
            wm_font_lg = ImageFont.truetype("arial.ttf", 18)
            wm_font_sm = ImageFont.truetype("arial.ttf", 13)
        except Exception:
            wm_font_lg = wm_font_sm = ImageFont.load_default()

        wm_line1 = location_id.upper()          # e.g. "USS" - pure ASCII, no emoji
        wm_line2 = f"{len(landmarks)} landmarks | Vlog Memory"  # | instead of bullet
        wm_line3 = "Powered by Gemini"

        b1 = draw.textbbox((0, 0), wm_line1, font=wm_font_lg)
        b2 = draw.textbbox((0, 0), wm_line2, font=wm_font_sm)
        b3 = draw.textbbox((0, 0), wm_line3, font=wm_font_sm)
        wm_w = max(b1[2]-b1[0], b2[2]-b2[0], b3[2]-b3[0]) + 24
        wm_h = (b1[3]-b1[1]) + (b2[3]-b2[1]) + (b3[3]-b3[1]) + 28
        wm_x = 800 - wm_w - 12
        wm_y = 600 - wm_h - 12

        draw.rounded_rectangle([wm_x, wm_y, wm_x + wm_w, wm_y + wm_h], radius=8, fill=(0, 0, 0, 160))
        y_cur = wm_y + 10
        draw.text((wm_x + 12, y_cur), wm_line1, fill=(255, 255, 255, 230), font=wm_font_lg)
        y_cur += (b1[3] - b1[1]) + 4
        draw.text((wm_x + 12, y_cur), wm_line2, fill=(148, 163, 184, 200), font=wm_font_sm)
        y_cur += (b2[3] - b2[1]) + 2
        draw.text((wm_x + 12, y_cur), wm_line3, fill=(56, 189, 248, 180), font=wm_font_sm)

        # \u2463 \u8f6c\u4e3a JPEG\uff08\u53bb\u63389 RGBA alpha \u901a\u9053\uff09
        base_buf = io.BytesIO()
        img.convert("RGB").save(base_buf, format="JPEG", quality=92)
        jpeg_bytes = base_buf.getvalue()

        # \u2464 piexif \u6ce8\u5165 EXIF UserComment\uff08\u903b\u8f91\u4fdd\u6301\u4e0d\u53d8\uff09
        user_comment_bytes = b"ASCII\x00\x00\x00" + payload_bytes
        exif_dict = {"Exif": {piexif.ExifIFD.UserComment: user_comment_bytes}}
        exif_bytes = piexif.dump(exif_dict)
        final_buf = io.BytesIO()
        piexif.insert(exif_bytes, jpeg_bytes, final_buf)
        final_buf.seek(0)

        filename = f"Vlog_Memory_{location_id}.jpg"
        print(f"[Postcard] \u5bfc\u51fa\u6210\u529f: {filename} ({len(landmarks)} \u4e2a\u5730\u6807, {len(payload_bytes)} bytes)")

        return StreamingResponse(
            final_buf,
            media_type="image/jpeg",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Postcard] \u5bfc\u51fa\u5931\u8d25: {e}")
        raise HTTPException(status_code=500, detail=f"\u5bfc\u51fa\u660e\u4fe1\u7247\u5931\u8d25: {str(e)}")


@app.post(
    "/api/v1/import-postcard",
    summary="导入 AI 明信片",
    description="解析上传的 JPEG 图片中的 EXIF UserComment，还原地标 JSON 并写入 Firestore"
)
async def api_import_postcard(
    file: UploadFile = File(..., description="含有 EXIF 数据的 JPEG 明信片"),
    room_code: str = Form("master", description="导入目标房间代码"),
):
    try:
        import piexif

        # ① 读取上传的图片
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="上传的文件为空。")

        # ② 解析 EXIF
        try:
            exif_data = piexif.load(file_bytes)
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="该图片不包含有效的 EXIF 数据，请确保上传的是通过本应用导出的 'Vlog Memory' 明信片。"
            )

        # ③ 提取 UserComment (tag 37510)
        raw_comment = exif_data.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if raw_comment is None:
            raise HTTPException(
                status_code=422,
                detail="图片 EXIF 中不包含 UserComment 字段，该图片可能不是有效的 Vlog Memory 明信片。"
            )

        # 去掉前 8 字节的字符集标识 (b"ASCII\x00\x00\x00")
        if len(raw_comment) <= 8:
            raise HTTPException(status_code=422, detail="UserComment 内容为空，明信片数据可能损坏。")

        payload_bytes = raw_comment[8:]

        # ④ 解析 JSON
        try:
            landmarks = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="EXIF UserComment 中的数据无法解析为地标 JSON，明信片可能损坏或不兼容。"
            )

        if not isinstance(landmarks, list) or len(landmarks) == 0:
            raise HTTPException(status_code=422, detail="明信片中没有可导入的地标数据。")

        # ⑥ 提取明信片原产地：从第一条有效地标中读取 location_id
        valid_landmarks = [lm for lm in landmarks if not lm.get("is_deleted")]
        if not valid_landmarks:
            raise HTTPException(status_code=422, detail="明信片中的地标均已被删除，无可导入的有效数据。")

        original_location_id = valid_landmarks[0].get("location_id", "USS")
        print(f"[Postcard] 明信片原产地: {original_location_id}，将导入到房间: {room_code}")

        # ⑦ Append-only 导入：为每条地标生成全新 UUID ID，绝不覆盖现有数据
        saved_count = 0
        skipped_count = 0
        for lm in landmarks:
            # 跳过明信片内已被删除的废弃记录（墓碑）
            if lm.get("is_deleted"):
                skipped_count += 1
                continue

            # 生成全新 ID，确保 append-only
            short_uuid = uuid.uuid4().hex[:6]
            name_slug = lm.get("name", lm.get("name_en", "import")).lower().replace(" ", "_")[:20]
            new_id = f"{room_code}_{original_location_id}_{name_slug}_{short_uuid}"
            lm["id"] = new_id
            lm["room_code"] = room_code
            lm["location_id"] = original_location_id  # 强制使用原产地，不优先信任前端
            lm.pop("is_deleted", None)

            # ── 明确保留多媒体字段（video_url / image_url / user_video_prompt）──────
            # Firestore 存储的原始字段会随 lm dict 完整保留，此处做防御性兜底，
            # 确保即使字段名略有差异也不丢失。
            for src, dst in [("videoUrl", "video_url"), ("imageUrl", "image_url"),
                             ("userVideoPrompt", "user_video_prompt"), ("userVideoPromptZh", "user_video_prompt_zh")]:
                if dst not in lm and src in lm:
                    lm[dst] = lm[src]

            print(f"[Postcard] 导入地标: {name_slug} | video_url={'✓' if lm.get('video_url') else '—'} | image_url={'✓' if lm.get('image_url') else '—'}")

            try:
                await save_landmark(new_id, lm, room_code, original_location_id)
                saved_count += 1
            except Exception as save_err:
                print(f"[Postcard] 导入地标 {new_id} 失败: {save_err}")

        print(f"[Postcard] 导入完成: {saved_count} 个新增, {skipped_count} 个墓碑跳过 → {room_code}/{original_location_id}")
        return ApiResponse.success(data={
            "imported": saved_count,
            "skipped": skipped_count,
            "total": len(landmarks),
            "imported_location_id": original_location_id,   # 前端用于判断是否需要自动飞行
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Postcard] 导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入明信片失败: {str(e)}")


# ======================== 全局 Vlog 拼接 ========================


@app.post(
    "/api/v1/stitch-vlog",
    response_model=ApiResponse[StitchVlogResponse],
    summary="提交视频拼接任务",
    description="提交视频拼接任务，返回任务ID，后续通过 GET /task/{taskId}/status 查询状态"
)
async def api_stitch_vlog(request: StitchVlogRequest):
    """
    全局快速拼接接口（异步模式）。

    接收一组已生成的视频片段 URL，使用 FFmpeg 拼接，
    返回任务ID。
    """
    valid_urls = [url for url in request.video_urls if url and url.strip()]

    if not valid_urls:
        raise HTTPException(
            status_code=400,
            detail="至少需要一个有效的视频 URL"
        )

    task = Task(
        task_id=str(uuid.uuid4()),
        task_type=TaskType.VIDEO_STITCH,
        metadata={
            "video_urls": valid_urls,
            "room_code": request.room_code,
            "location_id": request.location_id,
            "landmark_names": request.landmark_names,
            "video_blob_names": request.video_blob_names,  # 重新签名用
        },
    )

    await task_processor.submit_task(task)

    return ApiResponse.success(
        data=StitchVlogResponse(
            task_id=task.task_id,
            message=f"视频拼接任务已提交，共 {len(valid_urls)} 个片段"
        )
    )

@app.get(
    "/api/v1/vlogs",
    summary="获取指定房间的合成 Vlog 历史记录",
    description="支持沙盒机制：合并 master 与当前沙盒记录并按时间倒序"
)
async def api_get_vlogs(room_code: str = "master", location_id: str = "USS"):
    """获取指定房间 & 地点的 Vlog 数据列表"""
    try:
        from services.firestore_client import get_vlogs_by_room
        from services.gcs_client import generate_signed_url
        vlogs = await get_vlogs_by_room(room_code, location_id)
        
        # 为每个结果设置签名的视频URL
        for v in vlogs:
            blob_name = v.get("final_vlog_blob_name")
            if blob_name:
                v["video_url"] = generate_signed_url(blob_name, expiration_minutes=60)
        
        return ApiResponse.success(data=vlogs)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取 Vlog 列表数据失败: {str(e)}"
        )


# ======================== 任务状态查询 ========================


@app.get(
    "/task/{taskId}/status",
    response_model=ApiResponse[TaskStatusResponse],
    summary="查询任务状态",
    description="查询视频生成或拼接任务的当前状态、进度和结果"
)
async def get_task_status(taskId: str):
    """
    任务状态查询接口。

    返回任务当前状态：
    - pending: 待处理
    - processing: 处理中
    - completed: 已完成
    - failed: 失败

    以及进度信息、预计剩余时间、结果或错误信息。
    """
    task = task_store.get_task(taskId)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {taskId} 不存在"
        )

    if task.task_type == TaskType.VIDEO_STITCH:
        response_data = VideoStitchTaskStatusResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            status=task.status.value,
            progress=task.progress,
            total=task.total,
            result=task.result,
            error=task.error,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            estimated_time_remaining=task.estimated_time_remaining,
            metadata=task.metadata,
            resolution=task.metadata.get("resolution"),
            bitrate=task.metadata.get("bitrate"),
            duration=task.metadata.get("duration"),
            clip_count=task.metadata.get("clip_count"),
        )
    else:
        response_data = TaskStatusResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            status=task.status.value,
            progress=task.progress,
            total=task.total,
            result=task.result,
            error=task.error,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            estimated_time_remaining=task.estimated_time_remaining,
            metadata=task.metadata,
        )

    return ApiResponse.success(data=response_data)


# ======================== 视频下载代理 ========================


@app.get(
    "/api/v1/download-vlog",
    summary="代理下载视频文件",
    description="代理下载远端视频文件，强制触发浏览器的下载行为，解决 CORS 和直接播放问题"
)
async def download_vlog(
    video_url: str = Query(..., description="The URL of the video to download"),
    filename: str = Query("my_uss_vlog.mp4", description="Downloaded filename")
):
    """
    代理下载远端视频文件，强制触发浏览器的下载行为。

    因为直接在前端通过 <a> 标签下载第三方 URL 的视频往往会直接在浏览器播放
    而不是下载，此接口做一层代理转发，添加 Content-Disposition 头强制下载。
    """
    async def fetch_video_stream():
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", video_url) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"无法获取视频: {response.status_code}"
                    )
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk

    # 清理文件名，确保安全
    safe_filename = filename.replace('"', '').replace('/', '_').replace('\\', '_')
    
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"'
    }
    
    return StreamingResponse(
        fetch_video_stream(),
        media_type="video/mp4",
        headers=headers
    )


# ======================== 启动入口 ========================

if __name__ == "__main__":
    import uvicorn

    missing = settings.validate()
    if missing:
        print(f"[Warning] 以下环境变量未配置: {', '.join(missing)}")
        print("[Warning] 部分功能将不可用，请在 .env 文件中补充配置。")

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
