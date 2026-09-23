"""百家号发布器 - 待实现

百家号没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式）。
"""
from app.publishers._manual import ManualPublisher


class BaijiahaoPublisher(ManualPublisher):
    """百家号发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "baijiahao"
    platform_name = "百家号"

    def __init__(self):
        super().__init__(platform_code="baijiahao", platform_name="百家号")
