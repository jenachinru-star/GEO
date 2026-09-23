from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """系统配置，从.env文件读取"""

    # 应用配置
    APP_NAME: str = "GEO Monitor"
    APP_ENV: str = "development"
    DEBUG: bool = False
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
    MINIMAX_TIMEOUT: int = 60  # minimax代理不稳定，单独配置超时（秒）

    # 创作工具跳转地址
    ARTICLE_TOOL_URL: str = "https://ops.szcczh.com/paper-next/"
    VIDEO_TOOL_URL: str = "https://video.szcczh.com/"

    # 前端地址（SSO回调跳转用）
    FRONTEND_URL: str = "http://localhost:3000"

    # 豆包（火山方舟 ARK 接入）
    DOUBAO_API_KEY: str = ""
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "doubao-seed-1.6"

    # 通义千问（预留）
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = ""
    QWEN_MODEL: str = ""

    # 监测配置
    MONITOR_TIMES_PER_DAY: int = 3
    MONITOR_TEMPERATURE: float = 0.3
    MONITOR_MAX_TOKENS: int = 2000
    brand_aliases: List[str] = []  # 品牌别名列表，用于AnswerParser解析

    # LLM 配置
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    LLM_TEMPERATURE: float = 0.7

    # 生图配置（Seedream - 火山方舟 ARK 接入）
    SEEDREAM_API_KEY: str = ""
    SEEDREAM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    SEEDREAM_MODEL: str = "doubao-seedream-5-0-pro"

    # 生视频配置（Seedance - 火山方舟 ARK 接入）
    SEEDANCE_API_KEY: str = ""
    SEEDANCE_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    SEEDANCE_MODEL: str = ""

    # IAM单点登录配置
    IAM_HOST: str = "https://iam.szcczh.com"
    IAM_CLIENT_ID: str = ""
    IAM_CLIENT_SECRET: str = ""
    IAM_REDIRECT_URI: str = ""
    JWT_SECRET: str = Field(default="dev-only-insecure-secret-change-me", env="JWT_SECRET")
    JWT_EXPIRE_HOURS: int = 24

    # 发布账号凭证加密密钥
    ENCRYPT_KEY: str = Field(default="", env="ENCRYPT_KEY")

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    # GEO配置
    DEFAULT_SEMANTIC_COUNT: int = 10

    # 模型价格表（人民币元/百万token）
    MODEL_PRICING: dict = {
        "glm/glm-5.3-flash": {"input": 1.0, "output": 4.0},
        "minimax/MiniMax-M2.7-highspeed": {"input": 1.0, "output": 3.0},
        "doubao/ep-20260920202309-ss2fz": {"input": 23.0, "output": 48.0},
        "deepseek/deepseek-chat": {"input": 1.0, "output": 2.0},
    }

    # Resend 邮件服务
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""

    @property
    def is_debug(self) -> bool:
        """根据APP_ENV决定是否开启调试模式（development=True，production=False）"""
        return self.APP_ENV == "development"

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

# 启动检查：JWT_SECRET使用默认值时警告
if settings.JWT_SECRET == "dev-only-insecure-secret-change-me":
    import logging
    logging.getLogger(__name__).warning(
        "⚠️  JWT_SECRET 使用默认值！生产环境必须设置 JWT_SECRET 环境变量"
    )
