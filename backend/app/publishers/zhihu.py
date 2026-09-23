"""知乎发布器 - 待实现

知乎没有官方内容发布API，需要cookie模拟登录。
当前继承ManualPublisher（半自动模式），后续可实现cookie自动发布。
"""
from app.publishers._manual import ManualPublisher


class ZhihuPublisher(ManualPublisher):
    """知乎发布器（当前为半自动模式，待实现自动发布）"""

    platform_code = "zhihu"
    platform_name = "知乎"

    def __init__(self):
        super().__init__(platform_code="zhihu", platform_name="知乎")

    # 后续实现自动发布时，重写 publish() 方法
    # def publish(self, title, content, account, **kwargs):
    #     # 使用account中的cookie调用知乎发布接口
    #     pass
