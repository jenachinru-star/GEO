"""生图相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.adapters import adapter_factory
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)

# 生图每次固定成本（元）
IMAGE_GENERATE_COST = 0.1


def handle_image_generate(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理生图任务"""
    payload = json.loads(task.payload_json or "{}")
    prompt = payload.get("prompt", "")
    width = payload.get("width", 1024)
    height = payload.get("height", 1024)
    n = payload.get("n", 1)
    style = payload.get("style")
    user_id = task.created_by

    # 配额检查（按月费用上限）
    from app.services.quota_checker import check_quota, QuotaError
    try:
        check_quota(db, user_id)
    except QuotaError as e:
        raise ValueError(f"配额不足: {e.message}")

    # 设置 usage_context（worker execute_task 已设置，这里显式覆盖 task_type）
    from app.usage_context import usage_context
    ctx_token = usage_context.set(
        user_id=user_id,
        task_type="image_generate",
        ref_id=task.id,
        ref_type="async_task",
        source="worker",
    )

    try:
        if on_progress:
            on_progress(1, 2, "生图中")

        image_adapter = adapter_factory.get_image_adapter()
        if not image_adapter:
            raise ValueError("生图适配器不可用")

        result = image_adapter.generate(
            prompt=prompt,
            width=width,
            height=height,
            n=n,
            style=style,
        )

        if not result.success:
            raise ValueError(result.error_message or "生图失败")

        # 记录用量（固定成本，不依赖token价格表）
        from app.usage_logger import usage_logger
        usage_logger.log(
            platform="seedream",
            model="seedream-4.0",
            prompt_tokens=len(prompt),
            completion_tokens=0,
            total_tokens=len(prompt),
            estimated_cost=IMAGE_GENERATE_COST,
            user_id=user_id,
            task_type="image_generate",
            ref_id=task.id,
            success=True,
            source="worker",
        )

        if on_progress:
            on_progress(2, 2, "生图完成")

        return {
            "image_urls": result.image_urls,
            "task_id": result.task_id,
            "status": result.status,
            "width": result.width,
            "height": result.height,
        }
    finally:
        usage_context.reset(ctx_token)


# 注册任务处理函数
register_handler("image_generate", handle_image_generate)
