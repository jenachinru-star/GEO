"""
Worker 主进程 — 从数据库轮询 queued 状态的任务并执行。

启动方式：
    cd backend
    set APP_ROLE=worker
    python -m app.worker.worker

注意：
- API 进程不要启动 Worker（通过 APP_ROLE 环境变量区分）
- Worker 单进程运行，不做多实例并发（避免任务重复执行）
- 任务执行超时按任务类型动态调整，超时后标记为 cancelling，由执行线程自行终止
"""
import os
import sys
import time
import json
import logging
import signal
import threading
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
import app.worker.article_tasks  # noqa: F401
import app.worker.compliance_tasks  # noqa: F401
import app.worker.image_tasks  # noqa: F401
import app.worker.export_tasks  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worker")


class TaskCancelledError(Exception):
    """任务被取消时抛出，用于在执行链中传递取消信号（协作式取消）"""
    pass


# 全局运行标志
_running = True
POLL_INTERVAL = 3  # 轮询间隔（秒）
_last_executed_user = None  # 上一次执行任务的用户ID，用于轮询调度
_last_user_lock = threading.Lock()  # 保护 _last_executed_user 的多线程读写

# 任务超时时间（按任务类型），全量采集需要更长时间
TASK_TIMEOUT_BY_TYPE = {
    "geo_refresh": 3600,      # GEO全量采集：1小时（19语义×4平台并发约15分钟）
    "monitor_collect": 1800,  # 品牌监测采集：30分钟
    "asset_url_collect": 600, # 资产URL采集：10分钟
    "asset_file_parse": 300,  # 资产文件解析：5分钟
    "article_generate": 600,  # 文章生成：最多120秒，600秒留5倍余量
    "compliance_check": 300,  # 合规检查：5-30秒
    "image_generate": 300,    # 生图：5-30秒
}
TASK_TIMEOUT_DEFAULT = 600  # 默认超时时间
CANCEL_GRACE_SECONDS = 300  # cancelling状态宽限期：超过此时间仍未终止则强制failed


def get_task_timeout(task_type: str) -> int:
    """根据任务类型获取超时时间"""
    return TASK_TIMEOUT_BY_TYPE.get(task_type, TASK_TIMEOUT_DEFAULT)


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
    """认领下一个 queued 任务（按用户轮询调度，多线程安全）"""
    global _last_executed_user

    # 先查所有 queued 任务，按创建时间排序
    queued_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).all()

    if not queued_tasks:
        return None

    # 按用户轮询：优先选择与上一次执行用户不同的任务
    selected_task = None
    with _last_user_lock:
        prev_user = _last_executed_user
    if prev_user is not None:
        # 找第一个不是上一次用户的任务
        for t in queued_tasks:
            if t.created_by != prev_user:
                selected_task = t
                break
    # 如果所有任务都是上一次用户的，或者没有上一次用户记录，选最早的
    if selected_task is None:
        selected_task = queued_tasks[0]

    # 用原子UPDATE认领：只有status仍是queued时才更新成功
    from sqlalchemy import update as sa_update
    result = db.execute(
        sa_update(AsyncTask)
        .where(AsyncTask.id == selected_task.id, AsyncTask.status == "queued")
        .values(
            status="running",
            started_at=datetime.now(),
            progress_message="任务开始执行",
        )
    )
    db.commit()

    if result.rowcount == 0:
        # 被其他线程认领了
        return None

    db.refresh(selected_task)

    # 记录上一次执行的用户，用于轮询（加锁保护）
    with _last_user_lock:
        _last_executed_user = selected_task.created_by

    # 排队超时检查：任务在队列中等待过久（超过该任务类型超时的2倍），直接标记failed不执行
    queue_timeout = get_task_timeout(selected_task.task_type) * 2
    if selected_task.created_at and (datetime.utcnow() - selected_task.created_at).total_seconds() > queue_timeout:
        logger.warning(f"任务 #{selected_task.id} 排队超时（created_at={selected_task.created_at}, 阈值={queue_timeout}s），标记为failed")
        selected_task.status = "failed"
        selected_task.error_message = "任务排队超时"
        selected_task.finished_at = datetime.utcnow()
        db.commit()
        return None

    logger.info(f"认领任务 #{selected_task.id} (type={selected_task.task_type}, user={selected_task.created_by})")
    return selected_task


def execute_task(db: Session, task: AsyncTask, on_progress: ProgressCallback = None):
    """执行单个任务"""
    handler = get_handler(task.task_type)
    if not handler:
        raise ValueError(f"未注册的任务类型: {task.task_type}，已注册类型: {get_all_task_types()}")

    # 设置 usage_context，让 adapter 层能记录用量和检查配额
    from app.usage_context import usage_context
    ctx_token = usage_context.set(
        user_id=task.created_by,
        task_type=task.task_type,
        ref_id=task.id,
        ref_type="async_task",
        source="worker",
    )

    try:
        result = handler(db, task, on_progress)
        return result
    finally:
        usage_context.reset(ctx_token)


def complete_task(db: Session, task: AsyncTask, result: dict = None, error: str = None):
    """完成任务（成功或失败）"""
    # 状态防御：已经是终态的任务不允许再改
    if task.status in ("succeeded", "failed", "cancelled"):
        logger.warning(f"任务 #{task.id} 已处于终态 {task.status}，忽略 complete_task 调用")
        return
    # 如果任务被标记为 cancelling，只允许转 failed，不允许转 succeeded
    if task.status == "cancelling" and not error:
        logger.warning(f"任务 #{task.id} 处于 cancelling 状态，不允许标记为成功，按失败处理")
        error = error or "任务执行超时，已自动取消"

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
    """恢复卡住的任务：
    1. running超过该任务类型超时时间 → 标记为cancelling，由执行线程自行终止
    2. cancelling超过宽限期仍未终止 → 强制标记为failed（执行线程可能已崩溃）
    """
    now = datetime.now()

    # 1. running 超时 → cancelling
    running_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "running",
        AsyncTask.started_at.isnot(None)
    ).all()

    for task in running_tasks:
        timeout = get_task_timeout(task.task_type)
        elapsed = (now - task.started_at).total_seconds()
        if elapsed > timeout:
            logger.warning(f"任务 #{task.id} 超时（type={task.task_type}, elapsed={elapsed:.0f}s > {timeout}s），标记为cancelling，等待执行线程终止")
            task.status = "cancelling"
            task.error_message = f"任务执行超时（>{timeout}秒），正在取消..."
            task.progress_message = "任务超时，正在取消..."

    # 2. cancelling 卡死 → 强制 failed（执行线程可能已崩溃，无法响应取消）
    cancelling_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "cancelling",
        AsyncTask.started_at.isnot(None)
    ).all()

    for task in cancelling_tasks:
        timeout = get_task_timeout(task.task_type)
        elapsed = (now - task.started_at).total_seconds()
        # 任务被标记cancelling时已经running超过timeout，再给CANCEL_GRACE_SECONDS宽限期
        if elapsed > timeout + CANCEL_GRACE_SECONDS:
            logger.warning(f"任务 #{task.id} 处于cancelling状态过久（elapsed={elapsed:.0f}s > {timeout + CANCEL_GRACE_SECONDS}s），执行线程可能已崩溃，强制标记为failed")
            task.status = "failed"
            task.error_message = "任务执行超时，已自动取消（执行线程无响应）"
            task.progress_message = "任务超时，已强制取消"
            task.finished_at = now

    db.commit()


def run_worker_loop():
    """Worker 主循环（不注册 signal，可在子线程中运行）"""
    global _running
    _running = True

    logger.info("=" * 50)
    logger.info("GEO Worker 启动（内嵌模式）")
    logger.info(f"已注册任务类型: {get_all_task_types()}")
    logger.info(f"轮询间隔: {POLL_INTERVAL}秒 | 任务超时: 按任务类型动态调整（默认{TASK_TIMEOUT_DEFAULT}秒）")
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
                    # 检查任务是否被取消（recover_stuck_tasks标记cancelling，或用户取消标记cancelled）
                    db.refresh(task)
                    if task.status in ("cancelling", "cancelled"):
                        logger.warning(f"任务 #{task.id} 被取消（status={task.status}），中断执行（进度 {current}/{total}）")
                        raise TaskCancelledError(f"任务被取消，状态={task.status}")
                    task.progress = int(current / total * 100) if total > 0 else 100
                    short_msg = message[:80] if message else ""
                    task.progress_message = f"[{current}/{total}] {short_msg}"
                    db.commit()
                    logger.info(f"任务 #{task.id} 进度: {task.progress}% ({current}/{total}) {short_msg}")

                try:
                    result = execute_task(db, task, on_progress)
                    # 检查是否被取消（执行过程中可能被标记为cancelling）
                    db.refresh(task)
                    if task.status == "cancelling":
                        logger.info(f"任务 #{task.id} 执行完毕但已被标记取消，按失败处理")
                        complete_task(db, task, error="任务执行超时，已自动取消")
                    else:
                        complete_task(db, task, result=result)
                except TaskCancelledError as e:
                    # 任务被取消（超时或用户主动取消），按失败处理
                    db.rollback()
                    logger.warning(f"任务 #{task.id} 因取消信号终止: {e}")
                    complete_task(db, task, error="任务执行超时，已自动取消")
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
