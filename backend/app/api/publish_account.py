"""发布平台账号管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.publish_account import PublishAccount

router = APIRouter(prefix="/api/v1/publish-accounts", tags=["发布账号"])


class AccountCreate(BaseModel):
    platform: str = Field(..., description="平台code：baijiahao/wechat/zhihu/douyin...")
    account_name: str = Field("", description="账号昵称")
    credential: str = Field("", description="登录凭证（cookie/token）")
    note: str = Field("", description="备注")


class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    credential: Optional[str] = None
    login_status: Optional[str] = None
    note: Optional[str] = None


@router.get("", summary="获取我的发布账号列表")
def list_accounts(
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(PublishAccount).filter(PublishAccount.user_id == user_id)
    if platform:
        query = query.filter(PublishAccount.platform == platform)

    items = query.order_by(PublishAccount.created_at.desc()).all()

    result = [{
        "id": a.id,
        "platform": a.platform,
        "account_name": a.account_name,
        "login_status": a.login_status,
        "note": a.note,
        "last_verified_at": a.last_verified_at.isoformat() if a.last_verified_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        # 不返回 credential 明文
    } for a in items]

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("", summary="添加发布账号")
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = PublishAccount(
        user_id=user_id,
        platform=data.platform,
        account_name=data.account_name,
        credential=data.credential,
        note=data.note,
        login_status="unknown",
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return {
        "code": 0, "message": "success",
        "data": {"id": account.id, "platform": account.platform}
    }


@router.put("/{account_id}", summary="更新发布账号")
def update_account(
    account_id: int,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if data.account_name is not None:
        account.account_name = data.account_name
    if data.credential is not None:
        account.credential = data.credential
    if data.login_status is not None:
        account.login_status = data.login_status
    if data.note is not None:
        account.note = data.note

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{account_id}", summary="删除发布账号")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    db.delete(account)
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/{account_id}/verify", summary="标记账号已验证")
def verify_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """手动标记账号登录态有效"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.login_status = "valid"
    account.last_verified_at = datetime.now()
    db.commit()
    return {"code": 0, "message": "success"}
