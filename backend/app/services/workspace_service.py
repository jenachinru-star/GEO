"""Workspace 服务 — 工作空间相关公共逻辑"""
import logging
from sqlalchemy.orm import Session

from app.models.workspace import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


def get_user_workspace_id(db: Session, user_id: int) -> int | None:
    """获取用户作为 owner 的工作空间ID（个人空间）。

    如果用户没有 workspace 记录（历史数据或注册时未创建），返回 None。
    """
    ws_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.role == "owner",
    ).first()
    return ws_member.workspace_id if ws_member else None


def ensure_user_workspace(db: Session, user_id: int, username: str = "") -> int:
    """确保用户有一个个人工作空间，没有则创建。

    新用户注册/自动建号时调用。返回 workspace_id。
    """
    ws_id = get_user_workspace_id(db, user_id)
    if ws_id:
        return ws_id

    # 创建个人工作空间
    ws_name = f"{username}的空间" if username else f"个人空间"
    workspace = Workspace(
        name=ws_name,
        type="personal",
        status="active",
        created_by=user_id,
    )
    db.add(workspace)
    db.flush()  # 拿到 workspace.id

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role="owner",
        status="active",
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    logger.info(f"为用户 {user_id}({username}) 创建个人工作空间: {workspace.id}")
    return workspace.id
