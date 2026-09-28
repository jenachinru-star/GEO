"""审计日志中间件
自动记录用户关键操作（登录/发布/删除/配置修改/数据导出）。

注意：项目中没有 auth 中间件设置 request.state.user_id，
因此这里直接从 Authorization header 解析 JWT 获取用户信息（与 usage_context_middleware 同样做法）。
"""
import logging
import json
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# 需要记录审计日志的路径模式（正则匹配）
AUDIT_PATTERNS = {
    # 登录登出
    ("/api/v1/auth/local/login", "POST"): "login",
    ("/api/v1/auth/logout", "POST"): "logout",
    ("/api/v1/auth/iam/callback", "GET"): "login",
    # 发布相关
    ("/api/v1/distribution/.*/publish", "POST"): "publish",
    # 删除操作（通用匹配）
    (".*", "DELETE"): "delete",
    # 数据导出
    ("/api/v1/export/.*", "GET"): "export",
    ("/api/v1/publish-accounts/.*/articles/export", "GET"): "export",
    # 平台配置修改
    ("/api/v1/platforms/.*/toggle", "POST"): "config",
    ("/api/v1/platforms/.*", "PUT"): "config",
    # 发布账号修改
    ("/api/v1/publish-accounts", "POST"): "create",
    ("/api/v1/publish-accounts/.*", "PUT"): "update",
    # 对标账号修改
    ("/api/v1/benchmark", "POST"): "create",
    ("/api/v1/benchmark/.*", "PUT"): "update",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 先执行请求，获取响应状态
        response = await call_next(request)

        try:
            path = request.url.path
            method = request.method

            # 匹配需要记录的操作
            action = None
            for (pattern, pat_method), act in AUDIT_PATTERNS.items():
                if method == pat_method:
                    if re.fullmatch(pattern, path):
                        action = act
                        break

            if not action:
                return response

            # 只记录成功的操作（状态码2xx）
            if response.status_code >= 300:
                return response

            # 从 Authorization header 解析 JWT 获取用户信息
            user_id, username = self._extract_user_info(request)

            # 获取客户端信息
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")

            # 提取资源类型和ID
            resource_type = self._extract_resource_type(path)
            resource_id = self._extract_resource_id(path)

            # 保存审计日志（同步写入，50用户规模无性能问题）
            self._save_audit_log(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=client_ip,
                user_agent=user_agent,
                status="success",
            )

        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return response

    @staticmethod
    def _extract_user_info(request: Request):
        """从 Authorization header 解析 JWT，返回 (user_id, username)"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None, ""
        token = auth_header[7:]
        try:
            from app.services.iam_service import IAMService
            payload = IAMService.verify_jwt(token)
            if not payload:
                return None, ""
            user_id = payload.get("user_id")
            username = payload.get("username", "")
            return user_id, username
        except Exception:
            return None, ""

    @staticmethod
    def _extract_resource_type(path: str) -> str:
        """从URL路径提取资源类型"""
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            return parts[2]  # /api/v1/{resource_type}/...
        return ""

    @staticmethod
    def _extract_resource_id(path: str) -> str:
        """从URL路径提取资源ID"""
        parts = path.strip("/").split("/")
        # 查找数字ID部分
        for part in parts:
            if part.isdigit():
                return part
        return ""

    @staticmethod
    def _save_audit_log(**kwargs):
        """保存审计日志到数据库"""
        try:
            db = SessionLocal()
            log = AuditLog(**kwargs)
            db.add(log)
            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"保存审计日志失败: {e}")
