"""合规审查 API - 发布前自动检测内容是否符合平台规则"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.adapters import adapter_factory

router = APIRouter(prefix="/api/v1/compliance", tags=["合规审查"])


class ComplianceCheckRequest(BaseModel):
    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="文章正文")
    platform: str = Field(..., description="目标平台code")


class ComplianceIssue(BaseModel):
    level: str  # error / warning / info
    rule: str
    message: str
    suggestion: str


PLATFORM_RULES = {
    "baijiahao": [
        "医疗内容需资质认证",
        "禁止绝对化用语（最/第一/唯一）",
        "需标注信息来源",
    ],
    "wechat": [
        "医疗广告需资质",
        "禁止诱导分享",
        "需标注原创",
    ],
    "zhihu": [
        "需专业认证",
        "禁止软文",
        "引用需标注",
    ],
    "xiaohongshu": [
        "禁止医疗广告",
        "需个人经验分享",
        "禁止导流",
    ],
    "haodf": [
        "需医生实名认证",
        "内容需专业审核",
        "禁止个人联系方式",
    ],
    "dxy": [
        "需执业医师认证",
        "内容需同行评议",
        "禁止商业推广",
    ],
}


@router.post("/check", summary="发布前合规审查（异步任务）")
def check_compliance(
    req: ComplianceCheckRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """投递合规检查异步任务，完成后通过任务接口获取结果"""
    from app.models.task import AsyncTask
    import json

    # 快速失败：无规则时直接返回（不投递任务）
    rules = PLATFORM_RULES.get(req.platform, [])
    if not rules:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "passed": True,
                "score": 100,
                "issues": [],
                "message": "未找到该平台的合规规则，跳过检测"
            }
        }

    # 快速失败：无LLM时直接返回（不投递任务）
    adapter = adapter_factory.get_adapter("glm") or adapter_factory.get_adapter("doubao")
    if not adapter:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "passed": True,
                "score": 100,
                "issues": [],
                "message": "未配置LLM，跳过合规检测"
            }
        }

    # 投递异步任务
    task = AsyncTask(
        task_type="compliance_check",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({
            "title": req.title,
            "content": req.content,
            "platform": req.platform,
        }, ensure_ascii=False),
        progress_message="等待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "code": 0,
        "message": "合规检查任务已提交",
        "data": {
            "task_id": task.id,
            "status": "queued",
            "message": "合规检测中，请在任务中心查看进度",
        }
    }


@router.get("/rules/{platform}", summary="获取平台合规规则")
def get_platform_rules(
    platform: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取指定平台的合规规则列表"""
    rules = PLATFORM_RULES.get(platform, [])
    return {
        "code": 0,
        "message": "success",
        "data": {
            "platform": platform,
            "rules": rules,
        }
    }
