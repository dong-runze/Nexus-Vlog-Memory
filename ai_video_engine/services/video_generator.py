"""
services/video_generator.py
使用 google-genai SDK（与 gemini_agent.py 保持一致）调用 Veo 生成 5 秒视频片段。
支持图生视频（Image-to-Video）：将用户上传的图片作为初始参考帧传入 Veo。
"""

import asyncio
import os
import tempfile
import time
import urllib.request

from google import genai
from google.genai import types

from core.config import settings


TARGET_MODEL = "veo-2.0-generate-001"  # 可切换为 veo-3.0-generate-preview


def _get_client() -> genai.Client:
    """获取与 gemini_agent.py 相同的 google-genai Vertex AI 客户端。"""
    project_id = settings.GOOGLE_CLOUD_PROJECT or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location   = settings.GOOGLE_CLOUD_LOCATION or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project_id, location=location)


def _fetch_image_bytes(url: str) -> bytes:
    """从 HTTP(S) URL 下载图片字节流（用于构建 types.Image 参考帧）。"""
    req = urllib.request.Request(url, headers={"User-Agent": "VlogEngine/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _build_image_obj(image_url: str | None) -> types.Image | None:
    """
    将 image_url 转换为 google.genai.types.Image 对象。
    - 如果是 gs:// 格式 → 直接用 gcs_uri
    - 如果是 https:// 格式（Signed URL）→ 下载字节后用 image_bytes
    - 如果为空 → 返回 None（退化为纯文生视频）
    """
    if not image_url:
        return None

    url = image_url.strip()

    if url.startswith("gs://"):
        # GCS 原生 URI — 直接传给 SDK，无需下载
        if url.lower().endswith(".png"):
            mime = "image/png"
        elif url.lower().endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"
        print(f"[VideoGen] 图片 GCS URI 模式: {url[:60]}, mime={mime}")
        return types.Image(gcs_uri=url, mime_type=mime)

    if url.startswith("http://") or url.startswith("https://"):
        # Signed URL / CDN URL → 下载图片字节
        print(f"[VideoGen] 下载图片字节（HTTP 模式）: {url[:80]}...")
        try:
            img_bytes = _fetch_image_bytes(url)

            # 推断 MIME 类型（从 URL 路径部分判断，去掉 query string 后缀，默认 jpeg）
            path_part = url.split("?")[0].lower()
            if path_part.endswith(".png"):
                mime = "image/png"
            elif path_part.endswith(".webp"):
                mime = "image/webp"
            elif path_part.endswith(".gif"):
                mime = "image/gif"
            else:
                mime = "image/jpeg"

            print(f"[VideoGen] 图片下载成功: {len(img_bytes)} bytes, mime={mime}")
            # mime_type 必须明确传入，否则 Veo API 返回 400 INVALID_ARGUMENT
            return types.Image(image_bytes=img_bytes, mime_type=mime)
        except Exception as e:
            print(f"[VideoGen] ⚠️ 图片下载失败，退化为文生视频: {e}")
            return None

    print(f"[VideoGen] ⚠️ 无法识别的 image_url 格式，忽略: {url[:60]}")
    return None


async def generate_5s_video(prompt: str, output_filename: str, image_url: str | None = None) -> str:
    """
    使用 google-genai Veo 模型根据文字提示词生成 5 秒视频。

    Args:
        prompt: 英文视频提示词（已优化）。
        output_filename: 输出文件名，例如 'clip_abc123.mp4'。
        image_url: 可选，用户上传图片的 URL（支持 gs:// 和 https://）。
                   传入后启用图生视频（Image-to-Video），让照片"活"起来。

    Returns:
        本地保存的 mp4 文件绝对路径。
    """
    local_path = await asyncio.to_thread(_generate_video_sync, prompt, output_filename, image_url)
    return local_path


def _generate_video_sync(prompt: str, output_filename: str, image_url: str | None = None) -> str:
    """
    同步调用 google-genai Veo API，轮询等待完成后将视频写入本地临时目录。
    """
    client = _get_client()
    mode = "图生视频" if image_url else "文生视频"
    print(f"[VideoGen] google-genai 客户端初始化成功，model={TARGET_MODEL}，模式={mode}")
    print(f"[VideoGen] prompt='{prompt[:80]}...'")

    # 构建图片对象（None 时退化为纯文生视频）
    image_obj = _build_image_obj(image_url)
    if image_obj:
        print("[VideoGen] ✅ 图片参考帧已构建，启用 Image-to-Video 模式")
    else:
        print("[VideoGen] ℹ️ 无图片参考帧，使用 Text-to-Video 模式")

    # ── 发起视频生成 ──────────────────────────────────────────
    # 关键：prompt 只能是纯文本字符串，图片必须通过 image 参数传入
    generate_kwargs: dict = dict(
        model=TARGET_MODEL,
        prompt=prompt,   # 纯文本！绝不把图片塞进 prompt 列表
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=5,
            aspect_ratio="16:9",
            person_generation="allow_adult",  # 允许成人出镜（主题公园场景）
        ),
    )
    if image_obj is not None:
        generate_kwargs["image"] = image_obj  # 专用 image 参数！

    operation = client.models.generate_videos(**generate_kwargs)

    print("========== VEO RAW OPERATION ==========")
    print(f"operation type  : {type(operation)}")
    print(f"operation.name  : {getattr(operation, 'name', 'N/A')}")
    print(f"operation.done  : {operation.done}")
    print(f"operation.error : {getattr(operation, 'error', 'N/A')}")
    print("=======================================")

    # 轮询等待完成（最多 5 分钟）
    print("[VideoGen] 等待视频生成完成（polling）...")
    max_wait_seconds = 300
    poll_interval = 10
    elapsed = 0

    while not operation.done:
        if elapsed >= max_wait_seconds:
            raise RuntimeError("Veo 视频生成超时（5 分钟）")
        time.sleep(poll_interval)
        elapsed += poll_interval
        operation = client.operations.get(operation)
        print(f"[VideoGen] 已等待 {elapsed}s，done={operation.done}")

    # 获取结果
    result = operation.result
    print("========== VEO RAW RESULT ==========")
    print(f"result type       : {type(result)}")
    print(f"generated_videos  : {getattr(result, 'generated_videos', 'ATTR_MISSING')}")
    print("=====================================")

    if not result or not getattr(result, 'generated_videos', None):
        raise ValueError(
            f"Veo 模型拒绝生成视频，可能触发了安全拦截或参数不支持。\n"
            f"Operation error: {getattr(operation, 'error', 'N/A')}\n"
            f"Raw result: {result}"
        )

    # google-genai SDK: 通过 .video.video_bytes 获取原始字节
    generated = result.generated_videos[0]
    video_bytes: bytes = generated.video.video_bytes

    if not video_bytes:
        raise RuntimeError("Veo 视频字节流为空")

    # 写入临时文件
    work_dir = tempfile.mkdtemp(prefix="veo_clip_")
    local_path = os.path.join(work_dir, output_filename)

    with open(local_path, "wb") as f:
        f.write(video_bytes)

    size_kb = len(video_bytes) / 1024
    print(f"[VideoGen] ✅ 视频生成成功！文件: {local_path} ({size_kb:.1f} KB)")
    return local_path
