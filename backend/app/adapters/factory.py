from typing import Dict, Optional, List
from app.adapters.base import BaseAdapter
from app.adapters.deepseek import DeepSeekAdapter
from app.adapters.glm import GLMAdapter
from app.adapters.minimax import MiniMaxAdapter
from app.config import settings


class AdapterFactory:
    """平台适配器工厂 - 单例管理所有平台适配器"""

    _instance = None
    _adapters: Dict[str, BaseAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_adapters()
        return cls._instance

    def _init_adapters(self):
        """初始化所有已配置的平台适配器"""
        # DeepSeek
        if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_BASE_URL:
            self._adapters["deepseek"] = DeepSeekAdapter(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
                temperature=settings.MONITOR_TEMPERATURE,
                max_tokens=settings.MONITOR_MAX_TOKENS
            )

        # GLM
        if settings.GLM_API_KEY and settings.GLM_BASE_URL:
            self._adapters["glm"] = GLMAdapter(
                api_key=settings.GLM_API_KEY,
                base_url=settings.GLM_BASE_URL,
                model=settings.GLM_MODEL,
                temperature=settings.MONITOR_TEMPERATURE,
                max_tokens=settings.MONITOR_MAX_TOKENS
            )

        # MiniMax
        if settings.MINIMAX_API_KEY and settings.MINIMAX_BASE_URL:
            self._adapters["minimax"] = MiniMaxAdapter(
                api_key=settings.MINIMAX_API_KEY,
                base_url=settings.MINIMAX_BASE_URL,
                model=settings.MINIMAX_MODEL,
                temperature=settings.MONITOR_TEMPERATURE,
                max_tokens=settings.MONITOR_MAX_TOKENS
            )

    def get_adapter(self, platform_code: str) -> Optional[BaseAdapter]:
        """获取指定平台的适配器"""
        return self._adapters.get(platform_code)

    def get_all_adapters(self) -> Dict[str, BaseAdapter]:
        """获取所有已启用的适配器"""
        return self._adapters

    def get_enabled_platforms(self) -> List[str]:
        """获取已启用的平台列表"""
        return list(self._adapters.keys())

    def reload(self):
        """重新加载适配器（配置变更后调用）"""
        self._adapters = {}
        self._init_adapters()


# 全局单例
adapter_factory = AdapterFactory()
