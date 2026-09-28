"""竞品对比分析结果模型（缓存AI分析结果，避免重复调用LLM）"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class CompetitorAnalysis(Base):
    """竞品对比分析结果"""
    __tablename__ = "geo_competitor_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)  # 自己的公众号账号
    benchmark_id = Column(Integer, ForeignKey("geo_benchmark_account.id"), nullable=False, index=True)  # 对标账号

    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    result_json = Column(Text, default="")  # 分析结果（JSON格式）
    failed_reason = Column(Text, default="")
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_competitor_analysis_account_benchmark', 'account_id', 'benchmark_id', unique=True),
    )
