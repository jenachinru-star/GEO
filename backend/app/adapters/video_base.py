"""
视频生成适配器抽象基类
定义所有视频生成平台的统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class VideoResult:
    """视频生成结果"""
    success: bool
    video_urls: List[str] = field(default_factory=list)
    task_id: Optional[str] = None
    status: str = "pending"  # pending/running/succeeded/failed
    error_message: Optional[str] = None
    duration: Optional[int] = None  # 视频时长（秒）
    raw_response: Optional[dict] = None


class BaseVideoAdapter(ABC):
    """视频生成适配器抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def generate_async(self, prompt: str, **kwargs) -> VideoResult:
        """
        异步提交视频生成任务，立即返回 task_id

        Args:
            prompt: 视频描述提示词
            **kwargs: image_url（图生视频）, duration, resolution 等

        Returns:
            VideoResult: 包含 task_id 的结果（status=pending）
        """
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> VideoResult:
        """
        查询异步视频生成任务状态

        Args:
            task_id: 异步任务ID

        Returns:
            VideoResult: 任务当前状态和结果
        """
        pass

    def is_configured(self) -> bool:
        """检查适配器是否已配置"""
        return bool(self.api_key and self.base_url)
