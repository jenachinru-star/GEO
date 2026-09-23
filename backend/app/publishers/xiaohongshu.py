"""小红书发布器 - 待实现

小红书没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式）。
"""
from app.publishers._manual import ManualPublisher


class XiaohongshuPublisher(ManualPublisher):
    """小红书发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "xiaohongshu"
    platform_name = "小红书"

    def __init__(self):
        super().__init__(platform_code="xiaohongshu", platform_name="小红书")
