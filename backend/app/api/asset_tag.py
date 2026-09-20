"""数字资产 - 标签管理 API

功能：
- 标签CRUD
- 文章打标签/取消标签
- 按标签筛选文章
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetTag, AssetSource, AssetSourceTag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset/tags", tags=["数字资产-标签"])


# ============ 请求模型 ============

class TagCreateRequest(BaseModel):
    name: str
    color: str = "blue"


class TagUpdateRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class SetTagsRequest(BaseModel):
    source_id: int
    tag_ids: List[int]


# ============ 标签CRUD ============

@router.get("/", summary="获取我的标签列表")
def list_tags(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取用户的所有标签，带文章数统计"""
    tags = db.query(AssetTag).filter(
        AssetTag.user_id == user_id
    ).order_by(AssetTag.sort_order, AssetTag.created_at).all()

    result = []
    for tag in tags:
        # 统计每个标签下的文章数
        count = db.query(func.count(AssetSourceTag.id)).filter(
            AssetSourceTag.tag_id == tag.id
        ).scalar() or 0

        result.append({
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "count": count,
        })

    return {"code": 0, "message": "success", "data": {"tags": result}}


@router.post("/", summary="新建标签")
def create_tag(
    req: TagCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """新建标签"""
    # 检查重名
    existing = db.query(AssetTag).filter(
        AssetTag.user_id == user_id,
        AssetTag.name == req.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签已存在")

    tag = AssetTag(
        user_id=user_id,
        name=req.name,
        color=req.color,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    return {"code": 0, "message": "success", "data": {"id": tag.id}}


@router.put("/{tag_id}", summary="更新标签")
def update_tag(
    tag_id: int,
    req: TagUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新标签（重命名/改颜色）"""
    tag = db.query(AssetTag).filter(
        AssetTag.id == tag_id,
        AssetTag.user_id == user_id
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    if req.name is not None:
        tag.name = req.name
    if req.color is not None:
        tag.color = req.color

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{tag_id}", summary="删除标签")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除标签（同时删除文章和标签的关联）"""
    tag = db.query(AssetTag).filter(
        AssetTag.id == tag_id,
        AssetTag.user_id == user_id
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    # 删除关联
    db.query(AssetSourceTag).filter(AssetSourceTag.tag_id == tag_id).delete()
    # 删除标签
    db.delete(tag)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 文章打标签 ============

@router.post("/set", summary="给文章设置标签（覆盖式）")
def set_tags_to_source(
    req: SetTagsRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """给文章设置标签（覆盖式，先删旧关联再建新的）"""
    source = db.query(AssetSource).filter(
        AssetSource.id == req.source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="内容不存在")

    # 删除旧关联
    db.query(AssetSourceTag).filter(AssetSourceTag.source_id == req.source_id).delete()

    # 建新关联
    for tag_id in req.tag_ids:
        # 验证标签属于当前用户
        tag = db.query(AssetTag).filter(
            AssetTag.id == tag_id,
            AssetTag.user_id == user_id
        ).first()
        if tag:
            link = AssetSourceTag(source_id=req.source_id, tag_id=tag_id)
            db.add(link)

    db.commit()
    return {"code": 0, "message": "success"}


@router.get("/{source_id}/get", summary="获取文章的标签")
def get_source_tags(
    source_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取某篇文章的所有标签"""
    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="内容不存在")

    links = db.query(AssetSourceTag).filter(AssetSourceTag.source_id == source_id).all()
    tag_ids = [link.tag_id for link in links]

    tags = db.query(AssetTag).filter(AssetTag.id.in_(tag_ids)).all()
    result = [{"id": t.id, "name": t.name, "color": t.color} for t in tags]

    return {"code": 0, "message": "success", "data": {"tags": result}}
