from app.adapters.openai_compatible import OpenAICompatibleAdapter


class DeepSeekAdapter(OpenAICompatibleAdapter):
    """DeepSeek平台适配器 - 继承通用OpenAI兼容适配器"""
    platform_code = "deepseek"
