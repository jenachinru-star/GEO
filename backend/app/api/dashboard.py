from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.services import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["仪表盘"])


@router.get("/stats", summary="获取仪表盘统计数据（品牌视角，保留旧接口）")
def get_stats(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    service = DashboardService(db)
    data = service.get_stats()
    return {"code": 0, "message": "success", "data": data}


@router.get("/doctor-stats", summary="医生视角仪表盘统计")
def get_doctor_stats(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    service = DashboardService(db)
    result = service.get_doctor_stats(user_id)
    return {"code": 0, "message": "success", "data": result}
