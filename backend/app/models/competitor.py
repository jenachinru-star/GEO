from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Competitor(Base):
    """竞品基础表"""
    __tablename__ = "geo_competitor"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    aliases = Column(String(500), default="")  # 别名，逗号分隔
    industry = Column(String(100), default="")
    website = Column(String(500), default="")
    description = Column(Text, default="")
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorRecord(Base):
    """竞品监测记录表"""
    __tablename__ = "geo_competitor_record"

    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("geo_competitor.id"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False)
    platform_code = Column(String(50), nullable=False)
    rank = Column(Integer, default=0)
    mentioned = Column(Boolean, default=False)
    detect_date = Column(String(20), nullable=False, index=True)
    detect_time = Column(DateTime(timezone=True), server_default=func.now())
