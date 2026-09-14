"""
生图适配器抽象基类
定义所有生图平台适配器的统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ImageResult:
    """生图结果"""
    success: bool
    image_urls: List[str] = field(default_factory=list)
    task_id: Optional[str] = None
    status: str = "pending"  # pending/running/succeeded/failed
    error_message: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    raw_response: Optional[dict] = None


class BaseImageAdapter(ABC):
    """生图适配器抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ImageResult:
        """
        同步生成图片（阻塞直到完成或超时）

        Args:
            prompt: 生图提示词
            **kwargs: 其他参数（width, height, n, style 等）

        Returns:
            ImageResult: 生图结果
        """
        pass

    @abstractmethod
    def generate_async(self, prompt: str, **kwargs) -> ImageResult:
        """
        异步提交生图任务，立即返回 task_id

        Args:
            prompt: 生图提示词
            **kwargs: 其他参数

        Returns:
            ImageResult: 包含 task_id 的结果（status=pending）
        """
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> ImageResult:
        """
        查询异步生图任务状态

        Args:
            task_id: 异步任务ID

        Returns:
            ImageResult: 任务当前状态和结果
        """
        pass

    def is_configured(self) -> bool:
        """检查适配器是否已配置（API Key 和 Base URL 非空）"""
        return bool(self.api_key and self.base_url)
