"""采集相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.engines.collector import CollectorEngine
from app.worker.task_registry import register_handler

logger = logging.getLogger(__name__)


def handle_geo_refresh(db: Session, task: AsyncTask) -> dict:
    """处理 GEO/AEO 全量刷新任务"""
    payload = json.loads(task.payload_json or "{}")
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("payload 中缺少 user_id")

    collector = CollectorEngine(db)
    result = collector.collect_all_semantics(user_id, detect_round=99)
    return result


def handle_monitor_collect(db: Session, task: AsyncTask) -> dict:
    """处理品牌监测采集任务"""
    payload = json.loads(task.payload_json or "{}")
    question_id = payload.get("question_id")
    detect_round = payload.get("detect_round", 1)

    collector = CollectorEngine(db)
    if question_id:
        records = collector.collect_single_question_now(question_id)
        return {"total": 1, "success": 1, "records_count": len(records)}
    else:
        return collector.collect_all(detect_round=detect_round)


# 注册任务处理函数
register_handler("geo_refresh", handle_geo_refresh)
register_handler("monitor_collect", handle_monitor_collect)
