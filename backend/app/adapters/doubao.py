from app.adapters.openai_compatible import OpenAICompatibleAdapter


class DoubaoAdapter(OpenAICompatibleAdapter):
    """豆包平台适配器 - 火山方舟 ARK 接入，继承通用 OpenAI 兼容适配器

    配置项（.env）：
        DOUBAO_API_KEY   = 火山方舟 API Key
        DOUBAO_BASE_URL  = https://ark.cn-beijing.volces.com/api/v3
        DOUBAO_MODEL     = doubao-seed-1.6（普通对话版，模拟真实用户）
    """
    platform_code = "doubao"
