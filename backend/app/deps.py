"""通用依赖注入"""
from fastapi import Depends, HTTPException, Request
from app.services.iam_service import IAMService
from app.database import SessionLocal
from app.models.user import User


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


def get_current_admin_id(user_id: int = Depends(get_current_user_id)) -> int:
    """获取当前管理员用户ID。非管理员返回403。"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="需要管理员权限")
        return user_id
    finally:
        db.close()
