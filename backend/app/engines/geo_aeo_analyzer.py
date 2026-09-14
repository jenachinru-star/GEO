"""GEO/AEO检测解析引擎 — 区分被推荐(GEO)和被引用(AEO)"""
import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class GEOAEOResult:
    """GEO/AEO检测结果"""
    geo_mentioned: bool       # GEO：被推荐进列表
    geo_rank: int | None      # GEO排名，None=未形成明确排序
    aeo_cited: bool           # AEO：被引用为答案
    aeo_confidence: float     # AEO引用置信度 0~1
    raw_answer: str
    # 新增字段（供LLM分析结果回填）
    is_recommendation: bool = False
    recommendation_evidence: str = ""
    mention_evidence: str = ""
    citation_urls: list = None
    sentiment: str = "neutral"


class GEOAEOAnalyzer:
    """分析AI回答，判断医生是否被GEO推荐和AEO引用"""

    # AEO引用句式模式
    CITATION_PATTERNS = [
        r'(根据|按照|依据).{0,30}(医生|专家|教授|主任).{0,15}(的观点|指出|表示|认为|介绍|建议|提醒|强调)',
        r'(医生|专家|教授|主任).{0,15}(表示|指出|认为|建议|提醒|强调|推荐|介绍)',
        r'(引用|参考|援引).{0,30}(文章|研究|资料|观点)',
        r'据.{0,15}(介绍|了解|报道|分析)',
    ]

    # 治疗方案关键词（AEO辅助判断）
    TREATMENT_KEYWORDS = [
        '治疗方法', '治疗方案', '怎么治', '如何治疗', '治疗建议',
        '预防措施', '注意事项', '用药', '药物', '手术',
        '检查', '诊断', '症状', '原因', '危害',
    ]

    def __init__(self, doctor_name: str, hospital: str, department: str = "",
                 self_intro: str = "", aliases: List[str] = None):
        self.doctor_name = doctor_name or ""
        self.hospital = hospital or ""
        self.department = department or ""
        self.self_intro = self_intro or ""
        self.aliases = aliases or []
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[re.Pattern]:
        """构建实体匹配正则模式"""
        patterns = []
        # 医生姓名
        if self.doctor_name and len(self.doctor_name) >= 2:
            patterns.append(re.compile(re.escape(self.doctor_name)))
        # 医院+医生 组合（医院名单独不算命中）
        if self.hospital and self.doctor_name:
            patterns.append(re.compile(re.escape(self.hospital + self.doctor_name)))
            patterns.append(re.compile(re.escape(self.hospital + ".*?" + self.doctor_name)))
        # 统一自我介绍（通常包含医生名，作为辅助）
        if self.self_intro and len(self.self_intro) >= 4 and self.doctor_name in self.self_intro:
            patterns.append(re.compile(re.escape(self.self_intro)))
        # 别名
        for alias in self.aliases:
            if alias and len(alias) >= 2:
                patterns.append(re.compile(re.escape(alias), re.IGNORECASE))
        return patterns

    def analyze(self, answer: str) -> GEOAEOResult:
        """分析回答，返回GEO/AEO结果"""
        if not answer or not answer.strip():
            return GEOAEOResult(False, None, False, 0.0, answer)

        # 1. GEO检测：是否提及医生/医院
        geo_mentioned = False
        mention_pos = -1
        for pattern in self.patterns:
            match = pattern.search(answer)
            if match:
                geo_mentioned = True
                mention_pos = match.start()
                break

        if not geo_mentioned:
            return GEOAEOResult(False, None, False, 0.0, answer)

        # 2. 提取GEO排名
        geo_rank = self._extract_rank(answer, mention_pos)

        # 3. AEO检测：是否被引用为答案（geo_mentioned作为参数传入，避免作用域问题）
        aeo_cited, aeo_confidence = self._detect_aeo(answer, mention_pos, geo_mentioned)

        return GEOAEOResult(geo_mentioned, geo_rank, aeo_cited, aeo_confidence, answer)

    def _extract_rank(self, answer: str, mention_pos: int) -> int | None:
        """提取提及位置的排名。无法确定时返回 None（不再默认1）"""
        before_text = answer[:mention_pos]
        lines = before_text.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line:
                m = re.match(r'^(\d+)[\.、\)）]', line)
                if m:
                    rank = int(m.group(1))
                    if 1 <= rank <= 50:
                        return rank
                cn_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
                m = re.search(r'第([一二三四五六七八九十]+)', line)
                if m and m.group(1) in cn_num:
                    return cn_num[m.group(1)]
        # 按条目计数（仅当回答中确实存在列表结构时才适用）
        items = re.split(r'\n\s*\d+[\.、\)）]|\n\s*[-*•]\s', answer)
        if len(items) > 1:
            for i, item in enumerate(items):
                for pattern in self.patterns:
                    if pattern.search(item):
                        return i if i > 0 else 1
        # 无法确定排名，返回 None（不再默认1）
        return None

    def _detect_aeo(self, answer: str, mention_pos: int, geo_mentioned: bool) -> Tuple[bool, float]:
        """检测是否为AEO引用

        Args:
            answer: 完整回答文本
            mention_pos: 医生实体提及的字符位置
            geo_mentioned: 是否已被GEO提及（由调用方传入，避免作用域引用）
        """
        # 在提及位置前后取上下文
        start = max(0, mention_pos - 200)
        end = min(len(answer), mention_pos + 600)
        context = answer[start:end]

        max_confidence = 0.0

        # 检测引用句式
        for pattern in self.CITATION_PATTERNS:
            if re.search(pattern, context):
                max_confidence = max(max_confidence, 0.8)
                break

        # 检测治疗方案内容（辅助提升置信度）
        has_treatment = any(kw in context for kw in self.TREATMENT_KEYWORDS)
        if has_treatment:
            max_confidence = max(max_confidence, 0.5)

        # 如果回答整体较短且直接给出方案，AEO置信度中等
        if len(answer) < 500 and has_treatment and geo_mentioned:
            max_confidence = max(max_confidence, 0.6)

        return (max_confidence >= 0.5, round(max_confidence, 2))
