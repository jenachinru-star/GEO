from typing import Dict, Optional, List
from app.adapters.base import BaseAdapter
from app.adapters.deepseek import DeepSeekAdapter
from app.adapters.glm import GLMAdapter
from app.adapters.minimax import MiniMaxAdapter
from app.adapters.doubao import DoubaoAdapter
from app.adapters.image_base import BaseImageAdapter
from app.adapters.image_seedream import SeedreamImageAdapter
from app.adapters.video_base import BaseVideoAdapter
from app.adapters.video_seedance import SeedanceVideoAdapter
from app.config import settings


class AdapterFactory:
    """平台适配器工厂 - 单例管理所有平台适配器"""

    _instance = None
    _adapters: Dict[str, BaseAdapter] = {}
    _image_adapter: Optional[BaseImageAdapter] = None
    _video_adapter: Optional[BaseVideoAdapter] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_adapters()
            cls._instance._init_image_adapter()
            cls._instance._init_video_adapter()
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

        # 豆包（火山方舟 ARK 接入）
        if settings.DOUBAO_API_KEY and settings.DOUBAO_BASE_URL:
            self._adapters["doubao"] = DoubaoAdapter(
                api_key=settings.DOUBAO_API_KEY,
                base_url=settings.DOUBAO_BASE_URL,
                model=settings.DOUBAO_MODEL or "doubao-seed-1.6",
                temperature=settings.MONITOR_TEMPERATURE,
                max_tokens=settings.MONITOR_MAX_TOKENS
            )

    def get_adapter(self, platform_code: str) -> Optional[BaseAdapter]:
        """获取指定平台的适配器"""
        return self._adapters.get(platform_code)

    def _init_image_adapter(self):
        """初始化生图适配器"""
        if settings.SEEDREAM_API_KEY and settings.SEEDREAM_BASE_URL:
            self._image_adapter = SeedreamImageAdapter(
                api_key=settings.SEEDREAM_API_KEY,
                base_url=settings.SEEDREAM_BASE_URL,
                model=settings.SEEDREAM_MODEL or "doubao-seedream-5-0-pro",
            )

    def get_image_adapter(self) -> Optional[BaseImageAdapter]:
        """获取生图适配器（已配置时返回，否则返回 None）"""
        return self._image_adapter

    def is_image_configured(self) -> bool:
        """检查生图功能是否已配置"""
        return self._image_adapter is not None and self._image_adapter.is_configured()

    def _init_video_adapter(self):
        """初始化生视频适配器"""
        if settings.SEEDANCE_API_KEY and settings.SEEDANCE_BASE_URL:
            self._video_adapter = SeedanceVideoAdapter(
                api_key=settings.SEEDANCE_API_KEY,
                base_url=settings.SEEDANCE_BASE_URL,
                model=settings.SEEDANCE_MODEL or "",
            )

    def get_video_adapter(self) -> Optional[BaseVideoAdapter]:
        """获取生视频适配器（已配置时返回，否则返回 None）"""
        return self._video_adapter

    def is_video_configured(self) -> bool:
        """检查生视频功能是否已配置"""
        return self._video_adapter is not None and self._video_adapter.is_configured()

    def get_all_adapters(self) -> Dict[str, BaseAdapter]:
        """获取所有已启用的适配器"""
        return self._adapters

    def get_enabled_platforms(self) -> List[str]:
        """获取已启用的平台列表"""
        return list(self._adapters.keys())

    def reload(self):
        """重新加载适配器（配置变更后调用）"""
        self._adapters = {}
        self._image_adapter = None
        self._video_adapter = None
        self._init_adapters()
        self._init_image_adapter()
        self._init_video_adapter()


# 全局单例
adapter_factory = AdapterFactory()
