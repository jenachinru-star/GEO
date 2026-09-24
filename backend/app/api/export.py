"""数据导出API - 支持Excel格式导出"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import io
import urllib.parse

from app.database import get_db
from app.deps import get_current_user_id
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/v1/export", tags=["数据导出"])


def _excel_response(data: bytes, filename: str):
    """生成Excel文件响应（正确处理中文文件名）"""
    # HTTP头只支持latin-1，中文文件名需要用RFC 5987编码
    encoded_filename = urllib.parse.quote(filename)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=export.xlsx; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/monitor", summary="导出监测记录")
def export_monitor(
    question_id: int = Query(None, description="问题ID，不传则导出全部"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    data = ExportService.export_monitor_records(db, question_id, start_date, end_date, user_id=user_id)
    filename = f"监测记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _excel_response(data, filename)


@router.get("/questions", summary="导出监测问题列表")
def export_questions(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    data = ExportService.export_questions(db, user_id=user_id)
    filename = f"监测问题_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _excel_response(data, filename)


@router.get("/content", summary="导出内容资产")
def export_content(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    data = ExportService.export_content(db, user_id=user_id)
    filename = f"内容资产_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _excel_response(data, filename)


@router.get("/report", summary="导出完整报告（多Sheet）")
def export_full_report(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    data = ExportService.export_full_report(db, user_id=user_id)
    filename = f"GEO完整报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _excel_response(data, filename)


@router.get("/doctor-report", summary="导出医生个人GEO报告")
def export_doctor_report(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    data = ExportService.export_doctor_report(db, user_id)
    filename = f"GEO医生报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return _excel_response(data, filename)
