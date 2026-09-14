from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class ArticleDistribution(Base):
    """文章分发记录：记录一篇文章发布到了哪些平台"""
    __tablename__ = "geo_article_distribution"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("geo_article_draft.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # 发布平台code
    publish_url = Column(String(500), default="")  # 发布后的URL
    status = Column(String(20), default="published")  # pending/published/failed
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
