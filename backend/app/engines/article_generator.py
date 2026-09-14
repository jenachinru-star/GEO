"""
LLM 驱动的文章生成引擎
- 优先使用 LLM 生成结构化文章（JSON 输出）
- LLM 不可用时降级为模板生成
- 所有生成文章包含医疗免责声明
- 支持基于内容机会（opportunity_id）定向生成
"""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.content_opportunity import ContentOpportunity
from app.engines.article_template import article_template_engine
from app.config import settings

logger = logging.getLogger(__name__)

# 医疗内容合规规则
COMPLIANCE_RULES = """
【医疗内容合规要求】
1. 所有医疗建议必须包含"不能替代专业医疗诊断"的免责声明
2. 不得承诺治疗效果，不得使用"根治""百分百治愈"等绝对化用语
3. 涉及处方药时必须提示"请在医生指导下使用"
4. 内容应客观中立，避免夸大宣传
5. 引用医学数据时应注明来源
"""

# 文章生成 Prompt 模板
ARTICLE_GENERATION_PROMPT = """你是一位专业的医疗科普内容编辑。请根据以下信息生成一篇高质量的 GEO/AEO 优化文章。

【医生信息】
姓名：{doctor_name}
职称：{doctor_title}
医院：{hospital}
科室：{department}
专业：{specialty}

【语义问题】
{question}

【内容机会类型】
{opportunity_type}
{opportunity_evidence}

【写作要求】
1. 标题采用问答式（AEO 优化），包含关键词
2. 结构：引言 → 核心内容（3-5个要点）→ 实用建议 → 总结
3. 语言通俗易懂，适合大众阅读
4. 自然融入医生姓名、医院、科室信息（GEO 优化）
5. 字数 800-1500 字

{compliance_rules}

请严格以 JSON 格式输出，不要输出其他内容：
{{
  "title": "文章标题",
  "intro": "引言段落（100-200字）",
  "body": "正文内容（分点论述，600-1000字）",
  "conclusion": "总结段落（100-200字，包含免责声明）",
  "tags": ["标签1", "标签2", "标签3"]
}}
"""


class ArticleGenerator:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, semantic: Semantic, profile: DoctorProfile,
                 opportunity: Optional[ContentOpportunity] = None) -> dict:
        """生成文章，优先 LLM，失败降级模板"""
        # 尝试 LLM 生成
        try:
            result = self._generate_with_llm(semantic, profile, opportunity)
            if result:
                logger.info(f"LLM 文章生成成功: semantic={semantic.id}")
                return result
        except Exception as e:
            logger.warning(f"LLM 文章生成失败，降级模板: {e}")

        # 降级：模板生成
        return self._generate_with_template(semantic, profile, opportunity)

    def _generate_with_llm(self, semantic: Semantic, profile: DoctorProfile,
                            opportunity: Optional[ContentOpportunity] = None) -> Optional[dict]:
        """使用 LLM 生成文章（通过 adapter_factory，兼容 GLM/MiniMax 等已配置平台）"""
        from app.adapters import adapter_factory

        # 检查是否有可用的 AI 平台
        platforms = adapter_factory.get_enabled_platforms()
        if not platforms:
            logger.info("无可用AI平台，跳过 LLM 生成")
            return None

        adapter = adapter_factory.get_adapter(platforms[0])
        logger.info(f"文章生成使用平台: {platforms[0]}")

        opp_type = opportunity.opportunity_type if opportunity else "general"
        opp_evidence = ""
        if opportunity and opportunity.evidence_json:
            try:
                ev = json.loads(opportunity.evidence_json)
                opp_evidence = f"机会证据：{json.dumps(ev, ensure_ascii=False)}"
            except:
                pass

        prompt = ARTICLE_GENERATION_PROMPT.format(
            doctor_name=profile.real_name or "医生",
            doctor_title=profile.title or "",
            hospital=profile.hospital or "",
            department=profile.department or "",
            specialty=profile.specialty or "",
            question=semantic.question,
            opportunity_type=opp_type,
            opportunity_evidence=opp_evidence,
            compliance_rules=COMPLIANCE_RULES,
        )

        # 通过 adapter 调用（合规规则作为 system_prompt）
        result = adapter.query(prompt, system_prompt=COMPLIANCE_RULES.strip())

        if not result.success:
            logger.warning(f"LLM 文章生成调用失败: {result.error}")
            return None

        content = result.answer.strip()

        # 解析 JSON 输出
        result = self._parse_json_output(content)
        if not result:
            logger.warning(f"LLM 输出 JSON 解析失败，原始内容前200字: {content[:200]}")
            return None

        # 确保包含免责声明
        if "免责声明" not in result.get("conclusion", "") and "不能替代" not in result.get("conclusion", ""):
            result["conclusion"] += "\n\n免责声明：本文内容仅供健康科普参考，不能替代专业医疗诊断和治疗。如有健康问题，请及时就医。"

        # 组装 full_text
        result["full_text"] = self._assemble_full_text(result)
        result["source"] = "llm"
        return result

    def _parse_json_output(self, content: str) -> Optional[dict]:
        """解析 LLM 的 JSON 输出，处理各种格式变体"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except:
            pass

        # 尝试提取 ```json ... ``` 块
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            try:
                return json.loads(content[start:end].strip())
            except:
                pass

        # 尝试提取第一个 { 到最后一个 }
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except:
                pass

        return None

    def _generate_with_template(self, semantic: Semantic, profile: DoctorProfile,
                                opportunity: Optional[ContentOpportunity] = None) -> dict:
        """降级：使用模板引擎生成文章"""
        template = article_template_engine.generate(semantic, profile)
        result = {
            "title": template.title,
            "intro": template.intro,
            "body": template.body,
            "conclusion": template.conclusion,
            "tags": template.tags,
            "full_text": template.full_text,
            "source": "template",
        }
        # 确保包含免责声明
        if "免责声明" not in result["conclusion"] and "不能替代" not in result["conclusion"]:
            result["conclusion"] += "\n\n免责声明：本文内容仅供健康科普参考，不能替代专业医疗诊断和治疗。如有健康问题，请及时就医。"
            result["full_text"] = self._assemble_full_text(result)
        return result

    def _assemble_full_text(self, result: dict) -> str:
        """组装完整文章文本"""
        parts = [
            f"【标题】{result.get('title', '')}",
            f"【首段】{result.get('intro', '')}",
            f"【正文】{result.get('body', '')}",
            f"【文末】{result.get('conclusion', '')}",
        ]
        tags = result.get("tags", [])
        if tags:
            parts.append(f"【标签】{' '.join(tags)}")
        return "\n\n".join(parts)


# 全局单例
_article_generator: Optional[ArticleGenerator] = None


def get_article_generator(db: Session) -> ArticleGenerator:
    global _article_generator
    if _article_generator is None:
        _article_generator = ArticleGenerator(db)
    return _article_generator
