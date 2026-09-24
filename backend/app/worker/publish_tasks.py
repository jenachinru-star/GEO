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

    # 发布成功后，同步存储文章正文到WechatArticle（供AI分析使用）
    try:
        from app.models.wechat_stats import WechatArticle
        from datetime import date

        publish_url = result.publish_url or ""

        # 查找是否已有该文章的记录（同账号 + 标题完全匹配）
        article_record = db.query(WechatArticle).filter(
            WechatArticle.account_id == account.id,
            WechatArticle.title == article.title,
        ).first()

        if not article_record:
            article_record = WechatArticle(
                account_id=account.id,
                user_id=user_id,
                title=article.title,
                article_url=publish_url,
                publish_date=date.today(),
                content=article.content or "",  # 存储正文
            )
            db.add(article_record)
        else:
            # 已存在（理论上发布前不会有记录）：补全正文和URL
            if not article_record.content:
                article_record.content = article.content or ""
            if publish_url and not article_record.article_url:
                article_record.article_url = publish_url

        db.commit()
        logger.info(f"文章正文已同步存储到WechatArticle，article_id={article_record.id}")
    except Exception as e:
        logger.warning(f"同步存储文章正文失败（不影响发布结果）: {e}")
        db.rollback()

    return {
        "success": True,
        "platform": platform,
        "publish_url": result.publish_url,
        "publish_id": result.external_id,
        "message": (result.raw_response or {}).get("message", "") if result.raw_response else "",
    }


# 注册任务处理函数
register_handler("article_publish", handle_article_publish)
