"""
半自动发布器（兜底）
- 不真正调用平台API，返回平台创作页URL供用户手动发布
- 所有未接入真API/RPA的平台都用这个兜底
"""
from app.publishers.base import BasePublisher, PublishResult


class ManualPublisher(BasePublisher):
    """半自动发布器 - 复制内容+跳转平台创作页"""

    kind = "manual"

    # 平台创作页URL映射
    CREATE_URLS = {
        "baijiahao": "https://baijiahao.baidu.com",
        "wechat": "https://mp.weixin.qq.com",
        "zhihu": "https://zhuanlan.zhihu.com/write",
        "xiaohongshu": "https://creator.xiaohongshu.com/publish/publish",
        "douyin": "https://creator.douyin.com",
        "shipinhao": "https://channels.weixin.qqos.com",
    }

    def __init__(self, platform_code: str, platform_name: str = "", content_type: str = "article"):
        self.platform_code = platform_code
        self.platform_name = platform_name or platform_code
        self.content_type = content_type

    def publish(self, title: str, content: str, account: dict, **kwargs) -> PublishResult:
        """半自动模式：不真正发布，返回需要手动操作的提示"""
        return PublishResult(
            success=False,
            platform_code=self.platform_code,
            failed_reason="半自动模式，请手动前往平台创作页发布，发布后粘贴URL回填",
        )

    def check_status(self, external_id: str, account: dict) -> str:
        return "unknown"

    def get_publish_url(self) -> str:
        """返回平台创作页URL"""
        return self.CREATE_URLS.get(self.platform_code, "")

    def get_compliance_rules(self) -> list[str]:
        return []
