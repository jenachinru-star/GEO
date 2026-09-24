"""发布平台账号管理 API"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.publish_account import PublishAccount
from app.models.wechat_stats import WechatAccountStats, WechatArticle, WechatArticleStats
from app.models.article_analysis import ArticleAnalysis
from app.models.task import AsyncTask
from app.services.wechat_data_service import WechatDataService
from app.utils.crypto import encrypt, decrypt

router = APIRouter(prefix="/api/v1/publish-accounts", tags=["发布账号"])


class AccountCreate(BaseModel):
    platform: str = Field(..., description="平台code：baijiahao/wechat/zhihu/douyin...")
    account_name: str = Field("", description="账号昵称")
    credential: str = Field("", description="登录凭证（cookie/token），非微信平台使用")
    app_id: str = Field("", description="应用ID/AppID，微信公众号等平台使用")
    app_secret: str = Field("", description="应用密钥/AppSecret，微信公众号等平台使用（加密存储）")
    note: str = Field("", description="备注")


class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    credential: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None  # 留空表示不修改
    login_status: Optional[str] = None
    note: Optional[str] = None


@router.get("", summary="获取我的发布账号列表")
def list_accounts(
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(PublishAccount).filter(PublishAccount.user_id == user_id)
    if platform:
        query = query.filter(PublishAccount.platform == platform)

    items = query.order_by(PublishAccount.created_at.desc()).all()

    result = [{
        "id": a.id,
        "platform": a.platform,
        "account_name": a.account_name,
        "login_status": a.login_status,
        "note": a.note,
        "last_verified_at": a.last_verified_at.isoformat() if a.last_verified_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        # 不返回 credential 明文
    } for a in items]

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("", summary="添加发布账号")
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = PublishAccount(
        user_id=user_id,
        platform=data.platform,
        account_name=data.account_name,
        credential=encrypt(data.credential),
        app_id=data.app_id,
        app_secret=encrypt(data.app_secret),
        note=data.note,
        login_status="unknown",
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return {
        "code": 0, "message": "success",
        "data": {"id": account.id, "platform": account.platform}
    }


@router.put("/{account_id}", summary="更新发布账号")
def update_account(
    account_id: int,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if data.account_name is not None:
        account.account_name = data.account_name
    if data.credential is not None:
        account.credential = encrypt(data.credential)
    if data.app_id is not None:
        account.app_id = data.app_id
    if data.app_secret is not None and data.app_secret != "":
        # 留空表示不修改
        account.app_secret = encrypt(data.app_secret)
    if data.login_status is not None:
        account.login_status = data.login_status
    if data.note is not None:
        account.note = data.note

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{account_id}", summary="删除发布账号")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    db.delete(account)
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/{account_id}/verify", summary="标记账号已验证")
def verify_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """手动标记账号登录态有效"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.login_status = "valid"
    account.last_verified_at = datetime.now()
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/{account_id}/verify-real", summary="真实验证微信账号（调用API）")
def verify_account_real(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """调用微信API真实验证AppID/AppSecret是否有效"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform != "wechat":
        raise HTTPException(status_code=400, detail="仅支持微信公众号真实验证")

    app_secret = decrypt(account.app_secret) if account.app_secret else ""
    is_valid, error_msg = WechatDataService.verify_credentials(account.app_id, app_secret)

    if is_valid:
        account.login_status = "valid"
        account.last_verified_at = datetime.now()
        db.commit()
        return {"code": 0, "message": "验证成功", "data": {"valid": True}}
    else:
        account.login_status = "expired"
        account.last_verified_at = datetime.now()
        db.commit()
        return {"code": 0, "message": "验证失败", "data": {"valid": False, "error": error_msg}}


@router.get("/{account_id}/stats/overview", summary="账号数据概览")
def get_account_stats_overview(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号数据概览（最新数据+汇总）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 获取最近30天的统计数据
    start_date = date.today() - timedelta(days=30)
    stats_list = db.query(WechatAccountStats).filter(
        WechatAccountStats.account_id == account_id,
        WechatAccountStats.stat_date >= start_date,
    ).order_by(WechatAccountStats.stat_date.desc()).all()

    if not stats_list:
        return {"code": 0, "message": "success", "data": {
            "has_data": False,
            "message": "暂无数据，请先点击'手动采集'获取数据"
        }}

    latest = stats_list[0]

    # 计算30天汇总
    total_new_users = sum(s.new_users for s in stats_list)
    total_cancel_users = sum(s.cancel_users for s in stats_list)
    total_articles = sum(s.total_articles for s in stats_list)
    total_reads = sum(s.total_reads for s in stats_list)
    total_shares = sum(s.total_shares for s in stats_list)
    total_likes = sum(s.total_likes for s in stats_list)
    avg_reads_30d = (total_reads / total_articles) if total_articles > 0 else 0

    # 获取文章总数
    article_count = db.query(WechatArticle).filter(
        WechatArticle.account_id == account_id
    ).count()

    return {"code": 0, "message": "success", "data": {
        "has_data": True,
        "latest_date": latest.stat_date.isoformat(),
        "cumulate_users": latest.cumulate_users,
        "today_new_users": latest.new_users,
        "today_cancel_users": latest.cancel_users,
        "today_net_growth": latest.net_growth,
        "today_articles": latest.total_articles,
        "today_reads": latest.total_reads,
        "today_avg_reads": latest.avg_reads,
        # 30天汇总
        "month_new_users": total_new_users,
        "month_cancel_users": total_cancel_users,
        "month_net_growth": total_new_users - total_cancel_users,
        "month_articles": total_articles,
        "month_reads": total_reads,
        "month_shares": total_shares,
        "month_likes": total_likes,
        "month_avg_reads": avg_reads_30d,
        "total_articles": article_count,
    }}


@router.get("/{account_id}/stats/trend", summary="账号数据趋势")
def get_account_stats_trend(
    account_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号数据趋势（按日期）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    days = min(max(days, 7), 90)  # 限制7-90天
    start_date = date.today() - timedelta(days=days)

    stats_list = db.query(WechatAccountStats).filter(
        WechatAccountStats.account_id == account_id,
        WechatAccountStats.stat_date >= start_date,
    ).order_by(WechatAccountStats.stat_date.asc()).all()

    dates = [s.stat_date.isoformat() for s in stats_list]
    cumulate_users = [s.cumulate_users for s in stats_list]
    new_users = [s.new_users for s in stats_list]
    net_growth = [s.net_growth for s in stats_list]
    total_reads = [s.total_reads for s in stats_list]
    total_articles = [s.total_articles for s in stats_list]
    avg_reads = [s.avg_reads for s in stats_list]

    return {"code": 0, "message": "success", "data": {
        "dates": dates,
        "cumulate_users": cumulate_users,
        "new_users": new_users,
        "net_growth": net_growth,
        "total_reads": total_reads,
        "total_articles": total_articles,
        "avg_reads": avg_reads,
    }}


@router.get("/{account_id}/articles", summary="账号文章列表")
def get_account_articles(
    account_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取账号已发布文章列表（含最新数据）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    query = db.query(WechatArticle).filter(WechatArticle.account_id == account_id)
    total = query.count()
    articles = query.order_by(WechatArticle.publish_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for article in articles:
        # 获取最新的文章数据快照
        latest_stats = db.query(WechatArticleStats).filter(
            WechatArticleStats.article_id == article.id
        ).order_by(WechatArticleStats.stat_date.desc()).first()

        items.append({
            "id": article.id,
            "title": article.title,
            "article_url": article.article_url,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
            "reads": latest_stats.int_page_read_count if latest_stats else 0,
            "read_users": latest_stats.int_page_read_user if latest_stats else 0,
            "shares": latest_stats.share_count if latest_stats else 0,
            "likes": latest_stats.like_count if latest_stats else 0,
            "favorites": latest_stats.add_to_fav_count if latest_stats else 0,
        })

    return {"code": 0, "message": "success", "data": {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }}


@router.post("/{account_id}/stats/collect", summary="手动触发数据采集")
def collect_account_stats(
    account_id: int,
    days: int = 7,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """手动触发微信公众号数据采集（异步任务）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform != "wechat":
        raise HTTPException(status_code=400, detail="仅支持微信公众号数据采集")

    if account.login_status != "valid":
        raise HTTPException(status_code=400, detail="账号未验证，请先验证账号")

    # 检查是否已有running/queued的采集任务
    existing = db.query(AsyncTask).filter(
        AsyncTask.task_type == "wechat_data_collect",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing:
        return {"code": 0, "message": "已有采集任务在执行中，请稍候", "data": {"task_id": existing.id}}

    days = min(max(days, 1), 90)  # 限制1-90天

    task = AsyncTask(
        task_type="wechat_data_collect",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"account_id": account.id, "days": days}, ensure_ascii=False),
        progress_message=f"手动采集微信公众号数据 [{account.account_name}]，最近{days}天",
    )
    db.add(task)
    db.commit()

    return {"code": 0, "message": "采集任务已提交", "data": {"task_id": task.id}}


# ===== 阶段四B：文章详情 / AI分析 / 导出 =====
# 注意：articles/export 必须声明在 articles/{article_id} 之前，
# 否则 "export" 会被当作 article_id 匹配，int 校验失败返回422。


@router.get("/{account_id}/articles/export", summary="导出文章列表Excel")
def export_articles(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出账号文章列表为Excel"""
    import io
    from urllib.parse import quote
    from fastapi.responses import StreamingResponse
    from app.services.export_service import ExportService

    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 获取所有文章
    articles = db.query(WechatArticle).filter(
        WechatArticle.account_id == account_id,
    ).order_by(WechatArticle.publish_date.desc()).all()

    # 生成Excel
    output = ExportService.export_wechat_articles(db, account, articles)

    filename = f"公众号文章数据_{account.account_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    headers = {
        # 中文文件名需URL编码
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
    }
    return StreamingResponse(
        io.BytesIO(output),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/{account_id}/articles/{article_id}", summary="文章详情")
def get_article_detail(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取文章详情（含多时间点数据快照）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 获取所有时间点快照，按 snapshot_day 升序
    snapshots = db.query(WechatArticleStats).filter(
        WechatArticleStats.article_id == article_id,
    ).order_by(WechatArticleStats.snapshot_day.asc()).all()

    snapshot_data = {}
    for s in snapshots:
        snapshot_data[f"day_{s.snapshot_day}"] = {
            "snapshot_day": s.snapshot_day,
            "stat_date": s.stat_date.isoformat(),
            "int_page_read_count": s.int_page_read_count,
            "int_page_read_user": s.int_page_read_user,
            "share_count": s.share_count,
            "like_count": s.like_count,
            "add_to_fav_count": s.add_to_fav_count,
        }

    # 获取最新分析结果（仅状态与时间，详情走 analysis 接口）
    latest_analysis = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).order_by(ArticleAnalysis.created_at.desc()).first()

    return {"code": 0, "message": "success", "data": {
        "id": article.id,
        "title": article.title,
        "article_url": article.article_url,
        "cover_url": article.cover_url,
        "author": article.author,
        "digest": article.digest,
        "publish_date": article.publish_date.isoformat() if article.publish_date else None,
        "has_content": bool(article.content),
        "snapshots": snapshot_data,
        "latest_analysis": {
            "status": latest_analysis.status,
            "created_at": latest_analysis.created_at.isoformat()
            if latest_analysis and latest_analysis.created_at else None,
        } if latest_analysis else None,
    }}


@router.post("/{account_id}/articles/{article_id}/analyze", summary="提交文章AI分析")
def submit_article_analysis(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """提交文章AI分析任务（异步）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 检查该用户是否已有正在处理的分析任务（避免并发重复调用LLM）
    existing_task = db.query(AsyncTask).filter(
        AsyncTask.task_type == "article_analysis",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing_task:
        return {"code": 0, "message": "已有分析任务在执行中", "data": {"task_id": existing_task.id}}

    # 创建异步任务
    task = AsyncTask(
        task_type="article_analysis",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps(
            {"article_id": article_id, "analysis_type": "full"}, ensure_ascii=False),
        progress_message=f"AI分析文章 [{article.title[:20]}]",
    )
    db.add(task)
    db.commit()

    # 分析记录置为 processing（不存在则创建）
    analysis_record = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).first()
    if analysis_record:
        analysis_record.status = "processing"
        analysis_record.failed_reason = ""
    else:
        analysis_record = ArticleAnalysis(
            article_id=article_id,
            account_id=account_id,
            user_id=user_id,
            analysis_type="full",
            status="processing",
        )
        db.add(analysis_record)
    db.commit()

    return {"code": 0, "message": "分析任务已提交，约10-30秒后完成",
            "data": {"task_id": task.id}}


@router.get("/{account_id}/articles/{article_id}/analysis", summary="获取文章AI分析结果")
def get_article_analysis(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取文章AI分析结果"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    analysis = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).order_by(ArticleAnalysis.created_at.desc()).first()

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
