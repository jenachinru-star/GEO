"""
发布平台适配器抽象基类
定义所有发布平台的统一接口，和 adapters/（AI平台适配器）同构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    platform_code: str = ""
    external_id: Optional[str] = None  # 平台侧的内容ID
    publish_url: str = ""             # 发布后的访问URL
    failed_reason: str = ""
    raw_response: Optional[dict] = None


class BasePublisher(ABC):
    """发布平台适配器基类"""

    platform_code: str = ""
    platform_name: str = ""
    kind: str = "manual"  # api / rpa / manual
    content_type: str = "article"  # article / video

    @abstractmethod
    def publish(self, title: str, content: str, account: dict, **kwargs) -> PublishResult:
        """发布内容到平台

        Args:
            title: 标题
            content: 正文（文章是markdown，视频是描述文案）
            account: 账号信息（cookie/token等）
            **kwargs: cover_url, tags, video_url 等

        Returns:
            PublishResult: 发布结果
        """
        pass

    @abstractmethod
    def check_status(self, external_id: str, account: dict) -> str:
        """查询发布状态

        Returns:
            str: draft / reviewing / published / failed / removed
        """
        pass

    def get_compliance_rules(self) -> list[str]:
        """获取平台合规规则（用于发布前LLM审查）"""
        return []

    def get_publish_url(self) -> str:
        """获取平台创作页URL（半自动模式：直接跳转）"""
        return ""
