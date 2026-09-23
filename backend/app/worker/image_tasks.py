"""生图相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.adapters import adapter_factory
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_image_generate(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理生图任务"""
    payload = json.loads(task.payload_json or "{}")
    prompt = payload.get("prompt", "")
    width = payload.get("width", 1024)
    height = payload.get("height", 1024)
    n = payload.get("n", 1)
    style = payload.get("style")

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

    if on_progress:
        on_progress(2, 2, "生图完成")

    return {
        "image_urls": result.image_urls,
        "task_id": result.task_id,
        "status": result.status,
        "width": result.width,
        "height": result.height,
    }


# 注册任务处理函数
register_handler("image_generate", handle_image_generate)
