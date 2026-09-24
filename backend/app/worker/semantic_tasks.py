# -*- coding: utf-8 -*-
"""医生资料语义生成异步任务
payload: {"user_id": int, "profile": dict}
"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.semantic import Semantic
from app.engines.semantic_generator import SemanticGenerator
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_semantic_generate(db: Session, task: AsyncTask,
                             on_progress: ProgressCallback = None) -> dict:
    """处理医生资料语义生成任务"""
    payload = json.loads(task.payload_json or "{}")
    user_id = payload.get("user_id")
    profile = payload.get("profile", {})

    if not user_id:
        raise ValueError("payload 中缺少 user_id")

    if on_progress:
        on_progress(1, 2, "调用LLM生成语义问题（约10-30秒）")

    generator = SemanticGenerator(db=db, user_id=user_id)
    questions = generator.generate(profile)

    if on_progress:
        on_progress(2, 2, "保存语义问题")

    # 去重保存
    existing = {s.question for s in db.query(Semantic).filter(Semantic.user_id == user_id).all()}
    generated_count = 0
    for q in questions:
        if q and q not in existing:
            db.add(Semantic(user_id=user_id, question=q, category="general"))
            generated_count += 1
    if generated_count > 0:
        db.commit()

    return {"user_id": user_id, "generated_count": generated_count, "status": "completed"}


# 注册任务处理函数
register_handler("semantic_generate", handle_semantic_generate)
