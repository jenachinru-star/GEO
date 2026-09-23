"""LLM 用量日志记录器 — 异步批量写入，不阻塞主流程

设计思路：
- 适配器调用 log() 时只是把数据放入队列，立即返回
- 后台线程从队列取数据，批量写入数据库（默认每 1 秒或每 100 条写一次）
- 应用退出时调用 flush() 确保队列中数据全部写入
- 后台线程使用独立的 DB Session，不影响主线程

用法：
    from app.usage_logger import usage_logger

    usage_logger.log(
        platform="glm",
        model="glm-4-flash",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        user_id=1,
        task_type="geo_collect",
        ref_id=123,
        success=True,
        latency_ms=500,
    )
"""
import queue
import threading
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class UsageLogger:
    """LLM 用量异步日志记录器"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0, max_queue_size: int = 10000):
        """
        Args:
            batch_size: 批量写入的最大条数
            flush_interval: 定时刷新间隔（秒）
            max_queue_size: 队列最大长度，满时丢弃最旧记录（防止OOM）
        """
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_queue_size = max_queue_size
        self._dropped_count = 0  # 丢弃计数
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """启动后台写入线程"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="llm-usage-logger"
            )
            self._worker_thread.start()
            logger.info("✅ LLM 用量日志记录器已启动（batch_size=%d, flush_interval=%.1fs）",
                        self._batch_size, self._flush_interval)

    def stop(self, flush: bool = True):
        """停止后台写入线程

        Args:
            flush: 是否在停止前刷新队列中剩余数据
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

        if flush:
            self.flush()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("🛑 LLM 用量日志记录器已停止")

    def log(self, **kwargs):
        """记录一条 LLM 调用用量（非阻塞，仅入队）

        Args:
            platform: 平台代码（deepseek/glm/minimax）
            model: 模型名称
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            total_tokens: 总 token 数
            user_id: 用户 ID
            workspace_id: 工作空间 ID
            task_type: 任务类型
            ref_id: 关联业务 ID
            ref_type: 关联业务类型
            success: 是否成功
            error_type: 错误类型
            latency_ms: 耗时（毫秒）
            source: 来源（http/worker/system）
        """
        if not self._running:
            # 记录器未启动时直接丢弃（避免阻塞），但记一条 warning
            logger.debug("LLM 用量记录器未启动，丢弃日志: %s", kwargs.get("task_type", "unknown"))
            return

        # 计算估算成本（如果调用方已显式传入 estimated_cost 则优先使用）
        if "estimated_cost" not in kwargs:
            estimated_cost = self._calc_cost(
                kwargs.get("platform", ""),
                kwargs.get("model", ""),
                kwargs.get("prompt_tokens", 0),
                kwargs.get("completion_tokens", 0),
            )
            kwargs["estimated_cost"] = estimated_cost
        # 显式记录调用时间（本地时间，避免 SQLite func.now() 返回 UTC）
        kwargs["created_at"] = datetime.now()

        try:
            self._queue.put_nowait(kwargs)
        except queue.Full:
            self._dropped_count += 1
            # 每100条打一次warning，避免日志洪水
            if self._dropped_count % 100 == 0:
                logger.warning("用量日志队列已满（maxsize=%d），已丢弃 %d 条记录",
                               self._max_queue_size, self._dropped_count)

    def flush(self):
        """立即将队列中所有数据写入数据库（阻塞）"""
        batch = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break

        if batch:
            self._write_batch(batch)
            logger.info("📝 手动刷新 LLM 用量日志: %d 条", len(batch))

    def _worker_loop(self):
        """后台线程主循环：定时批量写入"""
        while self._running:
            time.sleep(self._flush_interval)

            batch = []
            while len(batch) < self._batch_size and not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    batch.append(item)
                except queue.Empty:
                    break

            if batch:
                try:
                    self._write_batch(batch)
                except Exception as e:
                    logger.error("LLM 用量日志批量写入失败: %s", e, exc_info=True)

    def _write_batch(self, batch: list):
        """批量写入数据库（在后台线程中调用，使用独立 Session）"""
        from app.database import SessionLocal
        from app.models.usage import LlmUsageLog

        db = SessionLocal()
        try:
            records = []
            for item in batch:
                record = LlmUsageLog(
                    user_id=item.get("user_id"),
                    workspace_id=item.get("workspace_id"),
                    platform=item.get("platform", "unknown"),
                    model=item.get("model", "unknown"),
                    prompt_tokens=item.get("prompt_tokens", 0),
                    completion_tokens=item.get("completion_tokens", 0),
                    total_tokens=item.get("total_tokens", 0),
                    estimated_cost=item.get("estimated_cost", 0.0),
                    task_type=item.get("task_type"),
                    ref_id=item.get("ref_id"),
                    ref_type=item.get("ref_type"),
                    success=item.get("success", True),
                    error_type=item.get("error_type"),
                    latency_ms=item.get("latency_ms", 0),
                    source=item.get("source", "http"),
                    created_at=item.get("created_at"),
                )
                records.append(record)

            db.add_all(records)
            db.commit()
            logger.debug("LLM 用量日志批量写入: %d 条", len(records))
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def _calc_cost(platform: str, model: str,
                    prompt_tokens: int, completion_tokens: int) -> float:
        """根据模型单价计算估算成本（元人民币）

        价格从 settings.MODEL_PRICING 读取，未配置时返回 0.0
        价格单位：元 / 百万 token
        """
        pricing = getattr(settings, "MODEL_PRICING", {})
        if not pricing:
            return 0.0

        # 按 platform + model 查找，找不到则按 platform 查找，再找不到返回 0
        key = f"{platform}/{model}"
        if key in pricing:
            price = pricing[key]
        elif platform in pricing:
            price = pricing[platform]
        else:
            return 0.0

        input_price = price.get("input", 0)    # 元/百万 token
        output_price = price.get("output", 0)  # 元/百万 token

        cost = (prompt_tokens / 1_000_000) * input_price + \
               (completion_tokens / 1_000_000) * output_price
        return round(cost, 6)

    @property
    def queue_size(self) -> int:
        """当前队列中待写入的条数"""
        return self._queue.qsize()


# 全局单例
usage_logger = UsageLogger()
