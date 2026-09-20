"""LLM 用量上下文管理 — 基于 contextvars 的用户/任务上下文传递

设计思路：
- HTTP 请求链路：在 get_current_user_id 依赖中设置 user_id
- Worker 异步任务：在 execute_task 入口设置 user_id + task_type + ref_id
- 适配器层：自动读取上下文，无需调用方显式传参
- 特殊场景：可通过 usage_ctx 参数显式覆盖

用法：
    from app.usage_context import usage_context

    # 设置上下文（with 语句自动清理）
    with usage_context.set(user_id=1, task_type="geo_collect", ref_id=123):
        adapter.query(question)

    # 或手动设置/清理
    token = usage_context.set(user_id=1, task_type="rag")
    try:
        adapter.query(question)
    finally:
        usage_context.reset(token)
"""
import contextvars
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ContextVar：每个 asyncio task / 线程有独立副本
_usage_ctx_var: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "llm_usage_context",
    default=None
)


class UsageContext:
    """LLM 用量上下文管理器"""

    @staticmethod
    def get() -> Optional[Dict[str, Any]]:
        """获取当前上下文"""
        return _usage_ctx_var.get()

    @staticmethod
    def set(**kwargs) -> contextvars.Token:
        """设置上下文，返回 Token 用于 reset

        支持的字段：
            user_id: int
            workspace_id: int
            task_type: str  (geo_collect / semantic_extend / article_gen / rag / llm_analyze / other)
            ref_id: int
            ref_type: str
            source: str  (http / worker / system)
        """
        ctx = dict(kwargs)
        return _usage_ctx_var.set(ctx)

    @staticmethod
    def reset(token: contextvars.Token):
        """重置上下文到设置前的状态"""
        _usage_ctx_var.reset(token)

    @staticmethod
    def clear():
        """清空上下文"""
        _usage_ctx_var.set(None)

    @staticmethod
    def merge(override: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """合并当前上下文与显式覆盖参数（显式参数优先级更高）"""
        current = _usage_ctx_var.get()
        if override:
            merged = dict(current) if current else {}
            merged.update({k: v for k, v in override.items() if v is not None})
            return merged
        return current

    @staticmethod
    def scope(**kwargs):
        """上下文管理器，with 语句自动设置和清理

        用法：
            with usage_context.scope(user_id=1, task_type="rag"):
                adapter.query(question)
        """
        return _UsageContextScope(**kwargs)


class _UsageContextScope:
    """with 语句上下文管理器"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.token = None

    def __enter__(self):
        self.token = _usage_ctx_var.set(dict(self.kwargs))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _usage_ctx_var.reset(self.token)
        return False  # 不吞异常


# 全局单例
usage_context = UsageContext()
