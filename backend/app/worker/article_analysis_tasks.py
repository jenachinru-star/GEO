# -*- coding: utf-8 -*-
"""文章AI分析异步任务
payload: {"article_id": int, "analysis_type": "full"}
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.wechat_stats import WechatArticle, WechatArticleStats
from app.models.article_analysis import ArticleAnalysis
from app.services.article_analysis_service import ArticleAnalysisService
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def _get_or_create_record(db: Session, article: WechatArticle,
                          analysis_type: str) -> ArticleAnalysis:
    """查找或创建分析记录（按 article_id + analysis_type）"""
    record = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article.id,
        ArticleAnalysis.analysis_type == analysis_type,
    ).first()
    if not record:
        record = ArticleAnalysis(
            article_id=article.id,
            account_id=article.account_id,
            user_id=article.user_id,
            analysis_type=analysis_type,
            status="pending",
        )
        db.add(record)
        db.flush()
    return record


def handle_article_analysis(db: Session, task: AsyncTask,
                            on_progress: ProgressCallback = None) -> dict:
    """处理文章AI分析任务"""
    payload = json.loads(task.payload_json or "{}")
    article_id = payload.get("article_id")
    analysis_type = payload.get("analysis_type", "full")

    if not article_id:
        raise ValueError("payload 中缺少 article_id")

    article = db.query(WechatArticle).filter(WechatArticle.id == article_id).first()
    if not article:
        raise ValueError(f"文章不存在: {article_id}")

    # 预取记录，失败时可直接置 failed
    record = _get_or_create_record(db, article, analysis_type)
    record.status = "processing"
    record.failed_reason = ""
    db.commit()

    try:
        if on_progress:
            on_progress(1, 3, "查询文章数据")

        # 最新数据快照（day_0）；可能为空（刚发布尚未采集）
        stats = db.query(WechatArticleStats).filter(
            WechatArticleStats.article_id == article_id,
            WechatArticleStats.snapshot_day == 0,
        ).first()

        if on_progress:
            on_progress(2, 3, "LLM分析中（约10-30秒）")

        result, tokens_used = ArticleAnalysisService.analyze_with_llm(
            db, article, stats, article.user_id
        )

        if on_progress:
            on_progress(3, 3, "分析完成，保存结果")

        record.result_json = json.dumps(result, ensure_ascii=False)
        record.status = "completed"
        record.failed_reason = ""
        record.tokens_used = tokens_used or 0
        record.completed_at = datetime.now()
        db.commit()

        return {"article_id": article_id, "analysis_type": analysis_type, "status": "completed"}

    except Exception as e:
        # 失败：把 ArticleAnalysis 置为 failed 并记录原因，再向上抛出（AsyncTask 也会 failed）
        reason = str(e)[:1000]
        logger.error(f"[文章AI分析] article_id={article_id} 失败: {reason}")
        try:
            db.rollback()
            failed_record = db.query(ArticleAnalysis).filter(
                ArticleAnalysis.article_id == article_id,
                ArticleAnalysis.analysis_type == analysis_type,
            ).first()
            if failed_record:
                failed_record.status = "failed"
                failed_record.failed_reason = reason
                failed_record.completed_at = datetime.now()
                db.commit()
        except Exception as inner:
            logger.error(f"[文章AI分析] 写入failed状态失败: {inner}")
            db.rollback()
        raise


# 注册任务处理函数
register_handler("article_analysis", handle_article_analysis)
