from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """系统配置，从.env文件读取"""

    # 应用配置
    APP_NAME: str = "GEO Monitor"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "geo-monitor-secret-key"

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/geo.db"

    # DeepSeek（API Key已失效，留空则显示"暂未配置"）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # GLM
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = ""
    GLM_MODEL: str = "glm-4-flash"

    # MiniMax
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2.7-highspeed"

    # 创作工具跳转地址
    ARTICLE_TOOL_URL: str = "https://ops.szcczh.com/paper-next/"
    VIDEO_TOOL_URL: str = "https://video.szcczh.com/"

    # 豆包（预留）
    DOUBAO_API_KEY: str = ""
    DOUBAO_BASE_URL: str = ""
    DOUBAO_MODEL: str = ""

    # 通义千问（预留）
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = ""
    QWEN_MODEL: str = ""

    # 监测配置
    MONITOR_TIMES_PER_DAY: int = 3
    MONITOR_TEMPERATURE: float = 0.3
    MONITOR_MAX_TOKENS: int = 2000

    # IAM单点登录配置
    IAM_HOST: str = "https://iam.szcczh.com"
    IAM_CLIENT_ID: str = ""
    IAM_CLIENT_SECRET: str = ""
    IAM_REDIRECT_URI: str = ""
    JWT_SECRET: str = "geo-monitor-jwt-secret"
    JWT_EXPIRE_HOURS: int = 24

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    # GEO配置
    DEFAULT_SEMANTIC_COUNT: int = 10

    @property
    def iam_enabled(self) -> bool:
        """IAM是否已配置"""
        return bool(self.IAM_CLIENT_ID and self.IAM_CLIENT_SECRET and self.IAM_REDIRECT_URI)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_enabled_platforms(self) -> List[str]:
        """获取已配置API Key的平台列表"""
        platforms = []
        if self.DEEPSEEK_API_KEY and self.DEEPSEEK_BASE_URL:
            platforms.append("deepseek")
        if self.GLM_API_KEY and self.GLM_BASE_URL:
            platforms.append("glm")
        if self.MINIMAX_API_KEY and self.MINIMAX_BASE_URL:
            platforms.append("minimax")
        if self.DOUBAO_API_KEY and self.DOUBAO_BASE_URL and self.DOUBAO_MODEL:
            platforms.append("doubao")
        if self.QWEN_API_KEY and self.QWEN_BASE_URL and self.QWEN_MODEL:
            platforms.append("qwen")
        return platforms


settings = Settings()
