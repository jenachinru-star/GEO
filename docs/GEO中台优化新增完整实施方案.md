# GEO 中台优化/修复/新增完整实施方案

> 基于 geo-score 开源项目审查结论，输出可直接执行的端到端方案
> 版本：v1.0 | 日期：2026-09-16

---

## 第一部分：整体思路、逻辑与框架

### 1.1 核心问题诊断

当前 GEO 中台存在一个**结构性缺口**：

```
当前链路：  问题配置 → 调用AI平台API → 解析回答 → 统计提及率/排名
                ↑                                    ↓
            只看"输出侧结果"                    结果差了不知道为什么
```

**问题**：用户看到"提及率 30%"，但系统无法回答以下任何一个问题：
- 是品牌官网被 AI 爬虫封禁了？（基础设施问题）
- 是官网内容没有结构化数据，AI 看不懂？（可理解性问题）
- 是内容段落写得不好，AI 不愿意引用？（内容质量问题）
- 是品牌缺乏第三方背书，AI 不信任？（可信度问题）

**geo-score 解决的正是这个缺口**：它从"输入侧"诊断网站对 AI 的友好程度，21 项检查覆盖从爬虫可达性到内容可引用性的完整链路。

### 1.2 目标架构：三层闭环

```
┌─────────────────────────────────────────────────────────────────┐
│                     第三层：优化与修复工具（新增）                  │
│  llms.txt生成器 │ JSON-LD生成器 │ 内容改写建议 │ 告警通知         │
├─────────────────────────────────────────────────────────────────┤
│                     第二层：输出侧监测（现有优化）                  │
│  采集引擎(预检+并发) │ 解析引擎(规则版本化+证据) │ 仪表盘(双维度)  │
│  竞品分析(并排对比) │ RAG问答 │ 内容资产库                          │
├─────────────────────────────────────────────────────────────────┤
│                     第一层：输入侧诊断（核心新增）                  │
│  GEO就绪度扫描引擎(21项检查) │ 内容GEO质量Linter(6项检查)         │
│  网站可达性矩阵(13UA并发) │ 门控预检机制                           │
└─────────────────────────────────────────────────────────────────┘
         ↓ 数据流向：诊断发现问题 → 优化工具修复 → 监测验证效果 ↑
```

**闭环逻辑**：
1. **诊断**：扫描引擎检测品牌官网的 21 项就绪度，内容 Linter 检测每篇文章的 6 项质量
2. **归因**：门控为 0 → 基础设施问题；Content Citability 低 → 内容质量问题；Brand Credibility 低 → 品牌建设问题
3. **修复**：llms.txt 生成器补 Understandable，JSON-LD 生成器补结构化数据，内容改写建议补 Content Citability
4. **监测**：优化后重新扫描 + 持续采集 AI 回答提及率，验证优化效果
5. **告警**：门控状态变化、评分骤降、竞品反超时主动通知

### 1.3 设计原则（从 geo-score 借鉴的工程方法论）

| 原则 | 具体含义 | 在本方案中的落地 |
|------|---------|----------------|
| **门控封顶** | 基础项为 0 时，其他项做得再好也无效，总分封顶 40 | 采集前先跑门控预检，门控为 0 直接跳过 API 调用并标 P0 |
| **分层评分** | 每项检查 2-4 档，每档有明确可观测条件，不是是/否 | 所有评分项都定义 tier 条件，避免"差不多"式判断 |
| **退出分母** | 无法判定的项标记"未判定"并退出分母，不给默认值 | LLM 分析失败、采集失败不与"真的未提及"混算 |
| **版本化** | 评分规则有版本号，不同版本不可比 | 判定规则抽取为 rubric JSON，每条记录标注 rubric_version |
| **证据绑定** | 每个评分都附带可复现的观测证据 | 所有检测结果存储 evidence 字段（原文片段+位置+置信度） |
| **零依赖核心** | 扫描引擎尽量用标准库，减少供应链风险 | site_auditor 用 urllib/正则，不引入 BeautifulSoup/selenium |
| **只测不修** | 诊断工具只给建议，不自动修改用户网站 | 所有修复工具生成代码/内容供用户复制，不自动部署 |

### 1.4 技术栈与复用策略

**复用 geo-score 的方式：抽取而非 import**

```
geo-score/cli/geo_score.py (15.8KB 单文件)
    │
    ├─ 抽取：检测函数（纯逻辑，无 I/O）
    │   ├─ robots.txt 解析逻辑
    │   ├─ 13 个 UA 定义 + 并发探测模式
    │   ├─ JSON-LD 提取（含 @graph 引用解析）
    │   ├─ 自足答案段检测（paragraphs/wc/is_cjk）
    │   ├─ 标题意图匹配（QP_INTENT/NAV_LABEL 正则）
    │   ├─ 时间信号检测（datePublished/dateModified）
    │   └─ 门控封顶 + 分层评分 + 归一化算法
    │
    └─ 重写：I/O 层
        ├─ urllib → httpx（异步，项目已有依赖）
        ├─ print → 数据库持久化 + REST API 返回
        ├─ 同步 → 异步（FastAPI 框架）
        └─ 单文件 → 模块化（engines/site_auditor/）
```

**许可证**：MIT，允许商业使用和修改，需在文件头部标注来源。

---

## 第二部分：P0 模块详细实施方案

### 模块一：GEO 就绪度扫描引擎（核心新增，10-12 人天）

#### 2.1.1 模块定位与功能边界

**做什么**：输入一个 URL，输出 0-100 分的 GEO 就绪度评分，包含 21 项检查的逐项结果、证据和改进建议。

**不做什么**：
- 不自动修改用户网站（只生成修复建议和代码片段）
- 不做需要登录的页面检测（只检测公开可访问页面）
- 不做 JS 渲染后的内容检测（只看原始 HTML 响应，这也是爬虫看到的）
- 不做第三方引用/提及的自动检测（需人工或 LLM 联网辅助，退出分母）

#### 2.1.2 目录结构

```
backend/app/
├── engines/
│   └── site_auditor/              # 新增：网站就绪度扫描引擎
│       ├── __init__.py
│       ├── models.py               # 数据类：ScanResult, CheckResult, Tier
│       ├── rubric.py               # 评分标准：21项检查定义、5支柱、分值、tier条件
│       ├── fetchers.py             # HTTP抓取：13UA并发、robots.txt、sitemap、llms.txt
│       ├── parsers.py              # HTML解析：JSON-LD提取、标题、段落、时间信号
│       ├── checkers/               # 21项检查实现，按支柱分文件
│       │   ├── __init__.py
│       │   ├── reachable.py        # g.robots, g.reachable, g.ssr (15分)
│       │   ├── understandable.py   # p1.sitemap ~ p1.page-type (22分)
│       │   ├── content_citability.py # p2.answer-passages ~ p2.named-author (35分)
│       │   ├── brand_credibility.py  # p3.listings ~ p3.video (18分)
│       │   └── answer_fit.py       # p4.answer-shape ~ p4.cn-engines (10分)
│       ├── scorer.py               # 评分聚合：门控封顶、归一化、档位判定
│       └── auditor.py              # 主入口：SiteAuditor.scan(url) → ScanResult
│
├── api/
│   └── site_audit.py               # 新增：REST API
│
├── models/
│   └── site_audit.py               # 新增：SQLAlchemy 模型
│
└── schemas/
    └── site_audit.py               # 新增：Pydantic 请求/响应模型

frontend/src/
├── pages/
│   └── SiteAudit.tsx               # 新增：站点体检页面
├── api/
│   └── siteAudit.ts                # 新增：API 封装
└── components/
    ├── ScoreGauge.tsx              # 新增：评分仪表盘组件
    ├── PillarBreakdown.tsx         # 新增：5支柱分解组件
    └── CheckItemCard.tsx           # 新增：检查项卡片组件
```

#### 2.1.3 数据模型设计

**表 1：site_audit_record（扫描记录主表）**

```sql
CREATE TABLE site_audit_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL,                  -- 用户输入的URL
    landed_url      TEXT,                           -- 实际跳转后的URL（重定向追踪）
    root_origin     TEXT NOT NULL,                  -- 协议+域名，用于跨次扫描关联
    score           INTEGER NOT NULL DEFAULT 0,     -- 归一化总分 0-100
    raw_score       INTEGER NOT NULL DEFAULT 0,     -- 原始分（含bonus）
    denominator     INTEGER NOT NULL DEFAULT 100,   -- 分母（退出分母项后）
    bonus           INTEGER NOT NULL DEFAULT 0,     -- 附加分（llms-full/ai.txt/geo-link/speakable）
    band            TEXT NOT NULL DEFAULT 'Not started', -- 档位：Not started/Early/Growing/Solid/Leading
    gate_capped     BOOLEAN NOT NULL DEFAULT 0,     -- 是否被门控封顶
    rubric_version  TEXT NOT NULL DEFAULT 'v1.1',   -- 评分标准版本
    auditor_version TEXT NOT NULL DEFAULT '1.0.0',  -- 扫描引擎版本
    sample_pages    TEXT NOT NULL DEFAULT '[]',     -- 抽样的8个页面URL（JSON数组）
    error_message   TEXT,                            -- 扫描失败时的错误信息
    status          TEXT NOT NULL DEFAULT 'pending', -- pending/running/completed/failed
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    user_id         INTEGER,                         -- 触发扫描的用户（可选）
    workspace_id    INTEGER                          -- 工作空间（可选，design-v2 多租户）
);
CREATE INDEX idx_audit_origin ON site_audit_record(root_origin);
CREATE INDEX idx_audit_created ON site_audit_record(created_at);
```

**表 2：site_audit_check（检查项明细表）**

```sql
CREATE TABLE site_audit_check (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id        INTEGER NOT NULL,                -- 关联扫描记录
    check_id        TEXT NOT NULL,                   -- 检查项ID，如 g.robots, p1.llms-txt
    pillar          TEXT NOT NULL,                   -- 支柱：Reachable/Understandable/...
    name            TEXT NOT NULL,                   -- 检查项名称
    name_zh         TEXT NOT NULL,                   -- 中文名称
    max_points      INTEGER NOT NULL,                -- 满分
    scored_points   INTEGER,                         -- 得分，NULL=退出分母
    tier_index      INTEGER,                         -- 当前档位索引（0-based），NULL=退出分母
    tier_total      INTEGER NOT NULL,                -- 总档位数
    is_gate         BOOLEAN NOT NULL DEFAULT 0,      -- 是否门控项
    needs_judgement BOOLEAN NOT NULL DEFAULT 0,      -- 是否需要人工判定（CLI退出分母）
    evidence        TEXT NOT NULL DEFAULT '{}',      -- 证据JSON：{snippet, position, details, page_url}
    current_condition TEXT,                           -- 当前档位的条件描述
    next_condition    TEXT,                           -- 上一档位的条件描述（满分时为NULL）
    improvement_hint  TEXT,                           -- 改进建议（自然语言）
    FOREIGN KEY (audit_id) REFERENCES site_audit_record(id) ON DELETE CASCADE
);
CREATE INDEX idx_check_audit ON site_audit_check(audit_id);
CREATE INDEX idx_check_checkid ON site_audit_check(check_id);
```

**表 3：site_audit_page（抽样页面详情表，可选，用于证据追溯）**

```sql
CREATE TABLE site_audit_page (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id        INTEGER NOT NULL,
    url             TEXT NOT NULL,
    depth           INTEGER NOT NULL DEFAULT 0,      -- 相对于scope的深度
    status_code     INTEGER,                          -- HTTP状态码
    content_length  INTEGER,                          -- 响应体大小
    has_main_text   BOOLEAN NOT NULL DEFAULT 0,      -- HTML中是否有正文（SSR检测）
    has_jsonld      BOOLEAN NOT NULL DEFAULT 0,      -- 是否有JSON-LD
    jsonld_types    TEXT NOT NULL DEFAULT '[]',      -- JSON-LD类型列表
    heading_count   INTEGER NOT NULL DEFAULT 0,      -- h1-h4数量
    paragraph_count INTEGER NOT NULL DEFAULT 0,      -- p标签数量
    answer_passage  TEXT,                             -- 自足答案段原文（如有）
    fetched_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (audit_id) REFERENCES site_audit_record(id) ON DELETE CASCADE
);
```

#### 2.1.4 API 设计

| 方法 | 路径 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/site-audit/scan` | 触发一次扫描（异步） | `{url: "https://example.com", scope?: "/docs"}` | `{audit_id: 123, status: "running"}` |
| GET | `/api/site-audit/{id}` | 获取扫描结果 | - | 完整 ScanResult（含21项检查） |
| GET | `/api/site-audit/{id}/brief` | 获取摘要（首屏三样） | - | `{score, band, points_to_next, top_gaps: [...]}` |
| GET | `/api/site-audit/history?url=...` | 获取某网站的历史扫描 | - | 按时间排序的扫描记录列表 |
| GET | `/api/site-audit/{id}/compare?with_url=...` | 与另一次扫描/网站对比 | - | 并排对比数据 |
| POST | `/api/site-audit/{id}/badge` | 生成SVG徽章 | `{style?: "flat"}` | SVG 文件 |
| GET | `/api/site-audit/rubric` | 获取当前评分标准 | - | rubric JSON（21项检查定义） |

**扫描结果响应结构（GET /api/site-audit/{id}）**：

```json
{
  "audit_id": 123,
  "url": "https://example.com",
  "landed_url": "https://www.example.com",
  "score": 71,
  "band": "Solid",
  "gate_capped": false,
  "rubric_version": "v1.1",
  "points_to_next": 12,
  "next_band": "Leading",
  "pillars": {
    "Reachable": {"scored": 11, "max": 15, "checks": [...]},
    "Understandable": {"scored": 15, "max": 22, "checks": [...]},
    "Content Citability": {"scored": 25, "max": 35, "checks": [...]},
    "Brand Credibility": {"scored": 8, "max": 10, "checks": [...]},
    "Answer Fit": {"scored": 2, "max": 4, "checks": [...]}
  },
  "top_gaps": [
    {"check_id": "p2.question-intent", "name": "标题匹配提问意图", "points_recoverable": 4, "hint": "..."},
    {"check_id": "p2.named-author", "name": "可验证作者署名", "points_recoverable": 3, "hint": "..."},
    {"check_id": "p2.freshness", "name": "时间信号", "points_recoverable": 3, "hint": "..."}
  ],
  "checks": [
    {
      "check_id": "g.robots",
      "pillar": "Reachable",
      "name": "Crawlers allowed in robots.txt",
      "name_zh": "robots放行检索爬虫",
      "max_points": 5,
      "scored_points": 3,
      "tier_index": 1,
      "tier_total": 3,
      "is_gate": true,
      "evidence": {"snippet": "User-agent: *\nAllow: /", "details": "no explicit Disallow, but no explicit Allow either"},
      "current_condition": "no explicit Disallow, but no explicit Allow",
      "next_condition": "mainstream retrieval user-agents explicitly allowed",
      "improvement_hint": "在robots.txt中添加 User-agent: GPTBot / ClaudeBot / PerplexityBot 的 Allow: / 指令"
    }
  ],
  "sample_pages": ["https://example.com/", "https://example.com/about", "..."],
  "created_at": "2026-09-16T10:00:00",
  "completed_at": "2026-09-16T10:00:20"
}
```

#### 2.1.5 核心代码移植步骤（按文件逐个实现）

**步骤 1：创建 rubric.py（评分标准定义）**

从 geo-score 的 `SPEC` 和 `TIERS` 字典抽取，转为 Python 数据类 + JSON 配置。

```python
# backend/app/engines/site_auditor/rubric.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Tier:
    points: int
    condition: str
    condition_zh: str

@dataclass
class CheckDef:
    check_id: str
    pillar: str
    pillar_zh: str
    name: str
    name_zh: str
    points: int
    tiers: List[Tier]
    is_gate: bool = False
    needs_judgement: bool = False
    why: str = ""
    why_zh: str = ""

# 21项检查定义（从geo-score SPEC+TIERS抽取，补充中文）
RUBRIC_V1_1: List[CheckDef] = [
    CheckDef(
        check_id="g.robots", pillar="Reachable", pillar_zh="可被抓取",
        name="Retrieval crawlers allowed in robots.txt", name_zh="robots放行检索爬虫",
        points=5, is_gate=True,
        tiers=[
            Tier(0, "robots.txt carries a Disallow that applies to retrieval user-agents", "对检索类UA设了Disallow"),
            Tier(3, "no explicit Disallow, but no explicit Allow either", "没有适用于检索UA的Disallow，但也没有Allow指令"),
            Tier(5, "mainstream retrieval user-agents explicitly allowed", "检索UA被明确放行"),
        ],
        why="The one check where failing makes every other change pointless.",
        why_zh="唯一一条没做到后面全部白做的检查。",
    ),
    # ... 其余20项按同样格式定义
]

BANDS = [
    (83, "Leading", "领先"),
    (66, "Solid", "基础扎实"),
    (51, "Growing", "成长期"),
    (31, "Early", "起步期"),
    (0, "Not started", "未起步"),
]

GATE_CAP = 40
BONUS_CAP = 6
BONUS_CHECKS = [
    ("b.llms-full", "llms-full.txt", 2),
    ("b.ai-txt", "ai.txt", 2),
    ("b.geo-link", "GEO link tags", 1),
    ("b.speakable", "speakable markup", 1),
]
```

**步骤 2：创建 fetchers.py（HTTP 抓取层）**

从 geo-score 抽取 UA 定义、idna 处理、重定向处理（307/308）、gzip 解压，改用 httpx 异步实现。

```python
# backend/app/engines/site_auditor/fetchers.py
import httpx
import gzip
import re
import urllib.parse
from typing import List, Tuple, Optional

# 从geo-score直接复制的13个UA定义
RETRIEVAL_UAS: List[Tuple[str, str]] = [
    ("GPTBot", "GPTBot/1.2 (+https://openai.com/gptbot)"),
    ("OAI-SearchBot", "OAI-SearchBot/1.0 (+https://openai.com/searchbot)"),
    ("ChatGPT-User", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0"),
    ("ClaudeBot", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ClaudeBot/1.0"),
    ("Claude-SearchBot", "Mozilla/5.0 ... Claude-SearchBot/1.0"),
    ("PerplexityBot", "Mozilla/5.0 ... PerplexityBot/1.0"),
    ("Perplexity-User", "Mozilla/5.0 ... Perplexity-User/1.0"),
    ("Google-Extended", "Mozilla/5.0 (compatible; Google-Extended/1.0)"),
    ("Applebot", "Mozilla/5.0 (compatible; Applebot/0.1)"),
    ("Bingbot", "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
]
CN_UAS: List[Tuple[str, str]] = [
    ("Baiduspider", "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)"),
    ("Sogou", "Sogou web spider/4.0"),
    ("PetalBot", "Mozilla/5.0 (compatible; PetalBot;+https://webmaster.petalsearch.com/site/petalbot)"),
]
UA_BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
ALL_UAS = RETRIEVAL_UAS + CN_UAS

async def fetch_url(client: httpx.AsyncClient, url: str, ua: str = UA_BROWSER,
                    timeout: int = 15) -> dict:
    """抓取单个URL，返回 {url, status, body, headers, elapsed, err}"""
    # 复用geo-score的idna()处理中文域名
    # 复用geo-score的gzip解压逻辑
    # 注意：httpx默认跟随重定向，包括307/308，无需自定义handler
    ...

async def fetch_concurrent(urls: List[str], ua: str = UA_BROWSER,
                            max_workers: int = 8) -> List[dict]:
    """并发抓取多个URL（对应geo-score的pmap）"""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        tasks = [fetch_url(client, url, ua) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

async def fetch_all_uas(url: str) -> List[dict]:
    """用13个UA并发抓取同一个URL，用于g.reachable检查"""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        tasks = [fetch_url(client, url, ua_string) for _, ua_string in ALL_UAS]
        return await asyncio.gather(*tasks, return_exceptions=True)

def parse_robots_txt(content: str) -> dict:
    """解析robots.txt，返回每个UA的allow/disallow规则（从geo-score抽取逻辑）"""
    ...

def discover_sitemap_url(robots_content: str, root: str) -> Optional[str]:
    """从robots.txt中查找Sitemap声明，否则尝试默认路径 /sitemap.xml"""
    ...
```

**步骤 3：创建 parsers.py（HTML 解析层）**

从 geo-score 抽取所有纯解析函数：visible_text, main_html, jsonld（含 @graph 引用解析 resolve_refs）, headings, paragraphs, wc, is_cjk。

```python
# backend/app/engines/site_auditor/parsers.py
import re
import json
import html
from typing import List, Set, Dict, Any

TAGSTRIP = re.compile(r"<(script|style|noscript|template|svg)\b.*?</\1>", re.S | re.I)

def visible_text(h: str) -> str:
    """从HTML提取可见文本（直接从geo-score复制）"""
    h = TAGSTRIP.sub(" ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()

def main_html(h: str) -> str:
    """提取<main>或<article>内容，没有则返回全文（从geo-score复制）"""
    m = re.search(r"<main\b[^>]*>(.*?)</main>", h, re.S | re.I) or \
        re.search(r'<article\b[^>]*>(.*?)</article>', h, re.S | re.I)
    return m.group(1) if m else h

def extract_jsonld(h: str) -> List[Dict[str, Any]]:
    """提取所有JSON-LD，解析@graph引用（从geo-score的jsonld+resolve_refs抽取）"""
    out = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', h, re.S | re.I):
        raw = m.group(1).strip()
        try:
            d = json.loads(raw)
        except Exception:
            try:
                d = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue
        out.extend(d if isinstance(d, list) else [d])
    # 扁平化@graph
    flat = []
    def walk(o):
        if isinstance(o, dict):
            if "@graph" in o and isinstance(o["@graph"], list):
                for g in o["@graph"]: walk(g)
            else: flat.append(o)
        elif isinstance(o, list):
            for x in o: walk(x)
    for o in out: walk(o)
    return _resolve_refs(flat)

def _resolve_refs(objs: List[Dict]) -> List[Dict]:
    """解析{"@id": "..."}引用（从geo-score的resolve_refs复制）"""
    by_id = {o["@id"]: o for o in objs if isinstance(o.get("@id"), str) and len(o) > 1}
    if not by_id: return objs
    def deref(v, depth=0):
        if depth > 3: return v
        if isinstance(v, dict):
            if set(v) == {"@id"} and v["@id"] in by_id:
                return deref({k: x for k, x in by_id[v["@id"]].items() if k != "@id"}, depth + 1)
            return {k: deref(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list): return [deref(x, depth + 1) for x in v]
        return v
    return [deref(o) for o in objs]

def get_jsonld_types(objs: List[Dict]) -> Set[str]:
    """获取所有JSON-LD的@type集合"""
    t = []
    for o in objs:
        v = o.get("@type")
        t.extend(v if isinstance(v, list) else [v] if v else [])
    return set(t)

def extract_headings(h: str) -> List[str]:
    """提取h1-h4标题文本（从geo-score的headings复制）"""
    out = [visible_text(m.group(1))[:200]
           for m in re.finditer(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]>", h, re.S | re.I)]
    t = re.search(r"<title\b[^>]*>(.*?)</title>", h, re.S | re.I)
    if t: out.append(visible_text(t.group(1))[:200])
    return [x for x in out if x]

def extract_paragraphs(h: str) -> List[str]:
    """提取main区域的p标签文本（从geo-score的paragraphs复制）"""
    return [p for p in (visible_text(m.group(1)) for m in
            re.finditer(r"<p\b[^>]*>(.*?)</p>", main_html(h), re.S | re.I)) if p]

def wc(s: str) -> int:
    """字数统计：中文>20字按字符数，否则按空格分词数（从geo-score复制）"""
    cjk = len(re.findall(r"[一-鿿]", s))
    return cjk if cjk > 20 else len(s.split())

def is_cjk(s: str) -> bool:
    """判断页面是否面向中文用户（从geo-score复制）"""
    if "<" in s and ">" in s: s = visible_text(s)
    return len(re.findall(r"[一-鿿]", s)) > max(30, len(s) * 0.08)

# 标题意图匹配正则（从geo-score直接复制）
QP_INTENT = re.compile(
    r"\b(how|what|why|when|where|which|who)\b|[?？]"
    r"|^(get|getting|set|setting|add|adding|build|building|create|creating|use|using|"
    r"install|installing|deploy|deploying|configure|connect|accept|send|manage|migrate|"
    r"write|writing|run|running|test|testing|choose|handle|customi[sz]e)\b"
    r"|怎么|如何|什么|为什么|是否|多少|入门|教程|指南", re.I)
NAV_LABEL = re.compile(r"^\s*(\w+\s*[|｜·]\s*\w+|[A-Za-z0-9_]{1,12}|[\u4e00-\u9fff]{1,3})\s*$")
```

**步骤 4：创建 checkers/ 下的 5 个检查实现文件**

每个检查函数接收 `PageData`（包含 url, html, status, jsonld 等）和上下文，返回 `(scored_points, evidence_dict)`。

以 `reachable.py` 为例（3 项门控检查，最关键）：

```python
# backend/app/engines/site_auditor/checkers/reachable.py
import re
from typing import Dict, Any, List, Tuple
from ..fetchers import RETRIEVAL_UAS, CN_UAS, ALL_UAS
from ..parsers import visible_text, main_html

async def check_robots(robots_content: str, root: str) -> Tuple[int, Dict]:
    """g.robots: 检查robots.txt是否允许检索爬虫（5分，门控）"""
    if not robots_content:
        return 3, {"details": "no robots.txt found — default allow", "snippet": ""}
    # 从geo-score抽取的robots解析逻辑
    # 0分：有适用于检索UA的Disallow
    # 3分：没有明确Disallow也没有明确Allow
    # 5分：检索UA被明确Allow
    ...

async def check_reachable(ua_results: List[Dict], browser_result: Dict) -> Tuple[int, Dict]:
    """g.reachable: 13个UA实测可达性（5分，门控）"""
    # 从geo-score抽取的逻辑：
    # 0分：多数UA被拦（非200或正文与浏览器不一致）
    # 3分：部分UA被拦，或正文与浏览器所见不一致
    # 5分：所有10个检索UA均200且正文一致
    # 注意：正文一致性按去空白后的文本比对，CSRF token/nonce/时间戳差异不算不一致
    ...

async def check_ssr(pages: List[Dict]) -> Tuple[int, Dict]:
    """g.ssr: 正文服务端可见（5分，门控）"""
    # 从geo-score抽取的逻辑：
    # 检查每个抽样页的HTML响应中是否有正文文本（visible_text长度>阈值）
    # 0分：所有页面正文都只在JS渲染后存在（HTML中无正文）
    # 3分：部分页面可见
    # 5分：所有抽样页正文均在HTML响应中
    ...
```

其余 4 个文件（understandable.py / content_citability.py / brand_credibility.py / answer_fit.py）按同样模式实现，每个检查函数对应 geo-score 中的一段检测逻辑。

**步骤 5：创建 scorer.py（评分聚合）**

从 geo-score 抽取 `score()` 函数的核心逻辑：门控封顶、归一化、档位判定、最大缺口排序。

```python
# backend/app/engines/site_auditor/scorer.py
from typing import List, Dict, Tuple
from .rubric import RUBRIC_V1_1, BANDS, GATE_CAP, BONUS_CAP
from .models import CheckResult

def aggregate_scores(check_results: List[CheckResult], bonus: Dict[str, int]) -> Dict:
    """聚合21项检查结果，计算总分、档位、门控状态、最大缺口"""
    got = 0
    den = 0
    gate_zero = False
    rows = []

    for cr in check_results:
        if cr.scored_points is None:
            rows.append((cr, None))
            continue
        got += cr.scored_points
        den += cr.max_points
        if cr.is_gate and cr.scored_points == 0:
            gate_zero = True
        rows.append((cr, cr.scored_points))

    b = min(sum(bonus.values()), BONUS_CAP)
    total = got + b
    norm = round(100 * total / den) if den else 0
    if gate_zero:
        norm = min(norm, GATE_CAP)

    band = next(name for threshold, name, _ in BANDS if norm >= threshold)

    # 计算距下一档差几分
    next_bands = [(t, n) for t, n, _ in BANDS if t > norm]
    points_to_next = (min(next_bands)[0] - norm) if next_bands else 0
    next_band_name = min(next_bands, key=lambda x: x[0])[1] if next_bands else None

    # 最大缺口排序（按可回收分数）
    gaps = []
    for cr in check_results:
        if cr.scored_points is not None and cr.scored_points < cr.max_points:
            gaps.append({
                "check_id": cr.check_id,
                "name": cr.name_zh,
                "points_recoverable": cr.max_points - cr.scored_points,
                "improvement_hint": cr.improvement_hint,
            })
    gaps.sort(key=lambda x: x["points_recoverable"], reverse=True)

    return {
        "raw_score": total,
        "normalized_score": norm,
        "denominator": den,
        "bonus": b,
        "band": band,
        "gate_capped": gate_zero,
        "points_to_next": points_to_next,
        "next_band": next_band_name,
        "top_gaps": gaps[:3],
        "all_gaps": gaps,
    }
```

**步骤 6：创建 auditor.py（主入口）**

编排整个扫描流程：URL 规范化 → robots.txt 抓取 → sitemap 发现 → 页面采样（8页）→ 并发抓取 → 21 项检查 → 评分聚合 → 结果持久化。

```python
# backend/app/engines/site_auditor/auditor.py
import asyncio
from typing import List, Dict, Optional
from .fetchers import fetch_url, fetch_concurrent, fetch_all_uas, parse_robots_txt, discover_sitemap_url
from .parsers import extract_jsonld, extract_headings, extract_paragraphs, is_cjk
from .checkers import reachable, understandable, content_citability, brand_credibility, answer_fit
from .scorer import aggregate_scores
from .models import ScanResult, CheckResult, PageData
from .rubric import RUBRIC_V1_1

class SiteAuditor:
    def __init__(self, db_session=None):
        self.db = db_session

    async def scan(self, url: str, scope: str = "") -> ScanResult:
        """执行完整扫描，返回ScanResult"""
        # 1. URL规范化：提取origin和scope路径（从geo-score的scope_of抽取）
        origin, path_scope = self._normalize_url(url, scope)

        # 2. 抓取robots.txt（origin/robots.txt）
        robots_result = await fetch_url(origin + "/robots.txt")
        robots_content = robots_result.get("body", "") if robots_result.get("status") == 200 else ""

        # 3. 发现sitemap
        sitemap_url = discover_sitemap_url(robots_content, origin)

        # 4. 页面采样：从首页+sitemap中选8个真实内容页（从geo-score的discover抽取）
        sample_pages = await self._discover_pages(origin, path_scope, sitemap_url, want=8)

        # 5. 并发抓取8个抽样页（浏览器UA）
        page_results = await fetch_concurrent(sample_pages)
        pages_data = [self._build_page_data(url, r) for url, r in zip(sample_pages, page_results)]

        # 6. g.reachable：13个UA并发抓取首页
        ua_results = await fetch_all_uas(origin + "/")
        browser_result = await fetch_url(origin + "/")

        # 7. 运行21项检查（按支柱分组）
        check_results = []
        # Reachable (3项门控)
        check_results.append(await reachable.check_robots(robots_content, origin))
        check_results.append(await reachable.check_reachable(ua_results, browser_result))
        check_results.append(await reachable.check_ssr(pages_data))
        # Understandable (5项)
        check_results.extend(await understandable.run_all(pages_data, robots_content, sitemap_url, origin))
        # Content Citability (5项)
        check_results.extend(await content_citability.run_all(pages_data))
        # Brand Credibility (5项)
        check_results.extend(await brand_credibility.run_all(pages_data, origin))
        # Answer Fit (3项)
        check_results.extend(await answer_fit.run_all(pages_data, origin))

        # 8. 评分聚合
        score_result = aggregate_scores(check_results, bonus={})

        # 9. 构建ScanResult
        return ScanResult(
            url=url, landed_url=browser_result.get("url", url),
            root_origin=origin, **score_result,
            check_results=check_results, sample_pages=sample_pages,
            pages_data=pages_data, rubric_version="v1.1",
        )

    def _normalize_url(self, url: str, scope: str) -> tuple:
        """URL规范化：提取origin和scope（从geo-score的scope_of抽取）"""
        ...

    async def _discover_pages(self, origin: str, scope: str, sitemap_url: str, want: int = 8) -> List[str]:
        """采样8个真实内容页（从geo-score的discover抽取）"""
        ...

    def _build_page_data(self, url: str, fetch_result: Dict) -> PageData:
        """从抓取结果构建PageData（解析HTML、提取JSON-LD、标题、段落）"""
        ...
```

**步骤 7：创建 API 层（api/site_audit.py）**

```python
# backend/app/api/site_audit.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.engines.site_auditor import SiteAuditor
from app.models.site_audit import SiteAuditRecord, SiteAuditCheck
from app.schemas.site_audit import ScanRequest, ScanResponse, BriefResponse
import asyncio

router = APIRouter(prefix="/api/site-audit", tags=["site-audit"])

@router.post("/scan", response_model=dict)
async def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发异步扫描"""
    # 1. 创建pending状态的记录
    record = SiteAuditRecord(url=req.url, status="pending", rubric_version="v1.1")
    db.add(record)
    db.commit()
    # 2. 后台执行扫描
    background_tasks.add_task(_run_scan, record.id, req.url, req.scope)
    return {"audit_id": record.id, "status": "running"}

async def _run_scan(audit_id: int, url: str, scope: str):
    """后台扫描任务"""
    db = next(get_db())  # 获取新的db session
    try:
        record = db.query(SiteAuditRecord).get(audit_id)
        record.status = "running"
        db.commit()

        auditor = SiteAuditor(db_session=db)
        result = await auditor.scan(url, scope)

        # 持久化结果到site_audit_check表
        for cr in result.check_results:
            db.add(SiteAuditCheck(audit_id=audit_id, **cr.to_dict()))

        record.score = result.normalized_score
        record.raw_score = result.raw_score
        record.band = result.band
        record.gate_capped = result.gate_capped
        record.status = "completed"
        record.completed_at = datetime.now()
        db.commit()
    except Exception as e:
        record.status = "failed"
        record.error_message = str(e)[:500]
        db.commit()

@router.get("/{audit_id}", response_model=ScanResponse)
async def get_scan_result(audit_id: int, db: Session = Depends(get_db)):
    """获取完整扫描结果"""
    record = db.query(SiteAuditRecord).get(audit_id)
    if not record:
        raise HTTPException(404, "Scan not found")
    checks = db.query(SiteAuditCheck).filter(SiteAuditCheck.audit_id == audit_id).all()
    return _build_response(record, checks)

@router.get("/{audit_id}/brief", response_model=BriefResponse)
async def get_scan_brief(audit_id: int, db: Session = Depends(get_db)):
    """获取首屏摘要（分数+档位+最大3个缺口）"""
    ...
```

**步骤 8：创建数据模型和 Pydantic schema**

按 2.1.3 的 SQL 设计创建 SQLAlchemy 模型，以及对应的 Pydantic 请求/响应模型。

**步骤 9：前端页面实现**

页面布局参考 geo-score 的输出格式：
- 顶部：评分仪表盘（0-100 环形进度）+ 档位标签 + 距下一档差几分
- 门控告警条（如果 gate_capped=true，红色置顶）
- 5 支柱分解（横向条形图，每柱显示 scored/max）
- 最大 3 个缺口卡片（按可回收分数排序，每个含改进建议）
- 21 项检查完整列表（可折叠，每项显示档位、证据、上一档要求）
- 抽样页面列表
- 历史趋势图（如果有多次扫描）

#### 2.1.6 验收标准

| 验收项 | 标准 | 验证方法 |
|--------|------|---------|
| 功能完整性 | 21 项检查全部实现，5 支柱分值正确 | 用 geo-score 的 5 个手工审计范例（examples/audits/v1.1/）对比，分数偏差 ≤5 |
| 门控机制 | robots 封禁/不可达/纯SPA 网站总分 ≤40 | 构造测试用例：amazon.com（robots封禁GPTBot）应 ≤40 |
| 并发性能 | 8 页采样 + 13 UA 探测，总耗时 ≤30 秒 | 实测 10 个网站取平均 |
| 数据持久化 | 扫描结果完整存储到 3 张表，可查询历史 | 扫描后查数据库验证 |
| API 完整性 | 7 个 API 端点全部可用，返回符合 schema | 用 curl/Postman 测试每个端点 |
| 前端可用性 | 站点体检页面可正常触发扫描、查看结果、展开检查项 | 手动走一遍完整流程 |
| 中文适配 | 中文网站的 CJK 检测、字数统计、标题意图匹配正常 | 用 3 个中文网站测试 |
| 错误处理 | 网站不可达/超时/非HTML 时不崩溃，返回友好错误 | 构造无效 URL 测试 |
| 许可证合规 | 所有从 geo-score 抽取的代码文件头部标注来源和 MIT 许可证 | 代码审查 |

---

### 模块二：内容 GEO 友好性 Linter（P0，5-7 人天）

#### 2.2.1 模块定位

对内容资产库中的每篇文章运行 GEO 内容质量检测，对应 geo-score 的 **Content Citability（35分）+ Answer Fit（10分）** 两个支柱，共 8 项检查，满分 45 分。

**与模块一的关系**：模块一检测的是"网站整体"，模块二检测的是"单篇内容"。模块二复用模块一的 parsers.py 和 checkers/content_citability.py + answer_fit.py 的检测逻辑，但输入是文章正文而非网页 HTML。

#### 2.2.2 检测项清单

| 检查ID | 名称 | 分值 | 检测逻辑（针对文章正文） |
|--------|------|------|------------------------|
| c.answer-passage | 自足答案段 | 9 | 文章首段是否为 50-200 字（中文）的独立段落，含标点，能独立成立不依赖上下文 |
| c.question-intent | 标题匹配提问意图 | 7 | 文章标题和小标题是否像用户提问（怎么/如何/什么/为什么 + 任务句/说明句），排除纯关键词串 |
| c.freshness | 时间信号 | 6 | 文章是否有发布日期，且有更新日期（如果内容有时效性） |
| c.sourced-stats | 数据带出处 | 7 | 文中的统计数字/结论是否标注来源，且来源可点击可核实 |
| c.named-author | 可验证作者署名 | 6 | 是否有真实作者署名（非"编辑部"），且作者有简介/身份页链接 |
| c.answer-shape | 内容结构适合提取 | 4 | 是否有子标题、列表、表格，段落长度适中（非大段长文） |
| c.question-coverage | 覆盖用户常问问题 | 4 | 需 LLM 辅助判定：文章是否覆盖了该主题下用户最常问的 3-5 个问题（退出分母或LLM辅助） |
| c.speakable | speakable 标记 | 1（bonus） | 是否有 speakable JSON-LD 标记（适合语音助手读取） |

**注意**：c.question-coverage 需要 LLM 联网或知识库辅助，默认退出分母；c.speakable 是 bonus 项。

#### 2.2.3 集成方式

**触发时机**：
1. 内容录入时自动检测（后台任务）
2. 内容编辑保存时重新检测
3. 手动批量检测（内容库页面"批量GEO检测"按钮）

**数据存储**：
- 不新建表，在现有 `geo_content` 表增加字段：
  - `geo_score` INTEGER DEFAULT NULL（内容GEO质量分 0-45）
  - `geo_check_results` TEXT DEFAULT '{}'（8项检查结果JSON）
  - `geo_last_checked_at` DATETIME
- 检测结果也可写入新表 `content_geo_check`（一对多，保留历史），推荐新建表以便趋势分析。

#### 2.2.4 实施步骤

**步骤 1：创建内容 Linter 引擎**

```python
# backend/app/engines/content_linter.py
from typing import Dict, List, Tuple
from .site_auditor.parsers import (
    visible_text, extract_headings, extract_paragraphs, wc, is_cjk,
    QP_INTENT, NAV_LABEL
)
from .site_auditor.rubric import Tier

class ContentLinter:
    """内容GEO质量检测引擎"""

    def lint(self, title: str, body_html: str, author: str = "",
             published_at: str = "", updated_at: str = "",
             source_urls: List[str] = None) -> Dict:
        """对单篇内容运行8项检查"""
        # 将文章HTML转为可检测的格式
        text = visible_text(body_html)
        headings = [title] + extract_headings(body_html)
        paragraphs = extract_paragraphs(body_html)
        cjk = is_cjk(text)

        results = {}
        # c.answer-passage (9分)
        results["c.answer-passage"] = self._check_answer_passage(paragraphs, cjk)
        # c.question-intent (7分)
        results["c.question-intent"] = self._check_question_intent(headings)
        # c.freshness (6分)
        results["c.freshness"] = self._check_freshness(published_at, updated_at, body_html)
        # c.sourced-stats (7分)
        results["c.sourced-stats"] = self._check_sourced_stats(text, body_html)
        # c.named-author (6分)
        results["c.named-author"] = self._check_named_author(author, body_html)
        # c.answer-shape (4分)
        results["c.answer-shape"] = self._check_answer_shape(body_html, paragraphs)
        # c.question-coverage (4分，默认退出分母)
        results["c.question-coverage"] = (None, {"details": "需要LLM辅助判定，退出分母"})

        # 聚合评分
        scored = sum(r[0] for r in results.values() if r[0] is not None)
        max_den = sum(9+7+6+7+6+4)  # 39分（排除question-coverage的4分和bonus）
        return {
            "score": scored,
            "denominator": max_den,
            "percentage": round(scored / max_den * 100, 1) if max_den else 0,
            "checks": results,
            "top_gaps": self._sort_gaps(results),
        }

    def _check_answer_passage(self, paragraphs: List[str], cjk: bool) -> Tuple[int, Dict]:
        """自足答案段检测（从geo-score p2.answer-passages抽取）"""
        lo, hi = (50, 200) if cjk else (25, 120)
        passed = 0
        example = ""
        for p in paragraphs[:6]:
            if lo <= wc(p) <= hi and any(c in p for c in ".。!?！？"):
                passed += 1
                if not example:
                    example = p[:90]
                break
        # 单篇文章：有=9分，无=0分（网站是按8页抽样比例，单篇简化为是/否）
        if passed:
            return 9, {"details": f"首段为{wc(paragraphs[0])}字的自足答案段", "snippet": example}
        else:
            return 0, {"details": f"首段{wc(paragraphs[0]) if paragraphs else 0}字，不在{lo}-{hi}字范围内或无标点", "snippet": paragraphs[0][:90] if paragraphs else ""}

    def _check_question_intent(self, headings: List[str]) -> Tuple[int, Dict]:
        """标题意图匹配（从geo-score p2.question-intent抽取）"""
        matched = 0
        total = 0
        for h in headings:
            if 3 <= len(h) <= 120:
                total += 1
                if QP_INTENT.search(h) and not NAV_LABEL.match(h):
                    matched += 1
        if total == 0:
            return 0, {"details": "无有效标题"}
        ratio = matched / total
        if ratio >= 0.75: return 7, {"details": f"{matched}/{total}个标题匹配提问意图"}
        if ratio >= 0.5: return 5, {"details": f"{matched}/{total}个标题匹配（约一半）"}
        if matched > 0: return 3, {"details": f"{matched}/{total}个标题匹配（少数）"}
        return 0, {"details": "标题多为关键词串或品牌标签", "examples": headings[:3]}

    # ... 其余检查方法类似实现
```

**步骤 2：集成到内容 API**

在 `api/content.py` 的创建和更新接口中，添加后台 Linter 任务：

```python
# 在 content.py 的 create_content 和 update_content 中
from app.engines.content_linter import ContentLinter
from app.worker import run_in_background

@router.post("/contents")
async def create_content(req: ContentCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    content = GeoContent(**req.dict())
    db.add(content)
    db.commit()
    db.refresh(content)
    # 后台触发GEO质量检测
    background_tasks.add_task(_lint_content, content.id)
    return content

async def _lint_content(content_id: int):
    db = next(get_db())
    content = db.query(GeoContent).get(content_id)
    linter = ContentLinter()
    result = linter.lint(
        title=content.title,
        body_html=content.body_html or content.body,
        author=content.author or "",
        published_at=content.published_at or "",
        updated_at=content.updated_at or "",
    )
    content.geo_score = result["score"]
    content.geo_check_results = json.dumps(result["checks"], ensure_ascii=False)
    content.geo_last_checked_at = datetime.now()
    db.commit()
```

**步骤 3：前端展示**

- 内容库列表页增加"GEO质量分"列（0-45 分，颜色编码：≥36 绿/≥27 黄/<27 红）
- 内容详情页增加"GEO质量诊断"标签页：
  - 总分仪表盘
  - 8 项检查逐项卡片（通过/未通过/未判定）
  - 每项的证据片段和改进建议
  - 最大 3 个缺口置顶
- 批量操作："批量GEO检测"按钮

#### 2.2.5 验收标准

| 验收项 | 标准 |
|--------|------|
| 检测准确性 | 用 10 篇已知质量的文章测试，人工评分与 Linter 评分偏差 ≤5 分 |
| 集成完整性 | 内容创建/编辑后自动触发检测，分数正确存储 |
| 改进建议 | 每个失分项都有具体的、可操作的改进建议（非"建议优化"这种空话） |
| 批量检测 | 支持对全库/筛选结果批量检测，有进度反馈 |
| 性能 | 单篇检测 <1 秒（纯规则，无 LLM 调用） |

---

### 模块三：采集引擎优化（P0，4-5 人天）

#### 2.3.1 优化一：门控预检机制

**问题**：当前采集引擎对所有问题一视同仁地调用 AI 平台 API，即使品牌官网被 AI 爬虫封禁（门控为 0），也在浪费 API 调用。

**方案**：在采集前增加"网站可达性预检"，如果门控为 0，标记该问题为"基础设施阻断"并跳过 API 调用。

```python
# backend/app/engines/collector.py 修改

class CollectorEngine:
    def __init__(self, db: Session):
        self.db = db
        self.parser = AnswerParser(settings.brand_aliases)
        self._gate_cache = {}  # 门控状态缓存：{root_origin: (gate_passed, timestamp)}

    async def _precheck_gate(self, brand_url: str) -> dict:
        """采集前预检：检查品牌官网的3项门控状态"""
        import urllib.parse
        origin = "{uri.scheme}://{uri.netloc}".format(uri=urllib.parse.urlsplit(brand_url))

        # 缓存1小时，避免重复检测
        if origin in self._gate_cache:
            cached_time, result = self._gate_cache[origin]
            if (datetime.now() - cached_time).total_seconds() < 3600:
                return result

        # 快速门控检测（只跑3项门控，不跑完整21项）
        from app.engines.site_auditor.fetchers import fetch_url, fetch_all_uas
        from app.engines.site_auditor.checkers.reachable import check_robots, check_reachable, check_ssr

        robots_result = await fetch_url(origin + "/robots.txt")
        robots_content = robots_result.get("body", "") if robots_result.get("status") == 200 else ""
        ua_results = await fetch_all_uas(origin + "/")
        browser_result = await fetch_url(origin + "/")

        robots_score, _ = await check_robots(robots_content, origin)
        reachable_score, _ = await check_reachable(ua_results, browser_result)
        # ssr快速检测：只看首页HTML是否有正文
        ssr_passed = len(visible_text(browser_result.get("body", ""))) > 100

        gate_zero = (robots_score == 0) or (reachable_score == 0) or (not ssr_passed)
        result = {
            "gate_passed": not gate_zero,
            "robots_score": robots_score,
            "reachable_score": reachable_score,
            "ssr_passed": ssr_passed,
            "blocked_reason": self._get_block_reason(robots_score, reachable_score, ssr_passed),
        }
        self._gate_cache[origin] = (datetime.now(), result)
        return result

    async def collect_one_question(self, question: Question, detect_round: int = 1) -> List[MonitorRecord]:
        # 新增：门控预检
        if question.brand_url:
            gate = await self._precheck_gate(question.brand_url)
            if not gate["gate_passed"]:
                # 门控未通过，跳过API调用，记录"基础设施阻断"
                return self._create_blocked_records(question, detect_round, gate)

        # 原有采集逻辑...
```

**新增 MonitorRecord 字段**：
- `collect_status` TEXT DEFAULT 'success'（success/failed/blocked/timeout）
- `block_reason` TEXT（门控阻断原因）

**仪表盘影响**：
- 门控阻断的记录不参与提及率统计（退出分母）
- 仪表盘顶部显示"基础设施阻断问题数"告警

#### 2.3.2 优化二：平台间并发采集

**问题**：当前串行采集，10 个问题 × 3 个平台 = 至少 60 秒+API 响应时间。

**方案**：平台间并发（ThreadPoolExecutor 或 asyncio.gather），问题间保留延迟避免限流。

```python
# collector.py 修改 collect_one_question

async def collect_one_question(self, question: Question, detect_round: int = 1) -> List[MonitorRecord]:
    platforms = adapter_factory.get_enabled_platforms()
    # 平台间并发采集
    tasks = [self._collect_platform(question, platform_code, detect_round) for platform_code in platforms]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    records = [r for r in results if isinstance(r, MonitorRecord)]
    # 批量入库...
```

注意：需要将 `query_single_platform` 改为异步，或用 `asyncio.to_thread` 包装同步调用。

#### 2.3.3 优化三：证据结构化

**问题**：当前 `mention_evidence` 只是提及位置前后 100 字符的纯文本，没有结构化标注。

**方案**：将证据字段改为 JSON 结构，包含类型、片段、位置、置信度、判定依据。

```python
# MonitorRecord 新增/修改字段
evidence_json = Column(Text, default='{}')  # 结构化证据
# 格式：
{
  "mention": {
    "type": "brand_name",  # brand_name / alias / hospital_doctor
    "matched_text": "深圳XX医院",
    "position": 1234,
    "snippet": "...深圳XX医院是一家三甲医院...",
    "confidence": 0.95
  },
  "recommendation": {
    "is_recommended": true,
    "evidence": "推荐深圳XX医院进行手术治疗",
    "position": 1250,
    "source": "llm_analyzer"  # rule / llm
  },
  "citation": {
    "is_cited": true,
    "citation_urls": ["https://example.com/article/123"],
    "citation_pattern": "根据XX医院的研究",
    "confidence": 0.8
  },
  "rank": {
    "value": 2,
    "method": "ordered_list",  # ordered_list / chinese_numeral / paragraph_count
    "evidence": "2. 深圳XX医院"
  }
}
```

#### 2.3.4 优化四：失败状态区分

**问题**：采集失败时 `rank=0, mentioned=False`，与"真的未提及"无法区分。

**方案**：新增 `collect_status` 字段，失败时标记为 failed/timeout/blocked，不参与提及率统计。

```sql
ALTER TABLE geo_monitor_record ADD COLUMN collect_status TEXT DEFAULT 'success';
ALTER TABLE geo_monitor_record ADD COLUMN error_detail TEXT;
```

仪表盘统计时：`WHERE collect_status = 'success'`，并单独展示"采集失败率"指标。

#### 2.3.5 验收标准

| 验收项 | 标准 |
|--------|------|
| 门控预检 | 被 robots 封禁的网站，采集时自动跳过并标记 blocked，不调用 API |
| 并发性能 | 3 平台并发采集，单问题耗时从 ~15 秒降到 ~5 秒 |
| 证据结构化 | 每条记录的 evidence_json 包含 mention/recommendation/citation/rank 四类证据 |
| 失败区分 | 采集失败的记录 collect_status != 'success'，不参与提及率统计 |
| 缓存有效 | 门控状态缓存 1 小时，不重复检测同一网站 |

---

## 第三部分：P1 模块详细实施方案

### 模块四：仪表盘双维度升级（P1，5-6 人天）

#### 2.4.1 设计目标

将仪表盘从"单一输出侧统计"升级为"输入侧就绪度 + 输出侧表现"双维度展示，让用户一眼看到：
1. 我的基础是否扎实（就绪度评分）
2. 我的表现如何（提及率/排名）
3. 基础和表现之间是否匹配（就绪度高但表现差 → 内容竞争问题；就绪度低且表现差 → 基础设施问题）

#### 2.4.2 页面布局设计

```
┌──────────────────────────────────────────────────────────────────┐
│  [门控告警条] 仅当存在门控为0的网站时显示（红色置顶）              │
│  ⚠ 检测到2个品牌官网存在基础设施阻断（AI爬虫无法获取内容）  [查看] │
├──────────────────────────────────────────────────────────────────┤
│  第一行：核心指标卡片（6个）                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  │ GEO就绪度 │ │ 平均提及率│ │ Top1推荐率│ │ 平均排名  │ │ 基础设施 │ │ 内容质量  │
│  │   71/100  │ │   45.2%  │ │   12.3%  │ │   2.8    │ │  3/3通过 │ │  32/45   │
│  │  Solid    │ │  ↑3.2%   │ │  ↑1.1%   │ │  ↓0.3    │ │          │ │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
├──────────────────────────────────────────────────────────────────┤
│  第二行：双维度对比                                                │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐
│  │  输入侧：5支柱就绪度雷达图    │ │  输出侧：7天趋势折线图       │
│  │  (Reachable/Understandable/  │ │  (提及率/Top1率/平均排名)    │
│  │   Content/Brand/AnswerFit)   │ │                              │
│  └─────────────────────────────┘ └─────────────────────────────┘
├──────────────────────────────────────────────────────────────────┤
│  第三行：诊断与优化                                                │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐
│  │  最大3个缺口（按可回收分排序）│ │  平台表现对比（柱状图）       │
│  │  1. 标题匹配提问意图 +4分    │ │  DeepSeek 52% / GLM 48% ... │
│  │  2. 可验证作者署名 +3分      │ │                              │
│  │  3. 时间信号 +3分            │ │                              │
│  │  [一键生成优化方案]           │ │                              │
│  └─────────────────────────────┘ └─────────────────────────────┘
├──────────────────────────────────────────────────────────────────┤
│  第四行：问题榜单                                                  │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐
│  │  表现最好的5个问题            │ │  表现最差的5个问题            │
│  └─────────────────────────────┘ └─────────────────────────────┘
└──────────────────────────────────────────────────────────────────┘
```

#### 2.4.3 数据接口设计

新增/修改以下 API：

| 方法 | 路径 | 功能 | 说明 |
|------|------|------|------|
| GET | `/api/dashboard/overview` | 双维度总览 | 合并现有 stats + 最新 site_audit 摘要 + 内容库平均质量分 |
| GET | `/api/dashboard/pillars` | 5支柱就绪度 | 返回最新扫描的5支柱得分，用于雷达图 |
| GET | `/api/dashboard/gate-alerts` | 门控告警列表 | 返回所有门控为0的品牌官网和问题 |
| GET | `/api/dashboard/top-gaps` | 最大缺口 | 跨所有扫描结果聚合，返回最常见的失分项 |

`overview` 响应结构：

```json
{
  "readiness": {
    "score": 71,
    "band": "Solid",
    "points_to_next": 12,
    "next_band": "Leading",
    "gate_capped": false,
    "last_audit_at": "2026-09-15T10:00:00",
    "pillars": {
      "Reachable": {"scored": 11, "max": 15},
      "Understandable": {"scored": 15, "max": 22},
      "Content Citability": {"scored": 25, "max": 35},
      "Brand Credibility": {"scored": 8, "max": 10},
      "Answer Fit": {"scored": 2, "max": 4}
    }
  },
  "performance": {
    "overall_mention_rate": 45.2,
    "overall_top1_rate": 12.3,
    "avg_rank": 2.8,
    "trend_7days": [...],
    "platform_stats": [...]
  },
  "content_quality": {
    "avg_score": 32,
    "max_score": 45,
    "total_contents": 156,
    "high_quality_count": 45,
    "low_quality_count": 32
  },
  "gate_alerts": {
    "total_blocked": 2,
    "blocked_questions": 5,
    "details": [{"url": "...", "reason": "robots封禁GPTBot", "question_count": 3}]
  },
  "top_gaps": [
    {"check_id": "p2.question-intent", "name": "标题匹配提问意图", "points_recoverable": 4, "occurrences": 12},
    {"check_id": "p2.named-author", "name": "可验证作者署名", "points_recoverable": 3, "occurrences": 8}
  ]
}
```

#### 2.4.4 实施步骤

1. **后端**：修改 `dashboard_service.py`，增加 `get_readiness_summary()`、`get_gate_alerts()`、`get_top_gaps()` 方法，合并到 `get_stats()` 返回
2. **后端**：新增 `api/dashboard.py` 的 `/pillars`、`/gate-alerts`、`/top-gaps` 端点
3. **前端**：重写 `pages/Dashboard.tsx`，按上述布局重组
4. **前端**：新增 `components/ScoreGauge.tsx`（环形评分仪表盘）、`components/PillarRadar.tsx`（5支柱雷达图）、`components/GateAlertBanner.tsx`（门控告警条）、`components/TopGapsPanel.tsx`（最大缺口面板）
5. **前端**：ECharts 雷达图配置（5维度，0-100归一化）

#### 2.4.5 验收标准

| 验收项 | 标准 |
|--------|------|
| 双维度展示 | 仪表盘同时展示就绪度评分和提及率/排名，二者并列 |
| 门控告警 | 存在门控为0的网站时，顶部红色告警条显示，点击可查看详情 |
| 5支柱雷达 | 雷达图正确显示5支柱得分，鼠标悬停显示详情 |
| 最大缺口 | 缺口按可回收分数排序，每个有具体改进建议 |
| 数据一致性 | 仪表盘数据与详情页数据一致，无矛盾 |

---

### 模块五：修复工具集（P1，6-8 人天）

geo-score 只做检测不做修复。工作目录可以新增"从诊断到修复"的工具集，形成闭环。

#### 2.5.1 llms.txt 生成器（3-4 人天）

**功能**：基于企业信息和内容库，自动生成符合 llmstxt.org 规范的 llms.txt 文件。

**llms.txt 规范结构**（geo-score p1.llms-txt 检查的评分依据）：
```
# 站点定义段（必须，4分）
# 公司名 - 一句话描述公司是什么、做什么

## 主题分节1（2+个含链接的分节，满分5分）
- [页面标题](URL) - 一句话描述
- [页面标题](URL) - 一句话描述

## 主题分节2
- [页面标题](URL) - 一句话描述
```

**实施步骤**：

1. **后端 API**：`POST /api/tools/llms-txt/generate`
   - 输入：`{company_name, company_desc, sections: [{title, content_ids: [...]}]}`
   - 输出：`{content: "...", preview_url: "..."}`
   - 逻辑：
     - 生成站点定义段（`# {company_name} - {company_desc}`）
     - 对每个主题分节，从内容库获取指定文章的标题和URL，生成 `- [标题](URL) - 摘要`
     - 可选：用 LLM 为每篇文章生成一句话摘要（如果内容库没有摘要字段）
2. **后端**：`GET /api/tools/llms-txt/download` 返回 .txt 文件
3. **前端页面**：`pages/ToolsLLMSTxt.tsx`
   - 左侧：配置表单（公司名、描述、主题分节配置、从内容库选择文章）
   - 右侧：实时预览生成的 llms.txt 内容
   - 底部：下载按钮 + 部署指南（"放到网站根目录，确保 https://yourdomain.com/llms.txt 可公开访问"）
4. **验证**：生成后自动运行 geo-score 的 p1.llms-txt 检查，确认能拿到 4-5 分

**验收标准**：生成的 llms.txt 通过 geo-score p1.llms-txt 检查（至少 4 分，含站点定义段）。

#### 2.5.2 JSON-LD 结构化数据生成器（3-4 人天）

**功能**：为企业官网和内容页生成符合 schema.org 规范的 JSON-LD 代码。

**生成类型**：

| 类型 | 适用场景 | 对应 geo-score 检查项 |
|------|---------|---------------------|
| Organization + WebSite | 全站通用，每个页面都应包含 | p1.organization（6分） |
| BreadcrumbList | 嵌套页面 | p1.breadcrumb（3分） |
| Article / BlogPosting / NewsArticle | 文章/新闻页 | p1.page-type（4分） |
| FAQPage | 问答页 | p1.page-type |
| HowTo | 教程/指南页 | p1.page-type |
| Product + Offer | 产品页 | p1.page-type |
| **MedicalOrganization + Hospital** | 医院官网（医疗场景扩展） | p1.organization 医疗适配 |
| **Physician** | 医生个人页（医疗场景扩展） | p2.named-author 医疗适配 |
| **MedicalWebPage / MedicalGuideline** | 医疗内容页 | p1.page-type 医疗适配 |

**实施步骤**：

1. **后端引擎**：`app/engines/jsonld_generator.py`
   - 每个类型一个生成函数，接收参数返回 JSON-LD 字符串
   - 示例：`generate_organization(name, url, logo, sameAs_list) -> str`
   - 医疗场景扩展：`generate_medical_organization(name, url, logo, medical_specialty, hospital_type)`
2. **后端 API**：`POST /api/tools/jsonld/generate`，输入类型+参数，输出代码
3. **前端页面**：`pages/ToolsJSONLD.tsx`
   - 类型选择器（下拉，含医疗专用类型）
   - 动态表单（根据类型显示不同字段）
   - 实时预览生成的 JSON-LD 代码（带语法高亮）
   - 复制按钮 + 安装指南（"插入页面 `<head>` 中，或 `<body>` 末尾"）
   - 验证提示：生成后提示"可用 Google 富媒体搜索测试工具验证"
4. **预设模板**：内置"医院官网全套"模板（Organization + WebSite + BreadcrumbList + MedicalWebPage），一键生成

**验收标准**：
- 生成的 Organization + WebSite JSON-LD 通过 geo-score p1.organization 检查（至少 5 分）
- 医疗专用类型（MedicalOrganization/Physician）可正常生成且字段完整
- 生成的代码是合法 JSON，可被 schema.org 验证工具解析

---

### 模块六：竞品网站体检与并排对比（P1，4-5 人天）

#### 2.6.1 功能描述

对每个竞品官网运行 GEO 就绪度扫描，生成企业与竞品的并排对比，找出差距最大的维度。

#### 2.6.2 数据模型扩展

在现有 `geo_competitor` 表增加字段：
- `website_url` TEXT（竞品官网URL，用于扫描）
- `last_audit_id` INTEGER（关联最新一次 site_audit_record）
- `last_audit_score` INTEGER（缓存最新评分，避免每次查关联表）

#### 2.6.3 API 设计

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/competitors/{id}/audit` | 触发竞品官网扫描 |
| GET | `/api/competitors/compare` | 获取本企业 vs 所有竞品的并排对比 |
| GET | `/api/competitors/{id}/compare-detail` | 本企业 vs 单个竞品的逐项对比 |

`compare` 响应结构：

```json
{
  "self": {
    "name": "本企业",
    "score": 71,
    "band": "Solid",
    "pillars": {"Reachable": 11, "Understandable": 15, "Content Citability": 25, "Brand Credibility": 8, "Answer Fit": 2}
  },
  "competitors": [
    {
      "id": 1,
      "name": "竞品A",
      "website_url": "https://competitor-a.com",
      "score": 65,
      "band": "Growing",
      "pillars": {...},
      "last_audit_at": "2026-09-15T10:00:00"
    }
  ],
  "gap_analysis": {
    "biggest_advantage": {"pillar": "Reachable", "self": 11, "competitor_avg": 8, "gap": 3},
    "biggest_disadvantage": {"pillar": "Content Citability", "self": 25, "competitor_avg": 30, "gap": -5},
    "per_check_gaps": [
      {"check_id": "p2.answer-passages", "name": "自足答案段", "self": 7, "competitor_avg": 9, "gap": -2}
    ]
  }
}
```

#### 2.6.4 前端实现

- 竞品管理页面增加"GEO评分"列和"扫描"按钮
- 新增"竞品对比"视图：
  - 5支柱雷达图叠加（本企业 vs 每个竞品，不同颜色）
  - 逐项对比表格（21项检查，本企业得分 vs 竞品平均分，差距列颜色编码）
  - 差距最大的 3 个检查项置顶，附带改进建议

#### 2.6.5 验收标准

| 验收项 | 标准 |
|--------|------|
| 竞品扫描 | 点击扫描按钮后，竞品官网被扫描，分数正确存储和显示 |
| 并排对比 | 雷达图和对比表格正确显示本企业与竞品的差异 |
| 差距分析 | 自动识别最大优势和最大劣势支柱，按差距排序 |
| 数据时效 | 显示每次扫描的时间，超过7天提示"数据可能过期" |

---

### 模块七：告警与通知系统（P1，5-6 人天）

#### 2.7.1 模块定位与整体思路

**要解决的问题**：当前系统所有异常都需要用户主动打开仪表盘才能发现。告警模块的目标是——**系统主动发现异常并推送给用户**，把问题发现时间从"1-3周后复盘"缩短到"24小时内拦截"。

**核心设计原则**：
1. **按优先级分发渠道**：P0/P1 紧急告警走邮件（即时），P2/P3 走系统内通知（不打扰），不搞全员轰炸
2. **不重复告警**：同一问题在静默期内不重复发送，避免告警疲劳
3. **可配置**：每个告警规则可独立开关、可调整阈值，不是写死的
4. **可追溯**：所有告警都存在数据库里，带状态流转（open → acknowledged → resolved），方便复盘
5. **渠道可扩展**：第一版只做邮件+系统内通知，邮件引擎预留接口，后面加飞书/企业微信/短信只需加一个 sender 实现

**整体架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                    告警检测引擎（alert_engine）                │
│                                                             │
│  事件触发（扫描完成/采集完成/内容入库后）                      │
│     │                                                       │
│     ├─ check_gate_change()        → 门控状态变化（P0）       │
│     ├─ check_score_drop()         → 评分骤降（P1）           │
│     ├─ check_mention_anomaly()    → 提及率异常（P1）         │
│     ├─ check_collection_failure() → 采集失败率（P2）         │
│     ├─ check_competitor_overtake()→ 竞品反超（P2）           │
│     └─ check_content_quality()    → 新内容低分（P3）          │
│                                                             │
│     每个检测函数：对比数据 → 判断是否超阈值 → 生成 AlertEvent  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    优先级路由（router）                       │
│                                                             │
│  P0 → 邮件即时发送 + 系统内通知（置顶红点）                    │
│  P1 → 邮件即时发送 + 系统内通知                              │
│  P2 → 系统内通知 + 次日早间汇总邮件                          │
│  P3 → 系统内通知，攒入每日运营日报                           │
│                                                             │
│  去重逻辑：同一 rule_type + 同一关联对象，在静默期内不重复触发  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌──────────────┐
        │邮件发送  │  │系统内通知 │  │（预留：飞书/  │
        │email.py │  │数据库写入 │  │企业微信/短信）│
        └─────────┘  └──────────┘  └──────────────┘
```

#### 2.7.2 六类告警的详细定义

每类告警都明确：**触发条件、检测方法、业务场景举例、严重级别、通知渠道、静默时长**。

---

**告警类型 1：门控状态变化（gate_change）— P0 紧急**

| 项目 | 说明 |
|------|------|
| **触发条件** | 品牌官网最新一次扫描中，3 个门控项（g.robots / g.reachable / g.ssr）任意一个从"非 0 分"变为"0 分" |
| **检测方法** | 每次 site_audit 扫描完成后，取该 root_origin 的上一次扫描记录，对比 gate_capped 字段和 3 个门控检查项的 scored_points。如果上次 gate_capped=false 且本次 gate_capped=true，或上次某门控项>0 本次=0，则触发 |
| **为什么紧急** | 门控为 0 意味着 AI 爬虫完全拿不到内容，其他所有优化全部无效，这是 GEO 的地基 |
| **业务举例** | 网站改版丢了 SSR、运维改 robots.txt 封了爬虫、服务器宕机返回 503、CDN WAF 按 UA 拦截了 GPTBot |
| **严重级别** | **P0** |
| **通知渠道** | 邮件即时发送（红色标题"紧急"）+ 系统内通知（置顶红点） |
| **静默时长** | 24 小时（同一网站 24 小时内不重复告警） |
| **邮件标题** | 【P0 紧急】{品牌名}官网 GEO 门控异常，AI 爬虫无法获取内容 |
| **邮件正文** | 包含：异常时间、具体哪个门控项从几分掉到 0 分、影响分析、总分变化、建议操作、跳转详情链接 |

---

**告警类型 2：评分骤降（score_drop）— P1 高**

| 项目 | 说明 |
|------|------|
| **触发条件** | 品牌官网最新一次扫描总分，比上一次扫描下降 ≥10 分（且不是门控导致的封顶） |
| **检测方法** | 每次 site_audit 扫描完成后，对比本次 normalized_score 与上一次的差值。如果差值 ≤ -10 且本次 gate_capped=false，则触发。同时找出失分最多的 3 个检查项，写入告警详情 |
| **为什么重要** | 评分骤降一定是某个地方出了问题——页面删了、sitemap 失效了、结构化数据丢了。早发现早修复 |
| **业务举例** | CMS 改版导致文章 URL 变更产生 404、批量删除了文章导致 lastmod 覆盖率下降、技术改了页面结构导致 JSON-LD 丢失 |
| **严重级别** | **P1** |
| **通知渠道** | 邮件即时发送 + 系统内通知 |
| **静默时长** | 24 小时 |
| **邮件标题** | 【P1】{品牌名}GEO 就绪度评分下降 {差值}分 |
| **邮件正文** | 包含：上次分数→本次分数、失分最多的 3 个检查项及原因、怀疑原因、建议操作、跳转链接 |

---

**告警类型 3：提及率异常（mention_anomaly）— P1 高**

| 项目 | 说明 |
|------|------|
| **触发条件** | 某个监测问题/医生，在某个平台的最新一轮提及率，比上一轮下降超过 40 个百分点（例如从 80% 掉到 40% 以下），或 Top1 推荐率下降超过 30 个百分点 |
| **检测方法** | 每次全量采集完成后，按问题×平台分组，对比最新一轮与上一轮的 mentioned 比率和 rank=1 比率。计算差值，超过阈值则触发。需要至少有前一轮数据才判断（首次采集不触发） |
| **为什么重要** | 这是最直接的业务事故信号。可能是 AI 平台算法变了、竞品内容冲击了、或你的内容被降权了 |
| **业务举例** | 张医生在 GLM 的 Top1 推荐率从 90% 掉到 30%、某核心问题在 DeepSeek 的提及率从 70% 掉到 20% |
| **严重级别** | **P1** |
| **通知渠道** | 邮件即时发送 + 系统内通知 |
| **静默时长** | 48 小时（同一问题×平台组合 48 小时内不重复） |
| **邮件标题** | 【P1】{问题名}在{平台}提及率异常下降 |
| **邮件正文** | 包含：问题名、平台、上次提及率→本次提及率、上次 Top1 率→本次 Top1 率、最近 3 轮数据对比、原始回答链接 |

---

**告警类型 4：采集失败率高（collection_failure）— P2 中**

| 项目 | 说明 |
|------|------|
| **触发条件** | 当天采集任务中，失败/超时/被阻断的记录数占总记录数的比例 ≥ 30% |
| **检测方法** | 每次采集任务结束后，统计 collect_status != 'success' 的记录数占比。超过阈值则触发。注意：要把"门控阻断"和"API 错误"分开统计，门控阻断不应计入失败率（因为那是预期行为） |
| **为什么重要** | 如果采集都失败了，仪表盘上的数据是假的——不是"提及率 0%"，而是"根本没采到数据"。必须区分这两种情况 |
| **业务举例** | DeepSeek API 改了返回格式导致解析失败、某平台限流导致大量超时、网络问题导致连接失败 |
| **严重级别** | **P2** |
| **通知渠道** | 系统内通知 + 次日早间汇总邮件（不单独即时发邮件） |
| **静默时长** | 24 小时 |
| **通知内容** | 包含：当天总采集数、成功数、失败数、失败率、各平台失败数分布、主要错误类型、跳转错误详情 |

---

**告警类型 5：竞品反超（competitor_overtake）— P2 中**

| 项目 | 说明 |
|------|------|
| **触发条件** | 某个竞品的最新 GEO 扫描评分，超过本企业最新评分；或本企业与竞品的差距缩小了 ≥15 分 |
| **检测方法** | 每次竞品官网扫描完成后，对比竞品最新 normalized_score 与本企业最新 normalized_score。如果竞品分 > 本企业分，且上次扫描时竞品分 ≤ 本企业分，则触发"反超"告警。如果差距缩小 ≥15 分（但尚未反超），触发"差距缩小"通知 |
| **为什么重要** | GEO 是相对竞争，竞品在做什么优化你需要知道，才能跟上 |
| **业务举例** | 竞品最近上了 llms.txt 和 JSON-LD，评分从 60 升到 74，超过了你 |
| **严重级别** | **P2** |
| **通知渠道** | 系统内通知 + 次日早间汇总邮件 |
| **静默时长** | 7 天（竞品评分每周扫描一次，一周内不重复） |
| **通知内容** | 包含：竞品名、上次评分→本次评分、本企业评分、差距、竞品进步最大的支柱、建议优先优化项 |

---

**告警类型 6：新内容质量低（content_quality_low）— P3 低**

| 项目 | 说明 |
|------|------|
| **触发条件** | 新录入/新编辑的内容，GEO 质量分 < 15/45（满分 45） |
| **检测方法** | 内容 Linter 每次检测完成后，如果分数 < 15，直接触发一条 P3 告警。这不是"变化检测"，而是"即时判断"——内容一入库就判断是否合格 |
| **为什么重要** | 低质量内容不仅不被 AI 引用，还稀释网站整体质量信号。早发现早改写，不要让垃圾内容上线 |
| **业务举例** | 运营录入了一篇标题是关键词串、正文只有 200 字、无作者无日期的文章 |
| **严重级别** | **P3** |
| **通知渠道** | 仅系统内通知（不发邮件），攒入次日运营日报 |
| **静默时长** | 不静默（每篇低分内容都通知，但同一内容不重复告警除非修改后仍低分） |
| **通知内容** | 包含：文章标题、质量分、失分最多的 3 项及改进建议、跳转编辑链接 |

---

#### 2.7.3 数据模型设计

**表 1：alert_rule（告警规则表）**

```sql
CREATE TABLE alert_rule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    rule_type       TEXT NOT NULL UNIQUE,
    severity        TEXT NOT NULL,                   -- P0/P1/P2/P3
    threshold       TEXT NOT NULL DEFAULT '{}',     -- 阈值JSON
    channels        TEXT NOT NULL DEFAULT '["system"]',
    is_enabled      BOOLEAN NOT NULL DEFAULT 1,
    silent_hours    INTEGER NOT NULL DEFAULT 24,
    notify_email    TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 系统初始化插入6条默认规则：
-- 1. gate_change (P0, system+email, 24h)
-- 2. score_drop (P1, system+email, 24h, drop_points=10)
-- 3. mention_anomaly (P1, system+email, 48h, drop_pct=40)
-- 4. collection_failure (P2, system, 24h, fail_rate=30%)
-- 5. competitor_overtake (P2, system, 7d)
-- 6. content_quality_low (P3, system, min_score=15)
```

**表 2：alert_event（告警事件表）**

```sql
CREATE TABLE alert_event (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id             INTEGER NOT NULL,
    rule_type           TEXT NOT NULL,
    severity            TEXT NOT NULL,
    title               TEXT NOT NULL,
    message             TEXT NOT NULL,
    message_html        TEXT,
    related_object_type TEXT,    -- website/question/doctor/content/competitor/collection
    related_object_id   INTEGER,
    related_object_name TEXT,
    related_url         TEXT,
    metric_before       REAL,
    metric_after        REAL,
    metric_diff         REAL,
    status              TEXT NOT NULL DEFAULT 'open',  -- open/acknowledged/resolved
    notified_channels   TEXT NOT NULL DEFAULT '[]',
    acknowledged_at     DATETIME,
    acknowledged_by     TEXT,
    resolved_at         DATETIME,
    resolve_note        TEXT,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES alert_rule(id)
);
CREATE INDEX idx_alert_event_status ON alert_event(status);
CREATE INDEX idx_alert_event_type ON alert_event(rule_type);
CREATE INDEX idx_alert_event_created ON alert_event(created_at);
```

**表 3：alert_daily_digest（每日运营日报表）**

```sql
CREATE TABLE alert_daily_digest (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_date     DATE NOT NULL UNIQUE,
    summary         TEXT NOT NULL DEFAULT '{}',
    sent_at         DATETIME,
    sent_to         TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.7.4 后端模块设计

**目录结构**：

```
backend/app/
├── engines/alert_engine.py           # 告警检测引擎（核心）
├── services/
│   ├── alert_service.py              # CRUD + 状态流转
│   ├── email_service.py             # SMTP邮件发送 + HTML模板
│   └── digest_service.py            # 每日日报汇总
├── api/alerts.py                    # API路由
├── models/alert.py                  # SQLAlchemy模型
└── schemas/alert.py                 # Pydantic模型
```

**alert_engine.py 核心逻辑**：

```python
class AlertEngine:
    """在数据变化事件发生时被调用，检测是否产生新告警"""

    def on_site_audit_completed(self, audit_id):
        """扫描完成：门控变化 + 评分骤降 + 竞品反超"""
        self._check_gate_change(audit_id)
        self._check_score_drop(audit_id)
        self._check_competitor_overtake(audit_id)

    def on_collection_completed(self, collection_date):
        """采集完成：提及率异常 + 采集失败率"""
        self._check_mention_anomaly(collection_date)
        self._check_collection_failure(collection_date)

    def on_content_audited(self, content_id, geo_score):
        """内容检测完成：内容质量"""
        self._check_content_quality(content_id, geo_score)

    def _create_alert(self, rule_type, severity, title, message, **kwargs):
        """通用创建：查规则→静默期去重→写事件→按渠道发送
        P0/P1 → 邮件即时发送 + 系统内
        P2/P3 → 仅系统内（次日日报汇总）"""
        ...
```

**email_service.py 核心逻辑**：

```python
def send_alert_email(event, rule):
    """SMTP发送HTML告警邮件——仅P0/P1调用"""
    to_email = rule.notify_email or settings.ALERT_EMAIL_TO
    # 构建 MIMEMultipart（纯文本+HTML双版本，内联CSS，邮件客户端兼容）
    # SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) 登录发送
    ...
```

**config.py 新增配置项**：

```python
SMTP_HOST: str = ""              # 如 smtp.exmail.qq.com
SMTP_PORT: int = 465
SMTP_USER: str = ""
SMTP_PASSWORD: str = ""
SMTP_FROM: str = ""
ALERT_EMAIL_TO: str = ""         # 告警收件邮箱（个人邮箱，后期可改公共邮箱）
FRONTEND_BASE_URL: str = "http://localhost:3000"
```

**.env.example 新增**：

```bash
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465
SMTP_USER=geo-alert@yourcompany.com
SMTP_PASSWORD=your-smtp-auth-code
SMTP_FROM=geo-alert@yourcompany.com
ALERT_EMAIL_TO=you@yourcompany.com
FRONTEND_BASE_URL=http://your-domain.com
```

#### 2.7.5 后端 API 设计

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/alerts/events` | 告警列表（状态/级别/类型筛选，分页） |
| GET | `/api/alerts/events/{id}` | 单个告警详情 |
| POST | `/api/alerts/events/{id}/ack` | 确认告警（open→acknowledged） |
| POST | `/api/alerts/events/{id}/resolve` | 解决告警（acknowledged→resolved） |
| GET | `/api/alerts/unread-count` | 未读告警数（铃铛轮询用） |
| GET | `/api/alerts/rules` | 所有告警规则 |
| PUT | `/api/alerts/rules/{id}` | 更新规则（阈值/渠道/启用） |
| GET | `/api/alerts/config` | 获取邮件配置（脱敏，不返回密码） |
| PUT | `/api/alerts/config` | 更新 SMTP 配置 |
| POST | `/api/alerts/test-email` | 发送测试邮件验证配置 |

#### 2.7.6 前端设计

**全局铃铛组件（Layout.tsx 右上角）**：
- Ant Design BellOutlined + 红色 Badge 未读数
- 点击下拉显示最近 5 条未读告警（标题+时间+严重级别颜色标签）
- 每 60 秒轮询 `/api/alerts/unread-count`
- 底部"查看全部"跳转告警列表页

**告警列表页（pages/Alerts.tsx）**：
- Tab 筛选：全部 / 待处理 / 已确认 / 已解决
- 严重级别颜色标签（P0红/P1橙/P2黄/P3绿）
- 每条告警卡片：标题、关联对象名、时间、前后数据对比、操作按钮（确认/详情/跳转）
- 详情 Drawer：完整消息、HTML正文、关联对象信息、操作时间线

**规则配置（Settings 页面内 Tab）**：
- 邮件配置区：SMTP服务器/端口/账号/授权码/收件人 + "发送测试邮件"按钮
- 规则列表区：6条规则的启用开关、阈值、通知渠道勾选框

#### 2.7.7 触发时机（事件驱动，非轮询）

| 触发时机 | 检测方法 | 调用位置 |
|---------|---------|---------|
| 每次站点扫描完成后 | gate_change + score_drop + competitor_overtake | 扫描任务末尾 |
| 每次全量采集完成后 | mention_anomaly + collection_failure | 采集任务末尾 |
| 每次内容GEO检测后 | content_quality_low | 内容Linter末尾 |
| 每天早上8:00（APScheduler） | 生成日报 + 发送P2/P3汇总邮件 | 定时任务 |

**为什么不用每分钟轮询数据库？** 告警检测是事件驱动的——数据变化时才需要检查。P0/P1 的时效性由事件驱动保证（扫描/采集完成立即触发），不需要持续轮询。

#### 2.7.8 实施步骤（6 天）

| 天 | 任务 | 产出 |
|----|------|------|
| 第1天 | 建3张表 + SQLAlchemy模型 + Pydantic schema + config配置项 + email_service.py | 数据库就绪，邮件可发测试 |
| 第2天 | alert_engine.py：实现 gate_change + score_drop + 通用_create_alert（含静默期去重） | P0/P1告警能触发并发邮件 |
| 第3天 | alert_engine.py：实现其余4类检测方法，接入各事件回调 | 6类告警全部触发 |
| 第4天 | alerts.py API：事件列表/确认/解决/未读数/规则/配置 | 后端API全部可用 |
| 第5天 | 前端：Layout铃铛组件 + Alerts.tsx告警列表页 | 系统内可查看管理告警 |
| 第6天 | 前端：Settings邮件配置+规则Tab + 测试邮件 + 日报服务 + 全链路联调 | 完整闭环可用 |

#### 2.7.9 验收标准

| 验收项 | 标准 |
|--------|------|
| 6类告警全部触发 | 构造测试数据，6类都能正确创建AlertEvent |
| P0/P1发邮件 | 触发后1分钟内收到邮件，含关键数据和跳转链接 |
| P2/P3不发即时邮件 | 只在系统内通知，不发即时邮件 |
| 去重静默 | 同一规则+对象在静默期内不重复告警 |
| 状态流转 | open → acknowledged → resolved 正确更新 |
| 铃铛红点 | 有未处理告警时铃铛显示红色数字 |
| 邮件配置 | Settings可配置SMTP，"发送测试邮件"可收到 |
| 规则可配置 | 每条规则可独立开关、调阈值 |
| 日报汇总 | 每天早上自动发送前一天P2/P3汇总邮件 |
| 错误降级 | SMTP配置错误时，告警仍写入系统内，不影响告警创建 |

---

## 第四部分：实施路线图与验收总标准

### 4.1 分阶段实施计划

#### 第一阶段：核心诊断能力（第 1-3 周，P0）

**目标**：补齐输入侧诊断能力，让系统能回答"为什么 AI 不提到我"。

| 周 | 任务 | 产出 | 负责人角色 |
|----|------|------|-----------|
| 第1周 | 模块一：site_auditor 引擎移植（rubric.py + fetchers.py + parsers.py + checkers/） | 21项检查可通过命令行运行，输出正确评分 | 后端 |
| 第2周 | 模块一：API + 数据模型 + 前端页面；模块二：content_linter 引擎 | 站点体检页面可正常使用；内容库显示GEO质量分 | 后端+前端 |
| 第3周 | 模块三：采集引擎优化（门控预检+并发+证据结构化+失败区分）；联调测试 | 采集前自动预检，并发采集，证据结构化 | 后端 |

**第一阶段验收**：
- [ ] 输入任意网站URL，20秒内返回0-100分GEO就绪度评分和21项检查详情
- [ ] 门控为0的网站（如amazon.com）评分≤40，且显示"基础设施阻断"
- [ ] 内容库每篇文章有GEO质量分（0-45）和逐项诊断
- [ ] 采集引擎对门控阻断的问题跳过API调用，标记blocked
- [ ] 平台间并发采集，单问题耗时降低50%以上
- [ ] 用geo-score的5个手工审计范例对比，分数偏差≤5

#### 第二阶段：集成与可视化（第 4-5 周，P1）

**目标**：将诊断能力集成到仪表盘和竞品分析，让用户直观看到双维度数据。

| 周 | 任务 | 产出 |
|----|------|------|
| 第4周 | 模块四：仪表盘双维度升级；模块六：竞品网站体检 | 仪表盘显示就绪度+表现双维度；竞品有GEO评分和并排对比 |
| 第5周 | 模块七：告警与通知系统；联调测试 | 门控变化/评分骤降/竞品反超时自动告警 |

**第二阶段验收**：
- [ ] 仪表盘顶部显示GEO就绪度评分和5支柱雷达图
- [ ] 存在门控阻断时顶部红色告警条
- [ ] 竞品页面显示GEO评分，支持5支柱雷达图叠加对比
- [ ] 门控状态变化时自动发送飞书告警
- [ ] 所有新功能在医生场景（design-v2）下正常工作

#### 第三阶段：修复工具与闭环（第 6-7 周，P1）

**目标**：从"诊断"延伸到"修复"，形成完整闭环。

| 周 | 任务 | 产出 |
|----|------|------|
| 第6周 | 模块五：llms.txt 生成器 + JSON-LD 生成器（含医疗专用类型） | 可生成llms.txt和各类JSON-LD代码，一键复制 |
| 第7周 | 优化建议整合：从诊断结果自动生成"优化行动清单"；全链路测试 | 每个扫描结果附带可执行的优化步骤和预计提升分数 |

**第三阶段验收**：
- [ ] 生成的llms.txt通过geo-score p1.llms-txt检查（≥4分）
- [ ] 生成的Organization+WebSite JSON-LD通过geo-score p1.organization检查（≥5分）
- [ ] 医疗专用JSON-LD类型（MedicalOrganization/Physician/MedicalWebPage）可正常生成
- [ ] 扫描结果页有"优化行动清单"，按优先级排序，每项含具体操作和预计提升分

#### 第四阶段：差异化与生态（第 8 周+，P2，持续迭代）

- GEO 行业基准排行榜（定期扫描医疗行业主要医院/医生官网）
- 历史趋势与扫描对比（任意两次扫描的逐项对比）
- GitHub Action 集成（官网代码仓库 CI 门禁）
- CLI 网站扫描命令（`geo score <url>`）
- SVG 徽章生成（可嵌入官网/简历的评分徽章）
- LLM 辅助内容改写建议（基于 Linter 结果，自动生成改写后的段落）

### 4.2 全局验收标准

| 维度 | 标准 | 验证方法 |
|------|------|---------|
| **功能完整性** | 7 个模块全部实现，21 项网站检查 + 8 项内容检查全部可用 | 逐项走查，用测试用例验证 |
| **评分准确性** | 与 geo-score 官方 CLI 对同一网站评分偏差 ≤5 分 | 用 10 个网站（含中英文、含门控阻断）对比 |
| **性能** | 单次网站扫描 ≤30 秒（8页采样+13UA探测）；单篇内容 Lint ≤1 秒 | 实测 10 次取平均 |
| **稳定性** | 连续运行 7 天无崩溃，错误率 <1% | 压力测试 + 长运行测试 |
| **数据一致性** | 仪表盘/详情页/导出报告的数据完全一致 | 交叉验证 |
| **医疗适配** | 医疗专用 JSON-LD 类型、医生页面检测、医疗合规提示正常 | 用医院官网和医生个人页测试 |
| **中文适配** | 中文网站 CJK 检测、字数统计、标题意图匹配、中文 UA 探测正常 | 用 5 个中文网站测试 |
| **许可证合规** | 所有从 geo-score 抽取的代码标注来源和 MIT 许可证 | 代码审查 |
| **文档完整性** | 每个模块有设计文档、API 文档、用户操作指南 | 文档审查 |
| **可回滚** | 每个模块可独立开关，关闭后不影响现有功能 | 功能开关测试 |

### 4.3 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| geo-score 评分规则更新（v1.2）导致本地实现过时 | 中 | 中 | rubric 版本化设计，每次更新只需替换 rubric.py，检测逻辑与规则分离 |
| 网站反爬/CDN 拦截导致扫描失败率高 | 高 | 中 | 13 UA 探测本身就是为了发现这个问题；对被拦截的网站标记"需人工验证"，不强行重试 |
| 医疗场景下通用评分权重不合适 | 中 | 高 | 第一阶段先用通用权重跑数据，第二阶段基于医疗行业基准校准权重（如 Brand Credibility 权重提高） |
| 并发采集导致 AI 平台 API 限流 | 中 | 中 | 平台间并发但问题间保留延迟；增加令牌桶限流；限流时自动降级为串行 |
| LLM 辅助判定（question-coverage）成本高 | 中 | 低 | 默认退出分母，仅在用户主动请求时调用 LLM；批量检测时用缓存 |
| 数据量增长导致 SQLite 性能瓶颈 | 低 | 中 | design-v2 已预留 PostgreSQL 迁移接口；site_audit 表按月分区 |
| 前端页面复杂度增加导致性能下降 | 低 | 低 | 雷达图/仪表盘组件懒加载；ECharts 实例销毁管理 |

### 4.4 关键决策点（需用户确认）

1. **评分权重是否医疗化调整**：第一阶段先用 geo-score 通用权重，还是直接为医疗场景定制权重？
   - 建议：先用通用权重跑 2-4 周数据，再基于实际数据校准
2. **LLM 辅助判定的范围**：question-coverage（内容覆盖用户常问问题）是否启用 LLM 辅助？
   - 建议：默认关闭（退出分母），作为可选功能，因为 LLM 调用有成本且不稳定
3. **告警通知渠道**：优先接入哪个渠道？
   - 建议：飞书 webhook（最简单，用户已有飞书环境），其次邮件
4. **行业基准的范围**：GEO 行业基准排行榜是否只做医疗行业？
   - 建议：先做医疗行业（与当前业务匹配），后续再扩展
5. **是否开源 site_auditor 模块**：从 geo-score 衍生的扫描引擎是否回馈开源社区？
   - 建议：MIT 许可证允许，可以考虑独立开源，但需先剥离业务相关代码

---

## 第五部分：文件变更清单总览

### 新增文件（后端）

```
backend/app/engines/site_auditor/
├── __init__.py
├── models.py                  # ScanResult, CheckResult, PageData 数据类
├── rubric.py                  # 21项检查定义、5支柱、分值、tier条件
├── fetchers.py                # 13UA并发抓取、robots.txt、sitemap、llms.txt
├── parsers.py                 # JSON-LD提取、标题、段落、CJK处理
├── scorer.py                  # 门控封顶、归一化、档位判定、缺口排序
├── auditor.py                 # 主入口：编排完整扫描流程
└── checkers/
    ├── __init__.py
    ├── reachable.py           # g.robots, g.reachable, g.ssr (15分)
    ├── understandable.py      # p1.sitemap ~ p1.page-type (22分)
    ├── content_citability.py  # p2.answer-passages ~ p2.named-author (35分)
    ├── brand_credibility.py   # p3.listings ~ p3.video (18分)
    └── answer_fit.py          # p4.answer-shape ~ p4.cn-engines (10分)

backend/app/engines/content_linter.py     # 内容GEO质量检测引擎
backend/app/engines/jsonld_generator.py   # JSON-LD代码生成器
backend/app/engines/llmstxt_generator.py  # llms.txt生成器
backend/app/engines/alert_engine.py       # 告警引擎

backend/app/api/site_audit.py    # 站点体检API
backend/app/api/alerts.py        # 告警API
backend/app/api/tools.py         # 修复工具API（llms.txt/JSON-LD生成）

backend/app/models/site_audit.py     # 3张表：site_audit_record/check/page
backend/app/models/alert.py          # 2张表：alert_rule/event
backend/app/models/content_geo_check.py  # 内容GEO检测历史表

backend/app/schemas/site_audit.py    # Pydantic请求/响应模型
backend/app/schemas/alert.py
backend/app/schemas/tools.py
```

### 新增文件（前端）

```
frontend/src/pages/SiteAudit.tsx         # 站点体检页面
frontend/src/pages/Alerts.tsx            # 告警中心页面
frontend/src/pages/ToolsLLMSTxt.tsx      # llms.txt生成器页面
frontend/src/pages/ToolsJSONLD.tsx       # JSON-LD生成器页面

frontend/src/components/ScoreGauge.tsx       # 环形评分仪表盘
frontend/src/components/PillarRadar.tsx      # 5支柱雷达图
frontend/src/components/PillarBreakdown.tsx  # 5支柱横向条形图
frontend/src/components/CheckItemCard.tsx    # 检查项卡片
frontend/src/components/GateAlertBanner.tsx  # 门控告警条
frontend/src/components/TopGapsPanel.tsx     # 最大缺口面板

frontend/src/api/siteAudit.ts    # 站点体检API封装
frontend/src/api/alerts.ts       # 告警API封装
frontend/src/api/tools.ts        # 工具API封装
```

### 修改文件

```
backend/app/engines/collector.py     # 门控预检+并发+证据结构化+失败区分
backend/app/services/dashboard_service.py  # 双维度数据聚合
backend/app/api/content.py           # 内容创建/编辑时触发Linter
backend/app/api/competitor.py        # 竞品扫描+对比API
backend/app/models/monitor.py        # 新增collect_status/evidence_json字段
backend/app/models/content.py        # 新增geo_score/geo_check_results字段
backend/app/models/competitor.py     # 新增website_url/last_audit_id字段
backend/app/main.py                   # 注册新API路由
backend/app/worker/worker.py          # 注册扫描/告警后台任务
backend/requirements.txt              # 如新增依赖（预计无新增，site_auditor零依赖）

frontend/src/pages/Dashboard.tsx      # 双维度仪表盘重写
frontend/src/pages/ContentHub.tsx     # 增加GEO质量分列和详情
frontend/src/pages/Competitor.tsx     # 增加GEO评分和对比视图
frontend/src/router/index.tsx         # 注册新页面路由
frontend/src/store/useStore.ts        # 新增状态管理
```

### 数据库迁移

```sql
-- 新增表（6张）
site_audit_record, site_audit_check, site_audit_page
content_geo_check
alert_rule, alert_event

-- 修改表（4张，ALTER TABLE）
geo_monitor_record: +collect_status, +error_detail, +evidence_json
geo_content: +geo_score, +geo_check_results, +geo_last_checked_at
geo_competitor: +website_url, +last_audit_id, +last_audit_score
geo_question: +brand_url（用于门控预检，如已有则跳过）
```

---

*文档结束。本方案覆盖 7 个模块的完整设计、代码级实施步骤、数据模型、API 定义、前端布局、验收标准和风险应对，可直接作为开发任务书使用。*

