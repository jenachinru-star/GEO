"""医生Profile API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.engines.semantic_generator import SemanticGenerator

router = APIRouter(prefix="/api/v1/doctor", tags=["医生Profile"])


@router.get("/profile", summary="获取当前医生Profile")
def get_profile(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    data = {
        "id": profile.id,
        "real_name": profile.real_name,
        "title": profile.title,
        "province": profile.province,
        "city": profile.city,
        "hospital": profile.hospital,
        "department": profile.department,
        "specialty": profile.specialty,
        "awards": profile.awards,
        "case_history": profile.case_history,
        "self_intro_template": profile.self_intro_template,
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "social_links": profile.social_links,
        "personal_website": profile.personal_website,
        "registration_url": profile.registration_url,
        "clinic_hours": profile.clinic_hours,
    } if profile else None
    return {"code": 0, "message": "success", "data": data}


@router.post("/profile", summary="创建/更新医生Profile")
def save_profile(data: dict, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    is_new = not profile
    if not profile:
        profile = DoctorProfile(user_id=user_id)
        db.add(profile)

    # 只更新传入的字段
    allowed_fields = ["real_name", "title", "province", "city", "hospital",
                      "department", "specialty", "awards", "case_history",
                      "avatar_url", "bio", "social_links", "personal_website",
                      "registration_url", "clinic_hours"]
    for key in allowed_fields:
        if key in data:
            setattr(profile, key, data[key])

    # 自动生成统一自我介绍格式
    city = data.get("city", "") or profile.city or ""
    hospital = data.get("hospital", "") or profile.hospital or ""
    department = data.get("department", "") or profile.department or ""
    real_name = data.get("real_name", "") or profile.real_name or ""
    profile.self_intro_template = f"{city}{hospital}{department}{real_name}医生"

    db.commit()
    db.refresh(profile)

    # 首次创建时自动生成语义
    semantic_count = db.query(Semantic).filter(Semantic.user_id == user_id).count()
    generated_count = 0
    if is_new or semantic_count == 0:
        generator = SemanticGenerator(db=db, user_id=user_id)
        questions = generator.generate({
            "real_name": profile.real_name,
            "title": profile.title,
            "province": profile.province,
            "city": profile.city,
            "hospital": profile.hospital,
            "department": profile.department,
            "specialty": profile.specialty,
        })
        existing = {s.question for s in db.query(Semantic).filter(Semantic.user_id == user_id).all()}
        for q in questions:
            if q not in existing:
                db.add(Semantic(user_id=user_id, question=q, category="general"))
                generated_count += 1
        if generated_count > 0:
            db.commit()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "profile": {
                "id": profile.id,
                "real_name": profile.real_name,
                "self_intro_template": profile.self_intro_template,
                "avatar_url": profile.avatar_url,
                "bio": profile.bio,
                "hospital": profile.hospital,
                "department": profile.department,
                "specialty": profile.specialty,
            },
            "semantic_generated": generated_count,
        }
    }


@router.post("/regenerate-semantics", summary="重新生成语义（只新增不重复）")
def regenerate_semantics(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善Profile")

    generator = SemanticGenerator(db=db, user_id=user_id)
    questions = generator.generate({
        "real_name": profile.real_name,
        "title": profile.title,
        "province": profile.province,
        "city": profile.city,
        "hospital": profile.hospital,
        "department": profile.department,
        "specialty": profile.specialty,
    })

    existing = {s.question for s in db.query(Semantic).filter(Semantic.user_id == user_id).all()}
    new_count = 0
    for q in questions:
        if q not in existing:
            db.add(Semantic(user_id=user_id, question=q, category="general"))
            new_count += 1
            existing.add(q)
    db.commit()

    return {"code": 0, "message": "success", "data": {"new_count": new_count, "total": len(existing)}}
