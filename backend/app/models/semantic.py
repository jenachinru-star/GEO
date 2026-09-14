from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Semantic(Base):
    """语义库 — 每个语义=一个患者会真实提问的问题"""
    __tablename__ = "geo_semantic"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    question = Column(String(500), nullable=False, index=True)
    category = Column(String(50), default="general")
    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)
    geo_rate = Column(Float, default=0.0)
    aeo_rate = Column(Float, default=0.0)
    article_count = Column(Integer, default=0)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
