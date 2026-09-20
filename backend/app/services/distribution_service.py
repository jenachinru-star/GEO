"""
Distribution 状态机服务 — 管理文章分发记录的状态流转。

状态流转图：
    draft → scheduled → processing → published
                          ↘ failed → (retry) → processing
    published → removed
"""
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.distribution import ArticleDistribution
from app.models.task import AsyncTask

logger = logging.getLogger(__name__)

# 合法的状态流转：{当前状态: [允许的下一个状态]}
VALID_TRANSITIONS = {
    "draft": ["scheduled", "removed"],
    "scheduled": ["processing", "removed"],
    "processing": ["published", "failed"],
    "published": ["removed"],
    "failed": ["processing", "removed"],  # failed 可以 retry（回到 processing）
    "removed": [],
}

# 终态（不需要再操作的状态）
FINAL_STATES = ["published", "removed"]


class DistributionService:
    @staticmethod
    def get_or_404(db: Session, dist_id: int, user_id: int) -> ArticleDistribution:
        dist = db.query(ArticleDistribution).filter(
            ArticleDistribution.id == dist_id,
            ArticleDistribution.user_id == user_id
        ).first()
        if not dist:
            raise HTTPException(status_code=404, detail="分发记录不存在")
        return dist

    @staticmethod
    def transition(db: Session, dist: ArticleDistribution, target_status: str,
                   note: str = "", publish_url: str = "") -> ArticleDistribution:
        """
        状态流转（带合法性校验）

        Args:
            dist: 分发记录
            target_status: 目标状态
            note: 备注（失败原因等）
            publish_url: 发布URL（仅 published 状态时填写）
        """
        current = dist.status
        allowed = VALID_TRANSITIONS.get(current, [])

        if target_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"非法状态流转: {current} → {target_status}，允许的目标状态: {allowed}"
            )

        dist.status = target_status

        if target_status == "scheduled":
            dist.scheduled_at = datetime.now()
        elif target_status == "processing":
            dist.retry_count = (dist.retry_count or 0) + 1 if current == "failed" else (dist.retry_count or 0)
            dist.progress_message = "正在发布..." if hasattr(dist, 'progress_message') else ""
        elif target_status == "published":
            dist.publish_url = publish_url or dist.publish_url
            dist.published_at = datetime.now()
            dist.verified_at = None  # 待验证

            # 发布成功后自动触发效果监测（7天后再采集对比）
            _auto_trigger_effect_monitor(db, dist)
        elif target_status == "failed":
            dist.failed_reason = note[:500] if note else dist.failed_reason
        elif target_status == "removed":
            pass

        if note:
            dist.note = (dist.note or "") + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}"

        db.commit()
        db.refresh(dist)
        logger.info(f"分发记录 #{dist.id} 状态流转: {current} → {target_status}")
        return dist

    @staticmethod
    def schedule(db: Session, dist: ArticleDistribution, scheduled_at: datetime = None) -> ArticleDistribution:
        """计划发布"""
        if scheduled_at:
            dist.scheduled_at = scheduled_at
        return DistributionService.transition(db, dist, "scheduled", note="计划发布")

    @staticmethod
    def start_processing(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """开始发布处理"""
        return DistributionService.transition(db, dist, "processing", note="开始发布")

    @staticmethod
    def mark_published(db: Session, dist: ArticleDistribution, publish_url: str) -> ArticleDistribution:
        """标记发布成功"""
        return DistributionService.transition(db, dist, "published",
                                               note=f"发布成功，URL: {publish_url}",
                                               publish_url=publish_url)

    @staticmethod
    def mark_failed(db: Session, dist: ArticleDistribution, reason: str) -> ArticleDistribution:
        """标记发布失败"""
        return DistributionService.transition(db, dist, "failed", note=f"发布失败: {reason}")

    @staticmethod
    def retry(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """重试发布（从 failed 回到 processing）"""
        return DistributionService.transition(db, dist, "processing", note="重试发布")

    @staticmethod
    def remove(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """移除（软删除，不实际删除记录）"""
        return DistributionService.transition(db, dist, "removed", note="移除记录")


def _auto_trigger_effect_monitor(db: Session, dist: ArticleDistribution):
    """发布成功后自动触发效果监测任务

    策略：创建一个异步任务，自动重新采集，用于对比发布前后的AI提及率变化
    """
    try:
        from app.models.article import ArticleDraft

        article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
        if not article or not article.semantic_id:
            logger.info(f"分发记录 #{dist.id} 无关联文章或语义，跳过自动监测")
            return

        task = AsyncTask(
            workspace_id=None,
            task_type="monitor_collect",
            status="queued",
            progress=0,
            progress_message="等待执行（发布后效果监测）",
            payload_json=json.dumps({
                "question_id": article.semantic_id,
                "detect_round": 99,
                "distribution_id": dist.id,
                "trigger_reason": "after_publish_effect_monitor"
            }),
            created_by=dist.user_id,
        )
        db.add(task)
        db.commit()
        logger.info(f"分发记录 #{dist.id} 已自动创建效果监测任务 task_id={task.id}")
    except Exception as e:
        logger.error(f"自动触发效果监测失败: {e}")

