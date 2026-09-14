from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Subscription(Base):
    """用户订阅"""
    __tablename__ = "geo_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
    plan = Column(String(20), default="free")  # free/pro
    article_quota_used = Column(Integer, default=0)
    semantic_quota = Column(Integer, default=10)
    paid_semantic_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
