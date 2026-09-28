"""全局错误处理中间件
统一异常处理，统一错误码和错误响应格式。

注意：必须重新抛出 HTTPException，让 FastAPI 默认处理器返回正确的 401/403/404 状态码，
否则 generic except Exception 会把它们全部变成 500。
"""
import logging
import traceback
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # 重新抛出，让 FastAPI 默认处理器返回正确状态码和 detail
            raise
        except RequestValidationError as e:
            # 请求参数验证错误
            logger.warning(f"请求参数验证错误: {e.errors()}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "code": 422,
                    "message": "请求参数错误",
                    "errors": e.errors(),
                }
            )
        except ValueError as e:
            # 业务逻辑错误
            logger.warning(f"业务逻辑错误: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "code": 400,
                    "message": str(e),
                }
            )
        except PermissionError as e:
            # 权限错误
            logger.warning(f"权限错误: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "code": 403,
                    "message": "没有权限执行此操作",
                }
            )
        except Exception as e:
            # 未捕获的异常
            error_detail = traceback.format_exc()
            logger.error(f"未捕获的异常: {e}\n{error_detail}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": 500,
                    "message": "服务器内部错误，请稍后重试",
                    "error_type": type(e).__name__,
                }
            )
