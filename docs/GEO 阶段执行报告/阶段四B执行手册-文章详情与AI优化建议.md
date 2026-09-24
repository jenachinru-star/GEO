# 阶段四B执行手册：文章详情与AI优化建议

> **执行模式**：新session执行，按需确认命令行操作
> **手册粒度**：B为主（函数/方法级别），关键改动用A（精确到行）
> **前置条件**：阶段四A已完成（commit 4c5dfd2），ENCRYPT_KEY已配置，工作区干净
> **Python路径**：`C:\Users\jenac\miniconda3\python.exe`（必须用这个）

---

## 一、阶段四B 目标

在阶段四A（微信公众号数据采集与账号概览）的基础上，增加：
1. **文章详情页**：查看单篇文章的详细数据和增长趋势
2. **AI文章优化建议**：4个维度（标题分析/内容分析/互动分析/选题建议），调用LLM给出可操作的优化建议
3. **文章数据快照完善**：发布后1/3/7/30天多时间点数据，展示增长趋势
4. **文章正文存储**：通过本系统发布的文章，发布时同步存储正文，供AI分析使用
5. **文章列表导出Excel**：导出文章数据到Excel

**交付物**：
- 1个数据库迁移（WechatArticle加content字段）
- 1个新模型（ArticleAnalysis）
- 1个AI分析服务（article_analysis_service.py）
- 1个异步任务（article_analysis_tasks.py）
- 4个新API（文章详情/AI分析提交/AI分析结果/文章导出）
- 1个前端页面（文章详情页）
- 2个前端修改（文章列表加按钮/导出功能）
- 数据采集服务完善（多时间点快照）
- 发布流程完善（同步存储正文）

---

## 二、改动文件清单

| 类型 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| 新建 | `backend/migrations/add_content_to_wechat_article.py` | 新建 | WechatArticle加content字段 |
| 新建 | `backend/app/models/article_analysis.py` | 新建 | AI分析结果模型 |
| 新建 | `backend/app/services/article_analysis_service.py` | 新建 | AI分析服务（4个维度） |
| 新建 | `backend/app/worker/article_analysis_tasks.py` | 新建 | AI分析异步任务 |
| 新建 | `frontend/src/pages/WechatArticleDetail.tsx` | 新建 | 文章详情页 |
| 修改 | `backend/app/models/wechat_stats.py` | 修改 | WechatArticle加content字段（模型层） |
| 修改 | `backend/app/models/__init__.py` | 修改 | 注册ArticleAnalysis模型 |
| 修改 | `backend/app/services/wechat_data_service.py` | 修改 | 完善多时间点快照逻辑 |
| 修改 | `backend/app/worker/publish_tasks.py` | 修改 | 发布时同步存储正文 |
| 修改 | `backend/app/worker/worker.py` | 修改 | 注册新任务类型 |
| 修改 | `backend/app/api/publish_account.py` | 修改 | 新增4个API |
| 修改 | `backend/app/services/export_service.py` | 修改 | 新增文章导出方法 |
| 修改 | `frontend/src/pages/WechatAccountStats.tsx` | 修改 | 文章列表加"详情"/"AI分析"/"导出"按钮 |
| 修改 | `frontend/src/router/index.tsx` | 修改 | 注册文章详情页路由 |

---

## 三、详细执行步骤

### 步骤1：WechatArticle 模型增加 content 字段

**文件**：`backend/app/models/wechat_stats.py`

在 `WechatArticle` 类中，`media_id` 字段后添加：

```python
    content = Column(Text, default="")           # 文章正文（通过本系统发布时同步存储）
```

修改后的 WechatArticle 类完整字段顺序：
```python
class WechatArticle(Base):
    __tablename__ = "geo_wechat_article"
    id = ...
    account_id = ...
    user_id = ...
    title = ...
    article_url = ...
    cover_url = ...
    author = ...
    digest = ...
    publish_date = ...
    media_id = ...
    content = Column(Text, default="")  # 新增
    created_at = ...
    updated_at = ...
```

---

### 步骤2：数据库迁移脚本

**文件**：`backend/migrations/add_content_to_wechat_article.py`

```python
"""WechatArticle表增加content字段
运行方式：cd backend && C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.add_content_to_wechat_article
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def upgrade():
    print("为 geo_wechat_article 表增加 content 字段...")
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(geo_wechat_article)"))
        columns = [row[1] for row in result.fetchall()]
        if 'content' in columns:
            print("⚠️ content 字段已存在，跳过")
            return
        conn.execute(text("ALTER TABLE geo_wechat_article ADD COLUMN content TEXT DEFAULT ''"))
        conn.commit()
    print("✅ content 字段添加完成")

if __name__ == "__main__":
    upgrade()
```

**执行迁移**：
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m migrations.add_content_to_wechat_article
```

---

### 步骤3：新建 ArticleAnalysis 模型

**文件**：`backend/app/models/article_analysis.py`

```python
"""文章AI分析结果模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class ArticleAnalysis(Base):
    """文章AI分析结果（缓存，避免重复调用LLM）"""
    __tablename__ = "geo_article_analysis"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("geo_wechat_article.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("geo_publish_account.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)

    analysis_type = Column(String(50), default="full")  # full / title / content / interaction / topic
    status = Column(String(20), default="pending")  # pending / processing / completed / failed
    result_json = Column(Text, default="")  # 分析结果（JSON格式）
    failed_reason = Column(Text, default="")
    tokens_used = Column(Integer, default=0)  # 消耗的token数

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_article_analysis_article_type', 'article_id', 'analysis_type', unique=True),
    )
```

---

### 步骤4：注册新模型

**文件**：`backend/app/models/__init__.py`

在文件中添加导入：
```python
from app.models.article_analysis import ArticleAnalysis
```

并在 `__all__` 列表中添加 `ArticleAnalysis`。

---

### 步骤5：完善数据采集服务 - 多时间点快照

**文件**：`backend/app/services/wechat_data_service.py`

**修改 `collect_and_store` 方法中的文章数据快照存储逻辑**。

找到当前存储文章数据快照的代码（约在方法的后半部分，`# 5. 存储文章基本信息和数据快照` 注释处），将原来的 `snapshot_day=0` 逻辑替换为多时间点快照逻辑。

**替换后的完整逻辑**：

```python
        # 5. 存储文章基本信息和数据快照
        article_count = 0
        article_stats_count = 0
        for item in article_total:
            msgid = str(item.get("msgid", ""))
            title = item.get("title", "")
            details = item.get("details", [])

            if not msgid or not details:
                continue

            # 查找或创建文章记录
            article = db.query(WechatArticle).filter(
                WechatArticle.account_id == account.id,
                WechatArticle.media_id == msgid,
            ).first()

            if not article:
                first_detail = details[0] if details else {}
                publish_date_str = first_detail.get("stat_date", "")
                try:
                    publish_date = date.fromisoformat(publish_date_str) if publish_date_str else None
                except ValueError:
                    publish_date = None

                article = WechatArticle(
                    account_id=account.id,
                    user_id=account.user_id,
                    title=title,
                    media_id=msgid,
                    publish_date=publish_date,
                )
                db.add(article)
                db.flush()
                article_count += 1

            # 计算多时间点快照：发布后第1/3/7/30天的累计数据
            # details是按日期排序的每日数据，需要累加计算
            if not article.publish_date:
                continue

            snapshot_days = [1, 3, 7, 30]
            cumulative = {
                "int_page_read_count": 0, "int_page_read_user": 0,
                "ori_page_read_user": 0, "ori_page_read_count": 0,
                "share_user": 0, "share_count": 0,
                "add_to_fav_user": 0, "add_to_fav_count": 0,
                "like_count": 0,
            }

            # 按日期排序details
            sorted_details = sorted(details, key=lambda x: x.get("stat_date", ""))

            for detail in sorted_details:
                stat_date_str = detail.get("stat_date", "")
                try:
                    stat_date = date.fromisoformat(stat_date_str)
                except ValueError:
                    continue

                # 累加数据
                for key in cumulative:
                    cumulative[key] += detail.get(key, 0)

                # 计算发布后第几天
                days_since_publish = (stat_date - article.publish_date).days + 1

                # 检查是否到达快照时间点
                for snapshot_day in snapshot_days:
                    if days_since_publish == snapshot_day:
                        self._save_article_snapshot(
                            db, article, account, snapshot_day, stat_date, cumulative
                        )
                        article_stats_count += 1

            # 保存当前最新数据作为 snapshot_day=0（当前数据，不受时间点限制）
            if sorted_details:
                latest = sorted_details[-1]
                stat_date_str = latest.get("stat_date", "")
                try:
                    stat_date = date.fromisoformat(stat_date_str)
                except ValueError:
                    stat_date = date.today()

                # 重新计算累计到最新日期
                latest_cumulative = {
                    "int_page_read_count": 0, "int_page_read_user": 0,
                    "ori_page_read_user": 0, "ori_page_read_count": 0,
                    "share_user": 0, "share_count": 0,
                    "add_to_fav_user": 0, "add_to_fav_count": 0,
                    "like_count": 0,
                }
                for detail in sorted_details:
                    for key in latest_cumulative:
                        latest_cumulative[key] += detail.get(key, 0)

                self._save_article_snapshot(
                    db, article, account, 0, stat_date, latest_cumulative
                )
```

**在 `WechatDataService` 类中添加辅助方法 `_save_article_snapshot`**：

```python
    @staticmethod
    def _save_article_snapshot(db, article, account, snapshot_day: int, stat_date: date, data: dict):
        """保存或更新文章数据快照"""
        from app.models.wechat_stats import WechatArticleStats

        existing = db.query(WechatArticleStats).filter(
            WechatArticleStats.article_id == article.id,
            WechatArticleStats.snapshot_day == snapshot_day,
        ).first()

        if existing:
            existing.stat_date = stat_date
            existing.int_page_read_count = data.get("int_page_read_count", 0)
            existing.int_page_read_user = data.get("int_page_read_user", 0)
            existing.ori_page_read_user = data.get("ori_page_read_user", 0)
            existing.ori_page_read_count = data.get("ori_page_read_count", 0)
            existing.share_user = data.get("share_user", 0)
            existing.share_count = data.get("share_count", 0)
            existing.add_to_fav_user = data.get("add_to_fav_user", 0)
            existing.add_to_fav_count = data.get("add_to_fav_count", 0)
            existing.like_count = data.get("like_count", 0)
        else:
            stats = WechatArticleStats(
                article_id=article.id,
                account_id=account.id,
                user_id=account.user_id,
                snapshot_day=snapshot_day,
                stat_date=stat_date,
                int_page_read_count=data.get("int_page_read_count", 0),
                int_page_read_user=data.get("int_page_read_user", 0),
                ori_page_read_user=data.get("ori_page_read_user", 0),
                ori_page_read_count=data.get("ori_page_read_count", 0),
                share_user=data.get("share_user", 0),
                share_count=data.get("share_count", 0),
                add_to_fav_user=data.get("add_to_fav_user", 0),
                add_to_fav_count=data.get("add_to_fav_count", 0),
                like_count=data.get("like_count", 0),
            )
            db.add(stats)
```

---

### 步骤6：发布时同步存储正文

**文件**：`backend/app/worker/publish_tasks.py`

先读取当前文件内容，了解发布流程。然后在发布成功后，把正文存到 `WechatArticle.content`。

**关键修改点**：在发布成功、获取到文章URL后，查找或创建 `WechatArticle` 记录，并存储正文。

在发布任务处理函数中，发布成功后添加：

```python
        # 发布成功后，同步存储文章正文到WechatArticle（供AI分析使用）
        try:
            from app.models.wechat_stats import WechatArticle
            from datetime import date

            # 查找是否已有该文章的记录（通过标题匹配）
            article_record = db.query(WechatArticle).filter(
                WechatArticle.account_id == account_id,
                WechatArticle.title == title,
            ).first()

            if not article_record:
                article_record = WechatArticle(
                    account_id=account_id,
                    user_id=user_id,
                    title=title,
                    article_url=publish_url,
                    publish_date=date.today(),
                    content=content,  # 存储正文
                )
                db.add(article_record)
            else:
                # 更新正文和URL
                if not article_record.content:
                    article_record.content = content
                if publish_url and not article_record.article_url:
                    article_record.article_url = publish_url

            db.commit()
            logger.info(f"文章正文已同步存储到WechatArticle，article_id={article_record.id}")
        except Exception as e:
            logger.warning(f"同步存储文章正文失败（不影响发布结果）: {e}")
            db.rollback()
```

注意：需要根据 publish_tasks.py 的实际变量名调整（title/content/account_id/user_id/publish_url 等）。

---

### 步骤7：新建 AI 分析服务

**文件**：`backend/app/services/article_analysis_service.py`

```python
"""文章AI优化建议服务
4个分析维度：
1. 标题分析：标题吸引力评估+优化建议
2. 内容分析：内容结构评估+优化方向
3. 互动分析：互动率评估+提升建议
4. 选题建议：基于账号历史数据+GEO热点的选题方向
"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.wechat_stats import WechatArticle, WechatArticleStats, WechatAccountStats
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
        """获取用户启用的LLM适配器"""
        from app.adapters import adapter_factory
        from app.models.user_platform_pref import UserPlatformPref

        # 获取用户启用的文本平台
        enabled_prefs = db.query(UserPlatformPref).filter(
            UserPlatformPref.user_id == user_id,
            UserPlatformPref.enabled == True,
            UserPlatformPref.platform_type == "text",
        ).all()

        if not enabled_prefs:
            # 回退到全局启用的平台
            platforms = adapter_factory.get_enabled_platforms()
            if not platforms:
                raise ValueError("未配置任何可用的AI平台")
            return adapter_factory.get_adapter(platforms[0])

        # 使用第一个启用的平台
        for pref in enabled_prefs:
            adapter = adapter_factory.get_adapter(pref.platform_code)
            if adapter:
                return adapter

        raise ValueError("未找到可用的AI平台适配器")

    @staticmethod
    def analyze_title(article: WechatArticle, stats: WechatArticleStats) -> dict:
        """标题分析（不需要LLM，基于数据规则）"""
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
        }

    @staticmethod
    def analyze_interaction(article: WechatArticle, stats: WechatArticleStats) -> dict:
        """互动分析（不需要LLM，基于数据规则）"""
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
                          stats: WechatArticleStats, account_stats_list: list,
                          user_id: int) -> dict:
        """使用LLM进行深度分析（标题优化+内容分析+选题建议）"""
        adapter = cls._get_llm_adapter(db, user_id)

        # 准备分析数据
        title_analysis = cls.analyze_title(article, stats)
        interaction_analysis = cls.analyze_interaction(article, stats)

        # 账号近期文章数据（用于选题建议）
        recent_articles = db.query(WechatArticle).filter(
            WechatArticle.account_id == article.account_id,
            WechatArticle.id != article.id,
        ).order_by(WechatArticle.publish_date.desc()).limit(20).all()

        recent_titles = [a.title for a in recent_articles if a.title]

        # GEO监测热点（用于选题建议）
        hot_semantics = db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.enabled == True,
        ).limit(10).all()
        hot_topics = [s.text for s in hot_semantics if s.text]

        # 构造prompt
        content_preview = (article.content or "")[:2000] if article.content else "（该文章非本系统发布，无正文内容，仅基于标题和数据进行分析）"

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
{chr(10).join(f'- {t}' for t in recent_titles[:10])}

## GEO监测热点话题
{chr(10).join(f'- {t}' for t in hot_topics[:5])}

## 行业基准
- 平均阅读量：{INDUSTRY_BENCHMARK['avg_reads_per_article']}
- 平均点赞率：{INDUSTRY_BENCHMARK['avg_like_rate']*100}%
- 平均分享率：{INDUSTRY_BENCHMARK['avg_share_rate']*100}%

## 请按以下JSON格式输出分析结果
{{
  "title_optimization": {{
    "current_title_score": {title_analysis['overall_score']},
    "problems": ["问题1", "问题2"],
    "optimized_titles": ["优化标题1", "优化标题2", "优化标题3"]
  }},
  "content_analysis": {{
    "structure_score": 0-10,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "optimization_suggestions": ["建议1", "建议2", "建议3"]
  }},
  "topic_suggestions": {{
    "content_gap": "账号内容缺口分析",
    "suggested_topics": [
      {{"topic": "选题1", "reason": "理由", "expected_effect": "预期效果"}},
      {{"topic": "选题2", "reason": "理由", "expected_effect": "预期效果"}},
      {{"topic": "选题3", "reason": "理由", "expected_effect": "预期效果"}},
      {{"topic": "选题4", "reason": "理由", "expected_effect": "预期效果"}},
      {{"topic": "选题5", "reason": "理由", "expected_effect": "预期效果"}}
    ]
  }}
}}

请直接输出JSON，不要输出其他内容。"""

        system_prompt = "你是一位资深的医疗行业微信公众号运营专家，擅长数据分析和内容优化。输出必须是严格的JSON格式。"

        logger.info(f"[文章AI分析] 开始LLM分析，article_id={article.id}")
        result = adapter.query(prompt, system_prompt=system_prompt)

        # 解析LLM输出
        llm_result = {}
        try:
            content = result.get("content", "") if isinstance(result, dict) else str(result)
            # 尝试提取JSON
            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start >= 0 and json_end > json_start:
                llm_result = json.loads(content[json_start:json_end+1])
        except Exception as e:
            logger.warning(f"[文章AI分析] LLM输出解析失败: {e}")
            llm_result = {"raw_output": str(result)[:500]}

        # 合并规则分析和LLM分析
        final_result = {
            "title_analysis": title_analysis,
            "interaction_analysis": interaction_analysis,
            "llm_analysis": llm_result,
        }

        # 把LLM生成的优化标题合并到title_analysis
        if "title_optimization" in llm_result:
            final_result["title_analysis"]["optimized_titles"] = \
                llm_result["title_optimization"].get("optimized_titles", [])
            final_result["title_analysis"]["problems"] = \
                llm_result["title_optimization"].get("problems", [])

        return final_result
```

---

### 步骤8：新建 AI 分析异步任务

**文件**：`backend/app/worker/article_analysis_tasks.py`

```python
"""文章AI分析异步任务"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.wechat_stats import WechatArticle, WechatArticleStats
from app.models.article_analysis import ArticleAnalysis
from app.services.article_analysis_service import ArticleAnalysisService
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_article_analysis(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理文章AI分析任务"""
    payload = json.loads(task.payload_json or "{}")
    article_id = payload.get("article_id")
    analysis_type = payload.get("analysis_type", "full")

    if not article_id:
        raise ValueError("payload 中缺少 article_id")

    article = db.query(WechatArticle).filter(WechatArticle.id == article_id).first()
    if not article:
        raise ValueError(f"文章不存在: {article_id}")

    if on_progress:
        on_progress(1, 3, "查询文章数据")

    # 获取最新文章数据快照
    stats = db.query(WechatArticleStats).filter(
        WechatArticleStats.article_id == article_id,
        WechatArticleStats.snapshot_day == 0,
    ).first()

    if on_progress:
        on_progress(2, 3, "LLM分析中（约10-30秒）")

    # 执行分析
    result = ArticleAnalysisService.analyze_with_llm(
        db, article, stats, [], article.user_id
    )

    if on_progress:
        on_progress(3, 3, "分析完成，保存结果")

    # 保存分析结果
    analysis_record = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == analysis_type,
    ).first()

    if analysis_record:
        analysis_record.result_json = json.dumps(result, ensure_ascii=False)
        analysis_record.status = "completed"
        analysis_record.completed_at = datetime.now()
    else:
        analysis_record = ArticleAnalysis(
            article_id=article_id,
            account_id=article.account_id,
            user_id=article.user_id,
            analysis_type=analysis_type,
            status="completed",
            result_json=json.dumps(result, ensure_ascii=False),
            completed_at=datetime.now(),
        )
        db.add(analysis_record)

    db.commit()

    return {"article_id": article_id, "analysis_type": analysis_type, "status": "completed"}


# 注册任务处理函数
register_handler("article_analysis", handle_article_analysis)
```

---

### 步骤9：注册新任务类型到 Worker

**文件**：`backend/app/worker/worker.py`

**修改1**：在导入区域（约第39行后）添加：
```python
import app.worker.article_analysis_tasks  # noqa: F401
```

**修改2**：在 `TASK_TIMEOUT_BY_TYPE` 字典中添加：
```python
"article_analysis": 300,  # 文章AI分析：5分钟
```

---

### 步骤10：新增 4 个 API

**文件**：`backend/app/api/publish_account.py`

在文件末尾添加以下4个API。

**API 1：文章详情**

```python
@router.get("/{account_id}/articles/{article_id}", summary="文章详情")
def get_article_detail(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取文章详情（含多时间点数据快照）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 获取所有时间点快照
    snapshots = db.query(WechatArticleStats).filter(
        WechatArticleStats.article_id == article_id,
    ).order_by(WechatArticleStats.snapshot_day.asc()).all()

    snapshot_data = {}
    for s in snapshots:
        snapshot_data[f"day_{s.snapshot_day}"] = {
            "snapshot_day": s.snapshot_day,
            "stat_date": s.stat_date.isoformat(),
            "int_page_read_count": s.int_page_read_count,
            "int_page_read_user": s.int_page_read_user,
            "share_count": s.share_count,
            "like_count": s.like_count,
            "add_to_fav_count": s.add_to_fav_count,
        }

    # 获取最新分析结果
    latest_analysis = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).order_by(ArticleAnalysis.created_at.desc()).first()

    return {"code": 0, "message": "success", "data": {
        "id": article.id,
        "title": article.title,
        "article_url": article.article_url,
        "cover_url": article.cover_url,
        "author": article.author,
        "digest": article.digest,
        "publish_date": article.publish_date.isoformat() if article.publish_date else None,
        "has_content": bool(article.content),
        "snapshots": snapshot_data,
        "latest_analysis": {
            "status": latest_analysis.status if latest_analysis else "none",
            "created_at": latest_analysis.created_at.isoformat() if latest_analysis and latest_analysis.created_at else None,
        } if latest_analysis else None,
    }}
```

**API 2：提交AI分析**

```python
@router.post("/{account_id}/articles/{article_id}/analyze", summary="提交文章AI分析")
def submit_article_analysis(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """提交文章AI分析任务（异步）"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 检查是否已有正在处理的分析
    existing_task = db.query(AsyncTask).filter(
        AsyncTask.task_type == "article_analysis",
        AsyncTask.status.in_(["queued", "running"]),
        AsyncTask.created_by == user_id,
    ).first()
    if existing_task:
        return {"code": 0, "message": "已有分析任务在执行中", "data": {"task_id": existing_task.id}}

    # 创建异步任务
    task = AsyncTask(
        task_type="article_analysis",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({"article_id": article_id, "analysis_type": "full"}, ensure_ascii=False),
        progress_message=f"AI分析文章 [{article.title[:20]}]",
    )
    db.add(task)
    db.commit()

    # 更新分析记录状态为processing
    analysis_record = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).first()
    if analysis_record:
        analysis_record.status = "processing"
    else:
        analysis_record = ArticleAnalysis(
            article_id=article_id,
            account_id=account_id,
            user_id=user_id,
            analysis_type="full",
            status="processing",
        )
        db.add(analysis_record)
    db.commit()

    return {"code": 0, "message": "分析任务已提交，约10-30秒后完成", "data": {"task_id": task.id}}
```

**API 3：获取AI分析结果**

```python
@router.get("/{account_id}/articles/{article_id}/analysis", summary="获取文章AI分析结果")
def get_article_analysis(
    account_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取文章AI分析结果"""
    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    article = db.query(WechatArticle).filter(
        WechatArticle.id == article_id,
        WechatArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    analysis = db.query(ArticleAnalysis).filter(
        ArticleAnalysis.article_id == article_id,
        ArticleAnalysis.analysis_type == "full",
    ).order_by(ArticleAnalysis.created_at.desc()).first()

    if not analysis:
        return {"code": 0, "message": "success", "data": {"status": "none", "result": None}}

    result_data = None
    if analysis.status == "completed" and analysis.result_json:
        try:
            result_data = json.loads(analysis.result_json)
        except Exception:
            result_data = None

    return {"code": 0, "message": "success", "data": {
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "result": result_data,
        "failed_reason": analysis.failed_reason,
    }}
```

**API 4：文章列表导出Excel**

```python
@router.get("/{account_id}/articles/export", summary="导出文章列表Excel")
def export_articles(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出账号文章列表为Excel"""
    from app.services.export_service import ExportService
    from fastapi.responses import StreamingResponse
    import io

    account = db.query(PublishAccount).filter(
        PublishAccount.id == account_id,
        PublishAccount.user_id == user_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 获取所有文章
    articles = db.query(WechatArticle).filter(
        WechatArticle.account_id == account_id,
    ).order_by(WechatArticle.publish_date.desc()).all()

    # 生成Excel
    output = ExportService.export_wechat_articles(db, account, articles)

    filename = f"公众号文章数据_{account.account_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
    }
    return StreamingResponse(io.BytesIO(output), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
```

同时需要在文件顶部添加导入：
```python
from app.models.wechat_stats import WechatArticle, WechatArticleStats, WechatAccountStats
from app.models.article_analysis import ArticleAnalysis
from app.models.task import AsyncTask
```

---

### 步骤11：新增文章导出方法

**文件**：`backend/app/services/export_service.py`

在类中添加静态方法 `export_wechat_articles`：

```python
    @staticmethod
    def export_wechat_articles(db, account, articles: list) -> bytes:
        """导出微信公众号文章列表为Excel

        Args:
            db: 数据库会话
            account: PublishAccount对象
            articles: WechatArticle列表

        Returns:
            bytes: Excel文件二进制数据
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from app.models.wechat_stats import WechatArticleStats
        import io

        wb = Workbook()
        ws = wb.active
        ws.title = "文章数据"

        # 标题行样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        # 表头
        headers = ["序号", "文章标题", "发布日期", "阅读量", "阅读人数", "点赞", "分享", "收藏", "点赞率", "分享率"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # 数据行
        for row_idx, article in enumerate(articles, 2):
            # 获取最新数据快照
            stats = db.query(WechatArticleStats).filter(
                WechatArticleStats.article_id == article.id,
                WechatArticleStats.snapshot_day == 0,
            ).first()

            reads = stats.int_page_read_count if stats else 0
            likes = stats.like_count if stats else 0
            shares = stats.share_count if stats else 0
            favorites = stats.add_to_fav_count if stats else 0
            like_rate = f"{(likes/reads*100):.2f}%" if reads > 0 else "0%"
            share_rate = f"{(shares/reads*100):.2f}%" if reads > 0 else "0%"

            ws.cell(row=row_idx, column=1, value=row_idx - 1)
            ws.cell(row=row_idx, column=2, value=article.title)
            ws.cell(row=row_idx, column=3, value=article.publish_date.isoformat() if article.publish_date else "")
            ws.cell(row=row_idx, column=4, value=reads)
            ws.cell(row=row_idx, column=5, value=stats.int_page_read_user if stats else 0)
            ws.cell(row=row_idx, column=6, value=likes)
            ws.cell(row=row_idx, column=7, value=shares)
            ws.cell(row=row_idx, column=8, value=favorites)
            ws.cell(row=row_idx, column=9, value=like_rate)
            ws.cell(row=row_idx, column=10, value=share_rate)

        # 调整列宽
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 8
        ws.column_dimensions['G'].width = 8
        ws.column_dimensions['H'].width = 8
        ws.column_dimensions['I'].width = 8
        ws.column_dimensions['J'].width = 8

        # 输出到字节流
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
```

---

### 步骤12：新建文章详情页

**文件**：`frontend/src/pages/WechatArticleDetail.tsx`

```tsx
import { useState, useEffect, useCallback } from 'react'
import {
  Card, Row, Col, Statistic, Button, Tag, message, Space,
  Descriptions, Spin, Empty, Alert, Tabs, Divider
} from 'antd'
import {
  ArrowLeftOutlined, EyeOutlined, LikeOutlined, ShareAltOutlined,
  StarOutlined, ThunderboltOutlined, ReloadOutlined, FileTextOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '@/api'
import { useParams, useNavigate } from 'react-router-dom'

const WechatArticleDetail = () => {
  const { accountId, articleId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [article, setArticle] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [pollingCount, setPollingCount] = useState(0)

  const loadArticle = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/articles/${articleId}`)
      setArticle(res.data)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }, [accountId, articleId])

  const loadAnalysis = useCallback(async () => {
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/articles/${articleId}/analysis`)
      setAnalysis(res.data)
      // 如果正在处理，继续轮询
      if (res.data?.status === 'processing' && pollingCount < 20) {
        setTimeout(() => {
          setPollingCount(c => c + 1)
          loadAnalysis()
        }, 3000)
      }
    } catch (e) {
      // 错误已由拦截器处理
    }
  }, [accountId, articleId, pollingCount])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      await request.post(`/publish-accounts/${accountId}/articles/${articleId}/analyze`)
      message.success('分析任务已提交，约10-30秒后完成')
      setPollingCount(0)
      setTimeout(() => loadAnalysis(), 3000)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setAnalyzing(false)
    }
  }

  useEffect(() => {
    if (accountId && articleId) {
      loadArticle()
      loadAnalysis()
    }
  }, [accountId, articleId, loadArticle, loadAnalysis])

  // 获取最新数据（snapshot_day=0）
  const latestData = article?.snapshots?.day_0 || {}

  // 数据增长趋势图
  const growthOption = article?.snapshots ? {
    title: { text: '文章数据增长趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['阅读量', '点赞', '分享'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['发布当天', '第1天', '第3天', '第7天', '第30天'],
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '阅读量', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.int_page_read_count || 0,
          article.snapshots.day_1?.int_page_read_count || 0,
          article.snapshots.day_3?.int_page_read_count || 0,
          article.snapshots.day_7?.int_page_read_count || 0,
          article.snapshots.day_30?.int_page_read_count || 0,
        ]
      },
      {
        name: '点赞', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.like_count || 0,
          article.snapshots.day_1?.like_count || 0,
          article.snapshots.day_3?.like_count || 0,
          article.snapshots.day_7?.like_count || 0,
          article.snapshots.day_30?.like_count || 0,
        ]
      },
      {
        name: '分享', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.share_count || 0,
          article.snapshots.day_1?.share_count || 0,
          article.snapshots.day_3?.share_count || 0,
          article.snapshots.day_7?.share_count || 0,
          article.snapshots.day_30?.share_count || 0,
        ]
      },
    ]
  } : {}

  const renderAnalysisContent = () => {
    if (!analysis || analysis.status === 'none') {
      return (
        <Empty description="暂无AI分析结果">
          <Button type="primary" icon={<ThunderboltOutlined />} loading={analyzing} onClick={handleAnalyze}>
            开始AI分析
          </Button>
        </Empty>
      )
    }

    if (analysis.status === 'processing') {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>AI正在分析中，约10-30秒...</p>
        </div>
      )
    }

    if (analysis.status === 'failed') {
      return (
        <Alert
          type="error"
          message="分析失败"
          description={analysis.failed_reason || '未知错误'}
          action={<Button onClick={handleAnalyze}>重试</Button>}
        />
      )
    }

    const result = analysis.result || {}
    const titleAnalysis = result.title_analysis || {}
    const interactionAnalysis = result.interaction_analysis || {}
    const llmAnalysis = result.llm_analysis || {}

    return (
      <div>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} loading={analyzing} onClick={handleAnalyze}>
            重新分析
          </Button>
          <Tag color="blue">分析时间：{analysis.completed_at ? new Date(analysis.completed_at).toLocaleString() : '-'}</Tag>
        </Space>

        <Tabs defaultActiveKey="title" items={[
          {
            key: 'title',
            label: '标题分析',
            children: (
              <div>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="当前标题">{article?.title}</Descriptions.Item>
                  <Descriptions.Item label="标题长度">{titleAnalysis.title_length} 字</Descriptions.Item>
                  <Descriptions.Item label="标题评分">{titleAnalysis.overall_score}/10</Descriptions.Item>
                  <Descriptions.Item label="阅读量">{titleAnalysis.reads}</Descriptions.Item>
                </Descriptions>

                {titleAnalysis.problems?.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <h4>存在问题</h4>
                    {titleAnalysis.problems.map((p: string, i: number) => (
                      <div key={i}>• {p}</div>
                    ))}
                  </div>
                )}

                {titleAnalysis.optimized_titles?.length > 0 && (
                  <div>
                    <h4>AI优化标题建议</h4>
                    {titleAnalysis.optimized_titles.map((t: string, i: number) => (
                      <Alert
                        key={i}
                        type="info"
                        showIcon
                        message={`建议 ${i + 1}：${t}`}
                        style={{ marginBottom: 8 }}
                      />
                    ))}
                  </div>
                )}

                {titleAnalysis.suggestions?.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h4>优化建议</h4>
                    {titleAnalysis.suggestions.map((s: string, i: number) => (
                      <div key={i}>• {s}</div>
                    ))}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'content',
            label: '内容分析',
            children: (
              <div>
                {!article?.has_content ? (
                  <Alert
                    type="warning"
                    message="该文章非本系统发布，无正文内容"
                    description="内容分析需要文章正文。如需内容分析，请将文章通过本系统发布，或手动粘贴正文（后续版本支持）。"
                  />
                ) : (
                  <div>
                    {llmAnalysis.content_analysis && (
                      <>
                        <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                          <Descriptions.Item label="内容结构评分">
                            {llmAnalysis.content_analysis.structure_score}/10
                          </Descriptions.Item>
                        </Descriptions>

                        {llmAnalysis.content_analysis.strengths?.length > 0 && (
                          <div style={{ marginBottom: 16 }}>
                            <h4>内容优点</h4>
                            {llmAnalysis.content_analysis.strengths.map((s: string, i: number) => (
                              <div key={i} style={{ color: '#52c41a' }}>✓ {s}</div>
                            ))}
                          </div>
                        )}

                        {llmAnalysis.content_analysis.weaknesses?.length > 0 && (
                          <div style={{ marginBottom: 16 }}>
                            <h4>内容不足</h4>
                            {llmAnalysis.content_analysis.weaknesses.map((w: string, i: number) => (
                              <div key={i} style={{ color: '#faad14' }}>⚠ {w}</div>
                            ))}
                          </div>
                        )}

                        {llmAnalysis.content_analysis.optimization_suggestions?.length > 0 && (
                          <div>
                            <h4>内容优化建议</h4>
                            {llmAnalysis.content_analysis.optimization_suggestions.map((s: string, i: number) => (
                              <Alert key={i} type="info" showIcon message={s} style={{ marginBottom: 8 }} />
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'interaction',
            label: '互动分析',
            children: (
              <div>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="阅读量">{interactionAnalysis.reads}</Descriptions.Item>
                  <Descriptions.Item label="点赞">{interactionAnalysis.likes}</Descriptions.Item>
                  <Descriptions.Item label="分享">{interactionAnalysis.shares}</Descriptions.Item>
                  <Descriptions.Item label="收藏">{interactionAnalysis.favorites}</Descriptions.Item>
                  <Descriptions.Item label="点赞率">{(interactionAnalysis.like_rate * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="分享率">{(interactionAnalysis.share_rate * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="收藏率">{(interactionAnalysis.favorite_rate * 100).toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="行业均值点赞率">2%</Descriptions.Item>
                </Descriptions>

                {interactionAnalysis.suggestions?.length > 0 && (
                  <div>
                    <h4>互动提升建议</h4>
                    {interactionAnalysis.suggestions.map((s: string, i: number) => (
                      <Alert key={i} type="info" showIcon message={s} style={{ marginBottom: 8 }} />
                    ))}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'topic',
            label: '选题建议',
            children: (
              <div>
                {llmAnalysis.topic_suggestions ? (
                  <>
                    <Alert
                      type="info"
                      showIcon
                      message="内容缺口分析"
                      description={llmAnalysis.topic_suggestions.content_gap}
                      style={{ marginBottom: 16 }}
                    />

                    <h4>AI推荐选题方向（5个）</h4>
                    {llmAnalysis.topic_suggestions.suggested_topics?.map((topic: any, i: number) => (
                      <Card key={i} size="small" style={{ marginBottom: 12 }}>
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label={`选题 ${i + 1}`}>{topic.topic}</Descriptions.Item>
                          <Descriptions.Item label="推荐理由">{topic.reason}</Descriptions.Item>
                          <Descriptions.Item label="预期效果">{topic.expected_effect}</Descriptions.Item>
                        </Descriptions>
                      </Card>
                    ))}
                  </>
                ) : (
                  <Empty description="暂无选题建议" />
                )}
              </div>
            )
          },
        ]} />
      </div>
    )
  }

  if (loading && !article) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin size="large" /></div>
  }

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        {article?.article_url && (
          <Button type="link" href={article.article_url} target="_blank">
            <FileTextOutlined /> 查看原文
          </Button>
        )}
      </Space>

      {/* 文章标题 */}
      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 8 }}>{article?.title}</h2>
        <Space>
          <Tag color="blue">发布日期：{article?.publish_date || '-'}</Tag>
          {article?.has_content && <Tag color="green">有正文</Tag>}
          {!article?.has_content && <Tag color="orange">无正文（非本系统发布）</Tag>}
        </Space>
      </Card>

      {/* 数据卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="阅读量" value={latestData.int_page_read_count || 0} prefix={<EyeOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="点赞" value={latestData.like_count || 0} prefix={<LikeOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="分享" value={latestData.share_count || 0} prefix={<ShareAltOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="收藏" value={latestData.add_to_fav_count || 0} prefix={<StarOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 数据增长趋势图 */}
      <Card title="数据增长趋势" style={{ marginBottom: 24 }}>
        <ReactECharts option={growthOption} style={{ height: 350 }} />
      </Card>

      {/* AI分析结果 */}
      <Card title="AI优化建议" extra={<ThunderboltOutlined style={{ color: '#faad14' }} />}>
        {renderAnalysisContent()}
      </Card>
    </div>
  )
}

export default WechatArticleDetail
```

---

### 步骤13：修改文章列表 - 增加按钮

**文件**：`frontend/src/pages/WechatAccountStats.tsx`

**修改1**：在 `articleColumns` 中增加"操作"列：

```tsx
  const articleColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: '25%' },
    { title: '发布日期', dataIndex: 'publish_date', key: 'publish_date', width: 100 },
    { title: '阅读量', dataIndex: 'reads', key: 'reads', width: 80, render: (v: number) => <span><EyeOutlined /> {v}</span> },
    { title: '点赞', dataIndex: 'likes', key: 'likes', width: 70, render: (v: number) => <span><LikeOutlined /> {v}</span> },
    { title: '分享', dataIndex: 'shares', key: 'shares', width: 70, render: (v: number) => <span><ShareAltOutlined /> {v}</span> },
    { title: '收藏', dataIndex: 'favorites', key: 'favorites', width: 70 },
    {
      title: '操作', key: 'action', width: 150,
      render: (_: any, record: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/publish-accounts/${accountId}/articles/${record.id}`)}>
            详情
          </Button>
          <Button type="link" size="small" onClick={() => navigate(`/publish-accounts/${accountId}/articles/${record.id}`)}>
            AI分析
          </Button>
        </Space>
      )
    },
  ]
```

**修改2**：在"已发布文章"卡片的 title 中增加"导出Excel"按钮：

```tsx
          <Card
            title="已发布文章"
            extra={
              <Button
                size="small"
                onClick={() => window.open(`/api/v1/publish-accounts/${accountId}/articles/export`, '_blank')}
              >
                导出Excel
              </Button>
            }
          >
```

注意：导出按钮的URL需要根据实际的API前缀调整。如果前端request有baseURL，需要用完整的后端地址。建议用：
```tsx
onClick={() => window.open(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/publish-accounts/${accountId}/articles/export`, '_blank')}
```

或者更简单的方式：用request获取blob然后下载。但为了简单，先用window.open方式，需要后端CORS配置允许。

---

### 步骤14：注册文章详情页路由

**文件**：`frontend/src/router/index.tsx`

在路由配置中添加（参考阶段四A添加的账号概览页路由的方式）：

```tsx
{
  path: '/publish-accounts/:accountId/articles/:articleId',
  name: 'WechatArticleDetail',
  component: () => import('@/pages/WechatArticleDetail'),
}
```

---

## 四、验证清单

### 后端验证

1. **数据库迁移**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\backend
   C:\Users\jenac\miniconda3\python.exe -m migrations.add_content_to_wechat_article
   ```
   确认 content 字段添加成功。

2. **后端import检查**：
   ```bash
   C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
   ```

3. **后端启动**：启动后端，确认无ERROR，新任务类型 `article_analysis` 已注册。

4. **API测试**：
   - `GET /api/v1/publish-accounts/{id}/articles/{article_id}` — 文章详情
   - `POST /api/v1/publish-accounts/{id}/articles/{article_id}/analyze` — 提交AI分析
   - `GET /api/v1/publish-accounts/{id}/articles/{article_id}/analysis` — 获取分析结果
   - `GET /api/v1/publish-accounts/{id}/articles/export` — 导出Excel

### 前端验证

1. **前端tsc检查**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\frontend
   npx tsc --noEmit
   ```

2. **前端启动**：启动前端，确认无编译错误。

3. **页面测试**：
   - 账号概览页：文章列表显示"详情"和"AI分析"按钮，右上角有"导出Excel"按钮
   - 点击"详情"：进入文章详情页，显示数据卡片+增长趋势图+AI分析区域
   - 点击"开始AI分析"：提交分析任务，显示loading，约10-30秒后显示分析结果
   - AI分析结果：4个Tab（标题分析/内容分析/互动分析/选题建议），内容正确展示
   - 导出Excel：点击导出，下载Excel文件，内容正确

### 数据采集验证

1. 手动触发采集，确认文章数据快照包含1/3/7/30天多时间点数据
2. 文章详情页的增长趋势图正确显示多时间点数据

### 发布流程验证

1. 通过本系统发布一篇文章到微信公众号
2. 确认发布后 WechatArticle 表中该文章的 content 字段有正文内容
3. 文章详情页显示"有正文"标签
4. AI分析的内容分析Tab正常展示

---

## 五、注意事项

1. **文章正文限制**：只有通过本系统发布的文章才有正文。历史文章（非本系统发布）没有正文，内容分析Tab会提示"无正文"。后续版本可以加手动粘贴正文功能。

2. **AI分析耗时**：LLM分析约10-30秒，前端用轮询方式获取结果（每3秒轮询一次，最多20次）。

3. **分析结果缓存**：分析结果存储在 `article_analysis` 表中，下次进入文章详情页直接展示缓存结果。用户可以点击"重新分析"强制重新生成。

4. **多时间点快照计算**：微信API的 `getarticletotal` 返回每天的数据，需要累加计算发布后第N天的累计数据。如果文章发布时间不足30天，对应的时间点快照会为空。

5. **用户隔离**：所有API都校验 `user_id`，确保用户只能查看自己的账号和文章数据。

6. **导出Excel**：导出接口返回文件流，前端用 `window.open` 方式下载。需要确保后端CORS配置允许该接口的跨域请求。

7. **医疗行业基准数据**：`INDUSTRY_BENCHMARK` 是硬编码的医疗行业公众号基准数据，后续可以调整为可配置。

---

## 六、Git 提交

完成所有改动并验证通过后：

```bash
cd C:\Users\jenac\Desktop\GEO
git add backend/migrations/add_content_to_wechat_article.py
git add backend/app/models/article_analysis.py
git add backend/app/models/wechat_stats.py
git add backend/app/models/__init__.py
git add backend/app/services/article_analysis_service.py
git add backend/app/services/export_service.py
git add backend/app/services/wechat_data_service.py
git add backend/app/worker/article_analysis_tasks.py
git add backend/app/worker/publish_tasks.py
git add backend/app/worker/worker.py
git add backend/app/api/publish_account.py
git add frontend/src/pages/WechatArticleDetail.tsx
git add frontend/src/pages/WechatAccountStats.tsx
git add frontend/src/router/index.tsx
git commit -m "feat: 阶段四B-文章详情与AI优化建议（10项）"
```

---

**手册结束。执行过程中有任何不明白、不确定的事项，主动提出讨论。**
