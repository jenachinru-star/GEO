"""审计日志API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.audit_log import AuditLog
from app.models.user import User
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])


@router.get("", summary="获取审计日志列表")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int = Query(None, description="按用户筛选（管理员可用）"),
    action: str = Query(None, description="按操作类型筛选"),
    resource_type: str = Query(None, description="按资源类型筛选"),
    start_date: str = Query(None, description="开始日期（YYYY-MM-DD）"),
    end_date: str = Query(None, description="结束日期（YYYY-MM-DD）"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    # 普通用户只能查看自己的日志，管理员可查看所有
    query = db.query(AuditLog)

    # 检查是否是管理员
    current_user = db.query(User).filter(User.id == current_user_id).first()
    is_admin = current_user and current_user.role == "admin"

    if not is_admin:
        query = query.filter(AuditLog.user_id == current_user_id)
    elif user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditLog.created_at <= datetime.fromisoformat(end_date) + timedelta(days=1))

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [{
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in logs]

    return {"code": 0, "message": "success", "data": {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "is_admin": is_admin,
    }}


@router.get("/actions", summary="获取操作类型列表")
def get_action_types():
    """获取所有操作类型（用于筛选下拉框）"""
    actions = [
        {"value": "login", "label": "登录"},
        {"value": "logout", "label": "登出"},
        {"value": "create", "label": "创建"},
        {"value": "update", "label": "更新"},
        {"value": "delete", "label": "删除"},
        {"value": "publish", "label": "发布"},
        {"value": "export", "label": "导出"},
        {"value": "config", "label": "配置修改"},
    ]
    return {"code": 0, "message": "success", "data": {"items": actions}}
