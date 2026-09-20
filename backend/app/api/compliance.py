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


@router.post("/check", summary="发布前合规审查")
def check_compliance(
    req: ComplianceCheckRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """调用LLM检测内容是否符合目标平台的合规规则"""

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

    # 用配置好的LLM检测
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

    rules_text = "\n".join([f"- {r}" for r in rules])
    prompt = f"""你是一个内容合规审查专家。请检测下面这篇医疗科普内容是否违反以下平台规则：

平台：{req.platform}
规则：
{rules_text}

文章标题：{req.title}
文章正文：{req.content}

请按以下JSON格式返回检测结果（只返回JSON，不要其他文字）：
{{
  "passed": true/false,
  "score": 0-100的分数,
  "issues": [
    {{
      "level": "error" / "warning" / "info",
      "rule": "违反的规则",
      "message": "问题描述",
      "suggestion": "修改建议"
    }}
  ]
}}
"""

    result = adapter.query(prompt)
    if not result.success:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "passed": True,
                "score": 100,
                "issues": [],
                "message": f"LLM调用失败，跳过检测: {result.error}"
            }
        }

    # 解析LLM返回的JSON
    import json
    try:
        # 提取JSON部分
        answer = result.answer.strip()
        if "```json" in answer:
            answer = answer.split("```json")[1].split("```")[0].strip()
        elif "```" in answer:
            answer = answer.split("```")[1].split("```")[0].strip()

        data = json.loads(answer)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "passed": data.get("passed", True),
                "score": data.get("score", 100),
                "issues": data.get("issues", []),
                "platform": req.platform,
            }
        }
    except Exception as e:
        return {
            "code": 0,
            "message": "success",
            "data": {
                "passed": True,
                "score": 100,
                "issues": [],
                "message": f"解析LLM结果失败，跳过: {str(e)}"
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
