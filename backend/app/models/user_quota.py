"""用户配额表 — 每月费用限额"""
from sqlalchemy import Column, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class UserQuota(Base):
    """用户月度配额（以费用元为单位）"""
    __tablename__ = "user_quota"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_quota"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    monthly_cost_limit = Column(Float, default=19.9, nullable=False)  # 月费用上限（元），-1=无限
    warn_threshold = Column(Float, default=0.8, nullable=False)  # 预警阈值（占比）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
