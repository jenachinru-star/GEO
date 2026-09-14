"""Workspace 模型 — 业务数据归属边界（P0阶段只建表+基础查询，不强制过滤）"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Workspace(Base):
    """工作空间"""
    __tablename__ = "geo_workspace"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), default="")
    type = Column(String(20), default="personal")  # personal/clinic/hospital
    status = Column(String(20), default="active")    # active/suspended/archived
    timezone = Column(String(50), default="Asia/Shanghai")
    locale = Column(String(20), default="zh-CN")
    created_by = Column(Integer, ForeignKey("geo_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkspaceMember(Base):
    """工作空间成员"""
    __tablename__ = "geo_workspace_member"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uix_workspace_user'),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    role = Column(String(20), default="owner")  # owner/editor/reviewer/viewer
    status = Column(String(20), default="active")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
