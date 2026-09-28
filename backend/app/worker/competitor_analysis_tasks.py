# -*- coding: utf-8 -*-
"""竞品对比分析异步任务
payload: {"account_id": int, "benchmark_id": int}
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.competitor_analysis import CompetitorAnalysis
from app.services.competitor_analysis_service import CompetitorAnalysisService
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_competitor_analysis(db: Session, task: AsyncTask,
                                on_progress: ProgressCallback = None) -> dict:
    """处理竞品对比分析任务"""
    payload = json.loads(task.payload_json or "{}")
    account_id = payload.get("account_id")
    benchmark_id = payload.get("benchmark_id")

    if not account_id or not benchmark_id:
        raise ValueError("payload 中缺少 account_id 或 benchmark_id")

    if on_progress:
        on_progress(1, 3, "查询对比数据")

    try:
        if on_progress:
            on_progress(2, 3, "LLM分析中（约10-30秒）")

        result = CompetitorAnalysisService.analyze(db, account_id, benchmark_id, task.created_by)

        if on_progress:
            on_progress(3, 3, "分析完成，保存结果")

        # 保存分析结果
        analysis_record = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.account_id == account_id,
            CompetitorAnalysis.benchmark_id == benchmark_id,
        ).first()

        tokens_used = result.get("tokens_used", 0)

        if analysis_record:
            analysis_record.result_json = json.dumps(result, ensure_ascii=False)
            analysis_record.status = "completed"
            analysis_record.failed_reason = ""
            analysis_record.tokens_used = tokens_used
            analysis_record.completed_at = datetime.now()
        else:
            analysis_record = CompetitorAnalysis(
                user_id=task.created_by,
                account_id=account_id,
                benchmark_id=benchmark_id,
                status="completed",
                result_json=json.dumps(result, ensure_ascii=False),
                tokens_used=tokens_used,
                completed_at=datetime.now(),
            )
            db.add(analysis_record)

        db.commit()
        return {"account_id": account_id, "benchmark_id": benchmark_id, "status": "completed"}

    except Exception as e:
        # 失败时更新记录状态
        reason = str(e)[:1000]
        logger.error(f"[竞品AI分析] 失败: {reason}")
        try:
            db.rollback()
            analysis_record = db.query(CompetitorAnalysis).filter(
                CompetitorAnalysis.account_id == account_id,
                CompetitorAnalysis.benchmark_id == benchmark_id,
            ).first()
            if analysis_record:
                analysis_record.status = "failed"
                analysis_record.failed_reason = reason
                analysis_record.completed_at = datetime.now()
                db.commit()
        except Exception as inner:
            logger.error(f"[竞品AI分析] 写入failed状态失败: {inner}")
            db.rollback()
        raise


# 注册任务处理函数
register_handler("competitor_analysis", handle_competitor_analysis)
