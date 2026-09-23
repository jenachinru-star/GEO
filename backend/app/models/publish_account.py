"""发布平台账号模型
存储用户在各发布平台的登录凭证（cookie/token）
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class PublishAccount(Base):
    """发布平台账号"""
    __tablename__ = "geo_publish_account"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    # 平台信息
    platform = Column(String(50), nullable=False, index=True)  # baijiahao/wechat/zhihu/douyin...
    account_name = Column(String(200), default="")  # 账号昵称/展示名

    # API密钥类（微信公众号等需要AppID/AppSecret的平台）
    app_id = Column(String(200), default="")  # 应用ID / AppID
    app_secret = Column(String(500), default="")  # 应用密钥 / AppSecret（加密存储）

    # 凭证（加密存储，这里先存明文，后续加密）
    credential = Column(Text, default="")  # cookie 或 access_token

    # 状态
    login_status = Column(String(20), default="unknown")  # valid / expired / needs_captcha
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 备注
    note = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
