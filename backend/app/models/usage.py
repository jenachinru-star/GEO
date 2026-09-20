"""LLM 调用用量日志 — 记录每次 LLM 调用的 token 消耗和成本估算"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from datetime import datetime
from app.database import Base


class LlmUsageLog(Base):
    """LLM 调用用量日志表
    每次 adapter.query() 调用都会写入一条记录（异步批量写入）
    """
    __tablename__ = "geo_llm_usage_log"

    id = Column(Integer, primary_key=True, index=True)

    # ===== 用户归因 =====
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=True, index=True)

    # ===== 平台与模型 =====
    platform = Column(String(50), nullable=False, index=True)   # deepseek / glm / minimax
    model = Column(String(100), nullable=False, index=True)

    # ===== Token 用量 =====
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # ===== 成本估算（元人民币）=====
    # 按 config.MODEL_PRICING 中的单价计算，价格未配置时为 0
    estimated_cost = Column(Float, default=0.0)

    # ===== 业务归因 =====
    task_type = Column(String(50), nullable=True, index=True)
    # geo_collect / semantic_extend / article_gen / rag / llm_analyze / image_gen / other
    ref_id = Column(Integer, nullable=True)        # 关联业务 ID（semantic_id / article_id / task_id）
    ref_type = Column(String(50), nullable=True)   # semantic / article / task / question

    # ===== 调用状态 =====
    success = Column(Boolean, default=True)
    error_type = Column(String(100), nullable=True)
    latency_ms = Column(Integer, default=0)

    # ===== 来源 =====
    source = Column(String(20), default="http")    # http / worker / system

    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "created_at"),
        Index("idx_usage_task_date", "task_type", "created_at"),
        Index("idx_usage_platform_date", "platform", "created_at"),
    )
