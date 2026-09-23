"""API 速率限制中间件

简单的内存限流：按客户端IP统计每分钟请求数，超过限制返回429。
适用于单实例部署，多实例部署需改用Redis等共享存储。
"""
import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于IP的速率限制中间件"""

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 健康检查接口不限流
        if request.url.path in ("/", "/api/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 清理1分钟前的记录
        self._requests[client_ip] = [t for t in self._requests[client_ip] if now - t < 60]

        if len(self._requests[client_ip]) >= self.requests_per_minute:
            logger.warning("速率限制: IP=%s 已达每分钟%d次请求上限", client_ip, self.requests_per_minute)
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response
