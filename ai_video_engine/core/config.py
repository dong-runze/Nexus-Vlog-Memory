"""
core/config.py
读取和校验 .env 环境变量，作为全局配置的唯一入口。
"""

import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv()


class Settings:
    """应用全局配置，从环境变量中读取。"""

    # Google Cloud 配置项
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")

    # 服务端口
    PORT: int = int(os.getenv("PORT", "8000"))

    # API 访问密钥（用于身份验证）
    API_KEY: str = os.getenv("API_KEY", "dev-api-key-12345")

    # CORS 允许的前端源（逗号分隔字符串 -> 列表）
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
    ]

    def validate(self) -> list[str]:
        """
        校验关键配置是否已设置。
        返回缺失配置项名称的列表，空列表表示全部通过。
        """
        missing: list[str] = []
        if not self.GOOGLE_CLOUD_PROJECT:
            missing.append("GOOGLE_CLOUD_PROJECT")
        if not self.GCS_BUCKET_NAME:
            missing.append("GCS_BUCKET_NAME")
        # 由于使用 ADC，GOOGLE_APPLICATION_CREDENTIALS 的存在交给 SDK 去探测
        return missing


# 全局单例
settings = Settings()
