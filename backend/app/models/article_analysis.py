# -*- coding: utf-8 -*-
"""文章AI分析结果模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class ArticleAnalysis(Base):
    """文章AI分析结果（缓存，避免重复调用LLM）"""
    __tablename__ = "geo_article_analysis"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("geo_wechat_article.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    analysis_type = Column(String(50), default="full")  # full / title / content / interaction / topic
    status = Column(String(20), default="pending")  # pending / processing / completed / failed
    result_json = Column(Text, default="")  # 分析结果（JSON格式）
    failed_reason = Column(Text, default="")
    tokens_used = Column(Integer, default=0)  # 消耗的token数

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_article_analysis_article_type', 'article_id', 'analysis_type', unique=True),
    )
