from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "geo_user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(500), default="")
    role = Column(String(20), default="doctor")  # admin/doctor/viewer
    status = Column(Boolean, default=True)
    phone = Column(String(20), default="")
    avatar = Column(String(500), default="")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
