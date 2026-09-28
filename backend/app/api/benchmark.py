"""对标账号管理API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.benchmark_account import BenchmarkAccount, BenchmarkArticle
from app.models.competitor_analysis import CompetitorAnalysis
from app.models.task import AsyncTask
import json

router = APIRouter(prefix="/api/v1/benchmark", tags=["对标账号"])


# ===== Pydantic 模型 =====

class BenchmarkCreate(BaseModel):
    account_name: str = Field(..., description="公众号名称")
    wechat_id: str = Field("", description="微信号")
    description: str = Field("", description="账号简介")
    industry: str = Field("", description="行业领域")
    followers: int = Field(0, description="粉丝数")
    avg_reads: int = Field(0, description="平均阅读量")
    avg_likes: int = Field(0, description="平均点赞数")
    avg_shares: int = Field(0, description="平均分享数")
    weekly_posts: int = Field(0, description="每周发文数")
    note: str = Field("", description="备注")


class BenchmarkUpdate(BaseModel):
    account_name: Optional[str] = None
    wechat_id: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    followers: Optional[int] = None
    avg_reads: Optional[int] = None
    avg_likes: Optional[int] = None
    avg_shares: Optional[int] = None
    weekly_posts: Optional[int] = None
    note: Optional[str] = None


class BenchmarkArticleCreate(BaseModel):
    title: str = Field(..., description="文章标题")
    article_url: str = Field("", description="文章URL")
    publish_date: Optional[date] = None
    reads: int = Field(0, description="阅读量")
    likes: int = Field(0, description="点赞数")
    shares: int = Field(0, description="分享数")
    favorites: int = Field(0, description="收藏数")


# ===== 竞品对比分析（必须定义在 /{benchmark_id} 路由之前，避免路径冲突） =====

@router.get("/analysis/compare", summary="获取对比数据（规则计算）")
def get_comparison(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    from app.services.benchmark_service import BenchmarkService
    result = BenchmarkService.compare(db, account_id, benchmark_id, user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/analysis", summary="提交竞品AI分析")
def submit_competitor_analysis(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 检查是否已有正在处理的分析
    existing_task = db.query(AsyncTask).filter(
        AsyncTask.task_type == "competitor_analysis",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing_task:
        return {"code": 0, "message": "已有分析任务在执行中", "data": {"task_id": existing_task.id}}

    # 创建异步任务
    task = AsyncTask(
        task_type="competitor_analysis",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"account_id": account_id, "benchmark_id": benchmark_id}, ensure_ascii=False),
        progress_message="竞品对比AI分析中",
    )
    db.add(task)

    # 更新分析记录状态
    analysis_record = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.account_id == account_id,
        CompetitorAnalysis.benchmark_id == benchmark_id,
    ).first()
    if analysis_record:
        analysis_record.status = "processing"
        analysis_record.failed_reason = ""
    else:
        analysis_record = CompetitorAnalysis(
            user_id=user_id,
            account_id=account_id,
            benchmark_id=benchmark_id,
            status="processing",
        )
        db.add(analysis_record)
    db.commit()

    return {"code": 0, "message": "分析任务已提交，约10-30秒后完成", "data": {"task_id": task.id}}


@router.get("/analysis", summary="获取竞品AI分析结果")
def get_competitor_analysis(
    account_id: int = Query(...),
    benchmark_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    analysis = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.account_id == account_id,
        CompetitorAnalysis.benchmark_id == benchmark_id,
        CompetitorAnalysis.user_id == user_id,
    ).order_by(CompetitorAnalysis.created_at.desc()).first()

    if not analysis:
        return {"code": 0, "message": "success", "data": {"status": "none", "result": None}}

    result_data = None
    if analysis.status == "completed" and analysis.result_json:
        try:
            result_data = json.loads(analysis.result_json)
        except Exception:
            result_data = None

    return {"code": 0, "message": "success", "data": {
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "result": result_data,
        "failed_reason": analysis.failed_reason,
    }}


# ===== 对标账号 CRUD =====

@router.get("", summary="获取我的对标账号列表")
def list_benchmarks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    items = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.user_id == user_id
    ).order_by(BenchmarkAccount.created_at.desc()).all()

    result = [{
        "id": b.id,
        "account_name": b.account_name,
        "wechat_id": b.wechat_id,
        "description": b.description,
        "industry": b.industry,
        "followers": b.followers,
        "avg_reads": b.avg_reads,
        "avg_likes": b.avg_likes,
        "avg_shares": b.avg_shares,
        "weekly_posts": b.weekly_posts,
        "data_source": b.data_source,
        "last_updated": b.last_updated.isoformat() if b.last_updated else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    } for b in items]

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("", summary="添加对标账号")
def create_benchmark(
    data: BenchmarkCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = BenchmarkAccount(
        user_id=user_id,
        account_name=data.account_name,
        wechat_id=data.wechat_id,
        description=data.description,
        industry=data.industry,
        followers=data.followers,
        avg_reads=data.avg_reads,
        avg_likes=data.avg_likes,
        avg_shares=data.avg_shares,
        weekly_posts=data.weekly_posts,
        note=data.note,
        last_updated=datetime.now(),
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return {"code": 0, "message": "success", "data": {"id": benchmark.id}}


@router.put("/{benchmark_id}", summary="更新对标账号")
def update_benchmark(
    benchmark_id: int,
    data: BenchmarkUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(benchmark, field, value)
    benchmark.last_updated = datetime.now()
    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{benchmark_id}", summary="删除对标账号")
def delete_benchmark(
    benchmark_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    # 级联删除对标文章
    db.query(BenchmarkArticle).filter(BenchmarkArticle.benchmark_id == benchmark_id).delete()
    db.delete(benchmark)
    db.commit()
    return {"code": 0, "message": "success"}


# ===== 对标文章 CRUD =====

@router.get("/{benchmark_id}/articles", summary="获取对标账号文章列表")
def list_benchmark_articles(
    benchmark_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    query = db.query(BenchmarkArticle).filter(BenchmarkArticle.benchmark_id == benchmark_id)
    total = query.count()
    articles = query.order_by(BenchmarkArticle.publish_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [{
        "id": a.id,
        "title": a.title,
        "article_url": a.article_url,
        "publish_date": a.publish_date.isoformat() if a.publish_date else None,
        "reads": a.reads,
        "likes": a.likes,
        "shares": a.shares,
        "favorites": a.favorites,
    } for a in articles]

    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/{benchmark_id}/articles", summary="添加对标文章")
def create_benchmark_article(
    benchmark_id: int,
    data: BenchmarkArticleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    benchmark = db.query(BenchmarkAccount).filter(
        BenchmarkAccount.id == benchmark_id,
        BenchmarkAccount.user_id == user_id,
    ).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="对标账号不存在")

    article = BenchmarkArticle(
        benchmark_id=benchmark_id,
        user_id=user_id,
        title=data.title,
        article_url=data.article_url,
        publish_date=data.publish_date,
        reads=data.reads,
        likes=data.likes,
        shares=data.shares,
        favorites=data.favorites,
    )
    db.add(article)
    db.commit()
    return {"code": 0, "message": "success", "data": {"id": article.id}}


@router.delete("/{benchmark_id}/articles/{article_id}", summary="删除对标文章")
def delete_benchmark_article(
    benchmark_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(BenchmarkArticle).filter(
        BenchmarkArticle.id == article_id,
        BenchmarkArticle.benchmark_id == benchmark_id,
        BenchmarkArticle.user_id == user_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"code": 0, "message": "success"}
