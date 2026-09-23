"""
LLM 辅助分析器 — 对已提及医生的记录，判断推荐关系、情感、引用URL关联。

设计原则：
- 只对第一层规则已确认"提及医生"的记录调用（节省成本）
- 输出结构化 JSON，方便解析和保存
- 调用失败时降级为规则判断（不阻塞采集）
- 低置信度结果标记 needs_review
"""
import json
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.adapters import adapter_factory

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """LLM分析结果"""
    is_recommendation: bool = False
    recommendation_evidence: str = ""
    sentiment: str = "neutral"  # positive/neutral/negative/mixed
    citation_urls: list = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    raw_response: str = ""


SYSTEM_PROMPT = """你是一个医疗AI回答分析专家。请分析给定的AI回答文本，判断其中关于目标医生的表述。

严格按以下 JSON 格式输出（不要输出任何其他文字）：
{
  "is_recommendation": true/false,
  "recommendation_evidence": "原文中表示推荐的那句话（如果没有则为空字符串）",
  "sentiment": "positive/neutral/negative/mixed",
  "citation_urls": ["回答中出现的所有URL（如果没有则为空数组）"],
  "confidence": 0.0-1.0之间的数字,
  "needs_review": true/false
}

判断规则：
1. is_recommendation：只有明确表示"推荐/建议选择/可以考虑/首选"等正向推荐关系才为true。
   - 普通提及、履历介绍、新闻报道 → false
   - "不建议选择/风险警示" → false
   - 用户问题中原样重复医生名 → false
2. sentiment：对目标医生的整体情感倾向。
3. citation_urls：提取回答中所有 http/https 开头的URL。
4. confidence：你对以上判断的置信度。
5. needs_review：如果判断不确定或回答内容模糊，设为true。
"""


class LLMAnalyzer:
    """LLM辅助分析器"""

    def __init__(self, platform_code: str = None):
        self.platform_code = platform_code

    def _get_adapter(self, db=None, user_id: int = None):
        if self.platform_code:
            return adapter_factory.get_adapter(self.platform_code)
        platforms = adapter_factory.get_enabled_platforms()

        # 过滤用户停用的平台
        if user_id and db:
            from app.models.user_platform_pref import UserPlatformPref
            disabled = {
                pref.platform_code for pref in
                db.query(UserPlatformPref).filter(
                    UserPlatformPref.user_id == user_id,
                    UserPlatformPref.enabled == False
                ).all()
            }
            if disabled:
                logger.info(f"用户 [{user_id}] 已停用平台: {disabled}，LLM分析时跳过")
                platforms = [p for p in platforms if p not in disabled]

        if platforms:
            return adapter_factory.get_adapter(platforms[0])
        return None

    def analyze(self, raw_answer: str, doctor_name: str, hospital: str = "",
                department: str = "", db=None, user_id: int = None) -> LLMResult:
        """
        调用LLM分析回答。

        Args:
            raw_answer: AI原始回答文本
            doctor_name: 医生姓名
            hospital: 医院名称
            department: 科室名称
            db: 数据库session（用于查询用户平台开关）
            user_id: 用户ID（用于过滤用户停用的平台）

        Returns:
            LLMResult，调用失败时返回默认值（降级）
        """
        adapter = self._get_adapter(db=db, user_id=user_id)
        if not adapter:
            logger.warning("无可用AI平台，LLM分析降级为默认值")
            return LLMResult()

        user_prompt = f"""目标医生信息：
姓名：{doctor_name}
医院：{hospital or '未知'}
科室：{department or '未知'}

AI回答文本：
\"\"\"
{raw_answer[:3000]}
\"\"\"

请分析以上AI回答中关于目标医生的表述，按指定JSON格式输出。"""

        try:
            result = adapter.query(user_prompt, system_prompt=SYSTEM_PROMPT)
            if not result.success:
                logger.warning(f"LLM分析调用失败: {result.error}")
                return LLMResult()

            # 解析JSON响应（处理可能的markdown代码块包裹）
            response_text = result.answer.strip()
            # 去除 ```json ... ``` 包裹
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()

            data = json.loads(response_text)

            llm_result = LLMResult(
                is_recommendation=bool(data.get("is_recommendation", False)),
                recommendation_evidence=str(data.get("recommendation_evidence", ""))[:500],
                sentiment=str(data.get("sentiment", "neutral")),
                citation_urls=data.get("citation_urls", []) or [],
                confidence=float(data.get("confidence", 0.0)),
                needs_review=bool(data.get("needs_review", False)),
                raw_response=result.answer[:1000],
            )
            return llm_result

        except json.JSONDecodeError as e:
            logger.warning(f"LLM分析结果JSON解析失败: {e}，原始响应: {result.answer[:200]}")
            return LLMResult()
        except Exception as e:
            logger.warning(f"LLM分析异常: {type(e).__name__}: {e}")
            return LLMResult()


# 全局单例
llm_analyzer = LLMAnalyzer()
