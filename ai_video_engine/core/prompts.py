"""
core/prompts.py
游乐园场景的 AI 视频提示词模板。
在实际业务中，根据用户选择的打卡节点和描述文本，
填充模板生成发送给 WaveSpeed AI 的 prompt。
"""


# USS (Universal Studios Singapore) 风格后缀模板
USS_STYLE_SUFFIX = (
    "Universal Studios Singapore style, "
    "highly detailed, 4K cinematic quality, "
    "vibrant colors, cinematic lighting, "
    "theme park atmosphere, joyful mood"
)


def build_video_prompt(node_name: str, user_text: str) -> str:
    """
    根据节点名称和用户描述文本，构建 WaveSpeed AI 视频生成的提示词。

    Args:
        node_name: 打卡节点名称（如 "过山车"、"摩天轮"）
        user_text: 用户自由输入的描述（如 "太刺激了！"）

    Returns:
        拼接完成的英文 prompt 字符串，直接传给 WaveSpeed API。
    """
    base_prompt = (
        f"A cinematic, vibrant vlog-style video clip of a visitor experiencing "
        f"'{node_name}' at a colorful amusement park. "
        f"The mood is: {user_text}. "
        f"Shot in smooth handheld camera style, warm sunlight, joyful atmosphere, "
        f"4K quality, 3 seconds long."
    )
    return base_prompt


def build_uss_video_prompt(user_text: str) -> str:
    """
    构建 USS 风格的视频生成提示词。

    将用户输入的描述与 USS 风格模板结合，生成高质量的
    游乐园主题视频提示词。

    Args:
        user_text: 用户输入的景点描述或介绍文本。

    Returns:
        包含 USS 风格后缀的完整提示词。
    """
    # 清理用户输入，确保不以逗号或句号结尾
    clean_text = user_text.strip().rstrip(",.")
    
    # 拼接 USS 风格后缀
    return f"{clean_text}, {USS_STYLE_SUFFIX}"


# ---------- 可扩展的场景模板 ----------

# 游乐园通用开场模板
INTRO_TEMPLATE = (
    "A sweeping aerial drone shot of a lively amusement park entrance, "
    "colorful banners and crowds, golden hour lighting, cinematic 4K."
)

# 游乐园通用结尾模板
OUTRO_TEMPLATE = (
    "A beautiful sunset timelapse over the amusement park skyline, "
    "ferris wheel silhouette, warm orange and purple tones, cinematic 4K."
)
