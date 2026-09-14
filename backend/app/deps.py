"""通用依赖注入"""
from fastapi import Depends, HTTPException, Request
from app.services.iam_service import IAMService


def get_current_user_id(request: Request) -> int:
    """从JWT中提取当前用户ID。未登录或token无效返回401。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth_header[7:]
    payload = IAMService.verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return payload["user_id"]
