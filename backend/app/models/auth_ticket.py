"""IAM登录ticket数据模型 - 数据库存储（替代内存存储，解决后端重启丢失问题）"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.database import Base


class AuthTicket(Base):
    """IAM登录一次性ticket（数据库存储，后端重启不丢失）"""
    __tablename__ = "geo_auth_ticket"

    id = Column(Integer, primary_key=True, index=True)
    ticket = Column(String(64), unique=True, index=True, nullable=False, comment="一次性ticket")
    jwt_token = Column(Text, nullable=False, comment="换取的JWT token")
    expire_at = Column(DateTime, nullable=False, comment="过期时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<AuthTicket ticket={self.ticket[:8]}... expire={self.expire_at}>"
