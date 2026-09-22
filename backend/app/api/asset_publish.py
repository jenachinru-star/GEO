"""数字资产 - GEO联动发布 API

功能：
- 从个人知识库发布内容到公开库
- AI通俗化改写（把专业内容改成患者能懂的话）
- 发布内容管理（CRUD）
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetDocument, AssetPublished
from app.adapters import adapter_factory
from app.usage_context import usage_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset/publish", tags=["数字资产-GEO发布"])


# ============ 请求体模型 ============

class PublishFromDocRequest(BaseModel):
    document_id: int  # 从哪个文档发布
    title: Optional[str] = None  # 自定义标题，不传用文档原标题
    platform: str = "glm"
    category: str = "medicine"
    tags: str = ""
    auto_rewrite: bool = True  # 是否自动AI通俗化改写


class PublishCreateRequest(BaseModel):
    title: str
    content: str
    summary: str = ""
    category: str = ""
    tags: str = ""
    keywords: str = ""
    source_document_id: Optional[int] = None


class PublishUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    keywords: Optional[str] = None
    status: Optional[str] = None  # draft / published / archived


# ============ 从文档一键发布 ============

@router.post("/from-document", summary="从文档一键发布为科普内容")
def publish_from_document(
    req: PublishFromDocRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """从个人知识库的文档一键创建发布草稿，可选AI通俗化改写"""
    doc = db.query(AssetDocument).filter(
        AssetDocument.id == req.document_id,
        AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 初始内容：用文档总结或正文前500字
    source_content = doc.summary or doc.content[:2000]
    title = req.title or doc.title

    rewritten_content = source_content
    summary = ""

    # AI通俗化改写
    if req.auto_rewrite:
        adapter = adapter_factory.get_adapter(req.platform)
        if adapter:
            ctx_token = usage_context.set(
                user_id=user_id,
                task_type="asset_publish_rewrite",
                ref_id=doc.id,
                ref_type="document",
                source="http"
            )
            try:
                system_prompt = """你是一位医学科普作家。请把下面的专业医学内容，改写成普通患者能看懂的科普文章。

要求：
1. 用通俗易懂的语言，避免专业术语（必须用的术语要解释清楚）
2. 结构清晰：开头引入→正文分点→结尾总结
3. 语气亲切，像医生在跟患者聊天
4. 不要有绝对化表述（如"百分百治愈"、"最好的药"等）
5. 不要推荐具体药物剂量
6. 保留核心医学事实，不要编造
7. 800-1500字左右

原文：
"""
                result = adapter.query(
                    f"{system_prompt}\n\n{source_content}",
                    system_prompt="你是专业的医学科普作家，擅长把专业内容改成患者能懂的话。",
                    usage_ctx={"task_type": "asset_publish_rewrite", "source": "http"}
                )
                if result.success:
                    rewritten_content = result.answer
                    # 提取前200字作为摘要
                    summary = rewritten_content[:200].replace("\n", " ") + "..."
            finally:
                usage_context.reset(ctx_token)

    # 创建草稿
    published = AssetPublished(
        user_id=user_id,
        source_document_id=doc.id,
        title=title,
        content=rewritten_content,
        summary=summary,
        category=req.category,
        tags=req.tags or doc.tags,
        status="draft",  # 草稿状态，编辑后再发布
        platform=req.platform,
    )
    db.add(published)
    db.commit()
    db.refresh(published)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": published.id,
            "title": published.title,
            "content": published.content,
            "summary": published.summary,
            "status": published.status,
        }
    }


# ============ 发布内容CRUD ============

@router.get("/stats/overview", summary="获取发布内容统计概览")
def stats_overview(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取当前用户的发布内容统计：总数、已发布、草稿、总浏览量、总引用数"""
    base_query = db.query(AssetPublished).filter(AssetPublished.user_id == user_id)

    total = base_query.count()
    published = base_query.filter(AssetPublished.status == "published").count()
    draft = base_query.filter(AssetPublished.status == "draft").count()

    view_sum = db.query(func.coalesce(func.sum(AssetPublished.view_count), 0)).filter(
        AssetPublished.user_id == user_id
    ).scalar() or 0
    citation_sum = db.query(func.coalesce(func.sum(AssetPublished.citation_count), 0)).filter(
        AssetPublished.user_id == user_id
    ).scalar() or 0

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "published": published,
            "draft": draft,
            "archived": base_query.filter(AssetPublished.status == "archived").count(),
            "total_views": int(view_sum),
            "total_citations": int(citation_sum),
        }
    }


@router.get("/list", summary="获取我的发布内容列表")
def list_published(
    status: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取用户的发布内容列表"""
    query = db.query(AssetPublished).filter(AssetPublished.user_id == user_id)
    if status:
        query = query.filter(AssetPublished.status == status)
    if category:
        query = query.filter(AssetPublished.category == category)
    if keyword:
        query = query.filter(AssetPublished.title.like(f"%{keyword}%"))

    items = query.order_by(AssetPublished.updated_at.desc()).all()

    result = [{
        "id": p.id,
        "title": p.title,
        "summary": p.summary,
        "category": p.category,
        "tags": p.tags,
        "status": p.status,
        "view_count": p.view_count,
        "citation_count": p.citation_count,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
    } for p in items]

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.get("/{pub_id}", summary="获取发布内容详情")
def get_published(
    pub_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取发布内容详情"""
    p = db.query(AssetPublished).filter(
        AssetPublished.id == pub_id,
        AssetPublished.user_id == user_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="内容不存在")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "summary": p.summary,
            "category": p.category,
            "tags": p.tags,
            "status": p.status,
            "keywords": p.keywords,
            "view_count": p.view_count,
            "citation_count": p.citation_count,
            "source_document_id": p.source_document_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
    }


@router.post("/", summary="创建新的发布内容")
def create_published(
    req: PublishCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建新的发布内容（手动新建）"""
    p = AssetPublished(
        user_id=user_id,
        source_document_id=req.source_document_id,
        title=req.title,
        content=req.content,
        summary=req.summary,
        category=req.category,
        tags=req.tags,
        keywords=req.keywords,
        status="draft",
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {"code": 0, "message": "success", "data": {"id": p.id}}


@router.put("/{pub_id}", summary="更新发布内容")
def update_published(
    pub_id: int,
    req: PublishUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新发布内容"""
    p = db.query(AssetPublished).filter(
        AssetPublished.id == pub_id,
        AssetPublished.user_id == user_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="内容不存在")

    if req.title is not None:
        p.title = req.title
    if req.content is not None:
        p.content = req.content
    if req.summary is not None:
        p.summary = req.summary
    if req.category is not None:
        p.category = req.category
    if req.tags is not None:
        p.tags = req.tags
    if req.keywords is not None:
        p.keywords = req.keywords

    # 状态变更：从草稿→已发布
    if req.status is not None and req.status != p.status:
        if req.status == "published" and p.status == "draft":
            p.published_at = datetime.now()
        p.status = req.status

    db.commit()
    return {"code": 0, "message": "success"}


@router.delete("/{pub_id}", summary="删除发布内容")
def delete_published(
    pub_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除发布内容"""
    p = db.query(AssetPublished).filter(
        AssetPublished.id == pub_id,
        AssetPublished.user_id == user_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="内容不存在")

    db.delete(p)
    db.commit()
    return {"code": 0, "message": "success"}

