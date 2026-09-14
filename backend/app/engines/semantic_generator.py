"""语义自动生成引擎 — 基于医生Profile调用LLM生成语义问题"""
import logging
import re
from typing import List
from app.adapters import adapter_factory
from app.adapters.base import QueryResult

logger = logging.getLogger(__name__)


class SemanticGenerator:
    """基于医生Profile信息，调用LLM生成关联语义问题"""

    SYSTEM_PROMPT = """你是一个医疗健康领域的语义分析专家。
根据医生的真实执业信息，生成患者会在AI搜索中真实提问的问题。

规则：
1. 必须将医生的执业地域（省+市）、医院、科室、专长疾病进行绑定
2. 生成的问题必须是患者真实会问的，不是学术问题
3. 每个问题要具体，不能太笼统（"妇科炎症看哪个医生"优于"妇科问题"）
4. 覆盖不同提问角度：找医生、找医院、问治疗、问费用、问预防等
5. 最少生成10个，最多15个
6. 严格基于医生提供的真实信息，不得编造医院或专长
7. 每个问题必须以中文问号"？"结尾

输出格式：每行一个问题，不要编号，不要解释，不要markdown。"""

    def __init__(self, platform_code: str = None):
        self.platform_code = platform_code

    def generate(self, profile: dict) -> List[str]:
        """生成语义问题列表"""
        user_prompt = f"""医生信息：
姓名：{profile.get('real_name', '')}
职称：{profile.get('title', '')}
地域：{profile.get('province', '')}{profile.get('city', '')}
医院：{profile.get('hospital', '')}
科室：{profile.get('department', '')}
专长：{profile.get('specialty', '')}

请生成患者会在AI搜索中提问的相关问题。"""

        adapter = self._get_adapter()
        if not adapter:
            logger.warning("无可用AI平台，使用模板兜底生成")
            return self._fallback_generate(profile)

        result: QueryResult = adapter.query(user_prompt, system_prompt=self.SYSTEM_PROMPT)
        if not result.success:
            logger.warning(f"语义生成LLM调用失败: {result.error}")
            return self._fallback_generate(profile)

        # 解析回答，每行一个问题
        questions = []
        for line in result.answer.split('\n'):
            line = line.strip()
            # 去掉编号前缀（1. / 1、 / (1) / 1)）
            line = re.sub(r'^[\d]+[\.、\)）]\s*', '', line)
            # 去掉markdown列表符号
            line = re.sub(r'^[-*•]\s*', '', line)
            if line and 5 < len(line) < 100:
                questions.append(line)

        # 去重（保持顺序）
        questions = list(dict.fromkeys(questions))

        # 不足10个用模板补充
        if len(questions) < 10:
            questions.extend(self._fallback_generate(profile))
            questions = list(dict.fromkeys(questions))

        # 统一确保每个问题以问号结尾
        questions = [self._ensure_question_mark(q) for q in questions]
        questions = list(dict.fromkeys(questions))

        return questions[:15]

    def _get_adapter(self):
        if self.platform_code:
            return adapter_factory.get_adapter(self.platform_code)
        platforms = adapter_factory.get_enabled_platforms()
        if platforms:
            return adapter_factory.get_adapter(platforms[0])
        return None

    def _fallback_generate(self, profile: dict) -> List[str]:
        """LLM不可用时的模板化兜底生成"""
        city = profile.get('city', '')
        hospital = profile.get('hospital', '')
        dept = profile.get('department', '')
        specialty_raw = profile.get('specialty', '')
        specialty = specialty_raw.split(',')[0].strip() if specialty_raw else ''
        name = profile.get('real_name', '')

        if not city or not specialty:
            return []

        templates = [
            f"{city}{specialty}看哪个医生好？",
            f"{city}{hospital}{dept}哪个医生好？",
            f"{city}{specialty}去哪治疗最好？",
            f"{city}{hospital}{specialty}怎么样？",
            f"{city}{specialty}治疗费用大概多少？",
            f"{city}{dept}专家推荐？",
            f"{city}{specialty}能治好吗？",
            f"{city}{hospital}{dept}挂号攻略？",
            f"{city}{specialty}预防方法有哪些？",
            f"{city}{specialty}最佳治疗时间？",
            f"{name}医生看{specialty}怎么样？",
            f"{city}{specialty}中医还是西医好？",
        ]
        return templates

    @staticmethod
    def _ensure_question_mark(question: str) -> str:
        """确保问题以问号结尾"""
        question = question.strip()
        if not question.endswith('？') and not question.endswith('?'):
            question = question + '？'
        return question
