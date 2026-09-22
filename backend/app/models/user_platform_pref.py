"""用户平台开关表 — 每个用户对每个AI模型的启用/停用"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class UserPlatformPref(Base):
    """用户对AI模型的偏好开关"""
    __tablename__ = "user_platform_pref"
    __table_args__ = (
        UniqueConstraint("user_id", "platform_code", name="uq_user_platform"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    platform_code = Column(String(50), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
