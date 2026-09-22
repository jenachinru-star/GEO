"""数字资产 - AI总结 API

支持调用不同AI平台对文档进行智能总结，提供多种prompt模板：
- 文献总结：医学文献专用，结构化提取研究方法、结果、结论
- 文章总结：通用文章总结，提取核心观点和论据
- 自定义总结：用户自定义prompt
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database import get_db
from app.deps import get_current_user_id
from app.models.asset import AssetDocument, AssetGenerated
from app.adapters import adapter_factory
from app.usage_context import usage_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/asset", tags=["数字资产-AI总结"])


# ============ 请求体模型 ============

class SummaryRequest(BaseModel):
    document_id: int
    platform: str = "glm"  # glm / minimax / deepseek
    prompt_template: str = "article"  # literature / article / custom
    custom_prompt: Optional[str] = None  # custom模板时使用


# ============ Prompt 模板 ============

PROMPT_TEMPLATES = {
    "literature": """你是一位资深医学研究员。请阅读以下医学文献，并用中文进行结构化总结。

请按以下格式输出：

## 研究背景与目的
（简要说明研究背景和要解决的科学问题）

## 研究方法
（研究设计、样本量、干预措施、主要结局指标）

## 主要结果
（核心数据、统计显著性、效应量）

## 结论与临床意义
（研究结论及其对临床实践的指导意义）

## 局限性
（研究的局限性和需要注意的地方）

文献标题：{title}

文献内容：
{content}
""",

    "article": """你是一位专业的内容分析助手。请阅读以下文章，并用中文进行总结。

请按以下格式输出：

## 核心观点
（3-5个核心观点，每个一句话）

## 详细摘要
（200-300字的详细摘要，保留关键数据和论据）

## 关键信息点
- 列出文章中最重要的5-8个信息点
- 每个信息点用一句话概括

## 对医生的价值
（这篇文章对临床医生有什么参考价值，100字以内）

文章标题：{title}

文章内容：
{content}
""",

    "brief": """请用简洁的中文总结以下内容，控制在200字以内，保留最关键的信息。

标题：{title}

内容：
{content}
""",

    "clinical": """你是一位资深临床医生。请阅读以下临床指南或专家共识，用中文提炼临床要点。

请按以下格式输出：

## 适用人群
（这个指南适用于哪些患者）

## 核心推荐意见
（按优先级列出3-5条最重要的推荐意见，标注推荐强度）

## 诊断标准
（疾病的诊断标准和关键指标）

## 治疗方案
（一线/二线治疗方案，药物选择和剂量）

## 注意事项
（禁忌症、不良反应、随访要求）

指南标题：{title}

指南内容：
{content}
""",
}


# ============ API 接口 ============

@router.post("/summary", summary="AI总结文档")
def generate_summary(
    req: SummaryRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """调用AI平台对文档进行智能总结"""
    # 查找文档
    doc = db.query(AssetDocument).filter(
        AssetDocument.id == req.document_id,
        AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 获取AI适配器
    adapter = adapter_factory.get_adapter(req.platform)
    if not adapter:
        # 尝试使用第一个可用平台
        enabled = adapter_factory.get_enabled_platforms()
        if not enabled:
            raise HTTPException(status_code=400, detail="未配置可用的AI平台")
        adapter = adapter_factory.get_adapter(enabled[0])
        req.platform = enabled[0]

    # 选择prompt模板
    if req.prompt_template == "custom" and req.custom_prompt:
        template = req.custom_prompt
    else:
        template = PROMPT_TEMPLATES.get(req.prompt_template, PROMPT_TEMPLATES["article"])

    # 构建prompt（截断超长内容，防止token超限）
    max_content_length = 8000
    content = doc.content[:max_content_length] if len(doc.content) > max_content_length else doc.content
    user_prompt = template.format(title=doc.title, content=content)

    # 设置用量上下文
    ctx_token = usage_context.set(
        user_id=user_id,
        task_type="asset_summary",
        ref_id=doc.id,
        ref_type="document",
        source="http"
    )

    try:
        # 调用AI
        result = adapter.query(
            user_prompt,
            system_prompt="你是一位专业的医学知识助手，擅长准确、简洁地总结医学文献和文章。",
            usage_ctx={"task_type": "asset_summary", "source": "http"}
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=f"AI总结失败: {result.error}")

        # 保存生成记录
        generated = AssetGenerated(
            document_id=doc.id,
            user_id=user_id,
            gen_type="summary",
            title=f"{doc.title} - AI总结",
            content=result.answer,
            platform=req.platform,
            model=getattr(adapter, 'model', ''),
            prompt_template=req.prompt_template,
            tokens_input=result.prompt_tokens or 0,
            tokens_output=result.completion_tokens or 0,
        )
        db.add(generated)

        # 如果是第一次总结，更新文档的summary字段
        if not doc.summary:
            doc.summary = result.answer

        db.commit()
        db.refresh(generated)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "id": generated.id,
                "content": result.answer,
                "platform": req.platform,
                "model": generated.model,
                "tokens_input": result.prompt_tokens,
                "tokens_output": result.completion_tokens,
            }
        }

    finally:
        usage_context.reset(ctx_token)


@router.get("/summary/history/{document_id}", summary="获取文档的AI总结历史")
def get_summary_history(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取文档的所有AI生成内容历史"""
    records = db.query(AssetGenerated).filter(
        AssetGenerated.document_id == document_id,
        AssetGenerated.user_id == user_id,
        AssetGenerated.gen_type == "summary"
    ).order_by(AssetGenerated.created_at.desc()).all()

    items = [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "platform": r.platform,
            "model": r.model,
            "prompt_template": r.prompt_template,
            "tokens_input": r.tokens_input,
            "tokens_output": r.tokens_output,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]

    return {"code": 0, "message": "success", "data": {"items": items}}


@router.get("/summary/templates", summary="获取可用的prompt模板")
def get_prompt_templates():
    """返回所有可用的总结prompt模板"""
    templates = [
        {"key": "article", "name": "文章总结", "description": "通用文章总结，提取核心观点和关键信息"},
        {"key": "literature", "name": "文献总结", "description": "医学文献专用，结构化提取方法、结果、结论"},
        {"key": "clinical", "name": "临床指南解读", "description": "临床指南/专家共识专用，提炼推荐意见和治疗方案"},
        {"key": "brief", "name": "简洁摘要", "description": "200字以内的极简摘要"},
    ]
    return {"code": 0, "message": "success", "data": {"templates": templates}}
