from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.models.doctor import DoctorProfile
from app.engines.entity_validator import entity_validator

router = APIRouter(prefix="/api/v1/entity", tags=["实体一致性"])


@router.get("/profile-score", summary="获取当前医生Profile的实体一致性评分")
def get_profile_score(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        return {"code": 0, "message": "success", "data": {"score": 0, "passed": False, "issues": [
            {"level": "error", "field": "profile", "message": "尚未完善医生资料", "suggestion": "请先在「我的资料」页填写医生信息"}
        ]}}
    result = entity_validator.validate_profile(profile)
    return {"code": 0, "message": "success", "data": result.to_dict()}
