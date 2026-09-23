"""合规检查相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.adapters import adapter_factory
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_compliance_check(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理合规检查任务"""
    from app.api.compliance import PLATFORM_RULES

    payload = json.loads(task.payload_json or "{}")
    title = payload.get("title", "")
    content = payload.get("content", "")
    platform = payload.get("platform", "")

    rules = PLATFORM_RULES.get(platform, [])
    if not rules:
        return {"passed": True, "score": 100, "issues": [], "message": "未找到该平台的合规规则，跳过检测"}

    if on_progress:
        on_progress(1, 2, "LLM合规检测中")

    # 用配置好的LLM检测（glm优先，doubao回退，与原接口逻辑一致）
    adapter = adapter_factory.get_adapter("glm") or adapter_factory.get_adapter("doubao")
    if not adapter:
        return {"passed": True, "score": 100, "issues": [], "message": "未配置LLM，跳过合规检测"}

    rules_text = "\n".join([f"- {r}" for r in rules])
    prompt = f"""你是一个内容合规审查专家。请检测下面这篇医疗科普内容是否违反以下平台规则：

平台：{platform}
规则：
{rules_text}

文章标题：{title}
文章正文：{content}

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
        return {"passed": True, "score": 100, "issues": [], "message": f"LLM调用失败，跳过检测: {result.error}"}

    # 解析LLM返回的JSON
    try:
        answer = result.answer.strip()
        if "```json" in answer:
            answer = answer.split("```json")[1].split("```")[0].strip()
        elif "```" in answer:
            answer = answer.split("```")[1].split("```")[0].strip()

        data = json.loads(answer)
        if on_progress:
            on_progress(2, 2, "合规检测完成")
        return {
            "passed": data.get("passed", True),
            "score": data.get("score", 100),
            "issues": data.get("issues", []),
            "platform": platform,
        }
    except Exception as e:
        return {"passed": True, "score": 100, "issues": [], "message": f"解析LLM结果失败，跳过: {str(e)}"}


# 注册任务处理函数
register_handler("compliance_check", handle_compliance_check)
