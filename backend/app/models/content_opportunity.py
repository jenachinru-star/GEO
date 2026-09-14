"""内容机会模型 — 从监测数据中识别的内容创作机会"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ContentOpportunity(Base):
    __tablename__ = "geo_content_opportunity"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=True, index=True)
    doctor_id = Column(Integer, ForeignKey("geo_doctor_profile.id"), nullable=True, index=True)
    question_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=False, index=True)
    opportunity_type = Column(String(30), nullable=False, index=True)
    # missing_mention: AI未提及医生
    # missing_citation: 有提及但无来源引用
    # low_rank: 排名靠后
    priority_score = Column(Float, default=0.0)  # 0-100
    evidence_json = Column(Text, default="{}")    # 证据数据
    status = Column(String(20), default="open", index=True)
    # open/planned/done/dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
