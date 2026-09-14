from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ArticleDraft(Base):
    """文章草稿"""
    __tablename__ = "geo_article_draft"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    semantic_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=False, index=True)
    title = Column(String(500), default="")
    content = Column(Text, default="")
    platform = Column(String(50), default="")
    status = Column(String(20), default="draft")  # draft/published
    entity_consistent = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
