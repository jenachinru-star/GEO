"""数字资产 - 文件夹管理 API

功能：
- 文件夹CRUD
- 文章移动到文件夹
- 标记已读/未读/星标
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetFolder, AssetSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset/folders", tags=["数字资产-文件夹"])


# ============ 请求模型 ============

class FolderCreateRequest(BaseModel):
    name: str
    parent_id: int = 0


class FolderUpdateRequest(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class MoveItemsRequest(BaseModel):
    source_ids: list[int]
    folder_id: Optional[int] = None  # None=移动到根目录


# ============ 初始化系统文件夹 ============

def init_system_folders(db: Session, user_id: int):
    """首次使用时，给用户创建系统预置文件夹"""
    existing = db.query(AssetFolder).filter(
        AssetFolder.user_id == user_id,
        AssetFolder.is_system == 1
    ).first()
    if existing:
        return

    system_folders = [
        {"name": "待读", "sort_order": 1},
        {"name": "已读", "sort_order": 2},
        {"name": "已收藏", "sort_order": 3},
    ]

    for f in system_folders:
        folder = AssetFolder(
            user_id=user_id,
            name=f["name"],
            parent_id=0,
            sort_order=f["sort_order"],
            is_system=1,
        )
        db.add(folder)
    db.commit()


# ============ 文件夹CRUD ============

@router.get("/tree", summary="获取文件夹树")
def get_folder_tree(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取用户的文件夹树（两级）"""
    # 确保系统文件夹存在
    init_system_folders(db, user_id)

    folders = db.query(AssetFolder).filter(
        AssetFolder.user_id == user_id
    ).order_by(AssetFolder.sort_order, AssetFolder.created_at).all()

    # 构建两级树
    root_folders = [f for f in folders if f.parent_id == 0]
    result = []

    for rf in root_folders:
        children = [f for f in folders if f.parent_id == rf.id]
        result.append({
            "id": rf.id,
            "name": rf.name,
            "parent_id": rf.parent_id,
            "is_system": rf.is_system,
            "sort_order": rf.sort_order,
            "children": [{
                "id": c.id,
                "name": c.name,
                "parent_id": c.parent_id,
                "is_system": c.is_system,
                "sort_order": c.sort_order,
            } for c in children]
        })

    return {"code": 0, "message": "success", "data": {"folders": result}}


@router.post("/", summary="新建文件夹")
def create_folder(
    req: FolderCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """新建文件夹"""
    folder = AssetFolder(
        user_id=user_id,
        name=req.name,
        parent_id=req.parent_id,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return {"code": 0, "message": "success", "data": {"id": folder.id}}


@router.put("/{folder_id}", summary="更新文件夹")
def update_folder(
    folder_id: int,
    req: FolderUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新文件夹（重命名/排序）"""
    folder = db.query(AssetFolder).filter(
        AssetFolder.id == folder_id,
        AssetFolder.user_id == user_id
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    if req.name is not None:
        folder.name = req.name
    if req.sort_order is not None:
        folder.sort_order = req.sort_order

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{folder_id}", summary="删除文件夹")
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除文件夹（系统预置文件夹不能删）"""
    folder = db.query(AssetFolder).filter(
        AssetFolder.id == folder_id,
        AssetFolder.user_id == user_id
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    if folder.is_system:
        raise HTTPException(status_code=400, detail="系统预置文件夹不能删除")

    # 把文件夹里的文章移到根目录
    db.query(AssetSource).filter(
        AssetSource.folder_id == folder_id
    ).update({"folder_id": None})

    db.delete(folder)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 文章操作 ============

@router.post("/move", summary="批量移动文章到文件夹")
def move_items(
    req: MoveItemsRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """批量移动文章到指定文件夹"""
    db.query(AssetSource).filter(
        AssetSource.id.in_(req.source_ids),
        AssetSource.user_id == user_id
    ).update({"folder_id": req.folder_id}, synchronize_session=False)
    db.commit()
    return {"code": 0, "message": "success"}


@router.post("/{source_id}/star", summary="切换星标收藏")
def toggle_star(
    source_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """切换星标状态"""
    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="内容不存在")

    source.is_starred = 0 if source.is_starred else 1
    db.commit()
    return {"code": 0, "message": "success", "data": {"is_starred": source.is_starred}}


@router.post("/{source_id}/read-status", summary="更新阅读状态")
def update_read_status(
    source_id: int,
    status: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新阅读状态：unread / reading / read"""
    if status not in ["unread", "reading", "read"]:
        raise HTTPException(status_code=400, detail="状态值不合法")

    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="内容不存在")

    source.read_status = status
    db.commit()
    return {"code": 0, "message": "success"}
