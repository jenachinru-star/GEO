from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class MonitorRecord(Base):
    """监测事实表"""
    __tablename__ = "geo_monitor_record"
    __table_args__ = (
        UniqueConstraint('semantic_id', 'platform_code', 'detect_date', 'detect_round', name='uix_semantic_platform_date_round'),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("geo_question.id"), nullable=True, index=True)
    platform_code = Column(String(50), nullable=False, index=True)  # glm/minimax/...
    rank = Column(Integer, default=0)  # 排名，0=未提及
    mentioned = Column(Boolean, default=False)  # 是否提及
    sentiment = Column(Float, default=0.0)  # 情感分 -1~1
    raw_answer = Column(Text, default="")  # 原始回答全文
    detect_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    detect_round = Column(Integer, default=1)  # 当天第几次采样 1/2/3
    detect_time = Column(DateTime(timezone=True), server_default=func.now())
    # GEO/AEO扩展字段
    semantic_id = Column(Integer, nullable=True, index=True)  # 医生维度关联语义ID（冗余，question_id也存这个值）
    detect_type = Column(String(20), default="brand", index=True)  # brand=品牌监测 / doctor=医生GEO/AEO监测
    recommend_count = Column(Integer, default=0)  # GEO：被推荐次数（0或1，单平台单次）
    cite_count = Column(Integer, default=0)  # AEO：被引用次数（0或1）
    aeo_confidence = Column(Float, default=0.0)  # AEO引用置信度 0~1
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ===== V2 证据字段 =====
    mention_evidence = Column(Text, default="")  # 医生命中证据片段
    recommendation_evidence = Column(Text, default="")  # 推荐关系证据
    citation_urls = Column(Text, default="[]")  # 引用URL列表（JSON字符串）
    analyzer_version = Column(String(50), default="rule_v1")  # 分析器版本
    raw_sources_json = Column(Text, default="[]")  # 原始来源数据（JSON字符串）
    is_recommendation = Column(Integer, default=0)  # 是否为推荐（1=是，0=否）
