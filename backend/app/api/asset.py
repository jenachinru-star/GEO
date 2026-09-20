"""数字资产 - 资产CRUD API

提供资产源的增删改查、标签分类、笔记管理等基础功能。
URL采集和文件解析通过异步任务后台执行。
"""
import os
import json
import uuid
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetSource, AssetDocument, AssetNote
from app.models.task import AsyncTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset", tags=["数字资产"])

# 文件上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "assets")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


# ============ 请求体模型 ============

class AssetCreateRequest(BaseModel):
    source_type: str = "url"  # url / file / clipboard / manual / pubmed
    title: str = ""
    url: str = ""
    source_site: str = ""
    content: str = ""  # clipboard/manual类型时直接传内容
    category: str = ""
    tags: str = ""


class AssetUpdateRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class NoteCreateRequest(BaseModel):
    document_id: int
    title: str = ""
    content: str = ""
    note_type: str = "personal"


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None


# ============ 资产源CRUD ============

@router.get("/sources", summary="获取资产源列表")
def list_sources(
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    folder_id: Optional[str] = None,  # 数字=文件夹ID，特殊值: starred / unread / reading / read
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取当前用户的资产源列表"""
    query = db.query(AssetSource).filter(AssetSource.user_id == user_id)

    if source_type:
        query = query.filter(AssetSource.source_type == source_type)
    if category:
        query = query.filter(AssetSource.category == category)
    if status:
        query = query.filter(AssetSource.status == status)
    if keyword:
        query = query.filter(
            or_(
                AssetSource.title.contains(keyword),
                AssetSource.url.contains(keyword),
                AssetSource.tags.contains(keyword),
            )
        )

    # 文件夹/特殊筛选
    if folder_id:
        if folder_id == "starred":
            query = query.filter(AssetSource.is_starred == 1)
        elif folder_id in ["unread", "reading", "read"]:
            query = query.filter(AssetSource.read_status == folder_id)
        else:
            try:
                fid = int(folder_id)
                query = query.filter(AssetSource.folder_id == fid)
            except ValueError:
                pass

    total = query.count()
    items = query.order_by(AssetSource.updated_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for s in items:
        result_items.append({
            "id": s.id,
            "source_type": s.source_type,
            "title": s.title,
            "url": s.url,
            "source_site": s.source_site,
            "status": s.status,
            "category": s.category,
            "tags": s.tags,
            "folder_id": s.folder_id,
            "is_starred": s.is_starred,
            "read_status": s.read_status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })

    return {"code": 0, "message": "success", "data": {
        "total": total,
        "items": result_items,
        "page": page,
        "page_size": page_size
    }}


@router.post("/sources", summary="创建资产源")
def create_source(
    req: AssetCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建新的资产源（收藏URL/手动添加内容）

    URL类型会自动触发异步采集任务
    """
    source = AssetSource(
        user_id=user_id,
        source_type=req.source_type,
        title=req.title,
        url=req.url,
        source_site=req.source_site,
        category=req.category,
        tags=req.tags,
        status="pending",
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # clipboard/manual类型：直接创建文档，不需要异步任务
    if req.source_type in ("clipboard", "manual") and req.content:
        doc = AssetDocument(
            source_id=source.id,
            user_id=user_id,
            title=req.title or "未命名文档",
            content=req.content,
            word_count=len(req.content),
        )
        db.add(doc)
        source.status = "completed"
        db.commit()
        return {"code": 0, "message": "success", "data": {"id": source.id, "task_id": None}}

    # URL类型：创建异步采集任务
    if req.source_type == "url" and req.url:
        task = AsyncTask(
            task_type="asset_url_collect",
            status="queued",
            progress=0,
            progress_message="等待采集",
            payload_json=json.dumps({"source_id": source.id}, ensure_ascii=False),
            created_by=user_id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"创建URL采集任务: source_id={source.id}, task_id={task.id}")
        return {"code": 0, "message": "success", "data": {"id": source.id, "task_id": task.id}}

    return {"code": 0, "message": "success", "data": {"id": source.id, "task_id": None}}


@router.post("/sources/upload", summary="上传文件创建资产源")
async def upload_source(
    file: UploadFile = File(...),
    category: str = "",
    tags: str = "",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """上传文件（TXT/MD/PDF/Word），自动解析为资产源"""
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB")

    # 保存文件
    file_ext = os.path.splitext(file.filename)[1].lower()
    saved_name = f"{uuid.uuid4().hex}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)

    with open(saved_path, 'wb') as f:
        f.write(content)

    # 创建资产源
    source = AssetSource(
        user_id=user_id,
        source_type="file",
        title=file.filename,
        file_name=file.filename,
        file_path=saved_path,
        category=category,
        tags=tags,
        status="pending",
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # 创建异步解析任务
    task = AsyncTask(
        task_type="asset_file_parse",
        status="queued",
        progress=0,
        progress_message="等待解析",
        payload_json=json.dumps({
            "source_id": source.id,
            "file_path": saved_path,
            "file_name": file.filename,
        }, ensure_ascii=False),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(f"创建文件解析任务: source_id={source.id}, task_id={task.id}")
    return {"code": 0, "message": "success", "data": {
        "id": source.id,
        "task_id": task.id,
        "file_name": file.filename,
    }}


@router.get("/sources/{source_id}", summary="获取资产源详情")
def get_source_detail(
    source_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取资产源详情（含文档内容、笔记等）"""
    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="资产不存在")

    result = {
        "id": source.id,
        "source_type": source.source_type,
        "title": source.title,
        "url": source.url,
        "source_site": source.source_site,
        "status": source.status,
        "error_message": source.error_message,
        "category": source.category,
        "tags": source.tags,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        "document": None,
        "notes": [],
    }

    # 获取文档
    doc = db.query(AssetDocument).filter(AssetDocument.source_id == source_id).first()
    if doc:
        result["document"] = {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "author": doc.author,
            "publish_date": doc.publish_date,
            "summary": doc.summary,
            "word_count": doc.word_count,
            "tags": doc.tags,
            "category": doc.category,
        }
        # 获取笔记
        notes = db.query(AssetNote).filter(
            AssetNote.document_id == doc.id,
            AssetNote.user_id == user_id
        ).order_by(AssetNote.updated_at.desc()).all()
        result["notes"] = [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "note_type": n.note_type,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ]

    return {"code": 0, "message": "success", "data": result}


@router.put("/sources/{source_id}", summary="更新资产源")
def update_source(
    source_id: int,
    req: AssetUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新资产源的标题、分类、标签"""
    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="资产不存在")

    if req.title is not None:
        source.title = req.title
    if req.category is not None:
        source.category = req.category
    if req.tags is not None:
        source.tags = req.tags

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/sources/{source_id}", summary="删除资产源")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除资产源及其关联的文档、分块、笔记"""
    source = db.query(AssetSource).filter(
        AssetSource.id == source_id,
        AssetSource.user_id == user_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="资产不存在")

    # 删除关联文件
    if source.file_path and os.path.exists(source.file_path):
        try:
            os.remove(source.file_path)
        except Exception:
            pass

    # 级联删除文档及其关联
    doc = db.query(AssetDocument).filter(AssetDocument.source_id == source_id).first()
    if doc:
        db.delete(doc)
    db.delete(source)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 笔记管理 ============

@router.post("/notes", summary="创建笔记")
def create_note(
    req: NoteCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """为文档创建笔记"""
    doc = db.query(AssetDocument).filter(
        AssetDocument.id == req.document_id,
        AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    note = AssetNote(
        document_id=req.document_id,
        user_id=user_id,
        title=req.title,
        content=req.content,
        note_type=req.note_type,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"code": 0, "message": "success", "data": {"id": note.id}}


@router.put("/notes/{note_id}", summary="更新笔记")
def update_note(
    note_id: int,
    req: NoteUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新笔记内容"""
    note = db.query(AssetNote).filter(
        AssetNote.id == note_id,
        AssetNote.user_id == user_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    if req.title is not None:
        note.title = req.title
    if req.content is not None:
        note.content = req.content
    if req.note_type is not None:
        note.note_type = req.note_type

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/notes/{note_id}", summary="删除笔记")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除笔记"""
    note = db.query(AssetNote).filter(
        AssetNote.id == note_id,
        AssetNote.user_id == user_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    db.delete(note)
    db.commit()
    return {"code": 0, "message": "success"}
