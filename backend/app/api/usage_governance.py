"""用量治理 API — 用户平台开关 + 配额管理 + 用量报表"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.adapters import adapter_factory
from app.models.user import User
from app.models.user_platform_pref import UserPlatformPref
from app.models.user_quota import UserQuota
from app.models.usage import LlmUsageLog
from app.services.quota_checker import ensure_user_quota, get_monthly_cost, DEFAULT_QUOTA

router = APIRouter(prefix="/api/v1/usage", tags=["用量治理"])


# ============ 辅助函数 ============

def _is_admin(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    return user and user.role == "admin"


def _require_admin(db: Session, user_id: int):
    if not _is_admin(db, user_id):
        raise HTTPException(status_code=403, detail="需要管理员权限")


# ============ 用户端：平台开关 ============

@router.get("/platforms/available", summary="获取可用AI平台列表（含用户开关状态）")
def get_available_platforms(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """返回系统已配置的所有AI平台，以及当前用户对各平台的启用状态"""
    enabled_platforms = adapter_factory.get_enabled_platforms()

    # 用户已有的开关记录
    prefs = db.query(UserPlatformPref).filter(
        UserPlatformPref.user_id == user_id
    ).all()
    pref_map = {p.platform_code: p.enabled for p in prefs}

    items = []
    for code in enabled_platforms:
        items.append({
            "platform_code": code,
            "enabled": pref_map.get(code, True),  # 默认启用
        })

    return {"code": 0, "message": "success", "data": {"platforms": items}}


@router.get("/platforms/pref", summary="获取我的平台开关偏好")
def get_my_pref(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取当前用户对各平台的启用/停用"""
    prefs = db.query(UserPlatformPref).filter(
        UserPlatformPref.user_id == user_id
    ).all()
    items = [{
        "platform_code": p.platform_code,
        "enabled": p.enabled,
    } for p in prefs]
    return {"code": 0, "message": "success", "data": {"prefs": items}}


@router.put("/platforms/pref", summary="更新我的平台开关偏好")
def update_my_pref(
    data: dict,  # {"platform_code": "glm", "enabled": true}
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """更新单个平台的开关"""
    platform_code = data.get("platform_code")
    enabled = data.get("enabled")
    if not platform_code or enabled is None:
        raise HTTPException(status_code=400, detail="platform_code 和 enabled 必填")

    pref = db.query(UserPlatformPref).filter(
        UserPlatformPref.user_id == user_id,
        UserPlatformPref.platform_code == platform_code,
    ).first()

    if pref:
        pref.enabled = enabled
    else:
        pref = UserPlatformPref(
            user_id=user_id,
            platform_code=platform_code,
            enabled=enabled,
        )
        db.add(pref)
    db.commit()

    return {"code": 0, "message": "success", "data": {"platform_code": platform_code, "enabled": enabled}}


# ============ 用户端：我的配额 ============

@router.get("/quota/my", summary="获取我的配额和当月用量")
def get_my_quota(
    target_user_id: Optional[int] = Query(None, description="管理员可指定查看的用户ID"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """当前用户的配额 + 当月费用 + 各平台用量明细
    管理员可传 target_user_id 查看指定用户的用量；普通用户忽略该参数。
    """
    is_admin = _is_admin(db, user_id)

    # 管理员可切换查看目标用户，普通用户只能看自己
    view_user_id = user_id
    if is_admin and target_user_id and target_user_id != user_id:
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        view_user_id = target_user_id

    quota = ensure_user_quota(db, view_user_id)
    used = get_monthly_cost(db, view_user_id)

    # 管理员查看自己时不限额，查看其他用户时显示该用户的配额
    if is_admin and view_user_id == user_id:
        limit = -1
        pct = 0
    else:
        limit = quota.monthly_cost_limit
        pct = round(used / limit * 100, 1) if limit and limit > 0 else 0

    # 各平台当月用量（按view_user_id统计）
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(
        LlmUsageLog.platform,
        func.sum(LlmUsageLog.total_tokens).label("tokens"),
        func.sum(LlmUsageLog.estimated_cost).label("cost"),
    ).filter(
        LlmUsageLog.user_id == view_user_id,
        LlmUsageLog.created_at >= month_start,
    ).group_by(LlmUsageLog.platform).all()

    by_platform = [{
        "platform": r.platform,
        "tokens": int(r.tokens or 0),
        "cost": round(float(r.cost or 0), 4),
    } for r in rows]

    # 获取目标用户信息（用于前端显示）
    target_user_info = None
    if view_user_id != user_id:
        tu = db.query(User).filter(User.id == view_user_id).first()
        if tu:
            target_user_info = {"user_id": tu.id, "username": tu.username, "email": tu.email or ""}

    return {"code": 0, "message": "success", "data": {
        "monthly_limit": limit,
        "used_cost": round(used, 4),
        "usage_pct": pct,
        "warn_threshold": quota.warn_threshold,
        "is_admin": is_admin,
        "by_platform": by_platform,
        "view_user_id": view_user_id,
        "target_user": target_user_info,
    }}


# ============ 管理员：全量配额管理 ============

@router.get("/quota/admin/users", summary="管理员：所有用户配额列表")
def admin_list_users_quota(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """列出所有用户的配额和当月用量"""
    _require_admin(db, user_id)

    users = db.query(User).all()
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = []
    for u in users:
        quota = db.query(UserQuota).filter(UserQuota.user_id == u.id).first()
        used = db.query(func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0.0)).filter(
            LlmUsageLog.user_id == u.id,
            LlmUsageLog.created_at >= month_start,
        ).scalar()
        limit = quota.monthly_cost_limit if quota else DEFAULT_QUOTA
        result.append({
            "user_id": u.id,
            "username": u.username,
            "email": u.email or "",
            "role": u.role,
            "monthly_limit": limit,
            "used_cost": round(float(used or 0), 4),
            "usage_pct": round(float(used or 0) / limit * 100, 1) if limit and limit > 0 else 0,
        })

    # 按用量降序
    result.sort(key=lambda x: x["used_cost"], reverse=True)
    return {"code": 0, "message": "success", "data": {"users": result}}


@router.put("/quota/admin/{target_user_id}", summary="管理员：修改用户配额")
def admin_update_quota(
    target_user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """管理员修改指定用户的月费用限额（-1=无限）"""
    _require_admin(db, user_id)

    new_limit = data.get("monthly_cost_limit")
    if new_limit is None:
        raise HTTPException(status_code=400, detail="monthly_cost_limit 必填")

    quota = db.query(UserQuota).filter(UserQuota.user_id == target_user_id).first()
    if not quota:
        quota = UserQuota(user_id=target_user_id, monthly_cost_limit=new_limit)
        db.add(quota)
    else:
        quota.monthly_cost_limit = new_limit
    db.commit()

    return {"code": 0, "message": "success", "data": {"user_id": target_user_id, "monthly_limit": new_limit}}


# ============ 管理员：用量交叉报表 ============

@router.get("/admin/user-platform", summary="管理员：用户×平台用量交叉报表")
def admin_usage_report(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """所有用户在各平台的当月token和费用"""
    _require_admin(db, user_id)

    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = db.query(
        LlmUsageLog.user_id,
        User.username,
        LlmUsageLog.platform,
        func.sum(LlmUsageLog.total_tokens).label("tokens"),
        func.sum(LlmUsageLog.estimated_cost).label("cost"),
    ).join(
        User, User.id == LlmUsageLog.user_id
    ).filter(
        LlmUsageLog.created_at >= month_start,
        LlmUsageLog.user_id.isnot(None),
    ).group_by(
        LlmUsageLog.user_id, User.username, LlmUsageLog.platform
    ).all()

    items = [{
        "user_id": r.user_id,
        "username": r.username,
        "platform": r.platform,
        "tokens": int(r.tokens or 0),
        "cost": round(float(r.cost or 0), 4),
    } for r in rows]

    return {"code": 0, "message": "success", "data": {"items": items}}


# ============ 管理员：用户角色管理 ============

@router.get("/admin/users", summary="管理员：列出所有用户（含角色）")
def admin_list_users(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """管理员列出所有用户"""
    _require_admin(db, user_id)
    users = db.query(User).order_by(User.id.asc()).all()
    items = [{
        "user_id": u.id,
        "username": u.username,
        "email": u.email or "",
        "role": u.role,
        "status": u.status,
    } for u in users]
    return {"code": 0, "message": "success", "data": {"users": items}}


@router.put("/admin/users/{target_user_id}/role", summary="管理员：修改用户角色")
def admin_change_role(
    target_user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """管理员修改用户角色（admin <-> doctor）"""
    _require_admin(db, user_id)

    new_role = data.get("role")
    if new_role not in ("admin", "doctor"):
        raise HTTPException(status_code=400, detail="role 必须是 admin 或 doctor")

    # 不能改自己
    if target_user_id == user_id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 如果是降级最后一个 admin，禁止
    if target.role == "admin" and new_role == "doctor":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="不能降级最后一个管理员")

    target.role = new_role
    db.commit()
    return {"code": 0, "message": "success", "data": {
        "user_id": target.id, "username": target.username, "role": new_role
    }}
