"""文章生成相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.content_opportunity import ContentOpportunity
from app.engines.article_generator import ArticleGenerator
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_article_generate(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文章生成任务"""
    payload = json.loads(task.payload_json or "{}")
    semantic_id = payload.get("semantic_id")
    opportunity_id = payload.get("opportunity_id")
    user_id = task.created_by

    if not semantic_id:
        raise ValueError("payload 中缺少 semantic_id")

    if on_progress:
        on_progress(1, 3, "查询语义和医生资料")

    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise ValueError("语义不存在或不属于当前用户")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("请先完善医生资料")

    opportunity = None
    if opportunity_id:
        opportunity = db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opportunity_id,
            ContentOpportunity.question_id == semantic_id
        ).first()

    if on_progress:
        on_progress(2, 3, "LLM生成文章中")

    generator = ArticleGenerator(db)
    result = generator.generate(semantic, profile, opportunity)

    if on_progress:
        on_progress(3, 3, "文章生成完成")

    return result


# 注册任务处理函数
register_handler("article_generate", handle_article_generate)
