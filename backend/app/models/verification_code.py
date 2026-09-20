"""验证码数据模型 — 邮箱验证码（注册/重置密码）"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.database import Base


class VerificationCode(Base):
    """邮箱验证码表"""
    __tablename__ = "geo_verification_code"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    type = Column(String(20), nullable=False, default="register")  # register / reset
    expire_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<VerificationCode email={self.email} type={self.type} used={self.used}>"
