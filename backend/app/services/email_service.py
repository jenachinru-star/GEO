"""邮件发送服务 — 基于 Resend API

使用 Resend HTTP API 发送邮件，不需要 SMTP 配置。
文档：https://resend.com/docs/api-reference/emails/send-email
"""
import requests
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """邮件发送服务（Resend API）"""

    @staticmethod
    def send_email(to: str, subject: str, text: str, html: Optional[str] = None) -> bool:
        """发送邮件

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            text: 纯文本内容
            html: HTML 内容（可选，优先于 text）

        Returns:
            bool: 是否发送成功
        """
        api_key = getattr(settings, "RESEND_API_KEY", "")
        from_email = getattr(settings, "RESEND_FROM_EMAIL", "GEO <noreply@example.com>")

        if not api_key:
            logger.error("Resend API Key 未配置，无法发送邮件")
            return False

        payload = {
            "from": from_email,
            "to": [to],
            "subject": subject,
        }

        if html:
            payload["html"] = html
        else:
            payload["text"] = text

        try:
            resp = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )

            if resp.status_code == 200 or resp.status_code == 201:
                logger.info(f"邮件发送成功: to={to}, subject={subject}")
                return True
            else:
                logger.error(f"邮件发送失败: status={resp.status_code}, body={resp.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"邮件发送异常: {e}")
            return False

    @staticmethod
    def send_verification_code(email: str, code: str, code_type: str = "register") -> bool:
        """发送验证码邮件

        Args:
            email: 收件人邮箱
            code: 6 位验证码
            code_type: 类型（register/reset）

        Returns:
            bool: 是否发送成功
        """
        type_text = "注册" if code_type == "register" else "重置密码"
        subject = f"【GEO 创作者中心】您的{type_text}验证码是 {code}"

        text = f"""
您的验证码是：{code}

5 分钟内有效，请勿泄露给他人。
如非本人操作，请忽略此邮件。

—— GEO 创作者中心
"""

        html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 24px; font-weight: bold; color: #1677ff;">GEO 创作者中心</div>
    </div>
    <div style="background: #f5f7fa; border-radius: 12px; padding: 30px; text-align: center;">
        <div style="font-size: 16px; color: #333; margin-bottom: 20px;">您的{type_text}验证码是</div>
        <div style="font-size: 36px; font-weight: bold; color: #1677ff; letter-spacing: 8px; margin-bottom: 20px;">{code}</div>
        <div style="font-size: 14px; color: #999;">5 分钟内有效，请勿泄露给他人</div>
    </div>
    <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #ccc;">
        如非本人操作，请忽略此邮件
    </div>
</div>
"""

        return EmailService.send_email(email, subject, text, html)


# 全局单例
email_service = EmailService()
