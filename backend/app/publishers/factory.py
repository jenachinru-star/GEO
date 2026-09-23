"""
发布器工厂 - 按平台code路由到对应发布器
和 adapters/factory.py 同构
"""
from typing import Dict, Optional
from app.publishers.base import BasePublisher
from app.publishers._manual import ManualPublisher
from app.publishers.wechat import WechatPublisher
from app.publishers.zhihu import ZhihuPublisher
from app.publishers.baijiahao import BaijiahaoPublisher
from app.publishers.xiaohongshu import XiaohongshuPublisher


# 已接入的发布器注册表
_REGISTRY: Dict[str, type] = {
    "wechat": WechatPublisher,
    "zhihu": ZhihuPublisher,
    "baijiahao": BaijiahaoPublisher,
    "xiaohongshu": XiaohongshuPublisher,
}


class PublisherFactory:
    """发布器工厂"""

    def __init__(self):
        self._publishers: Dict[str, BasePublisher] = {}

    def get_publisher(self, platform_code: str, platform_name: str = "") -> BasePublisher:
        """获取指定平台的发布器，未接入的返回 ManualPublisher 兜底"""
        if platform_code not in self._publishers:
            publisher_cls = _REGISTRY.get(platform_code)
            if publisher_cls:
                self._publishers[platform_code] = publisher_cls()
            else:
                # 未接入的平台用半自动兜底
                self._publishers[platform_code] = ManualPublisher(
                    platform_code=platform_code,
                    platform_name=platform_name,
                )
        return self._publishers[platform_code]

    def get_supported_platforms(self) -> list[str]:
        """获取已真正接入（非兜底）的平台列表"""
        return list(_REGISTRY.keys())


# 全局单例
publisher_factory = PublisherFactory()
