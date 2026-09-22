from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from sqlalchemy.sql import func
from app.database import Base


class Platform(Base):
    """AI平台配置表"""
    __tablename__ = "geo_platform"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # glm/minimax/doubao/qwen
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)
    model = Column(String(100), nullable=False)
    status = Column(Boolean, default=True)  # 是否启用
    priority = Column(Integer, default=0, nullable=False)
    timeout = Column(Integer, default=30)
    max_tokens = Column(Integer, default=2000)
    temperature = Column(Float, default=0.3)
    description = Column(String(500), default="")
    platform_type = Column(String(50), default="openai_compatible")
    extra_config = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self, include_api_key=False):
        api_key_masked = self.api_key[:4] + "****" + self.api_key[-4:] if self.api_key else ""
        d = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "base_url": self.base_url,
            "model": self.model,
            "status": self.status,
            "priority": self.priority or 0,
            "timeout": self.timeout or 30,
            "max_tokens": self.max_tokens or 2000,
            "temperature": self.temperature or 0.3,
            "description": self.description or "",
            "platform_type": self.platform_type or "openai_compatible",
            "configured": True,
            "api_key_masked": api_key_masked,
            "source": "db",
        }
        if include_api_key:
            d["api_key"] = self.api_key
        return d
