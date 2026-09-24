"""医生Profile API"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.models.doctor import DoctorProfile
from app.models.semantic import Semantic
from app.models.task import AsyncTask

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

    # 首次创建或语义为空时，提交异步任务生成语义（不阻塞HTTP响应）
    semantic_count = db.query(Semantic).filter(Semantic.user_id == user_id).count()
    semantic_task_id = None
    if is_new or semantic_count == 0:
        profile_data = {
            "real_name": profile.real_name,
            "title": profile.title,
            "province": profile.province,
            "city": profile.city,
            "hospital": profile.hospital,
            "department": profile.department,
            "specialty": profile.specialty,
        }
        task = AsyncTask(
            task_type="semantic_generate",
            status="queued",
            created_by=user_id,
            payload_json=json.dumps({"user_id": user_id, "profile": profile_data}, ensure_ascii=False),
            progress_message="生成医生资料语义问题",
        )
        db.add(task)
        db.commit()
        semantic_task_id = task.id

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
            "semantic_task_id": semantic_task_id,
        }
    }


@router.post("/regenerate-semantics", summary="重新生成语义（异步，只新增不重复）")
def regenerate_semantics(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善Profile")

    profile_data = {
        "real_name": profile.real_name,
        "title": profile.title,
        "province": profile.province,
        "city": profile.city,
        "hospital": profile.hospital,
        "department": profile.department,
        "specialty": profile.specialty,
    }
    task = AsyncTask(
        task_type="semantic_generate",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"user_id": user_id, "profile": profile_data}, ensure_ascii=False),
        progress_message="重新生成医生资料语义问题",
    )
    db.add(task)
    db.commit()

    return {"code": 0, "message": "已提交语义生成任务", "data": {"task_id": task.id}}
