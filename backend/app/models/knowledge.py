from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Knowledge(Base):
    """统一知识库"""
    __tablename__ = "geo_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True, default=1)
    title = Column(String(500), nullable=False)
    category = Column(String(50), default="company")  # company/business/tech/case/qualification/team
    level = Column(String(20), default="public")  # public/internal/confidential
    content = Column(Text, default="")
    version = Column(Integer, default=1)
    tags = Column(String(500), default="")
    status = Column(Boolean, default=True)
    embedding = Column(Text, default="")  # 向量
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
