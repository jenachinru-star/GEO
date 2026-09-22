from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Question(Base):
    """监测问题库"""
    __tablename__ = "geo_question"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True, default=1)
    question = Column(String(500), nullable=False, index=True)
    category = Column(String(50), default="general")  # brand/tech/competitor/industry/general
    tags = Column(String(500), default="")  # 逗号分隔
    priority = Column(Integer, default=5)  # 1-10，优先级
    status = Column(Boolean, default=True)  # 是否启用监测
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
