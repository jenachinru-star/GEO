"""LLM 用量统计 API — 运营看板数据接口

提供：
- 总览统计（总 token、总成本、调用次数、今日消耗）
- 按日期趋势
- 按任务类型分布
- 按平台对比
- 按用户排行
- 详细日志列表（分页）

注意：第一阶段暂未加管理员权限校验，后续应限制仅 admin 可访问。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.deps import get_current_admin_id, get_current_user_id
from app.models.usage import LlmUsageLog
from app.models.user import User

router = APIRouter(prefix="/api/v1/usage", tags=["LLM用量统计"])


# ============ 总览统计 ============

@router.get("/overview", summary="用量总览统计")
def get_overview(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """总览：总 token、总成本、调用次数、今日消耗、活跃用户数"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    # 时间范围内的汇总
    base_query = db.query(
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
        func.count(func.distinct(LlmUsageLog.user_id)).label("active_users"),
    ).filter(LlmUsageLog.created_at >= start_date)

    stats = base_query.first()

    # 今日消耗
    today_stats = db.query(
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        func.date(LlmUsageLog.created_at) == today
    ).first()

    # 成功率
    success_count = db.query(func.count(LlmUsageLog.id)).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.success == True
    ).scalar() or 0
    total_count = stats.call_count or 1
    success_rate = round(success_count / total_count * 100, 1)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "period_days": days,
            "total_tokens": stats.total_tokens or 0,
            "prompt_tokens": stats.prompt_tokens or 0,
            "completion_tokens": stats.completion_tokens or 0,
            "total_cost": round(stats.total_cost or 0, 4),
            "call_count": stats.call_count or 0,
            "active_users": stats.active_users or 0,
            "success_rate": success_rate,
            "today": {
                "total_tokens": today_stats.total_tokens or 0,
                "total_cost": round(today_stats.total_cost or 0, 4),
                "call_count": today_stats.call_count or 0,
            }
        }
    }


# ============ 按日期趋势 ============

@router.get("/trend", summary="按日期用量趋势")
def get_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """最近 N 天的 token 和成本趋势"""
    start_date = (datetime.now() - timedelta(days=days - 1)).date()

    records = db.query(
        func.date(LlmUsageLog.created_at).label("date"),
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        func.date(LlmUsageLog.created_at) >= start_date
    ).group_by(
        func.date(LlmUsageLog.created_at)
    ).order_by(
        func.date(LlmUsageLog.created_at)
    ).all()

    # 补全没有数据的日期
    date_map = {r.date.strftime("%Y-%m-%d") if hasattr(r.date, 'strftime') else str(r.date): r for r in records}
    result = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        if d in date_map:
            r = date_map[d]
            result.append({
                "date": d,
                "total_tokens": r.total_tokens or 0,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_cost": round(r.total_cost or 0, 4),
                "call_count": r.call_count or 0,
            })
        else:
            result.append({
                "date": d,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0,
                "call_count": 0,
            })

    return {"code": 0, "message": "success", "data": result}


# ============ 按任务类型分布 ============

@router.get("/by-task-type", summary="按任务类型用量分布")
def get_by_task_type(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """各任务类型的 token 消耗和成本占比"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    records = db.query(
        func.coalesce(LlmUsageLog.task_type, "unknown").label("task_type"),
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        LlmUsageLog.created_at >= start_date
    ).group_by(
        LlmUsageLog.task_type
    ).order_by(
        func.sum(LlmUsageLog.total_tokens).desc()
    ).all()

    total_tokens = sum(r.total_tokens or 0 for r in records) or 1

    result = []
    for r in records:
        result.append({
            "task_type": r.task_type,
            "total_tokens": r.total_tokens or 0,
            "total_cost": round(r.total_cost or 0, 4),
            "call_count": r.call_count or 0,
            "token_percentage": round((r.total_tokens or 0) / total_tokens * 100, 1),
        })

    return {"code": 0, "message": "success", "data": result}


# ============ 按平台对比 ============

@router.get("/by-platform", summary="按平台用量对比")
def get_by_platform(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """各 AI 平台的 token 消耗、成本和成功率对比"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    # 先查基础聚合数据（避免 SQLite 下复杂聚合函数的兼容性问题）
    records = db.query(
        LlmUsageLog.platform,
        LlmUsageLog.model,
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        LlmUsageLog.created_at >= start_date
    ).group_by(
        LlmUsageLog.platform,
        LlmUsageLog.model
    ).order_by(
        func.sum(LlmUsageLog.total_tokens).desc()
    ).all()

    # 成功率和平均延迟在 Python 里计算（避免 SQLite 聚合兼容性问题）
    result = []
    for r in records:
        # 查该平台模型的成功次数和总延迟
        stats = db.query(
            func.count(LlmUsageLog.id).label("total"),
            func.coalesce(func.sum(LlmUsageLog.latency_ms), 0).label("total_latency"),
        ).filter(
            LlmUsageLog.created_at >= start_date,
            LlmUsageLog.platform == r.platform,
            LlmUsageLog.model == r.model,
        ).first()
        success_count = db.query(func.count(LlmUsageLog.id)).filter(
            LlmUsageLog.created_at >= start_date,
            LlmUsageLog.platform == r.platform,
            LlmUsageLog.model == r.model,
            LlmUsageLog.success == True,
        ).scalar() or 0

        call_count = r.call_count or 1
        total_latency = stats.total_latency or 0
        result.append({
            "platform": r.platform,
            "model": r.model,
            "total_tokens": r.total_tokens or 0,
            "prompt_tokens": r.prompt_tokens or 0,
            "completion_tokens": r.completion_tokens or 0,
            "total_cost": round(r.total_cost or 0, 4),
            "call_count": r.call_count or 0,
            "success_rate": round(success_count / call_count * 100, 1),
            "avg_latency_ms": round(total_latency / call_count, 0) if call_count else 0,
        })

    return {"code": 0, "message": "success", "data": result}


# ============ 按用户排行 ============

@router.get("/by-user", summary="按用户用量排行")
def get_by_user(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """用户 token 消耗排行榜"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    records = db.query(
        LlmUsageLog.user_id,
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id.isnot(None)
    ).group_by(
        LlmUsageLog.user_id
    ).order_by(
        func.sum(LlmUsageLog.total_tokens).desc()
    ).limit(limit).all()

    # 关联用户名
    user_ids = [r.user_id for r in records if r.user_id]
    users = db.query(User.id, User.username, User.role).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in users}

    result = []
    for rank, r in enumerate(records, 1):
        u = user_map.get(r.user_id)
        result.append({
            "rank": rank,
            "user_id": r.user_id,
            "username": u.username if u else f"用户{r.user_id}",
            "role": u.role if u else "unknown",
            "total_tokens": r.total_tokens or 0,
            "total_cost": round(r.total_cost or 0, 4),
            "call_count": r.call_count or 0,
        })

    return {"code": 0, "message": "success", "data": result}


# ============ 详细日志列表 ============

@router.get("/logs", summary="LLM 调用详细日志")
def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id_filter: Optional[int] = Query(None, alias="user_id"),
    task_type: Optional[str] = None,
    platform: Optional[str] = None,
    success: Optional[bool] = None,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_admin_id),
):
    """分页查询 LLM 调用详细日志"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    query = db.query(LlmUsageLog).filter(LlmUsageLog.created_at >= start_date)

    if user_id_filter:
        query = query.filter(LlmUsageLog.user_id == user_id_filter)
    if task_type:
        query = query.filter(LlmUsageLog.task_type == task_type)
    if platform:
        query = query.filter(LlmUsageLog.platform == platform)
    if success is not None:
        query = query.filter(LlmUsageLog.success == success)

    total = query.count()
    items = query.order_by(LlmUsageLog.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for item in items:
        result.append({
            "id": item.id,
            "user_id": item.user_id,
            "platform": item.platform,
            "model": item.model,
            "prompt_tokens": item.prompt_tokens,
            "completion_tokens": item.completion_tokens,
            "total_tokens": item.total_tokens,
            "estimated_cost": item.estimated_cost,
            "task_type": item.task_type,
            "ref_id": item.ref_id,
            "ref_type": item.ref_type,
            "success": item.success,
            "error_type": item.error_type,
            "latency_ms": item.latency_ms,
            "source": item.source,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result,
        }
    }


# ============ 普通用户查看自己的用量 ============

@router.get("/my/overview", summary="我的用量总览")
def get_my_overview(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """普通用户查看自己的用量总览"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    stats = db.query(
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("total_cost"),
        func.count(LlmUsageLog.id).label("call_count"),
    ).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id == current_user_id,
    ).first()

    today_stats = db.query(
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("today_tokens"),
    ).filter(
        LlmUsageLog.created_at >= today,
        LlmUsageLog.user_id == current_user_id,
    ).first()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_tokens": int(stats.total_tokens or 0),
            "total_cost": float(stats.total_cost or 0),
            "call_count": int(stats.call_count or 0),
            "today_tokens": int(today_stats.today_tokens or 0),
        }
    }


@router.get("/my/trend", summary="我的用量趋势")
def get_my_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """普通用户查看自己的用量趋势（按日期）"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    rows = db.query(
        func.date(LlmUsageLog.created_at).label("date"),
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("cost"),
        func.count(LlmUsageLog.id).label("calls"),
    ).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id == current_user_id,
    ).group_by(func.date(LlmUsageLog.created_at)).all()

    data_map = {r.date: {"tokens": int(r.tokens or 0), "cost": float(r.cost or 0), "calls": int(r.calls or 0)} for r in rows}
    result = []
    for i in range(days):
        d = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": d, **data_map.get(d, {"tokens": 0, "cost": 0, "calls": 0})})

    return {"code": 0, "message": "success", "data": result}


@router.get("/my/by-task-type", summary="我的按任务类型分布")
def get_my_by_task_type(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """普通用户查看自己的按任务类型分布"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    rows = db.query(
        LlmUsageLog.task_type,
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("cost"),
        func.count(LlmUsageLog.id).label("calls"),
    ).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id == current_user_id,
    ).group_by(LlmUsageLog.task_type).all()

    result = [{"task_type": r.task_type, "tokens": int(r.tokens or 0), "cost": float(r.cost or 0), "calls": int(r.calls or 0)} for r in rows]
    return {"code": 0, "message": "success", "data": result}


@router.get("/my/by-platform", summary="我的按平台对比")
def get_my_by_platform(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """普通用户查看自己的按平台对比"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    rows = db.query(
        LlmUsageLog.platform,
        LlmUsageLog.model,
        func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("cost"),
        func.count(LlmUsageLog.id).label("calls"),
    ).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id == current_user_id,
    ).group_by(LlmUsageLog.platform, LlmUsageLog.model).all()

    result = [{"platform": r.platform, "model": r.model, "tokens": int(r.tokens or 0), "cost": float(r.cost or 0), "calls": int(r.calls or 0)} for r in rows]
    return {"code": 0, "message": "success", "data": result}


@router.get("/my/logs", summary="我的调用日志")
def get_my_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """普通用户查看自己的调用日志"""
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    query = db.query(LlmUsageLog).filter(
        LlmUsageLog.created_at >= start_date,
        LlmUsageLog.user_id == current_user_id,
    )

    total = query.count()
    items = query.order_by(LlmUsageLog.created_at.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for item in items:
        result.append({
            "id": item.id,
            "platform": item.platform,
            "model": item.model,
            "prompt_tokens": item.prompt_tokens,
            "completion_tokens": item.completion_tokens,
            "total_tokens": item.total_tokens,
            "estimated_cost": item.estimated_cost,
            "task_type": item.task_type,
            "success": item.success,
            "latency_ms": item.latency_ms,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result,
        }
    }

