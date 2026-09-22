"""GEO/AEO数据 API — 医生维度的数据检测与查询"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.deps import get_current_user_id
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.monitor import MonitorRecord
from app.engines.collector import CollectorEngine
from app.adapters import adapter_factory
import json
from app.models.task import AsyncTask
from app.services.workspace_service import get_user_workspace_id

router = APIRouter(prefix="/api/v1/geo", tags=["GEO/AEO数据"])


@router.get("/overview", summary="获取当前用户GEO/AEO总览")
def get_overview(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """总览：总GEO率、总AEO率、各语义统计、近7天趋势"""
    platforms = adapter_factory.get_enabled_platforms()

    # 用户的所有语义
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
    semantic_ids = [s.id for s in semantics]

    if not semantic_ids:
        return {"code": 0, "message": "success", "data": {
            "total_semantics": 0,
            "active_semantics": 0,
            "overall_geo_rate": 0,
            "overall_aeo_rate": 0,
            "semantic_stats": [],
            "trend_7days": [],
            "platforms": platforms,
            "last_refresh": None,
        }}

    # 取每个语义最新一轮的记录（detect_round=99）
    latest_date = db.query(func.max(MonitorRecord.detect_date)).filter(
        MonitorRecord.semantic_id.in_(semantic_ids),
        MonitorRecord.detect_type == "doctor"
    ).scalar()

    latest_records = []
    if latest_date:
        latest_records = db.query(MonitorRecord).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_type == "doctor",
            MonitorRecord.detect_date == latest_date,
            MonitorRecord.detect_round == 99
        ).all()

    # 总GEO/AEO率
    total_geo = sum(1 for r in latest_records if r.mentioned)
    total_aeo = sum(1 for r in latest_records if r.cite_count > 0)
    overall_geo_rate = round(total_geo / len(latest_records) * 100, 1) if latest_records else 0
    overall_aeo_rate = round(total_aeo / len(latest_records) * 100, 1) if latest_records else 0

    # 各语义统计
    semantic_stats = []
    for s in semantics:
        s_records = [r for r in latest_records if r.semantic_id == s.id]
        geo_count = sum(1 for r in s_records if r.mentioned)
        aeo_count = sum(1 for r in s_records if r.cite_count > 0)
        best_rank = min((r.rank for r in s_records if r.mentioned), default=0)
        semantic_stats.append({
            "semantic_id": s.id,
            "question": s.question,
            "is_active": s.is_active,
            "geo_rate": round(geo_count / len(s_records) * 100, 1) if s_records else 0,
            "aeo_rate": round(aeo_count / len(s_records) * 100, 1) if s_records else 0,
            "best_rank": best_rank,
            "platform_count": len(s_records),
        })

    # 近7天趋势
    week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    trend_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id.in_(semantic_ids),
        MonitorRecord.detect_type == "doctor",
        MonitorRecord.detect_date >= week_ago
    ).all()

    daily = {}
    for r in trend_records:
        if r.detect_date not in daily:
            daily[r.detect_date] = {"total": 0, "geo": 0, "aeo": 0}
        daily[r.detect_date]["total"] += 1
        if r.mentioned:
            daily[r.detect_date]["geo"] += 1
        if r.cite_count > 0:
            daily[r.detect_date]["aeo"] += 1

    trend_7days = []
    for date in sorted(daily.keys()):
        d = daily[date]
        trend_7days.append({
            "date": date,
            "geo_rate": round(d["geo"] / d["total"] * 100, 1) if d["total"] else 0,
            "aeo_rate": round(d["aeo"] / d["total"] * 100, 1) if d["total"] else 0,
            "total": d["total"],
        })

    # 最后刷新时间
    last_refresh = latest_date

    return {"code": 0, "message": "success", "data": {
        "total_semantics": len(semantics),
        "active_semantics": sum(1 for s in semantics if s.is_active),
        "overall_geo_rate": overall_geo_rate,
        "overall_aeo_rate": overall_aeo_rate,
        "semantic_stats": semantic_stats,
        "trend_7days": trend_7days,
        "platforms": platforms,
        "last_refresh": last_refresh,
    }}


@router.get("/semantic/{semantic_id}", summary="获取单个语义的GEO/AEO详情")
def get_semantic_detail(
    semantic_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """单个语义详情：各平台GEO/AEO状态、原始回答、趋势"""
    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise HTTPException(status_code=404, detail="语义不存在")

    # 最新一轮记录
    latest_date = db.query(func.max(MonitorRecord.detect_date)).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.detect_type == "doctor"
    ).scalar()

    platform_details = []
    if latest_date:
        records = db.query(MonitorRecord).filter(
            MonitorRecord.semantic_id == semantic_id,
            MonitorRecord.detect_type == "doctor",
            MonitorRecord.detect_date == latest_date,
            MonitorRecord.detect_round == 99
        ).all()
        for r in records:
            platform_details.append({
                "platform_code": r.platform_code,
                "geo_mentioned": r.mentioned,
                "geo_rank": r.rank,
                "aeo_cited": r.cite_count > 0,
                "aeo_confidence": r.aeo_confidence,
                "raw_answer": r.raw_answer,
                "detect_time": r.detect_time.isoformat() if r.detect_time else None,
            })

    # 趋势
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    trend_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.detect_type == "doctor",
        MonitorRecord.detect_date >= start_date
    ).all()

    daily = {}
    for r in trend_records:
        if r.detect_date not in daily:
            daily[r.detect_date] = {"total": 0, "geo": 0, "aeo": 0}
        daily[r.detect_date]["total"] += 1
        if r.mentioned:
            daily[r.detect_date]["geo"] += 1
        if r.cite_count > 0:
            daily[r.detect_date]["aeo"] += 1

    trend = []
    for date in sorted(daily.keys()):
        d = daily[date]
        trend.append({
            "date": date,
            "geo_rate": round(d["geo"] / d["total"] * 100, 1) if d["total"] else 0,
            "aeo_rate": round(d["aeo"] / d["total"] * 100, 1) if d["total"] else 0,
        })

    return {"code": 0, "message": "success", "data": {
        "semantic_id": semantic.id,
        "question": semantic.question,
        "platform_details": platform_details,
        "trend": trend,
        "last_refresh": latest_date,
    }}


@router.post("/refresh", summary="手动刷新GEO/AEO数据（异步任务，立即返回task_id）")
def refresh_data(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """手动触发当前用户所有启用语义的GEO/AEO采集（异步，由Worker执行）"""
    # 检查Profile
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善个人资料")

    # 检查启用的语义
    active_count = db.query(Semantic).filter(
        Semantic.user_id == user_id, Semantic.is_active == True
    ).count()
    if active_count == 0:
        raise HTTPException(status_code=400, detail="没有启用的语义，请先在语义库启用")

    # 检查AI平台
    platforms = adapter_factory.get_enabled_platforms()
    if not platforms:
        raise HTTPException(status_code=400, detail="没有已配置的AI平台")

    # 获取用户默认 workspace_id
    workspace_id = get_user_workspace_id(db, user_id)

    # 检查是否已有 running 的同类型任务（防止重复提交）
    running_task = db.query(AsyncTask).filter(
        AsyncTask.created_by == user_id,
        AsyncTask.task_type == "geo_refresh",
        AsyncTask.status.in_(["queued", "running"])
    ).first()
    if running_task:
        raise HTTPException(status_code=400, detail=f"已有正在执行的GEO刷新任务（ID: {running_task.id}），请等待完成")

    # 创建异步任务
    task = AsyncTask(
        workspace_id=workspace_id,
        task_type="geo_refresh",
        status="queued",
        progress=0,
        progress_message="等待执行",
        payload_json=json.dumps({"user_id": user_id}, ensure_ascii=False),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"code": 0, "message": "任务已创建", "data": {
        "task_id": task.id,
        "status": "queued",
        "message": "GEO/AEO刷新任务已提交，Worker将在后台执行"
    }}


@router.get("/trend", summary="获取GEO/AEO历史趋势")
def get_trend(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
    semantic_ids = [s.id for s in semantics]

    if not semantic_ids:
        return {"code": 0, "message": "success", "data": {"dates": [], "geo_rates": [], "aeo_rates": []}}

    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days-1, -1, -1)]

    geo_rates = []
    aeo_rates = []

    for date_str in dates:
        records = db.query(MonitorRecord).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_date == date_str,
            MonitorRecord.detect_type == "doctor"
        ).all()

        if records:
            geo_count = sum(1 for r in records if r.mentioned)
            aeo_count = sum(1 for r in records if r.cite_count and r.cite_count > 0)
            geo_rates.append(round(geo_count / len(records) * 100, 1))
            aeo_rates.append(round(aeo_count / len(records) * 100, 1))
        else:
            geo_rates.append(0)
            aeo_rates.append(0)

    return {
        "code": 0, "message": "success",
        "data": {"dates": dates, "geo_rates": geo_rates, "aeo_rates": aeo_rates}
    }
