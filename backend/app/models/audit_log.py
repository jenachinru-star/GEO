"""审计日志模型
记录用户关键操作，用于安全审计和操作追溯。
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "geo_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=True, index=True)  # 未登录时为null
    username = Column(String(100), default="")  # 冗余存储用户名，避免关联查询

    # 操作信息
    action = Column(String(50), nullable=False, index=True)  # 操作类型：login/logout/create/update/delete/export/publish/config
    resource_type = Column(String(50), default="")  # 资源类型：user/article/semantic/publish_account/benchmark/platform
    resource_id = Column(String(100), default="")    # 资源ID

    # 详情
    details = Column(Text, default="")  # 操作详情（JSON格式，记录变更前后的值等）
    ip_address = Column(String(50), default="")  # 客户端IP
    user_agent = Column(String(500), default="")  # 客户端User-Agent

    # 结果
    status = Column(String(20), default="success")  # success/failed
    error_message = Column(Text, default="")         # 失败时的错误信息

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index('ix_audit_log_user_action', 'user_id', 'action'),
        Index('ix_audit_log_created_at', 'created_at'),
    )
