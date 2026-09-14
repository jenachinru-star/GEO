import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MentionResult:
    """品牌提及解析结果"""
    mentioned: bool
    rank: int  # 排名，0=未提及
    sentiment: float  # 情感分 -1~1
    mentioned_alias: Optional[str] = None  # 匹配到的别名
    context: str = ""  # 提及上下文


class AnswerParser:
    """AI回答解析引擎 - 从回答中提取品牌提及、排名、情感"""

    # 正向情感词
    POSITIVE_WORDS = [
        "推荐", "优势", "领先", "优秀", "专业", "知名", "头部", "第一梯队",
        "强大", "成熟", "可靠", "创新", "领先", "出色", "优质", "值得",
        "首选", "口碑好", "实力强", "技术先进"
    ]
    # 负向情感词
    NEGATIVE_WORDS = [
        "不足", "缺点", "劣势", "落后", "较差", "一般", "普通", "问题",
        "风险", "争议", "不足", "欠缺", "较弱", "不成熟", "不稳定"
    ]

    def __init__(self, brand_aliases: List[str]):
        self.brand_aliases = brand_aliases
        # 编译正则模式
        self.alias_patterns = [
            re.compile(re.escape(alias), re.IGNORECASE)
            for alias in brand_aliases
            if alias.strip()
        ]

    def parse(self, answer: str) -> MentionResult:
        """解析回答，提取品牌提及信息"""
        if not answer or not answer.strip():
            return MentionResult(mentioned=False, rank=0, sentiment=0.0)

        # 1. 检测是否提及
        mentioned = False
        matched_alias = None
        mention_position = -1

        for i, pattern in enumerate(self.alias_patterns):
            match = pattern.search(answer)
            if match:
                mentioned = True
                matched_alias = self.brand_aliases[i]
                mention_position = match.start()
                break

        if not mentioned:
            return MentionResult(mentioned=False, rank=0, sentiment=0.0)

        # 2. 提取排名
        rank = self._extract_rank(answer, mention_position)

        # 3. 分析情感
        sentiment = self._analyze_sentiment(answer, mention_position)

        # 4. 提取上下文
        context = self._extract_context(answer, mention_position)

        return MentionResult(
            mentioned=True,
            rank=rank,
            sentiment=sentiment,
            mentioned_alias=matched_alias,
            context=context
        )

    def _extract_rank(self, answer: str, mention_pos: int) -> int:
        """提取品牌在回答中的排名"""
        # 方法1：查找提及位置前面最近的序号（1. 2. 3. 或 1、2、3、）
        before_text = answer[:mention_pos]

        # 匹配 "1." "2." "3." 或 "1、" "2、" "3、"
        num_pattern = re.compile(r'(\d+)[\.、\)）]\s*$')
        lines = before_text.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line:
                m = re.match(r'^(\d+)[\.、\)）]', line)
                if m:
                    rank = int(m.group(1))
                    if 1 <= rank <= 50:
                        return rank
                # 匹配 "第一" "第二"
                cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                m = re.search(r'第([一二三四五六七八九十]+)', line)
                if m:
                    num_str = m.group(1)
                    if num_str in cn_num:
                        return cn_num[num_str]

        # 方法2：按段落/换行计数，品牌在第几个条目
        items = re.split(r'\n\s*\d+[\.、\)）]|\n\s*[-*•]\s', answer)
        for i, item in enumerate(items):
            for pattern in self.alias_patterns:
                if pattern.search(item):
                    return i if i > 0 else 1

        # 方法3：如果都没匹配到，默认排名1（提及了但没明确序号）
        return 1

    def _analyze_sentiment(self, answer: str, mention_pos: int) -> float:
        """分析提及位置附近的情感倾向"""
        # 取提及位置前后200字符
        start = max(0, mention_pos - 100)
        end = min(len(answer), mention_pos + 200)
        context = answer[start:end]

        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in context)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in context)

        total = positive_count + negative_count
        if total == 0:
            return 0.1  # 中性偏正（被提及本身是正向信号）

        score = (positive_count - negative_count) / total
        return round(max(-1.0, min(1.0, score)), 2)

    def _extract_context(self, answer: str, mention_pos: int, window: int = 150) -> str:
        """提取提及位置的上下文"""
        start = max(0, mention_pos - window)
        end = min(len(answer), mention_pos + window)
        context = answer[start:end].strip()
        if start > 0:
            context = "..." + context
        if end < len(answer):
            context = context + "..."
        return context

    def parse_competitors(self, answer: str, competitor_aliases: Dict[int, List[str]]) -> Dict[int, Tuple[bool, int]]:
        """解析回答中竞品的提及情况
        返回: {competitor_id: (mentioned, rank)}
        """
        results = {}
        for comp_id, aliases in competitor_aliases.items():
            mentioned = False
            rank = 0
            for alias in aliases:
                if alias and alias.lower() in answer.lower():
                    mentioned = True
                    pos = answer.lower().find(alias.lower())
                    rank = self._extract_rank(answer, pos)
                    break
            results[comp_id] = (mentioned, rank)
        return results
