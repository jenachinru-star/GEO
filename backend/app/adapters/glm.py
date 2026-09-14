from app.adapters.openai_compatible import OpenAICompatibleAdapter


class GLMAdapter(OpenAICompatibleAdapter):
    """GLM（智谱清言）平台适配器 - 继承通用OpenAI兼容适配器"""
    platform_code = "glm"
