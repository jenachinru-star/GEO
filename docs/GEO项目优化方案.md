# GEO 后台运营工具 — 完整优化方案

> 版本：v1.0
> 日期：2026-09-13
> 基于：两份录音纪要 + 产品思维导图 + 当前前后端代码全量审查 + 开源项目调研

---

## 目录

1. [项目定位与核心概念](#1-项目定位与核心概念)
2. [当前代码现状](#2-当前代码现状)
3. [核心问题清单](#3-核心问题清单)
4. [目标产品架构](#4-目标产品架构)
5. [后端改造详细方案](#5-后端改造详细方案)
6. [前端改造详细方案](#6-前端改造详细方案)
7. [新增功能详细设计](#7-新增功能详细设计)
8. [数据模型变更清单](#8-数据模型变更清单)
9. [开源项目参考与可复用逻辑](#9-开源项目参考与可复用逻辑)
10. [开发排期](#10-开发排期)
11. [风险与注意事项](#11-风险与注意事项)

---

## 1. 项目定位与核心概念

### 1.1 一句话定位

**GEO后台运营工具 = 医生版"抖音创作者中心"**

类比抖音创作者中心：
- 抖音创作者中心：看账号数据、看发布过的视频、发布视频、找素材灵感
- GEO后台：看GEO/AEO数据、看每条语义下生成了多少文章、生成文章/视频（跳转现成工具）

### 1.2 核心概念定义（以思维导图为准）

| 概念 | 定义 | 举例 |
|---|---|---|
| **GEO** | 用户在一个问题下，被AI**推荐进列表**的次数。AI回答里出现了医生名字，算一次GEO推荐。AI还会推荐其他医生，GEO是做"被推荐列表里的其中一个" | 问"深圳哪个医院治妇科炎症最好？"→AI回答里出现了刘医生→GEO+1 |
| **AEO** | 用户在一个问题下，答案被AI**直接引用为唯一答案**的次数。AI用医生的文章内容来回答问题，算一次AEO引用 | 问"妇科炎症怎么治疗？"→AI直接引用了刘医生的文章内容→AEO+1 |
| **语义** | 一个使用AI问答的人会**真实提问的问题**。基于医生地域+科室+专长自动生成，最少10个。用户只能下拉选择不能自己填。每个语义可衍生无数文章 | "深圳妇科炎症看哪个医生？"、"深圳妇科炎症去哪治疗最好？" |
| **实体锚定** | 文章中自我介绍格式必须全网统一（"XX市XX医院XX科XX医生"），防止AI判定信息混乱而降权 | 统一用"深圳市第一人民医院妇科刘医生"，不能混用"深圳第一人民医院刘医生"等变体 |

### 1.3 与传统SEO的关系

**本质：SEO在AI时代的延伸变体，不是全新物种。**

| 维度 | 传统SEO | GEO/AEO |
|---|---|---|
| 战场 | 百度/Google搜索结果页 | DeepSeek/豆包/GLM的AI回答 |
| 用户行为 | 搜索→看到链接→点击进入网站 | 提问→AI直接说出医生名字/引用文章，无需点击 |
| 优化核心 | 外链权重、关键词密度、网站结构 | 实体一致性、问答式内容结构、内容真实性 |
| 结果指标 | 关键词排名、网站流量 | GEO率（被推荐次数）、AEO率（被引用次数） |
| 内容载体 | 自己的网站/落地页 | 分发到第三方平台的文章（今日头条/知乎/公众号等） |
| 反作弊逻辑 | 百度判断垃圾外链/关键词堆砌 | AI判断信息是否一致真实，不一致直接降权 |

**对外沟通策略**：跟医生不讲SEO概念，直接说"患者用AI问'深圳妇科炎症看哪个医生'的时候，让AI推荐你"。

---

## 2. 当前代码现状

### 2.1 技术栈

| 层 | 技术 | 版本/说明 |
|---|---|---|
| 后端框架 | Python FastAPI | 异步Web框架 |
| 数据库 | SQLite | 预留PostgreSQL迁移接口 |
| ORM | SQLAlchemy | declarative_base |
| 定时任务 | APScheduler | 每天10:00自动采集 |
| AI适配 | OpenAI兼容SDK | DeepSeek/GLM/MiniMax |
| 向量引擎 | 纯Python字符n-gram哈希 | 256维，语义能力弱 |
| 前端框架 | React 18 + TypeScript | Vite构建 |
| UI组件 | Ant Design 5 | 暗色侧边栏+亮色内容区 |
| 图表 | ECharts + echarts-for-react | |
| 状态管理 | Zustand | |
| HTTP客户端 | Axios | |
| 认证 | IAM SSO (Casdoor OAuth2.0) | JWT签发 |
| CLI | Go + Cobra | 独立二进制，与主系统脱节 |

### 2.2 后端文件结构

```
backend/app/
├── main.py              # FastAPI入口，注册9个路由，APScheduler定时任务
├── config.py            # Pydantic Settings，从.env读取
├── database.py          # SQLAlchemy引擎+Session
├── adapters/            # AI平台适配器（3个，代码重复率>90%）
│   ├── base.py          # 抽象基类
│   ├── deepseek.py      # DeepSeek适配器
│   ├── glm.py           # GLM适配器
│   ├── minimax.py       # MiniMax适配器
│   └── factory.py       # 单例工厂
├── api/                 # API路由（9组）
│   ├── auth.py          # IAM认证（SSO登录、ticket交换、userinfo）
│   ├── monitor.py       # 监测中心（问题CRUD、记录查询、矩阵、趋势、采集）
│   ├── content.py       # 内容资产（CRUD+向量生成）
│   ├── knowledge.py     # 知识库（CRUD+语义搜索+向量重建）
│   ├── competitor.py    # 竞品分析（CRUD+记录）
│   ├── dashboard.py     # 仪表盘统计
│   ├── rag.py           # RAG智能问答
│   ├── system.py        # 系统信息+平台状态+演示数据初始化
│   └── export.py        # Excel导出（5个导出接口）
├── engines/             # 核心引擎
│   ├── collector.py     # 采集引擎（串行多平台提问+解析+入库）
│   ├── parser.py        # 回答解析（品牌提及/排名/情感，正则实现）
│   ├── vector.py        # 向量引擎（纯Python n-gram哈希）
│   └── rag.py           # RAG引擎（检索+生成+多轮对话）
├── models/              # 数据模型（8张表）
│   ├── platform.py      # AI平台配置
│   ├── question.py      # 监测问题
│   ├── monitor.py       # 监测记录
│   ├── content.py       # 内容资产
│   ├── knowledge.py     # 知识库
│   ├── competitor.py    # 竞品+竞品记录
│   └── user.py          # 用户
├── schemas/             # Pydantic请求/响应模型（单文件）
└── services/            # 业务服务
    ├── monitor_service.py    # 监测查询+统计+采集触发
    ├── dashboard_service.py  # 仪表盘汇总统计
    ├── export_service.py     # Excel导出（openpyxl，样式完善）
    └── iam_service.py        # IAM SSO（OAuth2流程+JWT签发验证）
```

### 2.3 前端文件结构

```
frontend/src/
├── App.tsx              # 根组件，加载系统信息
├── main.tsx             # 入口
├── api/index.ts         # Axios封装+所有API（9组）
├── router/index.tsx     # 路由配置（8个页面，lazy加载）
├── store/useStore.ts    # Zustand全局状态
├── components/Layout.tsx # 主布局（暗色侧边栏+亮色内容区）
├── pages/
│   ├── Dashboard.tsx    # 数据仪表盘（指标卡+趋势图+平台环形图+排名表）
│   ├── Monitor.tsx      # 监测中心（问题矩阵表+采集+详情抽屉）
│   ├── Content.tsx      # 内容资产库（列表+添加+详情）
│   ├── Knowledge.tsx    # 统一知识库（分类树+语义搜索+CRUD）
│   ├── Competitor.tsx   # 竞品分析（对比图+列表）
│   ├── RAGChat.tsx      # 智能问答（多轮对话+平台切换）
│   ├── Settings.tsx     # 系统设置（系统信息+平台状态+快捷操作）
│   └── SSOCallback.tsx  # SSO回调落地页
└── styles/global.css    # 全局样式（设计令牌+卡片+矩阵单元格+动画）
```

### 2.4 当前已实现的功能

1. **监测中心**：问题管理、平台矩阵、采集记录、手动/定时采集、趋势图
2. **内容资产库**：内容CRUD、向量生成、效果评分（手动维护）
3. **统一知识库**：知识CRUD、三级权限、语义检索（弱）、向量重建
4. **竞品分析**：竞品CRUD、提及监测、对比图表
5. **智能问答**：RAG多轮对话、多平台切换、来源标注
6. **仪表盘**：核心指标、7天趋势、平台对比、Top/Bottom排名
7. **系统设置**：系统信息、平台状态、演示数据初始化
8. **IAM认证**：SSO登录、ticket交换、JWT签发
9. **数据导出**：5种Excel导出（监测记录/问题/知识库/内容/完整报告）

---

## 3. 核心问题清单

### 3.1 定位问题（P0）

| # | 问题 | 影响 |
|---|---|---|
| 1 | 当前是"品牌曝光监测工具"，不是"医生GEO创作者中心" | 整个产品方向偏离 |
| 2 | 监测对象是公司品牌，不是医生个人 | 目标用户和使用场景完全错误 |
| 3 | 没有医生Profile收集流程 | 语义生成、实体锚定、GEO/AEO检测都无数据基础 |
| 4 | 前端菜单是后台管理视角，没有创作者中心视角 | 医生用户看不懂、不会用 |

### 3.2 功能缺失（P0）

| # | 问题 | 说明 |
|---|---|---|
| 5 | 语义库完全缺失 | 思维导图核心功能，基于Profile自动生成语义问题 |
| 6 | GEO/AEO双维度检测缺失 | 当前只有"品牌提及率"，没有区分GEO推荐和AEO引用 |
| 7 | 文章生成入口缺失 | 应跳转现成文章工具，当前没有跳转入口 |
| 8 | 视频生成入口缺失 | 应跳转现成视频工具（待定） |
| 9 | 付费体系缺失 | 免费1次文章/付费全功能/新增语义收费，完全没有 |
| 10 | 实体一致性校验缺失 | 检查全网自我介绍格式是否统一，防止AI降权 |

### 3.3 架构问题（P1）

| # | 问题 | 说明 |
|---|---|---|
| 11 | 多租户数据隔离缺失 | 所有数据全局可见，医生能看到其他医生数据 |
| 12 | 业务API无JWT鉴权 | 除auth路由外，所有API无需登录即可访问 |
| 13 | 采集是同步阻塞 | 全量采集中串行执行+sleep，问题多时前端超时 |
| 14 | 向量引擎太弱 | 纯Python n-gram哈希，语义检索质量差，RAG不可靠 |
| 15 | 三个适配器代码重复 | deepseek/glm/minimax除类名外完全相同，重复率>90% |
| 16 | CORS全开 | allow_origins=["*"]，生产环境不安全 |
| 17 | IAM state/ticket存内存 | 重启丢失，多实例不共享 |
| 18 | SQLite并发限制 | 多用户写入时锁库 |

### 3.4 数据模型问题（P1）

| # | 问题 | 说明 |
|---|---|---|
| 19 | Question表无user_id | 无法按医生隔离语义 |
| 20 | Content表无author_id | 无法追踪文章归属 |
| 21 | MonitorRecord无detect_type | 无法区分GEO和AEO |
| 22 | 无DoctorProfile表 | 医生个人信息无处存储 |
| 23 | 无Subscription表 | 付费状态无法管理 |
| 24 | 无ArticleDraft表 | 生成的文章草稿无状态追踪 |
| 25 | User表role无doctor | 只有admin/operator/viewer |

### 3.5 代码质量问题（P2）

| # | 问题 | 说明 |
|---|---|---|
| 26 | 品牌名硬编码不一致 | config是"深圳层次智慧"，RAG prompt是"登麟科技（原层次智慧）" |
| 27 | schemas全部塞一个文件 | 200+行单文件，难以维护 |
| 28 | Go CLI与主系统脱节 | 独立二进制，无业务价值，增加维护成本 |
| 29 | 前端无路由守卫 | 未登录也能访问所有页面 |
| 30 | 竞品/RAG/知识库对医生端无用 | 应隐藏或仅保留给运营后台 |

---

## 4. 目标产品架构

### 4.1 产品结构图

```
GEO后台运营工具（医生创作者中心）
│
├── 👤 医生Profile（基础层）
│   ├── 姓名、职称、执业地域（省/市/医院）
│   ├── 科室、专长疾病
│   ├── 获奖履历、治病履历（可选）
│   └── 订阅状态（free/paid）
│
├── 📋 语义库
│   ├── 基于Profile自动生成最少10个语义问题
│   ├── 每个语义=一个患者会真实提问的问题
│   ├── 展示每个语义下的文章数、GEO率、AEO率
│   ├── 用户只能下拉选择，不能自己填写
│   └── 新增语义需额外付费
│
├── 📝 内容管理
│   ├── 已生成文章列表（按语义分组）
│   ├── 文章状态（草稿/已复制/已分发）
│   ├── 一键复制分发
│   ├── 实体一致性校验标记
│   └── 发布平台记录
│
├── 📊 数据中心
│   ├── GEO数据：被AI推荐进列表的次数/百分比
│   ├── AEO数据：被AI引用为答案的次数/百分比
│   ├── 按语义维度拆分
│   ├── 趋势图（每日手动刷新）
│   └── 付费用户可见
│
└── 🚀 创作入口（跳转现成工具）
    ├── 生成文章 → 跳转现成图文工具（传参：选中语义+Profile）
    └── 生成视频 → 跳转现成视频工具（待定）
```

### 4.2 技术架构图

```
┌─────────────────────────────────────────────────────┐
│                    前端 (React + AntD)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Profile  │ │ 语义库   │ │ 内容管理 │ │ 数据中心│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  ┌──────────────────────────────────────────────┐   │
│  │         创作入口（跳转外部文章/视频工具）        │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JWT鉴权)
┌──────────────────────▼──────────────────────────────┐
│              后端 (FastAPI + SQLAlchemy)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │  Profile │ │  Semantic│ │  Content │ │  GEO/  │ │
│  │  API     │ │  API     │ │  API     │ │  AEO   │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │  Auth    │ │  Export  │ │  System  │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────────────────────────────────────────┐   │
│  │              引擎层                           │   │
│  │  CollectorEngine(改造)  SemanticGenerator(新) │   │
│  │  GEOAEOAnalyzer(新)     EntityValidator(新)   │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │         适配器层（统一OpenAI兼容）              │   │
│  │  deepseek / glm / minimax / doubao / qwen    │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              数据层 (SQLite → 远期PostgreSQL)        │
│  user / doctor_profile / semantic / article_draft   │
│  monitor_record(geo/aeo) / content / subscription   │
└─────────────────────────────────────────────────────┘
```

### 4.3 业务闭环

```
医生注册登录(IAM SSO)
    → 完善Profile(医院/科室/专长)
    → 系统自动生成10+语义问题
    → 医生选择语义 → 点击"生成文章" → 跳转文章工具(传参)
    → 文章工具生成问答式文章(AEO问句标题+GEO本地化首段+分点正文)
    → 医生复制文章 → 分发到各平台(今日头条/知乎/公众号)
    → 医生在GEO后台手动刷新数据
    → 系统向各AI平台提问语义问题 → 解析GEO推荐/AEO引用
    → 医生查看数据 → 优化内容 → 循环
```

---

## 5. 后端改造详细方案

### 5.1 新增文件

#### 5.1.1 `app/models/doctor.py` — 医生Profile模型

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class DoctorProfile(Base):
    """医生个人资料（GEO基础数据）"""
    __tablename__ = "geo_doctor_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
    real_name = Column(String(100), nullable=False)           # 真实姓名
    title = Column(String(100), default="")                   # 职称（主任医师/副主任医师等）
    province = Column(String(50), default="")                 # 省
    city = Column(String(50), default="")                     # 市
    hospital = Column(String(200), default="")                # 医院全称
    department = Column(String(100), default="")              # 科室
    specialty = Column(String(500), default="")               # 专长疾病（逗号分隔）
    awards = Column(Text, default="")                         # 获奖履历
    case_history = Column(Text, default="")                   # 治病履历/数据统计
    self_intro_template = Column(String(500), default="")     # 统一自我介绍格式（自动生成）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 5.1.2 `app/models/semantic.py` — 语义模型

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Semantic(Base):
    """语义库 — 每个语义=一个患者会真实提问的问题"""
    __tablename__ = "geo_semantic"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    question = Column(String(500), nullable=False)            # 语义问题文本
    category = Column(String(50), default="general")          # 分类（疾病/医院/医生/治疗等）
    is_active = Column(Boolean, default=True)                 # 是否启用监测
    is_paid = Column(Boolean, default=False)                  # 是否付费新增的语义
    geo_rate = Column(Float, default=0.0)                     # GEO推荐率（缓存）
    aeo_rate = Column(Float, default=0.0)                     # AEO引用率（缓存）
    article_count = Column(Integer, default=0)                # 该语义下生成的文章数
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### 5.1.3 `app/models/article.py` — 文章草稿模型

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class ArticleDraft(Base):
    """文章草稿 — 从文章工具生成后回传或手动记录"""
    __tablename__ = "geo_article_draft"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    semantic_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=False, index=True)
    title = Column(String(500), default="")
    content = Column(Text, default="")
    platform = Column(String(50), default="")                 # 目标发布平台（doubao/toutiao/zhihu等）
    status = Column(String(20), default="draft")              # draft/copied/distributed
    entity_consistent = Column(Boolean, default=True)         # 实体一致性校验结果
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### 5.1.4 `app/models/subscription.py` — 订阅模型

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Subscription(Base):
    """用户订阅"""
    __tablename__ = "geo_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
    plan = Column(String(20), default="free")                 # free/pro
    article_quota_used = Column(Integer, default=0)           # 已用免费文章生成次数
    semantic_quota = Column(Integer, default=10)              # 语义数量上限
    paid_semantic_count = Column(Integer, default=0)          # 付费新增语义数
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 5.1.5 `app/engines/semantic_generator.py` — 语义自动生成引擎

```python
"""语义自动生成引擎 — 基于医生Profile生成最少10个语义问题"""
import logging
from typing import List
from app.adapters import adapter_factory

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

输出格式：每行一个问题，不要编号，不要解释。"""

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
            return self._fallback_generate(profile)

        result = adapter.query(user_prompt, system_prompt=self.SYSTEM_PROMPT)
        if not result.success:
            logger.warning(f"语义生成LLM调用失败: {result.error}")
            return self._fallback_generate(profile)

        # 解析回答，每行一个问题
        questions = []
        for line in result.answer.split('\n'):
            line = line.strip()
            # 去掉编号前缀
            import re
            line = re.sub(r'^[\d]+[\.、\)）]\s*', '', line)
            if line and len(line) > 5 and len(line) < 100:
                questions.append(line)

        # 去重
        questions = list(dict.fromkeys(questions))

        if len(questions) < 10:
            questions.extend(self._fallback_generate(profile))
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
        specialty = profile.get('specialty', '').split(',')[0] if profile.get('specialty') else ''
        name = profile.get('real_name', '')

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
        return [q for q in templates if city and specialty]
```

#### 5.1.6 `app/engines/geo_aeo_analyzer.py` — GEO/AEO解析引擎

```python
"""GEO/AEO检测解析引擎 — 区分被推荐(GEO)和被引用(AEO)"""
import re
from typing import Tuple
from dataclasses import dataclass

@dataclass
class GEOAEOResult:
    geo_mentioned: bool      # GEO：被推荐进列表
    aeo_cited: bool          # AEO：被引用为答案
    geo_rank: int            # GEO排名
    aeo_confidence: float    # AEO引用置信度
    raw_answer: str

class GEOAEOAnalyzer:
    """分析AI回答，判断GEO推荐和AEO引用"""

    def __init__(self, doctor_name: str, hospital: str, aliases: list = None):
        self.doctor_name = doctor_name
        self.hospital = hospital
        self.aliases = aliases or []
        # 构建匹配模式：医生姓名、医院+科室、全称等
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> list:
        """构建实体匹配正则模式"""
        patterns = []
        # 医生姓名
        if self.doctor_name:
            patterns.append(re.compile(re.escape(self.doctor_name)))
        # 医院全称
        if self.hospital:
            patterns.append(re.compile(re.escape(self.hospital)))
        # 医院+医生
        if self.hospital and self.doctor_name:
            patterns.append(re.compile(re.escape(self.hospital + self.doctor_name)))
        # 别名
        for alias in self.aliases:
            if alias:
                patterns.append(re.compile(re.escape(alias), re.IGNORECASE))
        return patterns

    def analyze(self, answer: str) -> GEOAEOResult:
        """分析回答，返回GEO/AEO结果"""
        if not answer or not answer.strip():
            return GEOAEOResult(False, False, 0, 0.0, answer)

        # 1. GEO检测：是否提及医生/医院
        geo_mentioned = False
        geo_rank = 0
        mention_pos = -1

        for pattern in self.patterns:
            match = pattern.search(answer)
            if match:
                geo_mentioned = True
                mention_pos = match.start()
                break

        if geo_mentioned:
            geo_rank = self._extract_rank(answer, mention_pos)

        # 2. AEO检测：回答内容是否引用了该医生的文章/观点
        # AEO判断逻辑：
        # - 回答中出现了"根据XX医生的观点"、"XX医生指出"、"XX医院的XX医生表示"等引用句式
        # - 或者回答内容与该医生已发布文章高度相似（需要语义匹配，此处用关键词启发式）
        aeo_cited = False
        aeo_confidence = 0.0

        if geo_mentioned:
            aeo_result = self._detect_aeo_citation(answer, mention_pos)
            aeo_cited = aeo_result[0]
            aeo_confidence = aeo_result[1]

        return GEOAEOResult(geo_mentioned, aeo_cited, geo_rank, aeo_confidence, answer)

    def _extract_rank(self, answer: str, mention_pos: int) -> int:
        """提取提及位置的排名"""
        before_text = answer[:mention_pos]
        # 查找最近的序号
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
        return 1  # 提及了但无明确序号，默认排名1

    def _detect_aeo_citation(self, answer: str, mention_pos: int) -> Tuple[bool, float]:
        """检测是否为AEO引用（直接引用文章内容作为答案）"""
        # 引用句式模式
        citation_patterns = [
            r'(根据|按照|依据).{0,20}(医生|专家|教授|主任).{0,10}(的观点|指出|表示|认为|介绍|建议)',
            r'(医生|专家|教授|主任).{0,10}(表示|指出|认为|建议|提醒|强调)',
            r'(引用|参考|援引).{0,20}(文章|研究|资料)',
            r'据.{0,10}(介绍|了解|报道)',
        ]

        # 在提及位置前后500字符范围内检测
        start = max(0, mention_pos - 200)
        end = min(len(answer), mention_pos + 500)
        context = answer[start:end]

        max_confidence = 0.0
        for pattern in citation_patterns:
            if re.search(pattern, context):
                max_confidence = max(max_confidence, 0.8)

        # 如果回答结构是"直接给出治疗方案/方法"，且提到了医生，AEO置信度中等
        if re.search(r'(治疗方法|治疗方案|怎么治|如何治疗|预防措施|注意事项)', context):
            max_confidence = max(max_confidence, 0.5)

        return (max_confidence >= 0.5, max_confidence)
```

#### 5.1.7 `app/engines/entity_validator.py` — 实体一致性校验引擎

```python
"""实体一致性校验 — 检查文章中自我介绍格式是否全网统一"""
import re
from typing import List, Tuple

class EntityValidator:
    """校验文章中的实体信息是否与Profile一致"""

    def __init__(self, profile: dict):
        self.standard_name = profile.get('real_name', '')
        self.standard_hospital = profile.get('hospital', '')
        self.standard_dept = profile.get('department', '')
        self.standard_city = profile.get('city', '')
        # 标准自我介绍格式
        self.standard_intro = f"{self.standard_city}{self.standard_hospital}{self.standard_dept}{self.standard_name}医生"

    def validate(self, article_text: str) -> Tuple[bool, List[str]]:
        """校验文章实体一致性，返回(是否一致, 问题列表)"""
        issues = []

        if not article_text or not article_text.strip():
            return False, ["文章内容为空"]

        # 1. 检查是否包含标准自我介绍
        if self.standard_hospital and self.standard_name:
            standard_pattern = re.escape(self.standard_hospital)
            if not re.search(standard_pattern, article_text):
                issues.append(f"未包含医院全称「{self.standard_hospital}」")

        # 2. 检查是否有简称变体（可能导致AI信息混乱）
        if self.standard_hospital:
            # 检测可能的简称：去掉"市"/"省"/"人民"等
            short_variants = self._generate_short_variants(self.standard_hospital)
            for variant in short_variants:
                if variant and variant != self.standard_hospital and variant in article_text:
                    # 检查简称是否单独出现（不在全称内部）
                    full_pos = article_text.find(self.standard_hospital)
                    short_pos = article_text.find(variant)
                    if short_pos >= 0 and (full_pos < 0 or short_pos < full_pos or short_pos > full_pos + len(self.standard_hospital)):
                        issues.append(f"检测到医院简称「{variant}」，建议统一使用全称「{self.standard_hospital}」")

        # 3. 检查医生姓名是否一致
        if self.standard_name:
            name_count = article_text.count(self.standard_name)
            if name_count == 0:
                issues.append(f"未包含医生姓名「{self.standard_name}」")

        # 4. 检查科室信息
        if self.standard_dept and self.standard_dept not in article_text:
            issues.append(f"未包含科室信息「{self.standard_dept}」")

        return (len(issues) == 0, issues)

    def _generate_short_variants(self, full_name: str) -> List[str]:
        """生成可能的简称变体"""
        variants = []
        if len(full_name) > 4:
            # 去掉"市"
            variants.append(full_name.replace('市', ''))
            # 去掉"省"
            variants.append(full_name.replace('省', ''))
            # 去掉"人民"
            variants.append(full_name.replace('人民', ''))
            # 去掉城市前缀
            if self.standard_city and full_name.startswith(self.standard_city):
                variants.append(full_name[len(self.standard_city):])
        return [v for v in variants if v and v != full_name and len(v) >= 4]
```

#### 5.1.8 `app/api/doctor.py` — 医生Profile API

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, DoctorProfile
from app.engines.semantic_generator import SemanticGenerator
from app.models.semantic import Semantic

router = APIRouter(prefix="/api/v1/doctor", tags=["医生Profile"])

@router.get("/profile", summary="获取当前医生Profile")
def get_profile(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    return {"code": 0, "message": "success", "data": profile}

@router.post("/profile", summary="创建/更新医生Profile")
def save_profile(data: dict, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        profile = DoctorProfile(user_id=user_id)
        db.add(profile)
    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    # 自动生成统一自我介绍格式
    profile.self_intro_template = f"{data.get('city','')}{data.get('hospital','')}{data.get('department','')}{data.get('real_name','')}医生"
    db.commit()
    db.refresh(profile)

    # 如果是首次创建，自动生成语义
    existing_semantics = db.query(Semantic).filter(Semantic.user_id == user_id).count()
    if existing_semantics == 0:
        generator = SemanticGenerator()
        questions = generator.generate(data)
        for q in questions:
            semantic = Semantic(user_id=user_id, question=q, category="general")
            db.add(semantic)
        db.commit()

    return {"code": 0, "message": "success", "data": profile}

@router.post("/regenerate-semantics", summary="重新生成语义")
def regenerate_semantics(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善Profile")
    generator = SemanticGenerator()
    questions = generator.generate({
        'real_name': profile.real_name, 'title': profile.title,
        'province': profile.province, 'city': profile.city,
        'hospital': profile.hospital, 'department': profile.department,
        'specialty': profile.specialty,
    })
    # 只新增不重复的
    existing = {s.question for s in db.query(Semantic).filter(Semantic.user_id == user_id).all()}
    new_count = 0
    for q in questions:
        if q not in existing:
            db.add(Semantic(user_id=user_id, question=q, category="general"))
            new_count += 1
    db.commit()
    return {"code": 0, "message": "success", "data": {"new_count": new_count, "total": len(questions)}}
```

#### 5.1.9 `app/api/semantic.py` — 语义库API

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.semantic import Semantic
from app.models.article import ArticleDraft

router = APIRouter(prefix="/api/v1/semantic", tags=["语义库"])

@router.get("", summary="获取当前用户的语义列表")
def get_semantics(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).order_by(Semantic.id).all()
    # 关联每个语义的文章数
    result = []
    for s in semantics:
        article_count = db.query(ArticleDraft).filter(
            ArticleDraft.user_id == user_id,
            ArticleDraft.semantic_id == s.id
        ).count()
        result.append({
            "id": s.id, "question": s.question, "category": s.category,
            "is_active": s.is_active, "is_paid": s.is_paid,
            "geo_rate": s.geo_rate, "aeo_rate": s.aeo_rate,
            "article_count": article_count,
        })
    return {"code": 0, "message": "success", "data": result}

@router.post("/{semantic_id}/toggle", summary="启用/禁用某个语义的监测")
def toggle_semantic(semantic_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    s = db.query(Semantic).filter(Semantic.id == semantic_id, Semantic.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="语义不存在")
    s.is_active = not s.is_active
    db.commit()
    return {"code": 0, "message": "success", "data": {"is_active": s.is_active}}

@router.post("/add-paid", summary="付费新增语义")
def add_paid_semantic(question: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # TODO: 检查付费状态，扣减额度
    s = Semantic(user_id=user_id, question=question, category="custom", is_paid=True)
    db.add(s)
    db.commit()
    return {"code": 0, "message": "success", "data": s}
```

#### 5.1.10 `app/deps.py` — 依赖注入（JWT鉴权）

```python
"""通用依赖注入"""
from fastapi import Depends, HTTPException, Request
from app.services.iam_service import IAMService

def get_current_user_id(request: Request) -> int:
    """从JWT中提取当前用户ID"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth_header[7:]
    payload = IAMService.verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    return payload["user_id"]
```

### 5.2 改造现有文件

#### 5.2.1 `app/models/user.py` — 扩展用户模型

```python
# 新增字段
role = Column(String(20), default="doctor")  # admin/operator/doctor/viewer
phone = Column(String(20), default="")
avatar = Column(String(500), default="")
```

#### 5.2.2 `app/models/monitor.py` — 扩展监测记录

```python
# 新增字段
detect_type = Column(String(10), default="geo")   # geo / aeo / both
semantic_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=True)
target_type = Column(String(20), default="doctor") # brand / doctor
target_id = Column(Integer, default=0)             # doctor_id 或 brand_id
recommend_count = Column(Integer, default=0)       # GEO推荐次数
cite_count = Column(Integer, default=0)            # AEO引用次数
```

#### 5.2.3 `app/models/content.py` → 改造为文章管理

```python
# 保留原表，新增字段
author_id = Column(Integer, ForeignKey("geo_user.id"), nullable=True)
semantic_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=True)
content_type = Column(String(20), default="article")  # article/video
platform_target = Column(String(50), default="")      # 目标平台
entity_consistent = Column(Boolean, default=True)     # 实体一致性
status = Column(String(20), default="draft")          # draft/copied/distributed
```

#### 5.2.4 `app/engines/collector.py` — 改造采集引擎

主要改动：
1. 采集目标从"品牌"改为"医生+语义"
2. 使用`GEOAEOAnalyzer`替代原`AnswerParser`做品牌提及解析
3. 记录`detect_type`区分GEO和AEO
4. 关联`semantic_id`
5. 改为异步任务（远期），短期保持同步但增加超时保护

核心改动片段：
```python
def collect_one_semantic(self, semantic: Semantic, profile: DoctorProfile, detect_round: int = 1):
    """采集单个语义在所有平台的GEO/AEO数据"""
    analyzer = GEOAEOAnalyzer(
        doctor_name=profile.real_name,
        hospital=profile.hospital,
        aliases=[profile.self_intro_template] if profile.self_intro_template else []
    )
    for platform_code in platforms:
        success, answer = self.query_single_platform(platform_code, semantic.question)
        if success:
            result = analyzer.analyze(answer)
            record = MonitorRecord(
                question_id=semantic.id,  # 复用question_id字段存semantic_id
                semantic_id=semantic.id,
                platform_code=platform_code,
                rank=result.geo_rank,
                mentioned=result.geo_mentioned,
                detect_type="both",
                recommend_count=1 if result.geo_mentioned else 0,
                cite_count=1 if result.aeo_cited else 0,
                raw_answer=answer,
                ...
            )
```

#### 5.2.5 `app/adapters/` — 合并重复代码

将`deepseek.py`、`glm.py`、`minimax.py`合并为一个`openai_compatible.py`：

```python
class OpenAICompatibleAdapter(BaseAdapter):
    """统一的OpenAI兼容接口适配器，消除三份重复代码"""
    def __init__(self, platform_code, api_key, base_url, model, ...):
        self.platform_code = platform_code
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)
        ...
    def query(self, question, system_prompt=None):
        # 统一实现，三个平台共用
        ...
    def get_platform_code(self):
        return self.platform_code
```

factory.py中通过参数区分平台，不再需要三个独立类。

#### 5.2.6 `app/main.py` — 注册新路由+JWT中间件

```python
# 新增路由
from app.api.doctor import router as doctor_router
from app.api.semantic import router as semantic_router
app.include_router(doctor_router)
app.include_router(semantic_router)

# CORS收紧
allow_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["http://localhost:3000"]
```

#### 5.2.7 `app/config.py` — 新增配置

```python
# 新增
ALLOWED_ORIGINS: str = "http://localhost:3000"
FREE_ARTICLE_QUOTA: int = 1
DEFAULT_SEMANTIC_COUNT: int = 10
ARTICLE_TOOL_URL: str = ""   # 现成文章工具跳转地址
VIDEO_TOOL_URL: str = ""     # 现成视频工具跳转地址
```

#### 5.2.8 `app/services/dashboard_service.py` — 改为医生视角

- 所有查询加`user_id`过滤
- 统计指标改为：总GEO率、总AEO率、各语义排名、活跃语义数、文章总数
- 去掉品牌相关统计

### 5.3 隐藏/废弃的模块

| 模块 | 处理方式 | 原因 |
|---|---|---|
| 竞品分析(competitor) | 前端隐藏，后端保留 | 医生端不需要，远期运营端可能用 |
| 智能问答(rag) | 前端隐藏，后端保留 | 医生端不需要 |
| 统一知识库(knowledge) | 前端隐藏，后端保留 | 文章生成的素材由现成工具管 |
| Go CLI | 评估废弃 | 与主系统脱节，无业务价值 |

---

## 6. 前端改造详细方案

### 6.1 路由重构

当前路由（8个页面）→ 目标路由（6个页面）：

```
/                        → 重定向到 /dashboard
/dashboard               → 数据概览（医生视角）
/semantic                → 语义库（新增，核心页面）
/content                 → 我的文章（改造内容资产库）
/data                    → GEO/AEO数据中心（改造监测中心）
/profile                 → 医生Profile（新增，首页第一步）
/create                  → 创作中心（新增，文章/视频跳转入口）
/sso                     → SSO回调（保留）
/settings                → 系统设置（保留，改为账号设置）
```

隐藏的路由（代码保留但菜单不显示）：
- `/competitor` 竞品分析
- `/knowledge` 知识库
- `/rag` 智能问答

### 6.2 新增页面

#### 6.2.1 `pages/Profile.tsx` — 医生Profile页

**功能**：
- 表单：姓名、职称、省、市、医院全称、科室、专长（多选/标签）、获奖履历、治病履历
- 保存后自动生成语义（调用`/doctor/regenerate-semantics`）
- 显示统一自我介绍格式预览
- 未完善Profile时，其他页面提示"请先完善Profile"

**关键交互**：
- 首次登录强制跳转到此页
- 保存成功后提示"已为您生成10个语义问题，前往语义库查看"

#### 6.2.2 `pages/Semantic.tsx` — 语义库页

**功能**：
- 语义列表卡片：问题文本、文章数、GEO率、AEO率、启用/禁用开关
- 按GEO率/AEO率排序
- "重新生成语义"按钮（付费用户可用）
- "新增语义"按钮（付费额外收费）
- 点击语义 → 展开该语义下的文章列表 + 数据趋势

**布局参考**：抖音创作者中心的"作品管理"列表样式

#### 6.2.3 `pages/Create.tsx` — 创作中心页

**功能**：
- 两个大卡片："生成文章"、"生成视频"
- 生成文章：先选语义（下拉）→ 选发布平台（豆包/今日头条/知乎/公众号）→ 点击"去生成"→ 跳转现成文章工具（带参数：semantic_id、user_id、profile）
- 生成视频：显示"待定"或跳转现成视频工具
- 显示免费额度："您还可免费生成 X 次文章"

**跳转实现**：
```typescript
const handleGenerateArticle = (semanticId: number, platform: string) => {
  const params = new URLSearchParams({
    semantic_id: String(semanticId),
    user_id: String(userId),
    platform,
    source: 'geo_backend'
  })
  window.open(`${ARTICLE_TOOL_URL}?${params.toString()}`, '_blank')
}
```

#### 6.2.4 `pages/DataCenter.tsx` — GEO/AEO数据中心

**功能**：
- 顶部指标卡：总GEO率、总AEO率、监测语义数、今日刷新状态
- GEO/AEO趋势图（双折线，近7天/30天）
- 各语义数据表：语义问题、GEO率、AEO率、GEO排名、趋势
- "手动刷新数据"按钮（付费用户每日一次，显示冷却时间）
- 免费用户显示"购买后可查看完整数据"

**与当前Monitor页的区别**：
- 当前是"问题×平台矩阵"，目标是"语义×GEO/AEO指标"
- 当前看品牌提及，目标看医生个人的GEO推荐和AEO引用

### 6.3 改造现有页面

#### 6.3.1 `pages/Dashboard.tsx` → 医生数据概览

- 去掉"整体提及率/Top1率/平均排名"等品牌指标
- 改为：我的GEO率、我的AEO率、活跃语义数、已生成文章数
- 趋势图改为GEO率+AEO率双线
- 排名表改为"表现最好的语义Top5"+"需优化的语义Bottom5"
- 所有数据按`user_id`过滤

#### 6.3.2 `pages/Content.tsx` → 我的文章

- 加`author_id`过滤，只看自己的文章
- 按语义分组展示
- 加"一键复制"按钮
- 加实体一致性标记（绿色✓一致 / 红色⚠有问题，点击查看问题）
- 加状态标签：草稿/已复制/已分发
- 去掉"效果评分"（手动维护无意义）

#### 6.3.3 `components/Layout.tsx` — 菜单重构

新菜单项：
```
📊 数据概览    /dashboard
📋 语义库      /semantic
📝 我的文章    /content
📈 数据中心    /data
🚀 创作中心    /create
👤 我的资料    /profile
⚙️ 账号设置    /settings
```

去掉：监测中心、内容资产库、统一知识库、竞品分析、智能问答

侧边栏底部显示：
- 订阅状态（免费版/专业版）
- 医生姓名+医院

#### 6.3.4 `store/useStore.ts` — 扩展状态

```typescript
// 新增
doctorProfile: any | null
subscription: any | null
semantics: any[]
setDoctorProfile: (p: any) => void
setSubscription: (s: any) => void
setSemantics: (list: any[]) => void
```

#### 6.3.5 `api/index.ts` — 新增API封装

```typescript
export const doctorApi = {
  getProfile: () => request.get('/doctor/profile'),
  saveProfile: (data: any) => request.post('/doctor/profile', data),
  regenerateSemantics: () => request.post('/doctor/regenerate-semantics'),
}

export const semanticApi = {
  getList: () => request.get('/semantic'),
  toggle: (id: number) => request.post(`/semantic/${id}/toggle`),
  addPaid: (question: string) => request.post('/semantic/add-paid', null, { params: { question } }),
}

export const articleApi = {
  getMyList: (params?: any) => request.get('/content', { params }),
  copy: (id: number) => request.post(`/content/${id}/copy`),
  validateEntity: (id: number) => request.post(`/content/${id}/validate-entity`),
}

export const createApi = {
  getArticleToolUrl: (semanticId: number, platform: string) => 
    `${config.ARTICLE_TOOL_URL}?semantic_id=${semanticId}&platform=${platform}`,
}
```

#### 6.3.6 路由守卫

在`router/index.tsx`中加`RequireAuth`组件：
```typescript
const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAppStore()
  if (!token) return <Navigate to="/sso" replace />
  return <>{children}</>
}
```

Profile页不强制登录（SSO后自动创建），其他页面需要登录。

### 6.4 前端设计风格

保持现有高级感风格（暗色侧边栏+亮色内容区+科技蓝主色），参考抖音创作者中心的信息密度：
- 数据概览用大指标卡+趋势图
- 语义库用卡片列表，每个卡片显示核心指标
- 创作中心用大图标卡片，突出操作入口

---

## 7. 新增功能详细设计

### 7.1 语义自动生成

**触发时机**：
1. 医生首次保存Profile后自动生成
2. 医生手动点击"重新生成"

**生成逻辑**：
1. 组装Profile信息（姓名+职称+地域+医院+科室+专长）
2. 调用LLM，使用精心设计的system_prompt（见`semantic_generator.py`）
3. 解析返回，每行一个问题，去编号、去重
4. 不足10个时用模板兜底
5. 存入`geo_semantic`表，`is_paid=false`

**质量控制**：
- 必须包含城市名（防止信息混乱）
- 必须与专长疾病相关
- 不超过15个
- 去重（与已有语义比对）

### 7.2 GEO/AEO数据检测

**触发方式**：
- 付费用户手动点击"刷新数据"（每日一次）
- 后台定时任务（每天凌晨，仅对付费用户）

**检测流程**：
1. 取该用户所有`is_active=true`的语义
2. 对每个语义，向每个已启用AI平台提问
3. 用`GEOAEOAnalyzer`解析回答：
   - GEO：回答中是否出现医生姓名/医院 → 是则GEO+1，记录排名
   - AEO：回答中是否有引用句式+治疗方案内容 → 是则AEO+1，记录置信度
4. 存入`geo_monitor_record`，`detect_type=both`
5. 更新`geo_semantic`表的`geo_rate`/`aeo_rate`缓存

**数据展示**：
- GEO率 = 被推荐的平台数 / 总平台数 × 100%
- AEO率 = 被引用的平台数 / 总平台数 × 100%
- 按语义维度拆分，按时间维度画趋势

### 7.3 文章工具跳转

**参数传递**：
- `semantic_id`：选中的语义ID
- `user_id`：医生用户ID
- `platform`：目标发布平台（doubao/toutiao/zhihu/wechat）
- `source=geo_backend`：来源标识

**文章工具侧需要做的**（不在本项目内）：
1. 接收参数，根据`semantic_id`拉取语义问题和医生Profile
2. 按问答式模板生成文章（AEO问句标题+GEO本地化首段+分点正文）
3. 生成后回调GEO后台的`/content`接口，回传文章内容
4. 或医生手动复制后在GEO后台记录

### 7.4 实体一致性校验

**触发时机**：
- 文章生成后自动校验
- 文章详情页手动点击"重新校验"

**校验规则**（见`entity_validator.py`）：
1. 是否包含医院全称
2. 是否包含医生姓名
3. 是否包含科室信息
4. 是否有医院简称变体（可能导致AI信息混乱）
5. 自我介绍格式是否统一

**结果展示**：
- 一致：绿色✓标记
- 不一致：红色⚠标记，展开显示具体问题列表和修改建议

### 7.5 付费体系

**免费用户**：
- 可完善Profile
- 自动生成10个语义
- 可免费生成1次文章（计数在`subscription.article_quota_used`）
- 不可查看GEO/AEO数据（显示"购买后可见"）
- 不可手动刷新数据

**付费用户**：
- 全部功能可用
- 每日手动刷新一次数据
- 可新增语义（额外收费，按个计费）
- 可导出数据报告

**实现方式**：
- `geo_subscription`表记录状态
- 前端根据`plan`字段控制按钮和页面访问
- 后端API中间件校验付费状态
- 支付对接暂不实现（先手动开通），预留接口

---

## 8. 数据模型变更清单

### 8.1 新增表（4张）

| 表名 | 用途 | 关键字段 |
|---|---|---|
| `geo_doctor_profile` | 医生Profile | user_id, real_name, title, province, city, hospital, department, specialty, awards, case_history, self_intro_template |
| `geo_semantic` | 语义库 | user_id, question, category, is_active, is_paid, geo_rate, aeo_rate, article_count |
| `geo_article_draft` | 文章草稿 | user_id, semantic_id, title, content, platform, status, entity_consistent |
| `geo_subscription` | 订阅 | user_id, plan, article_quota_used, semantic_quota, paid_semantic_count, expires_at |

### 8.2 修改表（4张）

| 表名 | 新增字段 | 说明 |
|---|---|---|
| `geo_user` | phone, avatar | role默认值改为doctor |
| `geo_monitor_record` | detect_type, semantic_id, target_type, target_id, recommend_count, cite_count | 支持GEO/AEO双维度 |
| `geo_content` | author_id, semantic_id, content_type, platform_target, entity_consistent, status | 改为文章管理 |
| `geo_question` | user_id | 兼容旧数据，远期可废弃用semantic替代 |

### 8.3 保留不改动（3张）

| 表名 | 说明 |
|---|---|
| `geo_platform` | AI平台配置，保留 |
| `geo_knowledge` | 知识库，前端隐藏但表保留 |
| `geo_competitor` / `geo_competitor_record` | 竞品，前端隐藏但表保留 |

### 8.4 数据迁移策略

由于当前是SQLite且数据量小，采用**新建表+代码兼容**方式：
1. 新增表通过`init_db()`自动创建
2. 修改表用`ALTER TABLE`在启动时执行（写在`database.py`的`init_db()`里）
3. 旧数据不删除，新功能用新表
4. `geo_question`表的数据不迁移到`geo_semantic`（因为语义是医生维度的，旧问题是品牌维度的）

---

## 9. 开源项目参考与可复用逻辑

### 9.1 GEO学术研究类

#### 9.1.1 GEO-optim/GEO（Princeton, KDD 2024）
- **地址**：https://github.com/GEO-optim/GEO
- **价值**：GEO概念的原始论文，测试了9种内容优化方法
- **可复用**：
  - **9种优化方法中3种被证明有效**，可直接融入文章生成模板：
    1. **Cite Sources（引用来源）**：+40%可见性，文章中加入权威来源引用
    2. **Statistics Addition（数据统计）**：+40%可见性，加入具体数字（治愈率、病例数）
    3. **Quotation Addition（引用引言）**：+20%可见性，加入专家直接引语
    4. **Fluency Optimization（流畅度优化）**：+15%可见性
  - **Keyword Stuffing在GEO中无效甚至负面**——这验证了思维导图中"不能自己乱填语义"的设计
- **用法**：在文章生成模板的system_prompt中，强制要求生成的文章包含数据统计、来源引用、专家观点这三个要素

#### 9.1.2 AutoGEO（ICLR 2026）
- **地址**：https://github.com/cxcscmu/AutoGEO
- **价值**：自动学习生成式引擎偏好，重写内容
- **可复用**：偏好规则抽取的思路——可以定期分析"被AEO引用的文章"和"未被引用的文章"的差异，自动优化文章生成模板

#### 9.1.3 geo-optimizer-skill / GeoReady
- **地址**：https://pypi.org/project/geo-optimizer-skill/
- **价值**：开源GEO优化CLI，47种方法基于Princeton论文
- **可复用**：
  - 内容评分清单（47项检查），可借鉴做"文章AI友好度评分"
  - llms.txt生成逻辑（让AI爬虫更容易发现内容）
  - 引用追踪（citation tracking）的实现思路

### 9.2 SEO/GEO工具类

#### 9.2.1 OpenSEO
- **定位**：开源Semrush/Ahrefs替代
- **可复用**：
  - 关键词研究→排名追踪→竞品分析的产品架构
  - AI可见性监测（AI visibility monitoring）模块
  - MCP server设计（AI agent可直接操作SEO数据）
- **借鉴点**：我们的"语义库"类似于OpenSEO的"关键词库"，"GEO/AEO检测"类似于"排名追踪"

#### 9.2.2 fastergeo
- **定位**：开源GEO平台CLI，看AI引擎如何谈论你的品牌
- **可复用**：
  - 多AI平台批量提问+结果对比的实现方式
  - "机器验证的工单"（machine-verified tickets）概念——检测到问题后自动生成优化工单

#### 9.2.3 aeo-platform（Webappski）
- **定位**：开源AEO测量引擎（npm包）
- **可复用**：AEO可见性测量网格（measurement grid）的实现，可参考其如何量化"被AI引用"

### 9.3 CMS/创作者中心类

#### 9.3.1 Payload CMS
- **定位**：代码优先的headless CMS，TypeScript-first
- **可复用**：
  - **多租户实现模式**：每个collection加`tenant`字段+访问控制过滤——这正是我们需要的"每个医生只看自己数据"的实现方式
  - 字段级访问控制（Field level access）
  - Hooks系统（内容保存前后的自动处理）——可用于文章保存时自动做实体一致性校验
- **借鉴点**：我们的`user_id`字段过滤模式就是Payload的多租户模式

#### 9.3.2 Strapi
- **定位**：最成熟的开源CMS，插件生态大
- **可复用**：
  - 内容类型构建器（Content Type Builder）的UI交互
  - 媒体库管理
  - 角色权限管理（RBAC）的实现

#### 9.3.3 geoflow
- **定位**：AI内容生产系统+自动化工作流+一键发布平台
- **可复用**：
  - "配置AI模型+素材库+提示词模板→定时批量生成→草稿→审核→发布"的工作流设计
  - 文章自动带SEO/GEO优化的生成逻辑
- **借鉴点**：我们的文章生成虽然跳转到现成工具，但"语义→模板→生成→草稿"的流程可以参考

### 9.4 可直接复用的代码逻辑

| 逻辑 | 来源 | 用法 |
|---|---|---|
| 内容优化9方法（3有效） | Princeton GEO论文 | 融入文章生成prompt |
| 多平台批量提问框架 | fastergeo | 参考collector.py的并发改造 |
| 多租户tenant字段过滤 | Payload CMS | 所有业务表加user_id+查询过滤 |
| 内容保存Hooks | Payload CMS | 文章保存时自动实体校验 |
| AI可见性测量网格 | aeo-platform | 参考GEO/AEO率的计算口径 |
| 引用追踪 | GeoReady | 远期做文章→AI引用的自动归因 |

---

## 10. 开发排期

### 第一阶段：骨架搭建（第1-2周）

**目标**：从"品牌监测后台"变成"医生创作者中心"的骨架

| 天 | 任务 | 后端 | 前端 |
|---|---|---|---|
| 1-2 | 医生Profile | 新增doctor.py模型+doctor.py API+deps.py鉴权 | Profile页+表单+保存 |
| 3-4 | 语义库 | 新增semantic.py模型+semantic_generator.py引擎+semantic.py API | Semantic页+列表+启用/禁用 |
| 5 | 语义自动生成 | 接入LLM生成逻辑+Profile保存后触发 | Profile保存后跳语义库 |
| 6-7 | 路由+菜单重构 | 注册新路由，旧路由保留 | Layout菜单重构+路由守卫+store扩展 |
| 8-10 | 联调测试 | 端到端走通：登录→填Profile→生成语义→看语义列表 | |

**交付物**：医生能登录、填Profile、看到自动生成的语义列表

### 第二阶段：GEO/AEO数据检测（第3-4周）

| 天 | 任务 | 后端 | 前端 |
|---|---|---|---|
| 1-3 | GEO/AEO解析引擎 | geo_aeo_analyzer.py+改造collector.py+monitor_record加字段 | |
| 4-5 | 数据采集API | 改造monitor.py API+按user_id过滤+手动刷新接口 | |
| 6-8 | 数据中心页 | | DataCenter页+指标卡+趋势图+语义数据表+刷新按钮 |
| 9-10 | 仪表盘改造 | dashboard_service改为医生视角 | Dashboard页改造 |
| 11-14 | 联调+优化 | 采集性能优化+异常处理 | 数据展示优化+空状态 |

**交付物**：医生能看到自己的GEO率/AEO率，能手动刷新数据

### 第三阶段：内容管理+创作入口（第5-6周）

| 天 | 任务 | 后端 | 前端 |
|---|---|---|---|
| 1-2 | 实体一致性校验 | entity_validator.py+content API加校验接口 | |
| 3-4 | 我的文章改造 | content加author_id/semantic_id/status+按用户过滤 | Content页改造+复制+一致性标记 |
| 5-6 | 创作中心 | config加跳转URL+生成计数 | Create页+文章/视频卡片+语义选择+平台选择+跳转 |
| 7-10 | 付费体系 | subscription模型+API中间件+免费额度计数 | 免费/付费UI控制+数据页付费提示+额度显示 |
| 11-14 | 联调+全流程测试 | | |

**交付物**：医生能选语义→跳文章工具→回来看文章→看数据，完整闭环

### 第四阶段：优化+上线（第7-8周）

- 适配器合并去重
- CORS收紧+JWT全路由覆盖
- 数据导出（医生个人报告）
- 性能优化（采集异步化）
- 安全审计
- 部署文档

---

## 11. 风险与注意事项

### 11.1 技术风险

| 风险 | 影响 | 应对 |
|---|---|---|
| GEO/AEO解析准确率低 | 数据不可信，医生不买单 | 先用规则+正则，积累数据后用LLM做二次校验；明确标注"检测基于AI回答解析，仅供参考" |
| 语义生成质量不稳定 | 生成的问题不接地气 | 精心设计system_prompt+人工审核前几批+模板兜底 |
| 文章工具跳转后数据回传断裂 | 文章数统计不准 | 短期用医生手动记录，中期和文章工具团队对接回调API |
| SQLite并发锁 | 多用户同时刷新时卡顿 | 早期用户量小可接受，超过50并发时迁移PostgreSQL |
| AI平台API限流 | 采集失败 | 串行+延迟+重试，当前设计已考虑 |

### 11.2 产品风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 医生觉得"这就是SEO换皮" | 不愿付费 | 对外不讲技术概念，只讲"患者用AI问的时候能推荐你"；用真实数据证明效果 |
| 现成文章/视频工具对接不畅 | 创作入口形同虚设 | 先把跳转做通（哪怕只是打开工具首页），后续再深化参数传递和回传 |
| 免费用户转化低 | 商业模式跑不通 | 免费给1次文章生成+看语义，数据页强提示付费价值；用GEO/AEO数据做付费钩子 |
| 视频工具"待定" | 创作中心缺一块 | 先显示"敬请期待"，不阻塞主流程 |

### 11.3 注意事项

1. **不要自己做文章生成器**——思维导图和录音都明确文章工具已经现成，GEO后台只做跳转和管理
2. **不要搞复杂的本体论/知识图谱**——思维导图里的"语义"就是问题，不是概念图谱
3. **实体一致性是核心壁垒**——这是思维导图反复强调的，AI会因为信息混乱而降权，这个校验功能要做好
4. **监测维度是医生姓名，不是公司品牌**——所有采集逻辑都要围绕医生个人
5. **付费体系要先做**——免费1次+付费看数据，这是商业模式的基础，不能后补
6. **GEO/AEO的定义要对内统一**——GEO=被推荐进列表，AEO=被引用为答案，不要混淆
7. **前端隐藏不等于删除**——竞品/知识库/RAG的代码先保留，菜单不显示，远期运营端可能用

---

## 附录：关键文件改动速查表

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `app/models/doctor.py` | 新增 | 医生Profile模型 |
| `app/models/semantic.py` | 新增 | 语义库模型 |
| `app/models/article.py` | 新增 | 文章草稿模型 |
| `app/models/subscription.py` | 新增 | 订阅模型 |
| `app/models/user.py` | 修改 | 加phone/avatar，role默认doctor |
| `app/models/monitor.py` | 修改 | 加detect_type/semantic_id/recommend_count/cite_count |
| `app/models/content.py` | 修改 | 加author_id/semantic_id/status/entity_consistent |
| `app/engines/semantic_generator.py` | 新增 | 语义自动生成引擎 |
| `app/engines/geo_aeo_analyzer.py` | 新增 | GEO/AEO解析引擎 |
| `app/engines/entity_validator.py` | 新增 | 实体一致性校验引擎 |
| `app/engines/collector.py` | 修改 | 采集目标改为医生+语义，用新解析器 |
| `app/adapters/openai_compatible.py` | 新增 | 统一适配器，替代三份重复 |
| `app/adapters/deepseek.py` | 废弃 | 合并到统一适配器 |
| `app/adapters/glm.py` | 废弃 | 合并到统一适配器 |
| `app/adapters/minimax.py` | 废弃 | 合并到统一适配器 |
| `app/adapters/factory.py` | 修改 | 用统一适配器 |
| `app/api/doctor.py` | 新增 | 医生Profile API |
| `app/api/semantic.py` | 新增 | 语义库API |
| `app/api/monitor.py` | 修改 | 加user_id过滤+GEO/AEO维度 |
| `app/api/content.py` | 修改 | 加author_id过滤+实体校验接口 |
| `app/deps.py` | 新增 | JWT鉴权依赖注入 |
| `app/main.py` | 修改 | 注册新路由+CORS收紧 |
| `app/config.py` | 修改 | 加ALLOWED_ORIGINS/ARTICLE_TOOL_URL等 |
| `app/services/dashboard_service.py` | 修改 | 医生视角统计 |
| `frontend/src/pages/Profile.tsx` | 新增 | 医生Profile页 |
| `frontend/src/pages/Semantic.tsx` | 新增 | 语义库页 |
| `frontend/src/pages/Create.tsx` | 新增 | 创作中心页 |
| `frontend/src/pages/DataCenter.tsx` | 新增 | GEO/AEO数据中心 |
| `frontend/src/pages/Dashboard.tsx` | 修改 | 医生数据概览 |
| `frontend/src/pages/Content.tsx` | 修改 | 我的文章 |
| `frontend/src/components/Layout.tsx` | 修改 | 菜单重构 |
| `frontend/src/router/index.tsx` | 修改 | 新路由+守卫 |
| `frontend/src/store/useStore.ts` | 修改 | 加profile/subscription/semantics |
| `frontend/src/api/index.ts` | 修改 | 加doctor/semantic/article API |
