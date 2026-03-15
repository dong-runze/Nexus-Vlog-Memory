"""
services/image_generator.py
使用 google-genai SDK（与 gemini_agent.py 保持一致）调用 Imagen 3 生成艺术级明信片底图。
"""

import asyncio
import io
import os
import traceback

from google import genai
from google.genai import types


# 常用简称 → 全称+地标描述 映射（防止 AI 图片太通用）
_LOCATION_MAPPING: dict[str, str] = {
    "USS": "Universal Studios Singapore theme park, featuring the iconic giant spinning globe, Hollywood Boulevard, Jurassic Park, Transformers ride, and colorful roller coasters",
    "MBS": "Marina Bay Sands Singapore, featuring the iconic three-tower hotel with rooftop infinity pool and ArtScience Museum at night",
    "GARDENS": "Gardens by the Bay Singapore, featuring the iconic Supertree Grove vertical gardens lit up at night with the giant glass conservatories",
    "SENTOSA": "Sentosa Island Singapore beach resort, featuring S.E.A. Aquarium, Adventure Cove Waterpark, and tropical beaches",
    "TOKYO": "Tokyo cityscape, featuring Tokyo Tower, Shibuya crossing, Mount Fuji in background, cherry blossoms",
    "DISNEYLAND": "Disneyland theme park, featuring the iconic Sleeping Beauty Castle with fireworks and colorful Disney characters",
}

# Imagen 3 使用的漫游缩略图提示词模板
_PROMPT_TEMPLATE = (
    "A highly engaging, vibrant travel vlog thumbnail photo of '{location_name}'. "
    "Crucial: The image MUST clearly feature the most iconic and recognizable landmarks, rides, or architecture of '{location_name}'. "
    "Atmosphere: Joyful travel memory, bustling with a happy vacation vibe, cinematic lighting, golden hour sunlight. "
    "Style: Ultra-realistic travel photography, wide-angle lens, vivid colors, highly detailed, perfect for a travel diary cover. "
    "No text overlays, no watermarks."
)

# google-genai SDK 正确的 Imagen 3 模型名
IMAGEN_MODEL = "imagen-3.0-generate-001"


def _get_client() -> genai.Client:
    """获取与 gemini_agent.py 相同的 google-genai Vertex AI 客户端。"""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location   = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project_id, location=location)


async def generate_ai_postcard_base(location_name: str) -> bytes:
    """
    异步调用 Imagen 3 生成艺术明信片底图。
    超时（25 秒）或失败时抛出异常，由调用方降级到 Pillow。
    """
    # 简称扭展：如果是已知简称，替换为含地标描述的全称
    mapped_name = _LOCATION_MAPPING.get(location_name.upper().strip(), location_name)
    prompt = _PROMPT_TEMPLATE.format(location_name=mapped_name)

    print(f"[ImageGen] ===== 开始生成明信片底图 =====")
    print(f"[ImageGen] 原始 location={location_name!r} → 映射后={mapped_name[:60]!r}")
    print(f"[ImageGen] model={IMAGEN_MODEL}, project={os.environ.get('GOOGLE_CLOUD_PROJECT')}, location={os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')}")
    print(f"[ImageGen] prompt (Front 120 chars): {prompt[:120]}...")

    try:
        # Imagen 生成实测需要 ~35 秒，设置 90s 超时留有余量
        image_bytes = await asyncio.wait_for(
            asyncio.to_thread(_generate_image_sync, prompt),
            timeout=90.0
        )
        print(f"[ImageGen] ✅ 生成成功，图片大小: {len(image_bytes) / 1024:.1f} KB")
        return image_bytes
    except asyncio.TimeoutError:
        raise RuntimeError("[ImageGen] Imagen API 调用超时（>90s），已降级")


def _generate_image_sync(prompt: str) -> bytes:
    """
    同步调用 google-genai Imagen API（在线程池中运行）。
    """
    try:
        client = _get_client()
        print(f"[ImageGen] google-genai 客户端初始化成功，调用 {IMAGEN_MODEL}...")

        result = client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:3",
                safety_filter_level="block_some",
                person_generation="dont_allow",
            )
        )

        if not result or not result.generated_images:
            raise RuntimeError("Imagen 未返回图片数据（generated_images 为空）")

        # google-genai SDK: 通过 .image.image_bytes 获取原始字节
        generated = result.generated_images[0]
        raw_bytes: bytes = generated.image.image_bytes

        if not raw_bytes:
            raise RuntimeError("Imagen 图片字节流为空")

        print(f"[ImageGen] ✅ 原始字节获取成功: {len(raw_bytes)} bytes")
        return raw_bytes

    except Exception as e:
        print(f"[ImageGen] ❌ 生成失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise
