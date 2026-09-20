"""
Worker 主进程 — 从数据库轮询 queued 状态的任务并执行。

启动方式：
    cd backend
    set APP_ROLE=worker
    python -m app.worker.worker

注意：
- API 进程不要启动 Worker（通过 APP_ROLE 环境变量区分）
- Worker 单进程运行，不做多实例并发（避免任务重复执行）
- 任务执行超时默认 600 秒，超时后标记为 failed
"""
import os
import sys
import time
import json
import logging
import signal
import traceback
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.task import AsyncTask
from app.worker.task_registry import get_handler, get_all_task_types, ProgressCallback
# 导入任务处理模块以触发注册
import app.worker.collector_tasks  # noqa: F401
import app.worker.asset_tasks  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worker")

# 全局运行标志
_running = True
TASK_TIMEOUT_SECONDS = 600  # 任务超时时间
POLL_INTERVAL = 3  # 轮询间隔（秒）


def get_friendly_error(e: Exception) -> str:
    """将 Python 异常转换为用户友好的中文提示，原始错误只记日志不暴露给前端"""
    error_type = type(e).__name__
    error_msg = str(e)

    # 按异常类型映射
    type_mapping = {
        "AttributeError": "系统配置缺失，请联系管理员",
        "ValueError": f"任务参数错误：{error_msg}",
        "ConnectionError": "网络连接失败，请检查网络后重试",
        "TimeoutError": "外部 API 响应超时，请稍后重试",
        "KeyError": "数据字段缺失，请检查配置后重试",
        "TypeError": "数据格式错误，请联系管理员",
        "ImportError": "系统模块加载失败，请联系管理员",
        "OperationalError": "数据库操作失败，请稍后重试",
        "IntegrityError": "数据冲突，请稍后重试",
        "ProgrammingError": "数据库查询失败，请联系管理员",
        "InterfaceError": "数据库接口异常，请稍后重试",
    }

    if error_type in type_mapping:
        return type_mapping[error_type]

    # 按错误内容关键词匹配（兜底）
    msg_lower = error_msg.lower()
    if "brand_aliases" in error_msg:
        return "系统配置缺失，请联系管理员"
    if "timeout" in msg_lower or "timed out" in msg_lower:
        return "请求超时，请稍后重试"
    if "connection" in msg_lower or "refused" in msg_lower:
        return "网络连接失败，请检查网络后重试"
    if "api key" in msg_lower or "apikey" in msg_lower or "unauthorized" in msg_lower:
        return "平台 API 密钥未配置或已失效，请检查平台配置"
    if "rate limit" in msg_lower or "too many requests" in msg_lower:
        return "平台调用频率超限，请稍后重试"

    # 默认友好提示（不暴露异常类型名和原始信息）
    return "任务执行失败，请稍后重试"


def signal_handler(signum, frame):
    """优雅退出"""
    global _running
    logger.info(f"收到信号 {signum}，准备退出...")
    _running = False


def claim_next_task(db: Session) -> AsyncTask | None:
    """认领下一个 queued 任务（先到先得，单Worker模式下直接取第一个）"""
    task = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).first()

    if task:
        task.status = "running"
        task.started_at = datetime.now()
        task.progress_message = "任务开始执行"
        db.commit()
        db.refresh(task)
        logger.info(f"认领任务 #{task.id} (type={task.task_type})")
    return task


def execute_task(db: Session, task: AsyncTask, on_progress: ProgressCallback = None):
    """执行单个任务"""
    handler = get_handler(task.task_type)
    if not handler:
        raise ValueError(f"未注册的任务类型: {task.task_type}，已注册类型: {get_all_task_types()}")

    result = handler(db, task, on_progress)
    return result


def complete_task(db: Session, task: AsyncTask, result: dict = None, error: str = None):
    """完成任务（成功或失败）"""
    if error:
        task.status = "failed"
        task.error_message = error[:2000] if error else ""
        task.progress_message = "执行失败"
        logger.error(f"任务 #{task.id} 失败: {error[:200]}")
    else:
        task.status = "succeeded"
        task.progress = 100
        task.progress_message = "执行完成"
        task.result_json = json.dumps(result or {}, ensure_ascii=False)
        logger.info(f"任务 #{task.id} 完成")

    task.finished_at = datetime.now()
    db.commit()


def recover_stuck_tasks(db: Session):
    """恢复卡住的任务（running超过超时时间的标记为failed）"""
    timeout_threshold = datetime.now() - timedelta(seconds=TASK_TIMEOUT_SECONDS)
    stuck_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "running",
        AsyncTask.started_at < timeout_threshold
    ).all()

    for task in stuck_tasks:
        logger.warning(f"任务 #{task.id} 超时（started_at={task.started_at}），标记为failed")
        task.status = "failed"
        task.error_message = f"任务执行超时（>{TASK_TIMEOUT_SECONDS}秒）"
        task.finished_at = datetime.now()
    db.commit()


def run_worker_loop():
    """Worker 主循环（不注册 signal，可在子线程中运行）"""
    global _running
    _running = True

    logger.info("=" * 50)
    logger.info("GEO Worker 启动（内嵌模式）")
    logger.info(f"已注册任务类型: {get_all_task_types()}")
    logger.info(f"轮询间隔: {POLL_INTERVAL}秒 | 任务超时: {TASK_TIMEOUT_SECONDS}秒")
    logger.info("=" * 50)

    while _running:
        try:
            db = SessionLocal()

            # 1. 恢复卡住的任务
            recover_stuck_tasks(db)

            # 2. 认领并执行任务
            task = claim_next_task(db)
            if task:
                # 进度回调：更新任务进度和说明到数据库
                def on_progress(current: int, total: int, message: str):
                    task.progress = int(current / total * 100) if total > 0 else 100
                    short_msg = message[:80] if message else ""
                    task.progress_message = f"[{current}/{total}] {short_msg}"
                    db.commit()
                    logger.info(f"任务 #{task.id} 进度: {task.progress}% ({current}/{total}) {short_msg}")

                try:
                    result = execute_task(db, task, on_progress)
                    complete_task(db, task, result=result)
                except Exception as e:
                    db.rollback()
                    # 原始错误完整信息记日志（含 traceback），不暴露给前端
                    raw_error = f"{type(e).__name__}: {str(e)}"
                    logger.error(f"任务 #{task.id} 失败: {raw_error}\n{traceback.format_exc()}")
                    # 友好化错误信息存数据库，前端展示中文提示
                    friendly_msg = get_friendly_error(e)
                    complete_task(db, task, error=friendly_msg)
            else:
                # 没有任务，等待
                time.sleep(POLL_INTERVAL)

            db.close()

        except Exception as e:
            logger.error(f"Worker 主循环异常: {type(e).__name__}: {e}")
            time.sleep(POLL_INTERVAL)

    logger.info("Worker 已退出")


def stop_worker_loop():
    """停止 Worker 循环（供外部调用）"""
    global _running
    _running = False
    logger.info("收到停止信号，Worker 即将退出...")


def main():
    """Worker 主循环（独立进程模式，注册 signal）"""
    global _running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    run_worker_loop()


if __name__ == "__main__":
    main()
