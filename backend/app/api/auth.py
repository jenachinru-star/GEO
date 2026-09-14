"""IAM认证API - 单点登录"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import secrets
import time

from app.database import get_db
from app.config import settings
from app.services.iam_service import IAMService

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# 内存存储ticket（一次性，60秒过期）
_ticket_store: dict = {}
TICKET_EXPIRE_SECONDS = 60


@router.get("/iam/url", summary="获取IAM授权地址")
def get_iam_url(db: Session = Depends(get_db)):
    """获取IAM登录授权地址，前端跳转用"""
    if not settings.iam_enabled:
        raise HTTPException(status_code=400, detail="IAM未配置")
    iam = IAMService(db)
    auth_url = iam.generate_auth_url()
    return {"code": 0, "message": "success", "data": {"auth_url": auth_url}}


@router.get("/iam/callback", summary="IAM登录回调")
def iam_callback(code: str = None, state: str = None, error: str = None,
                 error_description: str = None, db: Session = Depends(get_db)):
    """IAM登录成功后的回调处理，重定向到前端sso页面"""
    # 用户拒绝授权或配置错误
    if error:
        error_msg = error_description or error
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/sso?error={error_msg}")

    if not code or not state:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/sso?error=缺少授权参数")

    iam = IAMService(db)
    jwt_token, error_msg = iam.handle_callback(code, state)

    if error_msg:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/sso?error={error_msg}")

    # 生成一次性ticket，60秒过期
    ticket = secrets.token_hex(16)
    _ticket_store[ticket] = {
        "jwt": jwt_token,
        "expire": time.time() + TICKET_EXPIRE_SECONDS
    }

    # 重定向到前端回调落地页
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/sso?ticket={ticket}")


@router.post("/iam/exchange", summary="用ticket换取JWT")
def exchange_ticket(ticket: str):
    """前端用ticket换取JWT token（ticket一次性，过期作废）"""
    ticket_data = _ticket_store.pop(ticket, None)
    if not ticket_data:
        raise HTTPException(status_code=400, detail="ticket无效或已过期")
    if time.time() > ticket_data["expire"]:
        raise HTTPException(status_code=400, detail="ticket已过期")
    return {"code": 0, "message": "success", "data": {"token": ticket_data["jwt"]}}


@router.get("/userinfo", summary="获取当前用户信息")
def get_userinfo(request: Request, db: Session = Depends(get_db)):
    """获取当前登录用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = auth_header[7:]
    payload = IAMService.verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")

    from app.models import User
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "login_type": "iam_sso"
        }
    }


@router.post("/logout", summary="退出登录")
def logout():
    """退出登录（只清本系统会话，IAM会话保留）"""
    return {"code": 0, "message": "已退出登录"}


@router.get("/status", summary="获取IAM配置状态")
def get_iam_status():
    """获取IAM是否已配置"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "iam_enabled": settings.iam_enabled,
            "iam_host": settings.IAM_HOST
        }
    }
