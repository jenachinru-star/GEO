"""语义延伸引擎 — 对每个语义问题生成同义变体和深度延伸"""
import logging
import re
from typing import List, Dict, Tuple
from app.adapters import adapter_factory
from app.adapters.base import QueryResult

logger = logging.getLogger(__name__)


class SemanticExtender:
    """基于LLM对语义问题进行延伸：同义变体 + 深度延伸"""

    SYNONYM_SYSTEM_PROMPT = """你是一个医疗健康领域的语义分析专家。
任务：对给定的患者提问，生成意思完全相同、但表达方式不同的同义变体问题。

规则：
1. 意思必须完全相同，只是换一种问法（换词、换语序、换句式）
2. 必须是患者真实会在AI搜索中问的问题，不是学术问题
3. 保留原问题中的关键信息：地域、医院、科室、疾病、医生名等
4. 每个问题必须以问号"？"结尾
5. 生成3-5个变体，不要太多
6. 不要生成与原问题意思不同的问题

输出格式：每行一个问题，不要编号，不要解释，不要markdown。"""

    DEEP_SYSTEM_PROMPT = """你是一个医疗健康领域的语义分析专家。
任务：对给定的泛化患者提问，基于医生的专长疾病，生成更具体的深度延伸问题。

规则：
1. 把原问题中的泛化概念（如"妇科"）具体化为医生的专长疾病（如"妇科炎症"、"月经不调"）
2. 可以从不同角度延伸：具体疾病、具体症状、具体医院、具体治疗方式等
3. 必须是患者真实会在AI搜索中问的问题
4. 保留原问题的核心意图（找医生/找医院/问治疗等）
5. 每个问题必须以问号"？"结尾
6. 生成2-3个深度延伸问题
7. 严格基于医生提供的真实专长信息，不得编造疾病

输出格式：每行一个问题，不要编号，不要解释，不要markdown。"""

    def __init__(self, platform_code: str = None, db=None, user_id: int = None):
        self.platform_code = platform_code
        self.db = db
        self.user_id = user_id

    def extend(self, question: str, profile: dict = None,
               existing_questions: List[str] = None) -> Dict:
        """
        对单个语义问题进行延伸，返回预览列表（不直接保存）

        Args:
            question: 原问题
            profile: 医生资料（用于深度延伸），可选
            existing_questions: 现有语义问题列表（用于去重），可选

        Returns:
            {
                "synonyms": [{"question": "...", "is_duplicate": False, "similarity": 0.0}, ...],
                "deep": [{"question": "...", "is_duplicate": False, "similarity": 0.0}, ...],
                "source": "llm" | "template"
            }
        """
        existing = existing_questions or []
        source = "llm"

        # 生成同义变体
        synonyms_raw = self._generate_synonyms(question)
        if not synonyms_raw:
            synonyms_raw = self._fallback_synonyms(question)
            source = "template"

        # 生成深度延伸
        deep_raw = self._generate_deep(question, profile)
        if not deep_raw:
            deep_raw = self._fallback_deep(question, profile)
            if source == "llm":
                source = "partial"

        # 去重检查
        synonyms = [self._check_dup(q, existing + [question]) for q in synonyms_raw]
        deep = [self._check_dup(q, existing + [question] + synonyms_raw) for q in deep_raw]

        return {
            "synonyms": synonyms,
            "deep": deep,
            "source": source
        }

    def extend_batch(self, questions: List[str], profile: dict = None,
                     existing_questions: List[str] = None) -> List[Dict]:
        """批量延伸多个语义问题"""
        all_existing = list(existing_questions or [])
        results = []
        for q in questions:
            result = self.extend(q, profile, all_existing)
            results.append({"original": q, **result})
            # 把生成的也加入去重池
            all_existing.extend([x["question"] for x in result["synonyms"]])
            all_existing.extend([x["question"] for x in result["deep"]])
        return results

    def _generate_synonyms(self, question: str) -> List[str]:
        """用LLM生成同义变体（带平台 failover）"""
        adapters = self._get_adapters()
        if not adapters:
            return []

        user_prompt = f"原问题：{question}\n\n请生成这个问题的同义变体（3-5个）。"
        for code, adapter in adapters:
            try:
                result: QueryResult = adapter.query(user_prompt, system_prompt=self.SYNONYM_SYSTEM_PROMPT)
                if result.success:
                    questions = self._parse_questions(result.answer)
                    if questions:
                        logger.info(f"同义变体生成使用平台: {code}")
                        return questions
                else:
                    logger.warning(f"同义变体平台 {code} 调用失败: {result.error}，尝试下一个平台")
            except Exception as e:
                logger.warning(f"同义变体平台 {code} 异常: {e}，尝试下一个平台")
        logger.warning("同义变体所有平台均失败")
        return []

    def _generate_deep(self, question: str, profile: dict = None) -> List[str]:
        """用LLM生成深度延伸（带平台 failover）"""
        if not profile:
            return []

        specialty = profile.get('specialty', '')
        if not specialty:
            return []

        adapters = self._get_adapters()
        if not adapters:
            return []

        user_prompt = (
            f"原问题：{question}\n"
            f"医生专长：{specialty}\n\n"
            f"请基于医生的专长疾病，把这个泛化问题具体化为深度延伸问题（2-3个）。"
        )
        for code, adapter in adapters:
            try:
                result: QueryResult = adapter.query(user_prompt, system_prompt=self.DEEP_SYSTEM_PROMPT)
                if result.success:
                    questions = self._parse_questions(result.answer)
                    if questions:
                        logger.info(f"深度延伸生成使用平台: {code}")
                        return questions
                else:
                    logger.warning(f"深度延伸平台 {code} 调用失败: {result.error}，尝试下一个平台")
            except Exception as e:
                logger.warning(f"深度延伸平台 {code} 异常: {e}，尝试下一个平台")
        logger.warning("深度延伸所有平台均失败")
        return []

    def _get_adapters(self):
        """返回所有已启用平台的适配器列表（按优先级顺序），用于 failover，过滤用户停用的平台"""
        if self.platform_code:
            adapter = adapter_factory.get_adapter(self.platform_code)
            return [(self.platform_code, adapter)] if adapter else []
        platforms = adapter_factory.get_enabled_platforms()

        # 过滤用户停用的平台
        if self.user_id and self.db:
            from app.models.user_platform_pref import UserPlatformPref
            disabled = {
                pref.platform_code for pref in
                self.db.query(UserPlatformPref).filter(
                    UserPlatformPref.user_id == self.user_id,
                    UserPlatformPref.enabled == False
                ).all()
            }
            if disabled:
                logger.info(f"用户 [{self.user_id}] 已停用平台: {disabled}，语义延伸时跳过")
                platforms = [p for p in platforms if p not in disabled]

        if not platforms:
            logger.warning("没有已启用的AI平台")
            return []

        adapters = []
        for code in platforms:
            adapter = adapter_factory.get_adapter(code)
            if adapter:
                adapters.append((code, adapter))
        return adapters

    def _parse_questions(self, answer: str) -> List[str]:
        """解析LLM回答，提取问题列表"""
        questions = []
        for line in answer.split('\n'):
            line = line.strip()
            # 去掉编号前缀
            line = re.sub(r'^[\d]+[\.、\)）]\s*', '', line)
            # 去掉markdown列表符号
            line = re.sub(r'^[-*•]\s*', '', line)
            # 去掉引号
            line = line.strip('"\'""''')
            if line and 5 < len(line) < 100:
                # 确保以问号结尾
                if not line.endswith('？') and not line.endswith('?'):
                    line = line + '？'
                questions.append(line)
        # 去重（保持顺序）
        return list(dict.fromkeys(questions))

    def _check_dup(self, question: str, existing: List[str]) -> Dict:
        """检查与现有问题的相似度，标记可能重复"""
        max_sim = 0.0
        for existing_q in existing:
            sim = self._similarity(question, existing_q)
            if sim > max_sim:
                max_sim = sim
        return {
            "question": question,
            "is_duplicate": max_sim >= 0.8,
            "similarity": round(max_sim, 2)
        }

    def _similarity(self, q1: str, q2: str) -> float:
        """计算两个问题的字符集合Jaccard相似度（简单去重）"""
        # 去除标点和停用词
        def normalize(s):
            s = re.sub(r'[？?，,。.！!、\s]', '', s)
            return set(s)
        s1 = normalize(q1)
        s2 = normalize(q2)
        if not s1 or not s2:
            return 0.0
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0

    def _fallback_synonyms(self, question: str) -> List[str]:
        """同义变体降级模板"""
        # 去掉结尾问号
        base = question.rstrip('？?')
        templates = [
            f"{base}？",
            f"{base}比较好？",
            f"{base}推荐？",
            f"{base}哪个好？",
        ]
        # 简单替换"哪个"相关的
        if '哪个' in base:
            templates.append(base.replace('哪个', '什么') + '？')
        # 去重
        result = list(dict.fromkeys(templates))
        # 去掉和原问题完全一样的
        result = [q for q in result if q != question]
        return result[:4]

    def _fallback_deep(self, question: str, profile: dict = None) -> List[str]:
        """深度延伸降级模板"""
        if not profile:
            return []
        specialty_raw = profile.get('specialty', '')
        if not specialty_raw:
            return []
        specialties = [s.strip() for s in specialty_raw.split(',') if s.strip()]
        if not specialties:
            return []

        base = question.rstrip('？?')
        results = []
        for spec in specialties[:3]:
            # 尝试把泛化词替换为具体疾病
            if '妇科' in base and spec != '妇科':
                results.append(base.replace('妇科', spec) + '？')
            elif '哪个医生' in base:
                results.append(f"{base.replace('哪个医生', spec + '哪个医生')}？")
            else:
                results.append(f"{base}{spec}？")
        # 去重
        return list(dict.fromkeys(results))[:3]
