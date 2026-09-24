# -*- coding: utf-8 -*-
"""文章AI优化建议服务
4个分析维度：
1. 标题分析：标题吸引力评估（规则评分）+ LLM生成优化标题
2. 内容分析：LLM分析内容结构与优化方向（需要正文，无正文时提示）
3. 互动分析：规则计算点赞率/分享率/收藏率，对比医疗行业基准
4. 选题建议：LLM基于账号历史文章 + GEO监测热点生成5个选题方向

注意（阶段四B按实际代码修正，手册原代码与真实接口不符）：
- UserPlatformPref 无 platform_type 字段，仅按 user_id + enabled 过滤
- adapter.query() 返回 QueryResult（.answer/.success/.total_tokens），不是 dict
- Semantic 字段为 question / is_active（不是 text / enabled）
"""
import re
import json
import logging
from sqlalchemy.orm import Session
from app.models.wechat_stats import WechatArticle, WechatArticleStats
from app.models.article_analysis import ArticleAnalysis
from app.models.semantic import Semantic

logger = logging.getLogger(__name__)

# 医疗行业公众号基准数据（用于对比分析）
INDUSTRY_BENCHMARK = {
    "avg_reads_per_article": 500,      # 平均阅读量
    "avg_like_rate": 0.02,              # 平均点赞率（点赞/阅读）
    "avg_share_rate": 0.03,             # 平均分享率
    "avg_favorite_rate": 0.015,         # 平均收藏率
}


class ArticleAnalysisService:
    """文章AI分析服务"""

    @staticmethod
    def _get_llm_adapter(db: Session, user_id: int):
        """获取用户启用的LLM适配器；用户未配置时回退到全局启用的平台"""
        from app.adapters import adapter_factory
        from app.models.user_platform_pref import UserPlatformPref

        # 获取用户启用的平台（该表无 platform_type 字段，不做类型过滤）
        enabled_prefs = db.query(UserPlatformPref).filter(
            UserPlatformPref.user_id == user_id,
            UserPlatformPref.enabled == True,  # noqa: E712
        ).all()

        # 使用第一个能取到适配器的用户级平台
        for pref in enabled_prefs:
            adapter = adapter_factory.get_adapter(pref.platform_code)
            if adapter:
                return adapter

        # 回退到全局启用的平台
        platforms = adapter_factory.get_enabled_platforms()
        if not platforms:
            raise ValueError("未配置任何可用的AI平台，请先在平台配置中启用AI模型")
        adapter = adapter_factory.get_adapter(platforms[0])
        if not adapter:
            raise ValueError("未找到可用的AI平台适配器")
        return adapter

    @staticmethod
    def analyze_title(article: WechatArticle, stats: WechatArticleStats | None) -> dict:
        """标题分析（规则计算，不需要LLM；优化标题由LLM补充）"""
        title = article.title or ""
        reads = stats.int_page_read_count if stats else 0
        read_users = stats.int_page_read_user if stats else 0

        # 标题长度分析
        title_len = len(title)
        length_score = 10 if 15 <= title_len <= 25 else (7 if 10 <= title_len <= 30 else 4)

        # 阅读量评分
        if reads >= 2000:
            read_score = 10
        elif reads >= 1000:
            read_score = 8
        elif reads >= 500:
            read_score = 6
        elif reads >= 100:
            read_score = 4
        else:
            read_score = 2

        overall_score = round((length_score + read_score) / 2, 1)

        suggestions = []
        if title_len < 15:
            suggestions.append("标题偏短，建议增加到15-25字，包含更多关键词")
        elif title_len > 30:
            suggestions.append("标题偏长，建议精简到25字以内，突出核心信息")
        if reads < INDUSTRY_BENCHMARK["avg_reads_per_article"]:
            suggestions.append("阅读量低于行业均值，建议优化标题吸引力，可尝试数字型、疑问型或痛点型标题")

        return {
            "title": title,
            "title_length": title_len,
            "length_score": length_score,
            "read_score": read_score,
            "overall_score": overall_score,
            "reads": reads,
            "read_users": read_users,
            "suggestions": suggestions,
            "optimized_titles": [],  # 由LLM生成
            "problems": [],          # 由LLM生成
        }

    @staticmethod
    def analyze_interaction(article: WechatArticle, stats: WechatArticleStats | None) -> dict:
        """互动分析（规则计算，不需要LLM）"""
        reads = stats.int_page_read_count if stats else 0
        likes = stats.like_count if stats else 0
        shares = stats.share_count if stats else 0
        favorites = stats.add_to_fav_count if stats else 0

        like_rate = (likes / reads) if reads > 0 else 0
        share_rate = (shares / reads) if reads > 0 else 0
        favorite_rate = (favorites / reads) if reads > 0 else 0

        suggestions = []
        if like_rate < INDUSTRY_BENCHMARK["avg_like_rate"]:
            suggestions.append("点赞率低于行业均值，建议在文末增加引导点赞的话术，或增加内容的情感共鸣点")
        if share_rate < INDUSTRY_BENCHMARK["avg_share_rate"]:
            suggestions.append("分享率低于行业均值，建议增加实用价值（如干货清单、工具推荐），或增加社交货币属性（如观点鲜明、可炫耀）")
        if favorite_rate < INDUSTRY_BENCHMARK["avg_favorite_rate"]:
            suggestions.append("收藏率低于行业均值，建议增加可收藏的实用内容（如指南、清单、资源汇总）")

        return {
            "reads": reads,
            "likes": likes,
            "shares": shares,
            "favorites": favorites,
            "like_rate": round(like_rate, 4),
            "share_rate": round(share_rate, 4),
            "favorite_rate": round(favorite_rate, 4),
            "industry_benchmark": INDUSTRY_BENCHMARK,
            "suggestions": suggestions,
        }

    @classmethod
    def analyze_with_llm(cls, db: Session, article: WechatArticle,
                         stats: WechatArticleStats | None,
                         user_id: int) -> tuple[dict, int]:
        """使用LLM进行深度分析（标题优化 + 内容分析 + 选题建议）

        Returns: (final_result, tokens_used)
        """
        adapter = cls._get_llm_adapter(db, user_id)

        # 规则分析结果
        title_analysis = cls.analyze_title(article, stats)
        interaction_analysis = cls.analyze_interaction(article, stats)

        # 账号近期文章（用于选题建议）
        recent_articles = db.query(WechatArticle).filter(
            WechatArticle.account_id == article.account_id,
            WechatArticle.id != article.id,
        ).order_by(WechatArticle.publish_date.desc()).limit(20).all()
        recent_titles = [a.title for a in recent_articles if a.title]

        # GEO监测热点（Semantic：字段 question/is_active）
        hot_semantics = db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.is_active == True,  # noqa: E712
        ).limit(10).all()
        hot_topics = [s.question for s in hot_semantics if s.question]

        # 正文预览（无正文时明确告知LLM）
        if article.content:
            content_preview = article.content[:2000]
        else:
            content_preview = "（该文章非本系统发布，无正文内容，仅基于标题和数据进行分析）"

        prompt = f"""你是一位资深的医疗行业微信公众号运营专家。请对以下文章进行深度分析，并给出可操作的优化建议。

## 文章基本信息
- 标题：{article.title}
- 发布日期：{article.publish_date}
- 阅读量：{stats.int_page_read_count if stats else 0}
- 点赞：{stats.like_count if stats else 0}
- 分享：{stats.share_count if stats else 0}
- 收藏：{stats.add_to_fav_count if stats else 0}

## 文章正文（前2000字）
{content_preview}

## 账号近期文章标题（最近20篇）
{chr(10).join(f'- {t}' for t in recent_titles[:10]) or '（暂无历史文章）'}

## GEO监测热点话题
{chr(10).join(f'- {t}' for t in hot_topics[:5]) or '（暂无热点数据）'}

## 行业基准
- 平均阅读量：{INDUSTRY_BENCHMARK['avg_reads_per_article']}
- 平均点赞率：{INDUSTRY_BENCHMARK['avg_like_rate'] * 100}%
- 平均分享率：{INDUSTRY_BENCHMARK['avg_share_rate'] * 100}%

## 请按以下JSON格式输出分析结果
（每项控制条数，内容精炼，避免冗长）
{{
  "title_optimization": {{
    "current_title_score": {title_analysis['overall_score']},
    "problems": ["问题1", "问题2"],
    "optimized_titles": ["优化标题1", "优化标题2", "优化标题3"]
  }},
  "content_analysis": {{
    "structure_score": 0,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "optimization_suggestions": ["建议1", "建议2", "建议3"]
  }},
  "topic_suggestions": {{
    "content_gap": "账号内容缺口分析（一句话）",
    "suggested_topics": [
      {{"topic": "选题1", "reason": "理由（一句话）", "expected_effect": "预期效果（一句话）"}},
      {{"topic": "选题2", "reason": "理由（一句话）", "expected_effect": "预期效果（一句话）"}},
      {{"topic": "选题3", "reason": "理由（一句话）", "expected_effect": "预期效果（一句话）"}},
      {{"topic": "选题4", "reason": "理由（一句话）", "expected_effect": "预期效果（一句话）"}},
      {{"topic": "选题5", "reason": "理由（一句话）", "expected_effect": "预期效果（一句话）"}}
    ]
  }}
}}

## 输出格式硬性要求（必须严格遵守）
1. 只输出JSON本体，不要输出```代码块标记、前后解释或任何多余文字
2. JSON必须能被标准 json.loads 解析：键和字符串值都使用英文双引号
3. 字符串值内部如需引用，请使用中文书名号或「」，禁止再出现英文双引号
4. 字符串值内部禁止换行，所有内容写在同一行内
5. 数组最后一个元素后、对象最后一个键值对后，不要加多余逗号"""

        system_prompt = "你是一位资深的医疗行业微信公众号运营专家，擅长数据分析和内容优化。输出必须是严格的JSON格式。"

        logger.info(f"[文章AI分析] 开始LLM分析，article_id={article.id}")
        result = adapter.query(prompt, system_prompt=system_prompt)

        # QueryResult：成功取 .answer；失败直接抛错（由任务handler记录failed状态）
        if not getattr(result, "success", True):
            raise ValueError(result.error or "LLM调用失败")
        content = result.answer if hasattr(result, "answer") else str(result)
        tokens_used = getattr(result, "total_tokens", 0) or 0

        # 解析LLM输出（多级容错：直接解析 → 截取 → 修复 → schema兜底）
        llm_result = cls._extract_json_object(content)
        if llm_result is None:
            logger.warning("[文章AI分析] JSON解析与修复均失败，降级为schema正则抽取")
            llm_result = cls._fallback_schema_extract(content)

        # 合并规则分析与LLM分析
        final_result = {
            "title_analysis": title_analysis,
            "interaction_analysis": interaction_analysis,
            "llm_analysis": llm_result,
        }

        # 把LLM生成的优化标题/问题合并到 title_analysis
        title_opt = llm_result.get("title_optimization", {})
        if title_opt:
            final_result["title_analysis"]["optimized_titles"] = title_opt.get("optimized_titles", [])
            final_result["title_analysis"]["problems"] = title_opt.get("problems", [])

        return final_result, tokens_used

    # ===== JSON 输出容错解析（LLM偶发返回不规范JSON）=====

    @staticmethod
    def _extract_json_object(content: str) -> dict | None:
        """从LLM输出中尽力提取JSON对象。
        顺序：去代码围栏 → 直接解析 → 截取最外层花括号 → 修复后解析。
        """
        if not content:
            return None

        candidate = content.strip()

        # 去除 markdown 代码围栏
        fence = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
        if fence:
            candidate = fence.group(1).strip()

        # 直接解析
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass

        # 截取最外层花括号
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            sliced = candidate[start:end + 1]
            try:
                parsed = json.loads(sliced)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                pass

            # 修复常见格式问题后重试
            try:
                repaired = ArticleAnalysisService._repair_json(sliced)
                parsed = json.loads(repaired)
                return parsed if isinstance(parsed, dict) else None
            except Exception as e:
                logger.warning(f"[文章AI分析] JSON修复后仍解析失败: {e}")

        return None

    @staticmethod
    def _repair_json(s: str) -> str:
        """修复LLM输出JSON的常见问题：
        1) 中文弯引号充当JSON定界符 → 替换为英文直引号
        2) 字符串内裸换行/回车/制表符 → 转义
        3) 对象/数组尾逗号 → 删除
        """
        s = s.replace("\u201c", '"').replace("\u201d", '"')

        # 转义字符串内部的裸控制字符（状态机：跟踪字符串内外与转义）
        out: list[str] = []
        in_str = False
        escaped = False
        for ch in s:
            if in_str:
                if escaped:
                    out.append(ch)
                    escaped = False
                    continue
                if ch == "\\":
                    out.append(ch)
                    escaped = True
                    continue
                if ch == '"':
                    out.append(ch)
                    in_str = False
                    continue
                if ch == "\n":
                    out.append("\\n")
                    continue
                if ch == "\r":
                    out.append("\\r")
                    continue
                if ch == "\t":
                    out.append("\\t")
                    continue
                out.append(ch)
            else:
                if ch == '"':
                    in_str = True
                out.append(ch)
        s = "".join(out)

        # 删除对象/数组尾逗号
        s = re.sub(r",(\s*[}\]])", r"\1", s)
        return s

    @staticmethod
    def _fallback_schema_extract(content: str) -> dict:
        """JSON彻底无法解析时，按已知结构用正则抽取，保证部分结果可用。"""
        def string_list(key: str) -> list[str]:
            m = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if not m:
                return []
            return [x.replace('\\"', '"') for x in
                    re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))]

        # content_gap
        gap_m = re.search(r'"content_gap"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
        content_gap = gap_m.group(1).replace('\\"', '"') if gap_m else ""

        # structure_score
        score_m = re.search(r'"structure_score"\s*:\s*([0-9]+(?:\.[0-9]+)?)', content)
        structure_score = float(score_m.group(1)) if score_m else 0

        # suggested_topics（嵌套对象数组）
        topics: list[dict] = []
        topics_m = re.search(r'"suggested_topics"\s*:\s*\[(.*?)\]\s*[,}]',
                             content, re.DOTALL)
        if topics_m:
            for obj in re.findall(r"\{(.*?)\}", topics_m.group(1), re.DOTALL):
                item = {}
                for k in ("topic", "reason", "expected_effect"):
                    mm = re.search(rf'"{k}"\s*:\s*"((?:[^"\\]|\\.)*)"', obj)
                    item[k] = mm.group(1).replace('\\"', '"') if mm else ""
                if item.get("topic"):
                    topics.append(item)

        return {
            "title_optimization": {
                "problems": string_list("problems"),
                "optimized_titles": string_list("optimized_titles"),
            },
            "content_analysis": {
                "structure_score": structure_score,
                "strengths": string_list("strengths"),
                "weaknesses": string_list("weaknesses"),
                "optimization_suggestions": string_list("optimization_suggestions"),
            },
            "topic_suggestions": {
                "content_gap": content_gap,
                "suggested_topics": topics,
            },
            "_degraded": True,  # 标记：降级抽取，结构可能不完整
        }
