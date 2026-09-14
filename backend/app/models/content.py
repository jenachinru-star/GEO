from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.sql import func
from app.database import Base


class Content(Base):
    """内容资产表"""
    __tablename__ = "geo_content"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    category = Column(String(50), default="article")  # article/whitepaper/news/case/tech
    tags = Column(String(500), default="")
    content = Column(Text, default="")  # 内容全文
    summary = Column(String(1000), default="")  # 摘要
    publish_url = Column(String(1000), default="")
    publish_site = Column(String(200), default="")
    publish_time = Column(DateTime(timezone=True), nullable=True)
    citation_count = Column(Integer, default=0)  # 总引用次数
    effect_score = Column(Float, default=0.0)  # 效果评分 0-100
    embedding = Column(Text, default="")  # 向量（JSON数组字符串，SQLite方案）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
