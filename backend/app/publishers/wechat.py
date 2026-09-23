"""微信公众号发布器 - 官方API

使用微信公众平台官方API发布图文消息。
需要用户在发布账号中配置 AppID 和 AppSecret。

API文档：
- 获取access_token: https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
- 新增永久图文素材: https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Permanent_Assets.html
- 发布接口: https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html
"""
import logging
import requests
from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)

WECHAT_API_BASE = "https://api.weixin.qq.com"


class WechatPublisher(BasePublisher):
    """微信公众号发布器"""

    platform_code = "wechat"
    platform_name = "微信公众号"
    kind = "api"

    def _get_access_token(self, app_id: str, app_secret: str) -> str:
        """获取access_token"""
        url = f"{WECHAT_API_BASE}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "access_token" not in data:
            raise ValueError(f"获取access_token失败: {data}")
        return data["access_token"]

    def _upload_news(self, access_token: str, title: str, content: str,
                     author: str = "", digest: str = "") -> str:
        """新增永久图文素材，返回media_id"""
        url = f"{WECHAT_API_BASE}/cgi-bin/material/add_news"
        params = {"access_token": access_token}

        # 内容简单处理：纯文本转HTML，HTML保留
        if not content.startswith("<"):
            html_content = content.replace("\n", "<br/>")
        else:
            html_content = content

        article = {
            "title": title,
            "author": author,
            "digest": digest or title[:100],  # 摘要，最多120字
            "content": html_content,
            "content_source_url": "",  # 原文链接
            "thumb_media_id": "",  # 封面图media_id（需先上传图片，暂留空用默认封面）
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }

        payload = {"articles": [article]}
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if "media_id" not in data:
            raise ValueError(f"上传图文素材失败: {data}")
        return data["media_id"]

    def _submit_publish(self, access_token: str, media_id: str) -> str:
        """发布接口，返回publish_id"""
        url = f"{WECHAT_API_BASE}/cgi-bin/freepublish/submit"
        params = {"access_token": access_token}
        payload = {"media_id": media_id}
        resp = requests.post(url, params=params, json=payload, timeout=30)
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise ValueError(f"发布失败: {data}")
        return data.get("publish_id", "")

    def _get_publish_status(self, access_token: str, publish_id: str) -> dict:
        """查询发布状态（微信发布是异步的）"""
        url = f"{WECHAT_API_BASE}/cgi-bin/freepublish/get"
        params = {"access_token": access_token}
        payload = {"publish_id": publish_id}
        resp = requests.post(url, params=params, json=payload, timeout=10)
        return resp.json()

    def publish(self, title: str, content: str, account: dict, **kwargs) -> PublishResult:
        """发布文章到微信公众号

        Args:
            title: 文章标题
            content: 文章内容（纯文本或HTML）
            account: 账号信息，需包含 app_id 和 app_secret
            **kwargs: 可选参数，author/digest等

        Returns:
            PublishResult: 发布结果
        """
        try:
            app_id = account.get("app_id", "")
            app_secret = account.get("app_secret", "")

            if not app_id or not app_secret:
                return PublishResult(
                    success=False,
                    platform_code=self.platform_code,
                    failed_reason="微信公众号未配置AppID和AppSecret，请在发布账号中完善配置",
                )

            author = kwargs.get("author", "")
            digest = kwargs.get("digest", "")

            # 1. 获取access_token
            logger.info("微信公众号发布：获取access_token")
            access_token = self._get_access_token(app_id, app_secret)

            # 2. 上传图文素材
            logger.info(f"微信公众号发布：上传图文素材 title={title[:30]}")
            media_id = self._upload_news(access_token, title, content, author, digest)

            # 3. 提交发布
            logger.info(f"微信公众号发布：提交发布 media_id={media_id}")
            publish_id = self._submit_publish(access_token, media_id)

            # 微信发布是异步的，publish_id可用于查询状态
            # 文章URL需要通过发布状态查询获取，这里先返回占位
            article_url = ""

            return PublishResult(
                success=True,
                platform_code=self.platform_code,
                external_id=publish_id,
                publish_url=article_url,
                raw_response={
                    "publish_id": publish_id,
                    "media_id": media_id,
                    "message": "微信公众号发布成功（发布后可能需要几分钟生效，文章URL需通过publish_id查询获取）",
                },
            )

        except Exception as e:
            logger.error(f"微信公众号发布失败: {e}")
            return PublishResult(
                success=False,
                platform_code=self.platform_code,
                failed_reason=str(e),
            )

    def check_status(self, external_id: str, account: dict) -> str:
        """查询发布状态（实现BasePublisher抽象方法）

        Returns:
            str: draft / reviewing / published / failed / removed
        """
        try:
            app_id = account.get("app_id", "")
            app_secret = account.get("app_secret", "")
            if not app_id or not app_secret or not external_id:
                return "unknown"

            access_token = self._get_access_token(app_id, app_secret)
            data = self._get_publish_status(access_token, external_id)

            # 微信发布状态：0=成功, 1=发布中, 2=失败, 3=原创审核中
            publish_status = data.get("publish_status", -1)
            if publish_status == 0:
                return "published"
            elif publish_status == 1 or publish_status == 3:
                return "reviewing"
            elif publish_status == 2:
                return "failed"
            else:
                return "unknown"
        except Exception as e:
            logger.error(f"查询微信发布状态失败: {e}")
            return "unknown"
