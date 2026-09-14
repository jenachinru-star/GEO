from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "geo_user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(500), nullable=False)
    role = Column(String(20), default="doctor")  # admin/doctor/viewer
    status = Column(Boolean, default=True)
    phone = Column(String(20), default="")
    avatar = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
