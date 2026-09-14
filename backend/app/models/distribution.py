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
    status = Column(String(20), default="draft")  # draft/scheduled/processing/published/failed/removed
    published_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ===== V2 状态机新增字段 =====
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    failed_reason = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    publish_mode = Column(String(20), default="manual")  # manual/auto
    external_task_id = Column(String(100), default="")
    verified_at = Column(DateTime(timezone=True), nullable=True)
