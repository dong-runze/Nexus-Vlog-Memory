"""
services/gemini_agent.py
使用 Google 官方 SDK google-genai 调用 gemini-2.5-flash 大模型 (Vertex AI 模式)。
用于生成环球影城 Vlog 的图文交错剧本。
"""

import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


# ======================== 定义结构化输出模型 ========================

class ScriptNode(BaseModel):
    """Vlog 剧本单个节点：包含特定地标的双语旁白和极简分镜提示词"""
    landmark_name: str = Field(
        ...,
        description="关联的地标名称"
    )
    narration_zh: str = Field(
        ...,
        description="深情的中文旁白内容"
    )
    narration_en: str = Field(
        ...,
        description="深情的英文旁白内容"
    )
    video_prompt: str = Field(
        ...,
        description="极度精简（不超过 15 个纯英文单词）的分镜提示词，专供 5 秒 AI 视频模型使用，强调主体、光影和镜头运动"
    )
    opening_hours: str = Field(
        ...,
        description="该地标的营业时间，例如 'Daily: 10:00 AM - 7:00 PM'"
    )
    coordinates: str = Field(
        ...,
        description="真实地理坐标，格式例如 '1.25584, 103.82300'"
    )
    features_en: list[str] = Field(
        ...,
        description="3 个代表该景点特色/亮点的简短英文标签，每个标签不超过 4 个英文单词"
    )
    features_zh: list[str] = Field(
        ...,
        description="将 features_en 中的 3 个标签准确翻译为中文，顺序与 features_en 一一对应"
    )


class VlogScriptResponse(BaseModel):
    """整个 Vlog 的结构化剧本"""
    nodes: list[ScriptNode] = Field(
        ...,
        description="针对每个地标生成的剧本节点集合"
    )


# ======================== 初始化 Gemini Client ========================

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

try:
    # 强制使用 Vertex AI 模式
    client = genai.Client(vertexai=True, project=project_id, location=location)
    print(f"[Gemini] Vertex AI Client 初始化成功 (Project: {project_id}, Location: {location})")
except Exception as e:
    print(f"[Warning] Gemini Client 初始化失败 (请检查 ADC 凭据配置): {e}")
    client = None


# ======================== 核心生成逻辑 ========================

async def generate_vlog_script(landmarks: list[str], theme: str = "Cinematic", location_name: str = "") -> dict:
    """
    调用 gemini-2.5-flash 针对一组地标生成双语剧本。

    Args:
        landmarks: 用户在地标地图上选取的打卡点名称列表。
        theme: Vlog 的整体氛围主题。
        location_name: 当前景点名称（用于地理上下文强绑定）。

    Returns:
        dict: 结构化的剧本字典。
    """
    if not client:
        raise RuntimeError("Gemini Client 未正确初始化，无法生成剧本。")

    if not landmarks:
        raise ValueError("地标列表不能为空。")

    # 构建系统指令 System Instruction（地理强绑定约束置顶）
    location_constraint = (
        f"【绝对上下文强制约束】你现在处于【{location_name}】。"
        f"你生成的所有景点剧本、标签和旁白，必须且只能属于【{location_name}】这个地点。"
        f"如果传入的地标名称不属于该地点，请尽最大努力将其解释为【{location_name}】内最相似的设施，严禁跨地域生成。\n\n"
    ) if location_name else ""

    system_instruction = (
        location_constraint +
        "你是一位资深 Vlog 导演兼景点数据库管理员。你需要将用户提供的地标列表，编排成一段对应的 Vlog 剧本。\n"
        "对于每一个地标，你必须同时生成一段深情的中文旁白 (narration_zh) 和一段对应的英文旁白 (narration_en)。\n"
        "另外，针对每个地标生成一段极度精简（不超过 15 个纯英文单词）的分镜提示词 (video_prompt)，"
        "专供 5 秒 AI 视频模型使用，强调主体景象、光影和镜头运动。\n"
        "营业时间 (opening_hours) 必须包含具体的时间数字格式（例如 'Daily: 10:00 AM - 7:00 PM' 或 'Showtimes: 12:00 PM, 3:00 PM'），"
        "严禁使用 'Open during park hours' 等任何模糊词汇。如果不确定，请基于同类型景点合理估算一个具体时间。\n"
        "特色标签 [严格约束]：必须同时返回 features_en 和 features_zh 两个数组，绝对禁止使用旧的 features 字段。"
        "生成 3 个简短英文特色标签填入 features_en（每个不超过4个英文单词），"
        "并将这 3 个标签逐一准确翻译为中文，按相同顺序填入 features_zh。\n"
        "不仅如此，基于你对该地标的知识储备，你还必须自动生成它的真实经纬度坐标 (coordinates)。"
        "这些附属数据只需作为 JSON 字段返回，无需在旁白正文中提及或解释。"
    )

    # 构建用户 prompt
    user_prompt = f"游玩路线地标: {', '.join(landmarks)}\nVlog 主题: {theme}\n请为列表中每个地标生成对应的节点信息。"

    # 配置基于 Pydantic 的结构化输出
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=VlogScriptResponse,
        temperature=0.7,
    )

    print(f"[Gemini] 发送剧本生成请求，地标数量: {len(landmarks)}，模型: gemini-2.5-flash")
    
    import asyncio
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=config,
        )
        
        # 返回字典形式以便 FastAPI 序列化
        if response.parsed:
             return response.parsed.model_dump()
        else:
             # Fallback 处理
             parsed_model = VlogScriptResponse.model_validate_json(response.text)
             return parsed_model.model_dump()

    except Exception as e:
        print(f"[Gemini] 剧本生成失败: {e}")
        raise RuntimeError(f"Gemini API 调用失败: {e}")

# ======================== 地理仲裁 Agent ========================

class LandmarkValidationResult(BaseModel):
    """地标双语校验结果"""
    status: str = Field(..., description="valid | corrected | invalid")
    standard_name_en: str = Field(..., description="景点的标准英文名称")
    standard_name_zh: str = Field(..., description="景点的标准中文名称")
    message: str = Field(..., description="给用户的提示信息")


# 简称 → 旅游景点全称映射（防止大模型将缩写误识为军事/其他含义）
_LOCATION_FULL_NAME: dict[str, str] = {
    "USS": "Universal Studios Singapore (Theme Park)",
    "MBS": "Marina Bay Sands Singapore (Hotel & Entertainment Complex)",
    "GARDENS": "Gardens by the Bay Singapore (Nature Park)",
    "SENTOSA": "Sentosa Island Singapore (Beach Resort & Theme Park)",
    "NTU": "Nanyang Technological University Singapore (University Campus)",
    "NUS": "National University of Singapore (University Campus)",
}


def _get_full_location_name(loc_name: str) -> str:
    """Convert location abbreviation to full display name for LLM context."""
    return _LOCATION_FULL_NAME.get(loc_name.upper().strip(), loc_name)


async def validate_landmark_context(landmark_name: str, location_name: str) -> dict:
    """
    调用 Gemini 仲裁：接受中英文单语输入，判断地标是否属于指定地点，
    并强制返回双语标准名称。

    Returns:
        dict with keys: status, standard_name_en, standard_name_zh, message
    """
    if not client:
        return {
            "status": "valid",
            "standard_name_en": landmark_name,
            "standard_name_zh": landmark_name,
            "message": ""
        }

    # 简称扩展：防止大模型将缩写（如 "USS"）误识为军事等其他含义
    full_location_name = _get_full_location_name(location_name)
    if full_location_name != location_name:
        print(f"[Validate] 地点缩写扩展: {location_name!r} → {full_location_name!r}")

    system_instruction = (
        f"你是一个严格的地理校验仲裁员兼景点数据库管理员。"
        f"重要提示：当前地点是名为 [{full_location_name}] 的旅游景点/主题乐园，"
        f"请勿将其与任何军事缩写、航海术语或其他含义混淡。"
        f"用户会提供一个景点名称（可能是中文或英文）和一个地点名称，"
        f"你的任务是：\n"
        f"1. 判断该景点是否属于 [{full_location_name}]。\n"
        f"2. 无论用户只输入了中文还是英文，你必须始终同时返回 standard_name_en（标准英文名）和 standard_name_zh（标准中文名）。\n"
        f"3. 严格按以下规则返回 JSON（只返回 JSON，不含任何解释）：\n"
        f'   - 完全属于且拼写正确：{{"status": "valid", '
        f'"standard_name_en": "标准英文名", "standard_name_zh": "标准中文名", "message": ""}}\n'
        f'   - 有拼写错误/别名/子区域，自动纠正：{{"status": "corrected", '
        f'"standard_name_en": "纠正后标准英文名", "standard_name_zh": "纠正后标准中文名", '
        f'"message": "已自动为您更正为标准名称"}}\n'
        f'   - 与 [{full_location_name}] 完全无关：{{"status": "invalid", '
        f'"standard_name_en": "", "standard_name_zh": "", '
        f'"message": "该地点似乎不在[{full_location_name}]内，您是否想添加：[推荐 2 个该地点著名景点]？"}}'
    )

    user_prompt = f"景点名称：{landmark_name}\n地点：{full_location_name}"

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=LandmarkValidationResult,
        temperature=0.1,
    )

    import asyncio
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=config,
        )
        if response.parsed:
            return response.parsed.model_dump()
        else:
            result = LandmarkValidationResult.model_validate_json(response.text)
            return result.model_dump()
    except Exception as e:
        print(f"[Gemini] 地标校验失败: {e}")
        return {
            "status": "valid",
            "standard_name_en": landmark_name,
            "standard_name_zh": landmark_name,
            "message": ""
        }


async def translate_to_video_prompt(text: str) -> str:
    """
    将用户输入的任何语言的提示词翻译/优化为极简的英文视频提示词。
    """
    if not client:
        print("[Gemini] Client 未初始化，跳过翻译直接返回原本内容。")
        return text

    system_instruction = (
        "你是一个视频提示词翻译专家。无论用户输入什么语言，请将其准确翻译为专供 AI 视频大模型使用的英文提示词"
        "（极简、强调画面和光影）。如果用户输入的已经是英文，请仅做语法优化并直接输出。只输出英文结果，不要包含任何解释。\n\n"
        "【极其重要：图生视频特征保留】\n"
        "因为这段提示词将与一张用户上传的真实照片一起送入视频模型，你的任务是『让照片活过来』，而不是『重新生成画面』。\n"
        "1. 绝对禁止描述人物的长相、性别、穿着或数量（这会导致 AI 重新画人，造成主人公变脸）。\n"
        "2. 只能描述画面中已有元素的『微小动作』和『环境动态』（如水花、树叶、光线、烟雾）。\n"
        "3. 只能描述『镜头运动』（如 slow zoom in, cinematic pan, gentle dolly）。\n"
        "错误示范：'A man and a woman laughing in front of the globe.' （会导致变脸）\n"
        "正确示范：'The subjects in the foreground smile naturally and breathe gently. "
        "The water in the fountain splashes dynamically. Cinematic slow zoom in, golden hour lighting.'\n"
        "请确保你生成的英文 user_video_prompt 严格遵循『只写动作和镜头、绝不写人物特征』的原则。"
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.3,
    )

    import asyncio
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=text,
            config=config,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini] 翻译提示词失败: {e}")
        return text


# ======================== 视频提示词安全卫士 ========================

class VideoPromptGuardrailResult(BaseModel):
    """视频提示词安全检查结果"""
    status: Literal["safe", "unsafe"] = Field(..., description="safe | unsafe")
    message: str = Field(..., description="给用户看的风险说明（safe 时为空）")
    suggested_prompt: str = Field(..., description="优化后的安全英文提示词（safe 时为空）")


async def validate_and_enhance_video_prompt(prompt: str) -> dict:
    """
    检查视频 Prompt 是否包含 Veo 可能拦截的敏感词汇。
    如果安全直接通过，如果不安全则返回优化建议。
    """
    if not client:
        return {"status": "safe", "message": "", "suggested_prompt": ""}

    system_instruction = (
        "你是一个 AI 视频安全与法务合规专家，负责双重审查：\n\n"

        "【第一关：安全/危险词汇拦截】\n"
        "Veo 视频模型会严格拦截包含以下类别词汇的提示词：\n"
        "暴力动作（fight, punch, attack, kill, shoot）、危险坠落（drop, fall, crash, collapse）、"
        "灾难场景（explosion, disaster, fire, flood）、极速危险（speeding, racing, crash）、"
        "恐怖元素（terrifying, horror, scary, blood）。\n\n"

        "【第二关：版权与商标 (IP) 清洗 — 极其重要】\n"
        "Veo 视频模型会因『第三方内容提供商利益』而拒绝生成包含任何受版权保护实体名称的视频。\n"
        "绝对禁止使用以下及类似品牌、IP、角色名称（包括但不限于）：\n"
        "Universal Studios, Jurassic Park, Transformers, Minions, Shrek, Harry Potter, "
        "Disney, Marvel, Star Wars, Hello Kitty, Nintendo, Pokémon, Battlestar Galactica, "
        "DreamWorks, Paramount, Warner Bros 等以及任何其旗下角色或主题场景名称。\n"
        "替代方案：将其改写为『通用的场景描述 (Generic Description)』，保留场景主题但移除品牌标识。\n"
        "  错误示范：'A shot of the Universal Studios globe.' → "
        "正确示范：'A giant spinning cinematic globe monument in a theme park.'\n"
        "  错误示范：'A Jurassic Park rapid ride.' → "
        "正确示范：'A prehistoric tropical dinosaur jungle adventure ride.'\n"
        "  错误示范：'Minions characters dancing.' → "
        "正确示范：'Small yellow cartoon-like figures joyfully dancing in a colorful plaza.'\n\n"

        "【判断逻辑】\n"
        "请检查用户输入的 Prompt，任意一关触发均判定为 unsafe：\n"
        "1. 如果完全安全（两关均通过），返回 JSON: "
        '{\"status\": \"safe\", \"message\": \"\", \"suggested_prompt\": \"\"}\n'
        "2. 如果存在风险（任意一关触发），将提示词改写为安全、去 IP 化、电影感的通用英文描述，"
        "返回 JSON: "
        '{\"status\": \"unsafe\", \"message\": \"您的提示词包含可能被视频引擎拦截的敏感/版权内容，已为您自动优化。\", '
        '\"suggested_prompt\": \"改写后去 IP 化且具有电影感的英文提示词\"}'
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=VideoPromptGuardrailResult,
        temperature=0.1,
    )

    import asyncio
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=f"请检查以下视频 Prompt：\n{prompt}",
            config=config,
        )
        if response.parsed:
            return response.parsed.model_dump()
        result = VideoPromptGuardrailResult.model_validate_json(response.text)
        return result.model_dump()
    except Exception as e:
        print(f"[Gemini] 视频提示词校验失败（降级放行）: {e}")
        return {"status": "safe", "message": "", "suggested_prompt": ""}
