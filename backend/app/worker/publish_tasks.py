"""文章发布相关任务的处理函数"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.article import ArticleDraft
from app.models.publish_account import PublishAccount
from app.models.distribution import ArticleDistribution
from app.publishers.factory import publisher_factory
from app.utils.crypto import decrypt
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_article_publish(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文章发布任务"""
    payload = json.loads(task.payload_json or "{}")
    article_id = payload.get("article_id")
    distribution_id = payload.get("distribution_id")
    platform = payload.get("platform")
    user_id = task.created_by

    if not article_id or not platform:
        raise ValueError("payload 中缺少 article_id 或 platform")

    if on_progress:
        on_progress(1, 4, "查询文章和发布账号")

    # 查询文章
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise ValueError("文章不存在或不属于当前用户")

    # 查询发布账号
    account = db.query(PublishAccount).filter(
        PublishAccount.user_id == user_id,
        PublishAccount.platform == platform,
        PublishAccount.login_status == "valid",
    ).first()
    if not account:
        raise ValueError(f"未找到 {platform} 平台的有效发布账号，请先在发布账号中添加并标记为有效")

    # 解密账号信息
    account_dict = {
        "app_id": account.app_id or "",
        "app_secret": decrypt(account.app_secret) if account.app_secret else "",
        "credential": decrypt(account.credential) if account.credential else "",
        "account_name": account.account_name,
    }

    if on_progress:
        on_progress(2, 4, f"调用 {platform} 平台发布API")

    # 获取发布器并执行发布
    publisher = publisher_factory.get_publisher(platform)
    result = publisher.publish(
        title=article.title,
        content=article.content or "",
        account=account_dict,
    )

    if on_progress:
        on_progress(3, 4, "更新发布记录")

    # 更新distribution记录
    if distribution_id:
        dist = db.query(ArticleDistribution).filter(ArticleDistribution.id == distribution_id).first()
        if dist:
            if result.success:
                dist.status = "published"
                dist.publish_url = result.publish_url
                dist.published_at = datetime.now()
                dist.publish_mode = "auto"
                message = (result.raw_response or {}).get("message", "") if result.raw_response else ""
                dist.note = message or "一键发布成功"
                dist.failed_reason = ""
            else:
                dist.status = "failed"
                dist.failed_reason = result.failed_reason
                dist.note = f"发布失败: {result.failed_reason}"
            db.commit()

    if on_progress:
        on_progress(4, 4, "发布完成")

    if not result.success:
        raise ValueError(f"发布失败: {result.failed_reason}")

    return {
        "success": True,
        "platform": platform,
        "publish_url": result.publish_url,
        "publish_id": result.external_id,
        "message": (result.raw_response or {}).get("message", "") if result.raw_response else "",
    }


# 注册任务处理函数
register_handler("article_publish", handle_article_publish)
