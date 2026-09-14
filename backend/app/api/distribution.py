from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.deps import get_current_user_id
from app.models.distribution import ArticleDistribution
from app.models.article import ArticleDraft
from app.models.monitor import MonitorRecord
from app.services.distribution_service import DistributionService

router = APIRouter(prefix="/api/v1/distribution", tags=["文章分发"])


class DistributionCreate(BaseModel):
    article_id: int
    platform: str
    publish_url: str = ""
    status: str = "draft"  # 创建时默认 draft
    note: str = ""


class DistributionStatusUpdate(BaseModel):
    status: str  # scheduled / processing / published / failed / removed
    publish_url: str = ""
    note: str = ""


@router.get("", summary="获取分发记录列表")
def get_distributions(
    article_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDistribution).filter(ArticleDistribution.user_id == user_id)
    if article_id:
        query = query.filter(ArticleDistribution.article_id == article_id)
    if status:
        query = query.filter(ArticleDistribution.status == status)
    items = query.order_by(ArticleDistribution.created_at.desc()).all()

    # 批量查询文章标题和语义
    article_ids = list(set([d.article_id for d in items]))
    articles = {}
    if article_ids:
        for a in db.query(ArticleDraft).filter(ArticleDraft.id.in_(article_ids)).all():
            articles[a.id] = a
    semantic_ids = list(set([a.semantic_id for a in articles.values()]))
    semantics = {}
    if semantic_ids:
        from app.models.semantic import Semantic
        for s in db.query(Semantic).filter(Semantic.id.in_(semantic_ids)).all():
            semantics[s.id] = s.question

    result_items = []
    for d in items:
        article = articles.get(d.article_id)
        result_items.append({
            "id": d.id,
            "article_id": d.article_id,
            "article_title": article.title if article else '',
            "semantic_id": article.semantic_id if article else None,
            "semantic_question": semantics.get(article.semantic_id, '') if article else '',
            "platform": d.platform,
            "publish_url": d.publish_url,
            "status": d.status,
            "note": d.note,
            "publish_mode": d.publish_mode,
            "retry_count": d.retry_count,
            "failed_reason": d.failed_reason,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return {"code": 0, "message": "success", "data": {"items": result_items}}


@router.post("", summary="创建分发记录")
def create_distribution(
    data: DistributionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == data.article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 校验状态合法性
    valid_statuses = ["draft", "scheduled", "processing", "published", "failed", "removed"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态: {data.status}，合法值: {valid_statuses}")

    dist = ArticleDistribution(
        user_id=user_id, article_id=data.article_id,
        platform=data.platform, publish_url=data.publish_url,
        status=data.status, note=data.note,
        publish_mode="manual",
    )
    if data.status == "published":
        dist.published_at = datetime.now()
    db.add(dist)
    db.commit()
    db.refresh(dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id}}


@router.patch("/{dist_id}/status", summary="状态流转（计划/开始/成功/失败/重试/移除）")
def update_status(
    dist_id: int,
    data: DistributionStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.transition(
        db, dist, data.status,
        note=data.note, publish_url=data.publish_url
    )
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status}}


@router.post("/{dist_id}/retry", summary="重试发布（failed → processing）")
def retry_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.retry(db, dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status, "retry_count": dist.retry_count}}


@router.delete("/{dist_id}", summary="删除分发记录（物理删除，仅 draft 状态允许）")
def delete_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    if dist.status != "draft":
        raise HTTPException(status_code=400, detail=f"仅 draft 状态的记录可以物理删除，当前状态: {dist.status}。请使用移除（removed）接口")
    db.delete(dist)
    db.commit()
    return {"code": 0, "message": "success"}


@router.get("/{dist_id}/effect", summary="获取发布效果对比（发布前后GEO/AEO/排名变化）")
def get_distribution_effect(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    if dist.status != 'published':
        raise HTTPException(status_code=400, detail="仅已发布的记录可查看效果追踪")

    # 获取关联文章和语义
    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="关联文章不存在")

    semantic_id = article.semantic_id
    publish_time = dist.published_at or dist.created_at

    # 查询语义问题
    from app.models.semantic import Semantic
    semantic = db.query(Semantic).filter(Semantic.id == semantic_id).first()
    semantic_question = semantic.question if semantic else ''

    # 发布前数据（发布时间之前的采集记录）
    before_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at < publish_time
    ).all()

    # 发布后数据（发布时间之后的采集记录）
    after_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at >= publish_time
    ).all()

    def calc_stats(records):
        if not records:
            return {"total": 0, "mention_rate": 0, "citation_rate": 0, "avg_rank": None, "mentioned_count": 0}
        total = len(records)
        mentioned = sum(1 for r in records if r.mentioned)
        cited = sum(1 for r in records if r.cite_count and r.cite_count > 0)
        ranks = [r.rank for r in records if r.rank and r.rank > 0]
        avg_rank = sum(ranks) / len(ranks) if ranks else None
        return {
            "total": total,
            "mention_rate": round(mentioned / total * 100, 1),
            "citation_rate": round(cited / total * 100, 1),
            "avg_rank": round(avg_rank, 1) if avg_rank else None,
            "mentioned_count": mentioned,
        }

    before = calc_stats(before_records)
    after = calc_stats(after_records)

    # 变化量（排名：before - after，正数表示排名提升）
    change = {
        "mention_rate": round(after["mention_rate"] - before["mention_rate"], 1),
        "citation_rate": round(after["citation_rate"] - before["citation_rate"], 1),
        "avg_rank": round((before["avg_rank"] or 0) - (after["avg_rank"] or 0), 1) if before["avg_rank"] and after["avg_rank"] else None,
    }

    # 按日期统计趋势（最近30天）
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    trend_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at >= thirty_days_ago
    ).all()

    trend = {}
    for r in trend_records:
        date_str = r.detect_date if r.detect_date else (r.created_at.strftime('%Y-%m-%d') if hasattr(r.created_at, 'strftime') else str(r.created_at)[:10])
        if date_str not in trend:
            trend[date_str] = {"total": 0, "mentioned": 0, "cited": 0, "ranks": []}
        trend[date_str]["total"] += 1
        if r.mentioned:
            trend[date_str]["mentioned"] += 1
        if r.cite_count and r.cite_count > 0:
            trend[date_str]["cited"] += 1
        if r.rank and r.rank > 0:
            trend[date_str]["ranks"].append(r.rank)

    trend_data = sorted([
        {
            "date": d,
            "mention_rate": round(v["mentioned"] / v["total"] * 100, 1),
            "citation_rate": round(v["cited"] / v["total"] * 100, 1),
            "avg_rank": round(sum(v["ranks"]) / len(v["ranks"]), 1) if v["ranks"] else None,
        }
        for d, v in trend.items()
    ], key=lambda x: x["date"])

    return {
        "code": 0,
        "message": "success",
        "data": {
            "semantic_id": semantic_id,
            "semantic_question": semantic_question,
            "publish_time": publish_time.isoformat() if publish_time else None,
            "before": before,
            "after": after,
            "change": change,
            "trend": trend_data,
        }
    }


@router.post("/{dist_id}/recollect", summary="触发重新采集关联语义（用于效果验证）")
def recollect_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="关联文章不存在")

    # 创建异步采集任务（复用 monitor_collect）
    from app.models.task import AsyncTask
    import json
    task = AsyncTask(
        workspace_id=None,
        task_type="monitor_collect",
        status="queued",
        progress=0,
        progress_message="等待执行",
        payload_json=json.dumps({"question_id": article.semantic_id, "detect_round": 99}),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"code": 0, "message": "success", "data": {"task_id": task.id, "message": "已加入采集队列，完成后可查看最新效果"}}
