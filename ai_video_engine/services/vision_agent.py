"""
services/vision_agent.py
多模态视觉 Agent：利用 Gemini Vision 能力从景区图片中识别天气和时间段。
"""

import asyncio
import json
import os

import httpx

from google import genai
from google.genai import types


# ================================================================
# 初始化 Gemini Client（复用全局 ADC 凭证）
# ================================================================

_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

try:
    _client = genai.Client(vertexai=True, project=_project, location=_location)
    print("[VisionAgent] Gemini Vertex AI Client 初始化成功")
except Exception as e:
    print(f"[VisionAgent] Client 初始化失败: {e}")
    _client = None


async def detect_weather_from_image(image_url: str) -> dict:
    """
    利用 Gemini 2.5 Flash 的视觉能力分析景区图片，推断天气和时间段。

    Args:
        image_url: 景区图片的公网 URL。

    Returns:
        dict with keys: weather_en, weather_zh, time_en, time_zh
        Fallback（无法访问图片/模型报错）时返回空字符串的 dict。
    """
    fallback = {"weather_en": "", "weather_zh": "", "time_en": "", "time_zh": ""}

    if not _client:
        print("[VisionAgent] Client 未初始化，跳过天气识别。")
        return fallback

    if not image_url:
        return fallback

    try:
        # Step 1: 下载图片字节流
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(image_url)
            response.raise_for_status()
            image_bytes = response.content
            # 尝试从 Content-Type 获取 mime_type，兜底 jpeg
            content_type = response.headers.get("content-type", "image/jpeg")
            mime_type = content_type.split(";")[0].strip()
            if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                mime_type = "image/jpeg"
    except Exception as e:
        print(f"[VisionAgent] 图片下载失败 ({image_url[:60]}): {e}")
        return fallback

    # Step 2: 构造多模态 Prompt
    prompt = (
        "分析这张游乐园或景区的照片。"
        "请推断出照片中的【天气状况】和【大概时间段】。"
        "只返回如下严格的 JSON，不要有任何解释或 markdown：\n"
        '{"weather_en": "Sunny", "weather_zh": "晴天", "time_en": "Afternoon", "time_zh": "下午"}\n'
        "weather_en 可选值参考: Sunny, Partly Cloudy, Overcast, Rainy, Foggy, Night\n"
        "time_en 可选值参考: Dawn, Morning, Noon, Afternoon, Evening, Night"
    )

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    config = types.GenerateContentConfig(temperature=0.1)

    try:
        result = await asyncio.to_thread(
            _client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[image_part, prompt],
            config=config,
        )

        raw = result.text.strip()
        # 去除可能的 markdown 代码块包裹
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        print(f"[VisionAgent] 天气识别结果: {parsed}")
        return {
            "weather_en": parsed.get("weather_en", ""),
            "weather_zh": parsed.get("weather_zh", ""),
            "time_en": parsed.get("time_en", ""),
            "time_zh": parsed.get("time_zh", ""),
        }
    except json.JSONDecodeError as je:
        print(f"[VisionAgent] JSON 解析失败: {je}，原始输出: {result.text[:200]}")
        return fallback
    except Exception as e:
        print(f"[VisionAgent] Gemini 调用失败: {e}")
        return fallback
