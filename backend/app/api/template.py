from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.deps import get_current_user_id
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.article import ArticleDraft
from app.models.content_opportunity import ContentOpportunity
from app.engines.article_template import article_template_engine
from app.engines.article_generator import ArticleGenerator
from app.engines.llms_generator import llms_generator

router = APIRouter(prefix="/api/v1/template", tags=["文章模板"])


@router.get("/article/{semantic_id}", summary="生成GEO文章（LLM优先，模板兜底）")
def generate_article_template(
    semantic_id: int,
    opportunity_id: Optional[int] = Query(None, description="内容机会ID，用于定向生成"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    semantic = db.query(Semantic).filter(
        Semantic.id == semantic_id, Semantic.user_id == user_id
    ).first()
    if not semantic:
        raise HTTPException(status_code=404, detail="语义不存在")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善医生资料")

    # 查找内容机会（如果提供了 opportunity_id）
    opportunity = None
    if opportunity_id:
        opportunity = db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opportunity_id,
            ContentOpportunity.question_id == semantic_id
        ).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="内容机会不存在或与语义不匹配")

    # 使用 ArticleGenerator（LLM 优先，模板兜底）
    generator = ArticleGenerator(db)
    result = generator.generate(semantic, profile, opportunity)

    return {
        "code": 0, "message": "success",
        "data": {
            "title": result["title"],
            "intro": result["intro"],
            "body": result["body"],
            "conclusion": result["conclusion"],
            "tags": result["tags"],
            "full_text": result["full_text"],
            "source": result.get("source", "template"),
        }
    }


@router.get("/llms.txt", summary="生成医生llms.txt")
def generate_llms(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善医生资料")
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
    articles = db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id).order_by(ArticleDraft.created_at.desc()).all()
    content = llms_generator.generate(profile, semantics, articles)
    return PlainTextResponse(content, media_type="text/plain")
