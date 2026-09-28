"""竞品对比AI分析服务
基于对比数据，调用LLM给出差距分析和改进建议。
"""
import json
import logging
from sqlalchemy.orm import Session
from app.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)


class CompetitorAnalysisService:
    """竞品对比AI分析服务"""

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

    @classmethod
    def analyze(cls, db: Session, account_id: int, benchmark_id: int, user_id: int) -> dict:
        """执行竞品对比AI分析"""
        # 1. 获取对比数据
        comparison = BenchmarkService.compare(db, account_id, benchmark_id, user_id)

        # 2. 获取LLM适配器
        adapter = cls._get_llm_adapter(db, user_id)

        # 3. 构造prompt
        own = comparison["own"]
        benchmark = comparison["benchmark"]
        gaps = comparison["gaps"]

        own_top = comparison["own_top_articles"][:3]
        bench_top = comparison["benchmark_top_articles"][:3]

        prompt = f"""你是一位资深的医疗行业微信公众号运营专家。请根据以下数据，对自己账号与对标账号进行深度对比分析，并给出可操作的改进建议。

## 自己账号数据
- 账号名称：{own['account_name']}
- 粉丝数：{own['followers']}
- 平均阅读量：{own['avg_reads']}
- 平均点赞：{own['avg_likes']}
- 平均分享：{own['avg_shares']}
- 每周发文数：{own['weekly_posts']}
- 近30天发文数：{own['total_articles_30d']}
- 近30天总阅读：{own['total_reads_30d']}

## 对标账号数据
- 账号名称：{benchmark['account_name']}
- 微信号：{benchmark.get('wechat_id', '')}
- 粉丝数：{benchmark['followers']}
- 平均阅读量：{benchmark['avg_reads']}
- 平均点赞：{benchmark['avg_likes']}
- 平均分享：{benchmark['avg_shares']}
- 每周发文数：{benchmark['weekly_posts']}

## 差距分析（正数表示领先，负数表示落后）
- 粉丝数差距：{gaps['followers']}%
- 平均阅读差距：{gaps['avg_reads']}%
- 平均点赞差距：{gaps['avg_likes']}%
- 平均分享差距：{gaps['avg_shares']}%
- 发文频率差距：{gaps['weekly_posts']}%

## 自己账号爆款文章Top3
{chr(10).join(f'- {a["title"]}（阅读{a["reads"]}，点赞{a["likes"]}，分享{a["shares"]}）' for a in own_top) if own_top else '（暂无数据）'}

## 对标账号爆款文章Top3
{chr(10).join(f'- {a["title"]}（阅读{a["reads"]}，点赞{a["likes"]}，分享{a["shares"]}）' for a in bench_top) if bench_top else '（暂无数据）'}

## 请按以下JSON格式输出分析结果
{{
  "overall_assessment": "整体评估（100字以内）",
  "strengths": ["自己账号的优势1", "优势2", "优势3"],
  "weaknesses": ["自己账号的不足1", "不足2", "不足3"],
  "gap_analysis": {{
    "content_quality": "内容质量差距分析",
    "publishing_frequency": "发文频率差距分析",
    "engagement": "互动率差距分析",
    "audience_scale": "粉丝规模差距分析"
  }},
  "improvement_suggestions": [
    {{"area": "改进领域1", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}},
    {{"area": "改进领域2", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}},
    {{"area": "改进领域3", "suggestion": "具体建议", "priority": "high/medium/low", "expected_effect": "预期效果"}}
  ],
  "content_direction": "未来内容方向建议（100字以内）"
}}

请直接输出JSON，不要输出其他内容。"""

        system_prompt = "你是一位资深的医疗行业微信公众号运营专家，擅长竞品分析和内容优化。输出必须是严格的JSON格式。"

        logger.info(f"[竞品AI分析] 开始LLM分析，account_id={account_id}, benchmark_id={benchmark_id}")
        result = adapter.query(prompt, system_prompt=system_prompt)

        # 解析LLM输出（adapter.query()返回QueryResult对象，用.answer取内容）
        llm_result = {}
        tokens_used = 0
        try:
            content = result.answer if hasattr(result, 'answer') else str(result)
            tokens_used = getattr(result, 'total_tokens', 0) or 0
            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start >= 0 and json_end > json_start:
                llm_result = json.loads(content[json_start:json_end+1])
        except Exception as e:
            logger.warning(f"[竞品AI分析] LLM输出解析失败: {e}")
            llm_result = {"raw_output": str(result)[:500]}

        # 合并对比数据和LLM分析
        final_result = {
            "comparison": comparison,
            "llm_analysis": llm_result,
            "tokens_used": tokens_used,
        }

        return final_result
