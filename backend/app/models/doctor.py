from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DoctorProfile(Base):
    """医生个人资料（GEO基础数据）"""
    __tablename__ = "geo_doctor_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
    real_name = Column(String(100), nullable=False, default="")
    title = Column(String(100), default="")
    province = Column(String(50), default="")
    city = Column(String(50), default="")
    hospital = Column(String(200), default="")
    department = Column(String(100), default="")
    specialty = Column(String(500), default="")  # 逗号分隔
    awards = Column(Text, default="")
    case_history = Column(Text, default="")
    self_intro_template = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
