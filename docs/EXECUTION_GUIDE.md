# GEO 项目升级执行手册

> **本文档是新 session 执行的唯一依据。** 每个任务单元有明确的输入文件、输出文件、代码级步骤和验证标准。执行中发现方案遗漏或错误，立即停止并记录问题，不要自行猜测修改。

---

## 0. 执行前必读

### 0.1 你要做什么

基于芳草AI超级员工的功能对标，对 GEO 项目进行架构底座修复 + 内容生产闭环升级。具体执行：
- **P0 全部**：架构底座修复（6个任务单元）
- **P1 部分**：内容机会识别 + 文章生成引擎升级（2个任务单元）
- **附加**：生图适配器框架（配置项留空，不实际接入API）

### 0.2 你不要做什么

- 不做 design-v2 的完整 Workspace 数据迁移（旧表不加 workspace 过滤）
- 不做 MonitorRun/Observation/Analysis 拆表（沿用现有 MonitorRecord 表，只加字段）
- 不做客资CRM、智能体框架、视频生成、矩阵发布、AI客服（这些是P2/P3，不在本次范围）
- 不删除任何旧表、旧字段、旧API
- 不修改现有认证机制（IAM JWT）
- 不引入微服务、Kafka、K8s、Alembic

### 0.3 执行纪律

1. **按顺序执行**：T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09，不要跳步
2. **每步验证**：每个任务单元完成后必须运行验证步骤，通过后才继续
3. **记录问题**：发现方案与实际代码不符，在文档末尾"问题记录"区追加，不要改方案
4. **不猜代码**：不确定的字段名/方法名，先用 Read 工具确认，不要凭印象写
5. **语法检查**：每个 Python 文件写完后运行 `python -c "import 模块名"` 确认无语法错误

---

## 1. 项目当前状态快照

### 1.1 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 后端 | Python FastAPI + SQLAlchemy + SQLite | Python 3.14（当前环境） |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + ECharts + Zustand | — |
| 认证 | IAM SSO + JWT | — |
| 定时任务 | APScheduler（在API进程内运行） | — |
| AI平台 | GLM、MiniMax（已配置）；DeepSeek（已失效）；豆包/通义（预留未配置） | — |

### 1.2 后端目录结构（关键文件）

```
backend/app/
├── main.py              # FastAPI入口，注册18个路由，lifespan中启动APScheduler
├── config.py            # 配置管理（pydantic-settings，从.env读取）
├── database.py          # 数据库连接（SQLite）
├── deps.py              # 依赖注入（get_current_user_id，基于IAM JWT）
├── models/              # 15个数据模型
│   ├── __init__.py      # 模型导出（必须在这里注册新模型）
│   ├── monitor.py       # MonitorRecord（监测事实表，GEO/AEO数据都存在这里）
│   ├── article.py       # ArticleDraft（文章草稿）
│   ├── distribution.py  # ArticleDistribution（文章分发记录）
│   ├── semantic.py      # Semantic（语义库）
│   ├── doctor.py        # DoctorProfile（医生资料）
│   ├── user.py          # User（用户表）
│   └── ...              # 其他旧模型（question/content/knowledge/competitor等）
├── api/                 # 18个API路由文件
│   ├── __init__.py      # 路由导出（必须在这里注册新路由）
│   ├── geo.py           # GEO/AEO数据API（/refresh是同步阻塞的，需要改）
│   ├── article.py       # 文章管理API
│   ├── distribution.py  # 分发记录API
│   ├── semantic.py      # 语义库API
│   ├── monitor.py       # 监测中心API（采集接口也是同步的）
│   ├── template.py      # 文章模板API（调用article_template_engine）
│   └── ...
├── engines/             # 核心引擎
│   ├── collector.py     # 采集引擎（串行执行，在API进程内调用）
│   ├── geo_aeo_analyzer.py  # GEO/AEO分析器（纯正则，有bug需要修）
│   ├── parser.py        # 品牌提及解析器（纯正则）
│   ├── article_template.py  # 文章模板引擎（纯字符串拼接，质量低）
│   ├── semantic_generator.py # 语义生成引擎（LLM+模板兜底）
│   ├── rag.py           # RAG问答引擎
│   ├── vector.py        # 向量引擎（纯Python n-gram）
│   └── entity_validator.py  # 实体一致性校验
├── adapters/            # AI平台适配器
│   ├── base.py          # BaseAdapter抽象类
│   ├── factory.py       # 适配器工厂
│   ├── openai_compatible.py  # OpenAI兼容适配器（GLM/MiniMax/DeepSeek都用这个）
│   └── ...
├── services/            # 业务服务
│   ├── iam_service.py   # IAM认证服务
│   ├── dashboard_service.py
│   ├── export_service.py
│   └── monitor_service.py
└── schemas/             # Pydantic模型（都在__init__.py里）
```

### 1.3 前端目录结构（关键文件）

```
frontend/src/
├── main.tsx             # 入口
├── App.tsx              # 根组件
├── api/index.ts         # 所有API封装（在这里加新API）
├── router/index.tsx     # 路由配置（在这里加新路由）
├── store/useStore.ts    # Zustand状态管理（已有doctorProfile/semantics等）
├── components/Layout.tsx  # 主布局（左侧菜单只有5项，顶部Header有刷新/铃铛/头像）
├── styles/global.css    # 全局样式
└── pages/               # 页面组件
    ├── Dashboard.tsx    # 数据概览
    ├── Semantic.tsx     # 语义库
    ├── ContentHub.tsx   # 内容中心（28KB，内含文章列表等Tab）
    ├── DataCenter.tsx   # 数据中心
    ├── Monitor.tsx      # 监测中心（菜单中没有入口，但文件存在）
    ├── Knowledge.tsx    # 知识库（菜单中没有入口）
    ├── RAGChat.tsx      # RAG问答（菜单中没有入口）
    ├── Profile.tsx      # 个人资料
    ├── Settings.tsx     # 设置
    └── SSOCallback.tsx  # SSO回调
```

### 1.4 数据库状态

- 数据库文件：`backend/data/geo.db`（SQLite，约612KB）
- 备份文件：`backend/data/geo.db.backup_20260913_141723`（454KB）
- 表数量：约15张
- **执行前务必备份**：`copy backend\data\geo.db backend\data\geo.db.backup_before_upgrade`

### 1.5 认证机制

- 所有需要登录的API接口使用 `Depends(get_current_user_id)` 获取当前用户ID
- `get_current_user_id` 从 `Authorization: Bearer <token>` 头提取JWT，调用 `IAMService.verify_jwt(token)` 验证
- 新API如果需要登录，必须加这个依赖
- 本地开发时如果IAM未配置，可以临时用 `user_id=1` 测试（但不要提交这种代码）

---

## 2. 决策记录（6个决策点的最终结论）

| # | 决策点 | 最终结论 |
|---|---|---|
| 1 | Workspace迁移 | **渐进式三步走**：P0建`geo_workspace`+`geo_workspace_member`表，为每个用户创建个人Workspace；所有新表写入时自动填`workspace_id`；旧表不动，后续独立迁移 |
| 2 | 生图/生视频API | **生图只做框架+配置项留空**（Seedream Key暂时没有）；生视频不做；混剪/数字人不做 |
| 3 | 执行范围 | **P0全部（T01-T06）+ P1的T07（内容机会）+T08（文章生成升级）+生图框架**；不做客资CRM、智能体框架、P2/P3 |
| 4 | 数据库迁移 | **手写幂等迁移脚本** `backend/scripts/migrate_v2.py`，不引入Alembic；新增表用`CREATE TABLE IF NOT EXISTS`，新增列用`PRAGMA table_info`检查后`ALTER TABLE ADD COLUMN` |
| 5 | 前端菜单布局 | **任务中心放顶部Header**（铃铛旁加任务图标）；客资中心不做（不在本次范围）；账号管理不做；AI客服不做；内容机会放在ContentHub的Tab里 |
| 6 | LLM分析器 | **混合分层**：实体提及/排名用规则（修复bug）；推荐关系/情感/引用关联用LLM（只对已提及记录调用）；LLM调用失败降级为规则判断 |

---

## 3. 全局约定

### 3.1 代码风格

- Python：遵循现有代码风格，4空格缩进，双引号字符串，类型注解
- 前端：TypeScript，函数组件，Ant Design 5，现有`request`封装的axios
- 所有新文件头部加 `"""模块说明"""` 或 `// 模块说明`

### 3.2 API响应格式

统一使用：
```python
{"code": 0, "message": "success", "data": {...}}
```
错误时：
```python
raise HTTPException(status_code=400, detail="错误说明")
```
（现有代码就是这个风格，保持一致）

### 3.3 数据库迁移约定

- 所有表结构变更通过 `backend/scripts/migrate_v2.py` 执行
- 迁移脚本是幂等的，可以重复运行
- 新增表：`CREATE TABLE IF NOT EXISTS`
- 新增列：先 `PRAGMA table_info(表名)` 检查，不存在才 `ALTER TABLE 表名 ADD COLUMN 列名 类型`
- 初始化数据：先查询是否存在，不存在才插入
- 迁移记录：`geo_schema_version` 表记录版本号和执行时间

### 3.4 新表字段约定

所有新业务表必须包含：
- `id` — 主键，Integer，autoincrement
- `workspace_id` — Integer，nullable=True（预留，P0阶段从用户默认Workspace获取）
- `created_at` — DateTime，`server_default=func.now()`
- 其他业务字段按需添加

### 3.5 时间字段约定

- 数据库存储用 `DateTime(timezone=True)`，`server_default=func.now()`
- API返回时用 `.isoformat()` 转字符串
- 不要用字符串存日期（现有`detect_date`是字符串，不改）

---

## 4. 任务单元详细执行步骤

---

### T01：Workspace基础表 + AsyncTask模型 + Worker框架

**目标**：建立异步任务的基础设施。新建Workspace表（为未来迁移铺路）、AsyncTask表（所有异步任务的统一载体）、Worker进程框架（从数据库轮询任务并执行）。

**前置读取**（执行前必须先Read这些文件确认当前状态）：
1. `backend/app/models/__init__.py` — 确认模型导出方式
2. `backend/app/database.py` — 确认Base和get_db
3. `backend/app/main.py` — 确认当前lifespan和路由注册
4. `backend/app/config.py` — 确认配置类结构

#### 步骤 1：新建数据库迁移脚本

**新建文件**：`backend/scripts/migrate_v2.py`

```python
"""
GEO V2 数据库迁移脚本（幂等，可重复运行）
用法：cd backend && python -m scripts.migrate_v2
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "geo.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_table(conn, table_name: str, create_sql: str):
    """幂等创建表"""
    conn.execute(create_sql)
    conn.commit()


def ensure_column(conn, table_name: str, column_name: str, column_def: str):
    """幂等添加列"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        conn.commit()
        print(f"  + 列 {table_name}.{column_name}")


def record_migration(conn, version: str):
    """记录迁移版本"""
    ensure_table(conn, "geo_schema_version", """
        CREATE TABLE IF NOT EXISTS geo_schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            executed_at TEXT NOT NULL
        )
    """)
    cursor = conn.execute("SELECT COUNT(*) FROM geo_schema_version WHERE version=?", (version,))
    if cursor.fetchone()[0] == 0:
        conn.execute("INSERT INTO geo_schema_version (version, executed_at) VALUES (?, ?)",
                     (version, datetime.now().isoformat()))
        conn.commit()
        print(f"  + 迁移记录 {version}")


def migrate():
    conn = get_conn()
    print("开始数据库迁移...")

    # ===== 1. Workspace 相关表 =====
    print("[1/5] Workspace 相关表")
    ensure_table(conn, "geo_workspace", """
        CREATE TABLE IF NOT EXISTS geo_workspace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT 'personal',
            status TEXT NOT NULL DEFAULT 'active',
            timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
            locale TEXT NOT NULL DEFAULT 'zh-CN',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    ensure_table(conn, "geo_workspace_member", """
        CREATE TABLE IF NOT EXISTS geo_workspace_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'owner',
            status TEXT NOT NULL DEFAULT 'active',
            joined_at TEXT DEFAULT (datetime('now')),
            UNIQUE(workspace_id, user_id)
        )
    """)

    # ===== 2. AsyncTask 表 =====
    print("[2/5] AsyncTask 表")
    ensure_table(conn, "geo_async_task", """
        CREATE TABLE IF NOT EXISTS geo_async_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            progress INTEGER DEFAULT 0,
            progress_message TEXT DEFAULT '',
            payload_json TEXT DEFAULT '{}',
            result_json TEXT DEFAULT '{}',
            error_message TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT,
            finished_at TEXT
        )
    """)
    # 索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_status ON geo_async_task(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_type ON geo_async_task(task_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_async_task_workspace ON geo_async_task(workspace_id)")
    conn.commit()

    # ===== 3. 现有表加列 =====
    print("[3/5] 现有表加列")
    # MonitorRecord 加证据字段
    ensure_column(conn, "geo_monitor_record", "mention_evidence", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_monitor_record", "recommendation_evidence", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_monitor_record", "citation_urls", "TEXT DEFAULT '[]'")
    ensure_column(conn, "geo_monitor_record", "analyzer_version", "TEXT DEFAULT 'rule_v1'")
    ensure_column(conn, "geo_monitor_record", "raw_sources_json", "TEXT DEFAULT '[]'")
    ensure_column(conn, "geo_monitor_record", "is_recommendation", "INTEGER DEFAULT 0")

    # ArticleDistribution 加状态机字段
    ensure_column(conn, "geo_article_distribution", "scheduled_at", "TEXT")
    ensure_column(conn, "geo_article_distribution", "failed_reason", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_article_distribution", "retry_count", "INTEGER DEFAULT 0")
    ensure_column(conn, "geo_article_distribution", "publish_mode", "TEXT DEFAULT 'manual'")
    ensure_column(conn, "geo_article_distribution", "external_task_id", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_article_distribution", "verified_at", "TEXT")

    # ===== 4. 为现有用户创建默认 Workspace =====
    print("[4/5] 初始化默认 Workspace")
    cursor = conn.execute("SELECT id, username FROM geo_user")
    users = cursor.fetchall()
    for user_id, username in users:
        # 检查是否已有owner角色的workspace
        cursor2 = conn.execute(
            "SELECT w.id FROM geo_workspace w JOIN geo_workspace_member m ON w.id=m.workspace_id "
            "WHERE m.user_id=? AND m.role='owner'", (user_id,))
        if cursor2.fetchone() is None:
            ws_name = f"{username or '用户'}的个人工作台"
            conn.execute("INSERT INTO geo_workspace (name, type, created_by) VALUES (?, 'personal', ?)",
                         (ws_name, user_id))
            ws_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO geo_workspace_member (workspace_id, user_id, role) VALUES (?, ?, 'owner')",
                         (ws_id, user_id))
            print(f"  + 为用户 {user_id}({username}) 创建 Workspace {ws_id}")
    conn.commit()

    # ===== 5. 记录迁移版本 =====
    print("[5/5] 记录迁移版本")
    record_migration(conn, "v2.0_base")

    print("✅ 数据库迁移完成")
    conn.close()


if __name__ == "__main__":
    migrate()
```

**验证**：
```bash
cd backend
python -m scripts.migrate_v2
# 应该输出：开始数据库迁移... → ✅ 数据库迁移完成
# 重复运行一次，应该不报错（幂等），且没有重复的"+ 列"输出
```

#### 步骤 2：新建 Workspace 模型

**新建文件**：`backend/app/models/workspace.py`

```python
"""Workspace 模型 — 业务数据归属边界（P0阶段只建表+基础查询，不强制过滤）"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Workspace(Base):
    """工作空间"""
    __tablename__ = "geo_workspace"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), default="")
    type = Column(String(20), default="personal")  # personal/clinic/hospital
    status = Column(String(20), default="active")    # active/suspended/archived
    timezone = Column(String(50), default="Asia/Shanghai")
    locale = Column(String(20), default="zh-CN")
    created_by = Column(Integer, ForeignKey("geo_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WorkspaceMember(Base):
    """工作空间成员"""
    __tablename__ = "geo_workspace_member"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uix_workspace_user'),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), nullable=False, index=True)
    role = Column(String(20), default="owner")  # owner/editor/reviewer/viewer
    status = Column(String(20), default="active")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### 步骤 3：新建 AsyncTask 模型

**新建文件**：`backend/app/models/task.py`

```python
"""异步任务模型 — 所有耗时操作的统一载体（采集/生图/生视频/智能体执行等）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AsyncTask(Base):
    """异步任务"""
    __tablename__ = "geo_async_task"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=True, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    # geo_refresh / monitor_collect / article_generate / image_generate / video_generate / agent_chat
    status = Column(String(20), default="queued", index=True)
    # queued/running/succeeded/failed/cancelled
    progress = Column(Integer, default=0)  # 0-100
    progress_message = Column(String(500), default="")
    payload_json = Column(Text, default="{}")   # 任务参数（JSON字符串）
    result_json = Column(Text, default="{}")    # 任务结果（JSON字符串）
    error_message = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("geo_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
```

#### 步骤 4：注册新模型

**修改文件**：`backend/app/models/__init__.py`

先 Read 这个文件确认当前内容，然后在文件末尾添加（在现有导出之后）：

```python
# ===== V2 新增模型 =====
from app.models.workspace import Workspace, WorkspaceMember
from app.models.task import AsyncTask

__all__ = [
    # ... 现有的导出列表保持不变 ...
    # 在现有列表末尾追加：
    "Workspace",
    "WorkspaceMember",
    "AsyncTask",
]
```

**注意**：不要删除现有的任何导入或导出，只追加。

**验证**：
```bash
cd backend
python -c "from app.models import Workspace, WorkspaceMember, AsyncTask; print('模型导入OK')"
```

#### 步骤 5：新建 Worker 框架

**新建目录**：`backend/app/worker/`

**新建文件**：`backend/app/worker/__init__.py`
```python
"""Worker 进程框架 — 从数据库轮询异步任务并执行"""
```

**新建文件**：`backend/app/worker/task_registry.py`

```python
"""任务类型 → 处理函数的注册映射"""
from typing import Callable, Dict
from sqlalchemy.orm import Session
from app.models.task import AsyncTask

# 任务处理函数签名：def handler(db: Session, task: AsyncTask) -> dict
TaskHandler = Callable[[Session, AsyncTask], dict]

_task_handlers: Dict[str, TaskHandler] = {}


def register_handler(task_type: str, handler: TaskHandler):
    """注册任务处理函数"""
    _task_handlers[task_type] = handler


def get_handler(task_type: str) -> TaskHandler | None:
    """获取任务处理函数"""
    return _task_handlers.get(task_type)


def get_all_task_types() -> list[str]:
    """获取所有已注册的任务类型"""
    return list(_task_handlers.keys())
```

**新建文件**：`backend/app/worker/collector_tasks.py`

```python
"""采集相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.engines.collector import CollectorEngine
from app.worker.task_registry import register_handler

logger = logging.getLogger(__name__)


def handle_geo_refresh(db: Session, task: AsyncTask) -> dict:
    """处理 GEO/AEO 全量刷新任务"""
    payload = json.loads(task.payload_json or "{}")
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("payload 中缺少 user_id")

    collector = CollectorEngine(db)
    result = collector.collect_all_semantics(user_id, detect_round=99)
    return result


def handle_monitor_collect(db: Session, task: AsyncTask) -> dict:
    """处理品牌监测采集任务"""
    payload = json.loads(task.payload_json or "{}")
    question_id = payload.get("question_id")
    detect_round = payload.get("detect_round", 1)

    collector = CollectorEngine(db)
    if question_id:
        records = collector.collect_single_question_now(question_id)
        return {"total": 1, "success": 1, "records_count": len(records)}
    else:
        return collector.collect_all(detect_round=detect_round)


# 注册任务处理函数
register_handler("geo_refresh", handle_geo_refresh)
register_handler("monitor_collect", handle_monitor_collect)
```

**新建文件**：`backend/app/worker/worker.py`

```python
"""
Worker 主进程 — 从数据库轮询 queued 状态的任务并执行。

启动方式：
    cd backend
    set APP_ROLE=worker
    python -m app.worker.worker

注意：
- API 进程不要启动 Worker（通过 APP_ROLE 环境变量区分）
- Worker 单进程运行，不做多实例并发（避免任务重复执行）
- 任务执行超时默认 600 秒，超时后标记为 failed
"""
import os
import sys
import time
import json
import logging
import signal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.task import AsyncTask
from app.worker.task_registry import get_handler, get_all_task_types
# 导入任务处理模块以触发注册
import app.worker.collector_tasks  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("worker")

# 全局运行标志
_running = True
TASK_TIMEOUT_SECONDS = 600  # 任务超时时间
POLL_INTERVAL = 3  # 轮询间隔（秒）


def signal_handler(signum, frame):
    """优雅退出"""
    global _running
    logger.info(f"收到信号 {signum}，准备退出...")
    _running = False


def claim_next_task(db: Session) -> AsyncTask | None:
    """认领下一个 queued 任务（先到先得，单Worker模式下直接取第一个）"""
    task = db.query(AsyncTask).filter(
        AsyncTask.status == "queued"
    ).order_by(AsyncTask.created_at.asc()).first()

    if task:
        task.status = "running"
        task.started_at = datetime.now()
        task.progress_message = "任务开始执行"
        db.commit()
        db.refresh(task)
        logger.info(f"认领任务 #{task.id} (type={task.task_type})")
    return task


def execute_task(db: Session, task: AsyncTask):
    """执行单个任务"""
    handler = get_handler(task.task_type)
    if not handler:
        raise ValueError(f"未注册的任务类型: {task.task_type}，已注册类型: {get_all_task_types()}")

    result = handler(db, task)
    return result


def complete_task(db: Session, task: AsyncTask, result: dict = None, error: str = None):
    """完成任务（成功或失败）"""
    if error:
        task.status = "failed"
        task.error_message = error[:2000] if error else ""
        task.progress_message = "执行失败"
        logger.error(f"任务 #{task.id} 失败: {error[:200]}")
    else:
        task.status = "succeeded"
        task.progress = 100
        task.progress_message = "执行完成"
        task.result_json = json.dumps(result or {}, ensure_ascii=False)
        logger.info(f"任务 #{task.id} 完成")

    task.finished_at = datetime.now()
    db.commit()


def recover_stuck_tasks(db: Session):
    """恢复卡住的任务（running超过超时时间的标记为failed）"""
    timeout_threshold = datetime.now() - timedelta(seconds=TASK_TIMEOUT_SECONDS)
    stuck_tasks = db.query(AsyncTask).filter(
        AsyncTask.status == "running",
        AsyncTask.started_at < timeout_threshold
    ).all()

    for task in stuck_tasks:
        logger.warning(f"任务 #{task.id} 超时（started_at={task.started_at}），标记为failed")
        task.status = "failed"
        task.error_message = f"任务执行超时（>{TASK_TIMEOUT_SECONDS}秒）"
        task.finished_at = datetime.now()
    db.commit()


def main():
    """Worker 主循环"""
    global _running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 50)
    logger.info("GEO Worker 启动")
    logger.info(f"已注册任务类型: {get_all_task_types()}")
    logger.info(f"轮询间隔: {POLL_INTERVAL}秒 | 任务超时: {TASK_TIMEOUT_SECONDS}秒")
    logger.info("=" * 50)

    while _running:
        try:
            db = SessionLocal()

            # 1. 恢复卡住的任务
            recover_stuck_tasks(db)

            # 2. 认领并执行任务
            task = claim_next_task(db)
            if task:
                try:
                    result = execute_task(db, task)
                    complete_task(db, task, result=result)
                except Exception as e:
                    db.rollback()
                    complete_task(db, task, error=f"{type(e).__name__}: {str(e)}")
            else:
                # 没有任务，等待
                time.sleep(POLL_INTERVAL)

            db.close()

        except Exception as e:
            logger.error(f"Worker 主循环异常: {type(e).__name__}: {e}")
            time.sleep(POLL_INTERVAL)

    logger.info("Worker 已退出")


if __name__ == "__main__":
    main()
```

#### 步骤 6：修改 main.py，区分 API 和 Worker 角色

**修改文件**：`backend/app/main.py`

先 Read 确认当前内容，然后做以下修改：

**修改点 1**：在文件顶部导入区添加环境变量判断：
```python
import os
APP_ROLE = os.getenv("APP_ROLE", "api")  # api / worker
```

**修改点 2**：修改 `lifespan` 函数，只有 API 角色才启动定时任务：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 启动 {settings.APP_NAME} v1.0.0 (role={APP_ROLE})")
    print(f"📦 环境: {settings.APP_ENV}")
    print(f"🔧 已启用平台: {settings.get_enabled_platforms()}")
    init_db()
    print("✅ 数据库初始化完成")

    if APP_ROLE == "api":
        # 启动定时任务（每天上午10点执行采集）
        scheduler.add_job(
            scheduled_collect,
            'cron',
            hour=10,
            minute=0,
            id='daily_collect',
            replace_existing=True
        )
        scheduler.start()
        print("⏰ 定时任务已启动（每天10:00自动采集）")
    else:
        print("⏭️  Worker 模式，不启动定时任务和HTTP服务")

    yield

    # 关闭时停止调度器
    if APP_ROLE == "api":
        scheduler.shutdown()
    print("👋 应用关闭")
```

**修改点 3**：在文件末尾的 `if __name__ == "__main__":` 之前，添加 Worker 启动入口：
```python
def run_worker():
    """以 Worker 角色启动"""
    from app.worker.worker import main as worker_main
    worker_main()


if __name__ == "__main__":
    if APP_ROLE == "worker":
        run_worker()
    else:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG
        )
```

**验证**：
```bash
cd backend
# 1. 语法检查
python -c "from app.main import app; print('main导入OK')"
python -c "from app.worker.worker import main; print('worker导入OK')"

# 2. 启动 API（确认不报错，定时任务正常启动）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 看到 "🚀 启动 GEO Monitor v1.0.0 (role=api)" 和 "⏰ 定时任务已启动"
# Ctrl+C 停止

# 3. 启动 Worker（确认不报错，进入轮询状态）
set APP_ROLE=worker
python -m app.worker.worker
# 看到 "GEO Worker 启动" 和 "已注册任务类型: ['geo_refresh', 'monitor_collect']"
# Ctrl+C 停止（应该看到 "收到信号，准备退出..." 和 "Worker 已退出"）
```

#### T01 完成标准

- [ ] 数据库迁移脚本运行成功，新增了 `geo_workspace`、`geo_workspace_member`、`geo_async_task`、`geo_schema_version` 表
- [ ] `geo_monitor_record` 表新增了 7 个列（mention_evidence 等）
- [ ] `geo_article_distribution` 表新增了 6 个列（scheduled_at 等）
- [ ] 每个现有用户都有了一个 owner 角色的 Workspace
- [ ] Workspace、WorkspaceMember、AsyncTask 三个模型可以正常导入
- [ ] Worker 进程可以启动，显示已注册的任务类型
- [ ] API 进程启动时 role=api，Worker 进程启动时 role=worker
- [ ] 迁移脚本可以重复运行（幂等），不报错

---

### T02：Distribution 状态机升级

**目标**：将 ArticleDistribution 从简单的"发布记录"升级为带完整状态流转的发布任务管理。

**前置读取**：
1. `backend/app/models/distribution.py` — 确认当前字段
2. `backend/app/api/distribution.py` — 确认当前API
3. `backend/app/schemas/__init__.py` — 确认是否有 Distribution 的 schema

#### 步骤 1：新建 Distribution 服务层

**新建文件**：`backend/app/services/distribution_service.py`

```python
"""
Distribution 状态机服务 — 管理文章分发记录的状态流转。

状态流转图：
    draft → scheduled → processing → published
                          ↘ failed → (retry) → processing
    published → removed
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.distribution import ArticleDistribution

logger = logging.getLogger(__name__)

# 合法的状态流转：{当前状态: [允许的下一个状态]}
VALID_TRANSITIONS = {
    "draft": ["scheduled", "removed"],
    "scheduled": ["processing", "removed"],
    "processing": ["published", "failed"],
    "published": ["removed"],
    "failed": ["processing", "removed"],  # failed 可以 retry（回到 processing）
    "removed": [],
}

# 终态（不需要再操作的状态）
FINAL_STATES = ["published", "removed"]


class DistributionService:
    @staticmethod
    def get_or_404(db: Session, dist_id: int, user_id: int) -> ArticleDistribution:
        dist = db.query(ArticleDistribution).filter(
            ArticleDistribution.id == dist_id,
            ArticleDistribution.user_id == user_id
        ).first()
        if not dist:
            raise HTTPException(status_code=404, detail="分发记录不存在")
        return dist

    @staticmethod
    def transition(db: Session, dist: ArticleDistribution, target_status: str,
                   note: str = "", publish_url: str = "") -> ArticleDistribution:
        """
        状态流转（带合法性校验）

        Args:
            dist: 分发记录
            target_status: 目标状态
            note: 备注（失败原因等）
            publish_url: 发布URL（仅 published 状态时填写）
        """
        current = dist.status
        allowed = VALID_TRANSITIONS.get(current, [])

        if target_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"非法状态流转: {current} → {target_status}，允许的目标状态: {allowed}"
            )

        dist.status = target_status

        if target_status == "scheduled":
            dist.scheduled_at = datetime.now()
        elif target_status == "processing":
            dist.retry_count = (dist.retry_count or 0) + 1 if current == "failed" else (dist.retry_count or 0)
            dist.progress_message = "正在发布..." if hasattr(dist, 'progress_message') else ""
        elif target_status == "published":
            dist.publish_url = publish_url or dist.publish_url
            dist.published_at = datetime.now()
            dist.verified_at = None  # 待验证
        elif target_status == "failed":
            dist.failed_reason = note[:500] if note else dist.failed_reason
        elif target_status == "removed":
            pass

        if note:
            dist.note = (dist.note or "") + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}"

        db.commit()
        db.refresh(dist)
        logger.info(f"分发记录 #{dist.id} 状态流转: {current} → {target_status}")
        return dist

    @staticmethod
    def schedule(db: Session, dist: ArticleDistribution, scheduled_at: datetime = None) -> ArticleDistribution:
        """计划发布"""
        if scheduled_at:
            dist.scheduled_at = scheduled_at
        return DistributionService.transition(db, dist, "scheduled", note="计划发布")

    @staticmethod
    def start_processing(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """开始发布处理"""
        return DistributionService.transition(db, dist, "processing", note="开始发布")

    @staticmethod
    def mark_published(db: Session, dist: ArticleDistribution, publish_url: str) -> ArticleDistribution:
        """标记发布成功"""
        return DistributionService.transition(db, dist, "published",
                                               note=f"发布成功，URL: {publish_url}",
                                               publish_url=publish_url)

    @staticmethod
    def mark_failed(db: Session, dist: ArticleDistribution, reason: str) -> ArticleDistribution:
        """标记发布失败"""
        return DistributionService.transition(db, dist, "failed", note=f"发布失败: {reason}")

    @staticmethod
    def retry(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """重试发布（从 failed 回到 processing）"""
        return DistributionService.transition(db, dist, "processing", note="重试发布")

    @staticmethod
    def remove(db: Session, dist: ArticleDistribution) -> ArticleDistribution:
        """移除（软删除，不实际删除记录）"""
        return DistributionService.transition(db, dist, "removed", note="移除记录")
```

#### 步骤 2：修改 Distribution API

**修改文件**：`backend/app/api/distribution.py`

完整替换为以下内容（保留原有接口，新增状态流转接口）：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.deps import get_current_user_id
from app.models.distribution import ArticleDistribution
from app.models.article import ArticleDraft
from app.services.distribution_service import DistributionService

router = APIRouter(prefix="/api/v1/distribution", tags=["文章分发"])


class DistributionCreate(BaseModel):
    article_id: int
    platform: str
    publish_url: str = ""
    status: str = "draft"  # 创建时默认 draft
    note: str = ""


class DistributionStatusUpdate(BaseModel):
    status: str  # scheduled / processing / published / failed / removed
    publish_url: str = ""
    note: str = ""


@router.get("", summary="获取分发记录列表")
def get_distributions(
    article_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDistribution).filter(ArticleDistribution.user_id == user_id)
    if article_id:
        query = query.filter(ArticleDistribution.article_id == article_id)
    if status:
        query = query.filter(ArticleDistribution.status == status)
    items = query.order_by(ArticleDistribution.created_at.desc()).all()
    return {"code": 0, "message": "success", "data": {"items": [
        {
            "id": d.id,
            "article_id": d.article_id,
            "platform": d.platform,
            "publish_url": d.publish_url,
            "status": d.status,
            "note": d.note,
            "publish_mode": d.publish_mode,
            "retry_count": d.retry_count,
            "failed_reason": d.failed_reason,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in items
    ]}}


@router.post("", summary="创建分发记录")
def create_distribution(
    data: DistributionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    article = db.query(ArticleDraft).filter(
        ArticleDraft.id == data.article_id, ArticleDraft.user_id == user_id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 校验状态合法性
    valid_statuses = ["draft", "scheduled", "processing", "published", "failed", "removed"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态: {data.status}，合法值: {valid_statuses}")

    dist = ArticleDistribution(
        user_id=user_id, article_id=data.article_id,
        platform=data.platform, publish_url=data.publish_url,
        status=data.status, note=data.note,
        publish_mode="manual",
    )
    if data.status == "published":
        dist.published_at = datetime.now()
    db.add(dist)
    db.commit()
    db.refresh(dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id}}


@router.patch("/{dist_id}/status", summary="状态流转（计划/开始/成功/失败/重试/移除）")
def update_status(
    dist_id: int,
    data: DistributionStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.transition(
        db, dist, data.status,
        note=data.note, publish_url=data.publish_url
    )
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status}}


@router.post("/{dist_id}/retry", summary="重试发布（failed → processing）")
def retry_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    dist = DistributionService.retry(db, dist)
    return {"code": 0, "message": "success", "data": {"id": dist.id, "status": dist.status, "retry_count": dist.retry_count}}


@router.delete("/{dist_id}", summary="删除分发记录（物理删除，仅 draft 状态允许）")
def delete_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    if dist.status != "draft":
        raise HTTPException(status_code=400, detail=f"仅 draft 状态的记录可以物理删除，当前状态: {dist.status}。请使用移除（removed）接口")
    db.delete(dist)
    db.commit()
    return {"code": 0, "message": "success"}
```

#### 步骤 3：注册 DistributionService（不需要，直接 import 即可）

#### T02 验证

```bash
cd backend
# 1. 语法检查
python -c "from app.services.distribution_service import DistributionService; print('service导入OK')"
python -c "from app.api.distribution import router; print('api导入OK')"

# 2. 启动 API，访问 /docs 确认新接口出现
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000/docs，找到 "文章分发" 分组
# 应该有：GET /api/v1/distribution, POST /api/v1/distribution,
#          PATCH /api/v1/distribution/{dist_id}/status,
#          POST /api/v1/distribution/{dist_id}/retry,
#          DELETE /api/v1/distribution/{dist_id}
```

#### T02 完成标准

- [ ] DistributionService 可以正常导入，状态流转校验逻辑正确
- [ ] API 新增了 PATCH /status、POST /retry 接口
- [ ] 非法状态流转返回 400 错误
- [ ] 非 draft 状态的记录不能物理删除
- [ ] 列表接口返回新增字段（publish_mode/retry_count/failed_reason/scheduled_at/verified_at）

---

### T03：GEO/AEO 分析器修复 + 证据字段保存

**目标**：修复现有分析器的3个bug（医院名单独命中、排名默认1、AEO无URL验证），引入LLM辅助判断推荐/情感/引用关联，保存证据片段。

**前置读取**：
1. `backend/app/engines/geo_aeo_analyzer.py` — 确认当前实现
2. `backend/app/engines/collector.py` — 确认 collect_one_semantic 方法
3. `backend/app/adapters/factory.py` — 确认适配器工厂
4. `backend/app/models/monitor.py` — 确认新增字段已加（T01迁移脚本已加）

#### 步骤 1：修复 geo_aeo_analyzer.py 的 bug

**修改文件**：`backend/app/engines/geo_aeo_analyzer.py`

**修改点 1**：修复 `_build_patterns`，医院名不能单独作为命中 pattern：
```python
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
```
**关键变化**：删除了 `if self.hospital and len(self.hospital) >= 4: patterns.append(re.compile(re.escape(self.hospital)))` 这一行——医院名单独出现不再算医生命中。

**修改点 2**：修复 `_extract_rank`，无法确定时返回 None：
```python
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
    # 按条目计数
    items = re.split(r'\n\s*\d+[\.、\)）]|\n\s*[-*•]\s', answer)
    for i, item in enumerate(items):
        for pattern in self.patterns:
            if pattern.search(item):
                return i if i > 0 else 1
    # 无法确定排名，返回 None（不再默认1）
    return None
```

**修改点 3**：修改 `analyze` 方法，rank 可能为 None：
```python
def analyze(self, answer: str) -> GEOAEOResult:
    if not answer or not answer.strip():
        return GEOAEOResult(False, None, False, 0.0, answer)
    # ... 其余逻辑不变 ...
    # 2. 提取GEO排名（可能为 None）
    geo_rank = self._extract_rank(answer, mention_pos)
    # ... 其余不变 ...
```

**修改点 4**：修改 `GEOAEOResult` dataclass，rank 允许 None：
```python
@dataclass
class GEOAEOResult:
    geo_mentioned: bool
    geo_rank: int | None        # 排名，None=未形成明确排序
    aeo_cited: bool
    aeo_confidence: float
    raw_answer: str
    # 新增字段（供LLM分析结果回填）
    is_recommendation: bool = False
    recommendation_evidence: str = ""
    mention_evidence: str = ""
    citation_urls: list = None
    sentiment: str = "neutral"
```

#### 步骤 2：新建 LLM 分析器

**新建文件**：`backend/app/engines/llm_analyzer.py`

```python
"""
LLM 辅助分析器 — 对已提及医生的记录，判断推荐关系、情感、引用URL关联。

设计原则：
- 只对第一层规则已确认"提及医生"的记录调用（节省成本）
- 输出结构化 JSON，方便解析和保存
- 调用失败时降级为规则判断（不阻塞采集）
- 低置信度结果标记 needs_review
"""
import json
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.adapters import adapter_factory

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """LLM分析结果"""
    is_recommendation: bool = False
    recommendation_evidence: str = ""
    sentiment: str = "neutral"  # positive/neutral/negative/mixed
    citation_urls: list = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    raw_response: str = ""


SYSTEM_PROMPT = """你是一个医疗AI回答分析专家。请分析给定的AI回答文本，判断其中关于目标医生的表述。

严格按以下 JSON 格式输出（不要输出任何其他文字）：
{
  "is_recommendation": true/false,
  "recommendation_evidence": "原文中表示推荐的那句话（如果没有则为空字符串）",
  "sentiment": "positive/neutral/negative/mixed",
  "citation_urls": ["回答中出现的所有URL（如果没有则为空数组）"],
  "confidence": 0.0-1.0之间的数字,
  "needs_review": true/false
}

判断规则：
1. is_recommendation：只有明确表示"推荐/建议选择/可以考虑/首选"等正向推荐关系才为true。
   - 普通提及、履历介绍、新闻报道 → false
   - "不建议选择/风险警示" → false
   - 用户问题中原样重复医生名 → false
2. sentiment：对目标医生的整体情感倾向。
3. citation_urls：提取回答中所有 http/https 开头的URL。
4. confidence：你对以上判断的置信度。
5. needs_review：如果判断不确定或回答内容模糊，设为true。
"""


class LLMAnalyzer:
    """LLM辅助分析器"""

    def __init__(self, platform_code: str = None):
        self.platform_code = platform_code

    def _get_adapter(self):
        if self.platform_code:
            return adapter_factory.get_adapter(self.platform_code)
        platforms = adapter_factory.get_enabled_platforms()
        if platforms:
            return adapter_factory.get_adapter(platforms[0])
        return None

    def analyze(self, raw_answer: str, doctor_name: str, hospital: str = "",
                department: str = "") -> LLMResult:
        """
        调用LLM分析回答。

        Args:
            raw_answer: AI原始回答文本
            doctor_name: 医生姓名
            hospital: 医院名称
            department: 科室名称

        Returns:
            LLMResult，调用失败时返回默认值（降级）
        """
        adapter = self._get_adapter()
        if not adapter:
            logger.warning("无可用AI平台，LLM分析降级为默认值")
            return LLMResult()

        user_prompt = f"""目标医生信息：
姓名：{doctor_name}
医院：{hospital or '未知'}
科室：{department or '未知'}

AI回答文本：
\"\"\"
{raw_answer[:3000]}
\"\"\"

请分析以上AI回答中关于目标医生的表述，按指定JSON格式输出。"""

        try:
            result = adapter.query(user_prompt, system_prompt=SYSTEM_PROMPT)
            if not result.success:
                logger.warning(f"LLM分析调用失败: {result.error}")
                return LLMResult()

            # 解析JSON响应（处理可能的markdown代码块包裹）
            response_text = result.answer.strip()
            # 去除 ```json ... ``` 包裹
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()

            data = json.loads(response_text)

            llm_result = LLMResult(
                is_recommendation=bool(data.get("is_recommendation", False)),
                recommendation_evidence=str(data.get("recommendation_evidence", ""))[:500],
                sentiment=str(data.get("sentiment", "neutral")),
                citation_urls=data.get("citation_urls", []) or [],
                confidence=float(data.get("confidence", 0.0)),
                needs_review=bool(data.get("needs_review", False)),
                raw_response=result.answer[:1000],
            )
            return llm_result

        except json.JSONDecodeError as e:
            logger.warning(f"LLM分析结果JSON解析失败: {e}，原始响应: {result.answer[:200]}")
            return LLMResult()
        except Exception as e:
            logger.warning(f"LLM分析异常: {type(e).__name__}: {e}")
            return LLMResult()


# 全局单例
llm_analyzer = LLMAnalyzer()
```

#### 步骤 3：修改 collector.py，保存证据字段并调用LLM分析

**修改文件**：`backend/app/engines/collector.py`

**修改点 1**：在文件顶部导入 LLM 分析器：
```python
from app.engines.llm_analyzer import llm_analyzer
```

**修改点 2**：修改 `collect_one_semantic` 方法中成功采集的部分，保存证据字段并调用LLM分析。

找到这段代码（大约在第161-178行）：
```python
            if success and answer:
                result = analyzer.analyze(answer)
                logger.info(f"  -> {platform_code}: GEO={'是' if result.geo_mentioned else '否'}(排名{result.geo_rank}), AEO={'是' if result.aeo_cited else '否'}")
                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=result.geo_rank,
                    mentioned=result.geo_mentioned,
                    sentiment=0.0,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=1 if result.geo_mentioned else 0,
                    cite_count=1 if result.aeo_cited else 0,
                    aeo_confidence=result.aeo_confidence,
                )
```

替换为：
```python
            if success and answer:
                result = analyzer.analyze(answer)
                logger.info(f"  -> {platform_code}: GEO={'是' if result.geo_mentioned else '否'}(排名{result.geo_rank}), AEO={'是' if result.aeo_cited else '否'}")

                # 提取提及证据片段
                mention_evidence = ""
                if result.geo_mentioned:
                    # 在原文中找到医生名的位置，取前后100字符
                    for pattern in analyzer.patterns:
                        m = pattern.search(answer)
                        if m:
                            start = max(0, m.start() - 100)
                            end = min(len(answer), m.end() + 100)
                            mention_evidence = answer[start:end].strip()
                            break

                # LLM辅助分析（只对已提及医生的记录调用，节省成本）
                is_recommendation = False
                recommendation_evidence = ""
                citation_urls = []
                sentiment_score = 0.0
                if result.geo_mentioned:
                    try:
                        llm_result = llm_analyzer.analyze(
                            answer, profile.real_name, profile.hospital, profile.department
                        )
                        is_recommendation = llm_result.is_recommendation
                        recommendation_evidence = llm_result.recommendation_evidence
                        citation_urls = llm_result.citation_urls
                        # 情感转分数：positive=0.5, neutral=0.0, negative=-0.5, mixed=0.2
                        sentiment_map = {"positive": 0.5, "neutral": 0.0, "negative": -0.5, "mixed": 0.2}
                        sentiment_score = sentiment_map.get(llm_result.sentiment, 0.0)
                    except Exception as e:
                        logger.warning(f"LLM分析失败，降级: {e}")

                # AEO引用判断：有URL且被引用才算（design-v2要求）
                aeo_cited = result.aeo_cited and len(citation_urls) > 0
                # 如果规则判断AEO但没有URL，降低置信度
                aeo_confidence = result.aeo_confidence if aeo_cited else (result.aeo_confidence * 0.3 if result.aeo_cited else 0.0)

                record = MonitorRecord(
                    question_id=semantic.id,
                    semantic_id=semantic.id,
                    platform_code=platform_code,
                    rank=result.geo_rank if result.geo_rank else 0,  # 数据库rank是Integer，None存0
                    mentioned=result.geo_mentioned,
                    sentiment=sentiment_score,
                    raw_answer=answer,
                    detect_date=today,
                    detect_round=detect_round,
                    detect_type="doctor",
                    recommend_count=1 if is_recommendation else 0,
                    cite_count=1 if aeo_cited else 0,
                    aeo_confidence=aeo_confidence,
                    # 新增证据字段
                    mention_evidence=mention_evidence,
                    recommendation_evidence=recommendation_evidence,
                    citation_urls=json.dumps(citation_urls, ensure_ascii=False),
                    analyzer_version="rule_v2+llm_v1",
                    raw_sources_json="[]",
                    is_recommendation=1 if is_recommendation else 0,
                )
```

**注意**：需要在文件顶部 `import json`（如果还没有的话，先 Read 确认）。

#### T03 验证

```bash
cd backend
# 1. 语法检查
python -c "from app.engines.llm_analyzer import LLMAnalyzer, llm_analyzer; print('LLM分析器导入OK')"
python -c "from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer; print('分析器导入OK')"
python -c "from app.engines.collector import CollectorEngine; print('采集引擎导入OK')"

# 2. 单元测试：医院名单独出现不应命中
python -c "
from app.engines.geo_aeo_analyzer import GEOAEOAnalyzer
analyzer = GEOAEOAnalyzer(doctor_name='张三', hospital='北京医院', department='心内科')
# 测试1：只有医院名，没有医生名 → 不应提及
result = analyzer.analyze('北京医院是一家三甲医院。')
print(f'只有医院名: mentioned={result.geo_mentioned} (期望 False)')
# 测试2：医院+医生 → 应提及
result = analyzer.analyze('1. 北京医院张三医生')
print(f'医院+医生: mentioned={result.geo_mentioned}, rank={result.geo_rank} (期望 True, rank=1)')
# 测试3：无序列表 → rank应为None
result = analyzer.analyze('推荐张三医生。他很专业。')
print(f'无序列表: mentioned={result.geo_mentioned}, rank={result.geo_rank} (期望 True, rank=None)')
"
```

#### T03 完成标准

- [ ] 医院名单独出现不再被误判为医生命中
- [ ] 排名无法确定时返回 None（数据库存0），不再默认1
- [ ] LLM分析器可以正常导入和调用
- [ ] 采集成功时保存 mention_evidence、recommendation_evidence、citation_urls、analyzer_version 字段
- [ ] 只有已提及医生的记录才调用LLM（成本控制）
- [ ] AEO引用必须有URL才算（design-v2要求）
- [ ] LLM调用失败时降级为规则判断，不阻塞采集

---

### T04：采集接口异步化

**目标**：将 `/geo/refresh` 和 `/monitor/collect` 从同步阻塞改为异步任务创建，立即返回 task_id，由 Worker 后台执行。

**前置读取**：
1. `backend/app/api/geo.py` — 确认当前 `/refresh` 实现
2. `backend/app/api/monitor.py` — 确认当前采集接口实现
3. `backend/app/models/task.py` — 确认 AsyncTask 模型（T01已建）
4. `backend/app/deps.py` — 确认 get_current_user_id

#### 步骤 1：修改 geo.py 的 /refresh 接口

**修改文件**：`backend/app/api/geo.py`

**修改点 1**：在文件顶部导入区添加：
```python
import json
from app.models.task import AsyncTask
from app.models.workspace import WorkspaceMember
```

**修改点 2**：找到 `refresh_data` 函数（大约第196-219行），完整替换为：

```python
@router.post("/refresh", summary="手动刷新GEO/AEO数据（异步任务，立即返回task_id）")
def refresh_data(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """手动触发当前用户所有启用语义的GEO/AEO采集（异步，由Worker执行）"""
    # 检查Profile
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完善个人资料")

    # 检查启用的语义
    active_count = db.query(Semantic).filter(
        Semantic.user_id == user_id, Semantic.is_active == True
    ).count()
    if active_count == 0:
        raise HTTPException(status_code=400, detail="没有启用的语义，请先在语义库启用")

    # 检查AI平台
    platforms = adapter_factory.get_enabled_platforms()
    if not platforms:
        raise HTTPException(status_code=400, detail="没有已配置的AI平台")

    # 获取用户默认 workspace_id
    ws_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.role == "owner"
    ).first()
    workspace_id = ws_member.workspace_id if ws_member else None

    # 检查是否已有 running 的同类型任务（防止重复提交）
    running_task = db.query(AsyncTask).filter(
        AsyncTask.created_by == user_id,
        AsyncTask.task_type == "geo_refresh",
        AsyncTask.status.in_(["queued", "running"])
    ).first()
    if running_task:
        raise HTTPException(status_code=400, detail=f"已有正在执行的GEO刷新任务（ID: {running_task.id}），请等待完成")

    # 创建异步任务
    task = AsyncTask(
        workspace_id=workspace_id,
        task_type="geo_refresh",
        status="queued",
        progress=0,
        progress_message="等待执行",
        payload_json=json.dumps({"user_id": user_id}, ensure_ascii=False),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"code": 0, "message": "任务已创建", "data": {
        "task_id": task.id,
        "status": "queued",
        "message": "GEO/AEO刷新任务已提交，Worker将在后台执行"
    }}
```

#### 步骤 2：修改 monitor.py 的采集接口

**修改文件**：`backend/app/api/monitor.py`

先 Read 确认当前采集接口的函数名和参数，然后做类似修改：

找到采集相关的 POST 接口（通常是 `/collect`），将同步调用 `collector.collect_all()` 或 `collector.collect_single_question_now()` 改为创建 AsyncTask。

模板代码：
```python
@router.post("/collect", summary="触发采集（异步任务）")
def collect(
    data: CollectRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 获取 workspace_id（同 geo.py）
    ws_member = db.query(WorkspaceMember).filter(...).first()
    workspace_id = ws_member.workspace_id if ws_member else None

    # 检查是否有 running 任务
    # ...

    task = AsyncTask(
        workspace_id=workspace_id,
        task_type="monitor_collect",
        status="queued",
        payload_json=json.dumps({"question_id": data.question_id, "detect_round": data.detect_round}),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "任务已创建", "data": {"task_id": task.id, "status": "queued"}}
```

**注意**：如果 monitor.py 的采集接口函数名或参数与上面不同，按实际代码调整，核心逻辑不变（创建AsyncTask，payload里放参数）。

#### T04 验证

```bash
cd backend
# 1. 语法检查
python -c "from app.api.geo import router; print('geo API导入OK')"
python -c "from app.api.monitor import router; print('monitor API导入OK')"

# 2. 启动 API + Worker，测试异步流程
# 终端1：启动 API
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 终端2：启动 Worker
set APP_ROLE=worker
python -m app.worker.worker

# 3. 调用 /geo/refresh（需要有效token，或临时注释掉Depends测试）
# 应该立即返回 {"task_id": N, "status": "queued"}，而不是阻塞1-3分钟
# Worker 终端应该看到 "认领任务 #N (type=geo_refresh)" 和执行日志
```

#### T04 完成标准

- [ ] `/geo/refresh` 接口在 1 秒内返回 task_id，不再阻塞
- [ ] `/monitor/collect` 接口同样异步化
- [ ] 重复提交同类型任务返回 400 错误（防重复）
- [ ] Worker 能认领并执行 geo_refresh 和 monitor_collect 任务
- [ ] 任务完成后 AsyncTask 状态变为 succeeded，result_json 中有采集结果

---

### T05：任务查询 API + 前端任务中心

**目标**：提供任务查询API，前端新建任务中心页面，用户可以查看所有异步任务的状态和进度。

**前置读取**：
1. `backend/app/models/task.py` — 确认 AsyncTask 字段
2. `frontend/src/api/index.ts` — 确认 API 封装风格
3. `frontend/src/router/index.tsx` — 确认路由配置
4. `frontend/src/components/Layout.tsx` — 确认菜单和 Header 结构

#### 步骤 1：新建任务查询 API

**新建文件**：`backend/app/api/task.py`

```python
"""异步任务查询 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.database import get_db
from app.deps import get_current_user_id
from app.models.task import AsyncTask

router = APIRouter(prefix="/api/v1/task", tags=["异步任务"])


@router.get("/{task_id}", summary="查询单个任务状态")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.created_by == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 解析 result_json
    result_data = {}
    if task.result_json:
        try:
            result_data = json.loads(task.result_json)
        except:
            pass

    return {"code": 0, "message": "success", "data": {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "result": result_data,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }}


@router.get("", summary="任务列表")
def list_tasks(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(AsyncTask).filter(AsyncTask.created_by == user_id)
    if task_type:
        query = query.filter(AsyncTask.task_type == task_type)
    if status:
        query = query.filter(AsyncTask.status == status)

    total = query.count()
    items = query.order_by(AsyncTask.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    return {"code": 0, "message": "success", "data": {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": t.id,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "progress_message": t.progress_message,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        } for t in items]
    }}


@router.post("/{task_id}/cancel", summary="取消任务（仅 queued 状态可取消）")
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.created_by == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "queued":
        raise HTTPException(status_code=400, detail=f"仅 queued 状态的任务可取消，当前状态: {task.status}")

    task.status = "cancelled"
    task.finished_at = task.finished_at or __import__("datetime").datetime.now()
    task.progress_message = "用户取消"
    db.commit()
    return {"code": 0, "message": "任务已取消"}
```

#### 步骤 2：注册 task 路由

**修改文件**：`backend/app/api/__init__.py`

先 Read 确认当前内容，然后：
1. 添加 `from app.api.task import router as task_router`
2. 在 `__all__` 中添加 `task_router`

**修改文件**：`backend/app/main.py`

在路由注册区添加：
```python
app.include_router(task_router)
```

#### 步骤 3：前端新增 taskApi

**修改文件**：`frontend/src/api/index.ts`

在文件末尾（`export default request` 之前）添加：

```typescript
// ============ 异步任务 API ============
export const taskApi = {
  get: (id: number) => request.get(`/task/${id}`),
  list: (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
    request.get('/task', { params }),
  cancel: (id: number) => request.post(`/task/${id}/cancel`),
}
```

#### 步骤 4：新建任务中心页面

**新建文件**：`frontend/src/pages/TaskCenter.tsx`

```tsx
import { useState, useEffect, useCallback } from 'react'
import { Table, Tag, Progress, Button, Space, Card, Typography, Empty, Badge, message } from 'antd'
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { taskApi } from '@/api'

const { Title } = Typography

// 任务类型名称映射
const TASK_TYPE_NAMES: Record<string, string> = {
  geo_refresh: 'GEO/AEO刷新',
  monitor_collect: '监测采集',
  article_generate: '文章生成',
  image_generate: '图片生成',
  video_generate: '视频生成',
  agent_chat: '智能体对话',
}

// 状态配置
const STATUS_CONFIG: Record<string, { color: string; label: string; icon: any }> = {
  queued: { color: 'default', label: '等待中', icon: <ClockCircleOutlined /> },
  running: { color: 'processing', label: '执行中', icon: <LoadingOutlined /> },
  succeeded: { color: 'success', label: '已完成', icon: <CheckCircleOutlined /> },
  failed: { color: 'error', label: '失败', icon: <CloseCircleOutlined /> },
  cancelled: { color: 'warning', label: '已取消', icon: <CloseCircleOutlined /> },
}

const TaskCenter = () => {
  const [tasks, setTasks] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await taskApi.list({ page, page_size: pageSize, status: statusFilter })
      setTasks(res.data.items)
      setTotal(res.data.total)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 自动刷新：有 running/queued 任务时每3秒刷新一次
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'running' || t.status === 'queued')
    if (!hasActive) return
    const timer = setInterval(fetchTasks, 3000)
    return () => clearInterval(timer)
  }, [tasks, fetchTasks])

  const handleCancel = async (id: number) => {
    try {
      await taskApi.cancel(id)
      message.success('任务已取消')
      fetchTasks()
    } catch (e) {
      // 错误已处理
    }
  }

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      width: 80,
      render: (id: number) => <span style={{ fontFamily: 'monospace' }}>#{id}</span>,
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      width: 140,
      render: (type: string) => TASK_TYPE_NAMES[type] || type,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.queued
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      width: 180,
      render: (progress: number, record: any) => {
        if (record.status === 'succeeded') return <Progress percent={100} size="small" status="success" />
        if (record.status === 'failed') return <Progress percent={progress || 0} size="small" status="exception" />
        if (record.status === 'running') return <Progress percent={progress || 0} size="small" status="active" />
        return <Progress percent={0} size="small" />
      },
    },
    {
      title: '进度说明',
      dataIndex: 'progress_message',
      ellipsis: true,
      render: (msg: string, record: any) => record.error_message || msg || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      width: 100,
      render: (_: any, record: any) => (
        record.status === 'queued' ? (
          <Button type="link" danger size="small" onClick={() => handleCancel(record.id)}>取消</Button>
        ) : '-'
      ),
    },
  ]

  const runningCount = tasks.filter(t => t.status === 'running' || t.status === 'queued').length

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          任务中心
          {runningCount > 0 && (
            <Badge count={runningCount} style={{ marginLeft: 12, backgroundColor: '#1890ff' }} />
          )}
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} loading={loading}>刷新</Button>
        </Space>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条任务`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps) },
          }}
          locale={{ emptyText: <Empty description="暂无任务" /> }}
        />
      </Card>
    </div>
  )
}

export default TaskCenter
```

#### 步骤 5：注册路由和菜单

**修改文件**：`frontend/src/router/index.tsx`

1. 在 lazy 导入区添加：
```typescript
const TaskCenter = lazy(() => import('@/pages/TaskCenter'))
```

2. 在路由配置中添加（在 MainLayout 的子路由中）：
```typescript
<Route path="tasks" element={<RequireAuth><TaskCenter /></RequireAuth>} />
```

**修改文件**：`frontend/src/components/Layout.tsx`

在顶部 Header 的刷新按钮旁边，添加任务中心入口（带未完成任务数的 Badge）：

1. 在导入区添加：
```typescript
import { useEffect, useState } from 'react'  // 如果还没导入useState
import { taskApi } from '@/api'
```

2. 在 `menuItems` 数组中添加任务中心菜单项（在"数据中心"后面）：
```typescript
{ key: '/tasks', icon: <SyncOutlined />, label: '任务中心' },
```
（需要导入 `SyncOutlined` 图标，或用现有的 `ReloadOutlined`）

3. 在 Header 中，刷新按钮旁边添加任务图标（可选，菜单已有入口的话可以不加）：
```typescript
<Tooltip title="任务中心">
  <Button type="text" icon={<SyncOutlined />} onClick={() => navigate('/tasks')} />
</Tooltip>
```

#### T05 验证

```bash
cd backend
python -c "from app.api.task import router; print('task API导入OK')"

cd frontend
# TypeScript 检查
npx tsc --noEmit
# 应该没有新增的类型错误
```

启动前后端，访问 `/tasks` 路径，应该能看到任务中心页面。提交一个 GEO 刷新任务后，任务中心应该能看到任务状态从 queued → running → succeeded 的变化（自动刷新）。

#### T05 完成标准

- [ ] 任务查询 API（GET /task/{id}, GET /task, POST /task/{id}/cancel）可用
- [ ] 前端任务中心页面可访问（/tasks）
- [ ] 任务列表显示类型、状态、进度、进度说明、创建时间
- [ ] 有 running/queued 任务时自动每3秒刷新
- [ ] queued 状态的任务可以取消
- [ ] 左侧菜单有"任务中心"入口
- [ ] 任务完成后状态正确更新为 succeeded/failed

---

### T06：P0 联调验收

**目标**：完整跑通 P0 所有功能，确认前后端协同正常，无回归问题。

#### 步骤 1：全量语法和类型检查

```bash
# 后端
cd backend
python -c "
import app.main
import app.worker.worker
import app.services.distribution_service
import app.engines.llm_analyzer
import app.api.task
print('所有后端模块导入成功')
"

# 前端
cd frontend
npx tsc --noEmit
echo "前端TypeScript检查完成"
```

#### 步骤 2：数据库迁移验证

```bash
cd backend
python -m scripts.migrate_v2
# 确认输出 "✅ 数据库迁移完成"
# 用 sqlite3 或 Python 检查新增表和列
python -c "
import sqlite3
conn = sqlite3.connect('data/geo.db')
tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()]
print('表列表:', tables)
# 检查关键新表
for t in ['geo_workspace', 'geo_workspace_member', 'geo_async_task', 'geo_schema_version']:
    assert t in tables, f'缺少表: {t}'
print('✅ 所有新表已创建')
# 检查 monitor_record 新列
cols = [r[1] for r in conn.execute('PRAGMA table_info(geo_monitor_record)').fetchall()]
for c in ['mention_evidence', 'recommendation_evidence', 'citation_urls', 'analyzer_version', 'is_recommendation']:
    assert c in cols, f'缺少列: geo_monitor_record.{c}'
print('✅ monitor_record 所有新列已添加')
# 检查 distribution 新列
cols = [r[1] for r in conn.execute('PRAGMA table_info(geo_article_distribution)').fetchall()]
for c in ['scheduled_at', 'failed_reason', 'retry_count', 'publish_mode', 'external_task_id', 'verified_at']:
    assert c in cols, f'缺少列: geo_article_distribution.{c}'
print('✅ distribution 所有新列已添加')
# 检查每个用户有默认Workspace
ws_count = conn.execute('SELECT COUNT(*) FROM geo_workspace').fetchone()[0]
user_count = conn.execute('SELECT COUNT(*) FROM geo_user').fetchone()[0]
print(f'用户数: {user_count}, Workspace数: {ws_count}')
conn.close()
"
```

#### 步骤 3：端到端流程测试

启动 API 和 Worker，然后按以下顺序测试：

1. **登录**：通过 IAM 登录获取 token（或用现有 token）
2. **创建采集任务**：调用 `POST /api/v1/geo/refresh`，确认立即返回 task_id
3. **查看任务**：调用 `GET /api/v1/task/{task_id}`，确认状态从 queued → running → succeeded
4. **查看任务列表**：调用 `GET /api/v1/task`，确认任务在列表中
5. **前端验证**：浏览器访问前端，导航到任务中心，确认任务显示正确
6. **Distribution 状态机**：创建一个 draft 状态的分发记录，依次流转 draft → scheduled → processing → published，确认非法流转返回400
7. **分析器验证**：触发一次采集后，查看 MonitorRecord 的新字段（mention_evidence 等）是否有值

#### 步骤 4：回归测试

确认以下现有功能没有被破坏：
- [ ] 仪表盘数据正常显示
- [ ] 语义库列表正常
- [ ] 内容中心文章列表正常
- [ ] 数据中心监测记录正常
- [ ] 个人资料保存正常
- [ ] 文章创建/编辑/删除正常
- [ ] 导出功能正常

#### T06 完成标准

- [ ] 所有后端模块导入无错误
- [ ] 前端 TypeScript 检查无错误
- [ ] 数据库迁移脚本幂等运行成功
- [ ] 所有新表和新列已创建
- [ ] 采集异步流程端到端跑通（API创建任务 → Worker执行 → 状态更新 → 前端显示）
- [ ] Distribution 状态机流转正常，非法流转被拒绝
- [ ] 采集记录保存了证据字段
- [ ] 现有功能无回归

---

### T07：内容机会识别模块

**目标**：从监测数据自动识别"应该写什么内容"，把数据缺口转化为可执行的内容任务。

**前置读取**：
1. `backend/app/models/semantic.py` — Semantic 模型
2. `backend/app/models/monitor.py` — MonitorRecord 模型
3. `backend/app/models/article.py` — ArticleDraft 模型
4. `backend/app/api/__init__.py` — 路由注册方式

#### 步骤 1：新建 ContentOpportunity 模型

**新建文件**：`backend/app/models/content_opportunity.py`

```python
"""内容机会模型 — 从监测数据中识别的内容创作机会"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ContentOpportunity(Base):
    __tablename__ = "geo_content_opportunity"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("geo_workspace.id"), nullable=True, index=True)
    doctor_id = Column(Integer, ForeignKey("geo_doctor_profile.id"), nullable=True, index=True)
    question_id = Column(Integer, ForeignKey("geo_semantic.id"), nullable=False, index=True)
    opportunity_type = Column(String(30), nullable=False, index=True)
    # missing_mention: AI未提及医生
    # missing_citation: 有提及但无来源引用
    # competitor_gap: 竞品被推荐更多
    # low_rank: 排名靠后
    priority_score = Column(Float, default=0.0)  # 0-100
    evidence_json = Column(Text, default="{}")    # 证据数据
    status = Column(String(20), default="open", index=True)
    # open/planned/done/dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
```

**注册模型**：在 `backend/app/models/__init__.py` 中添加导入和导出。

#### 步骤 2：新建机会识别引擎

**新建文件**：`backend/app/engines/opportunity_engine.py`

```python
"""
内容机会识别引擎 — 扫描监测数据，自动识别内容创作机会。

机会类型：
- missing_mention: AI回答中未提及医生 → 需要写内容提升曝光
- missing_citation: 有提及但无来源引用 → 需要写权威内容并发布到可引用平台
- low_rank: 排名靠后（>3） → 需要优化内容质量和关键词
- competitor_gap: 竞品被推荐更多 → 需要差异化内容
"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.semantic import Semantic
from app.models.monitor import MonitorRecord
from app.models.content_opportunity import ContentOpportunity
from app.models.doctor import DoctorProfile

logger = logging.getLogger(__name__)


class OpportunityEngine:
    def __init__(self, db: Session):
        self.db = db

    def scan(self, user_id: int) -> dict:
        """扫描用户的所有语义，生成内容机会"""
        semantics = self.db.query(Semantic).filter(
            Semantic.user_id == user_id,
            Semantic.is_active == True
        ).all()

        if not semantics:
            return {"total": 0, "new": 0, "message": "没有启用的语义"}

        semantic_ids = [s.id for s in semantics]

        # 获取最新一轮采集记录
        latest_date = self.db.query(func.max(MonitorRecord.detect_date)).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_type == "doctor"
        ).scalar()

        if not latest_date:
            return {"total": 0, "new": 0, "message": "没有采集数据，请先执行GEO刷新"}

        latest_records = self.db.query(MonitorRecord).filter(
            MonitorRecord.semantic_id.in_(semantic_ids),
            MonitorRecord.detect_type == "doctor",
            MonitorRecord.detect_date == latest_date,
            MonitorRecord.detect_round == 99
        ).all()

        # 按 semantic_id 分组
        records_by_semantic = {}
        for r in latest_records:
            if r.semantic_id not in records_by_semantic:
                records_by_semantic[r.semantic_id] = []
            records_by_semantic[r.semantic_id].append(r)

        new_count = 0
        for semantic in semantics:
            records = records_by_semantic.get(semantic.id, [])
            if not records:
                continue

            total = len(records)
            mentioned_count = sum(1 for r in records if r.mentioned)
            cited_count = sum(1 for r in records if r.cite_count and r.cite_count > 0)
            avg_rank = sum(r.rank for r in records if r.mentioned and r.rank > 0) / max(1, mentioned_count)
            mention_rate = mentioned_count / total if total > 0 else 0

            # 1. missing_mention: 提及率 < 50%
            if mention_rate < 0.5:
                opp = self._create_or_update(
                    user_id, semantic, "missing_mention",
                    priority=80 - mention_rate * 50,  # 提及率越低优先级越高
                    evidence={
                        "mention_rate": round(mention_rate * 100, 1),
                        "mentioned_count": mentioned_count,
                        "total_count": total,
                        "platforms_missing": [r.platform_code for r in records if not r.mentioned],
                    }
                )
                if opp: new_count += 1

            # 2. missing_citation: 有提及但引用率 < 30%
            elif cited_count / max(1, mentioned_count) < 0.3:
                opp = self._create_or_update(
                    user_id, semantic, "missing_citation",
                    priority=60,
                    evidence={
                        "citation_rate": round(cited_count / max(1, mentioned_count) * 100, 1),
                        "cited_count": cited_count,
                        "mentioned_count": mentioned_count,
                    }
                )
                if opp: new_count += 1

            # 3. low_rank: 平均排名 > 3
            if mentioned_count > 0 and avg_rank > 3:
                opp = self._create_or_update(
                    user_id, semantic, "low_rank",
                    priority=50,
                    evidence={"avg_rank": round(avg_rank, 1), "mentioned_count": mentioned_count}
                )
                if opp: new_count += 1

        return {"total": len(semantics), "new": new_count, "message": f"扫描完成，新增 {new_count} 个内容机会"}

    def _create_or_update(self, user_id: int, semantic: Semantic,
                          opp_type: str, priority: float, evidence: dict) -> ContentOpportunity | None:
        """创建或更新内容机会（同一语义+同一类型不重复创建 open 状态的）"""
        existing = self.db.query(ContentOpportunity).filter(
            ContentOpportunity.question_id == semantic.id,
            ContentOpportunity.opportunity_type == opp_type,
            ContentOpportunity.status == "open"
        ).first()

        if existing:
            # 更新证据和优先级
            existing.evidence_json = json.dumps(evidence, ensure_ascii=False)
            existing.priority_score = priority
            self.db.commit()
            return None

        # 获取 doctor_id
        profile = self.db.query(DoctorProfile).filter(DoctorProfile.user_id == user_id).first()
        doctor_id = profile.id if profile else None

        # 获取 workspace_id
        from app.models.workspace import WorkspaceMember
        ws = self.db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == user_id, WorkspaceMember.role == "owner"
        ).first()
        workspace_id = ws.workspace_id if ws else None

        opp = ContentOpportunity(
            workspace_id=workspace_id,
            doctor_id=doctor_id,
            question_id=semantic.id,
            opportunity_type=opp_type,
            priority_score=priority,
            evidence_json=json.dumps(evidence, ensure_ascii=False),
            status="open",
        )
        self.db.add(opp)
        self.db.commit()
        self.db.refresh(opp)
        return opp

    def dismiss(self, opp_id: int, user_id: int) -> bool:
        """忽略机会"""
        from datetime import datetime
        opp = self.db.query(ContentOpportunity).filter(
            ContentOpportunity.id == opp_id,
            ContentOpportunity.status == "open"
        ).first()
        if not opp:
            return False
        opp.status = "dismissed"
        opp.resolved_at = datetime.now()
        self.db.commit()
        return True


# 需要导入 func
from sqlalchemy import func
```

#### 步骤 3：新建机会 API

**新建文件**：`backend/app/api/opportunity.py`

```python
"""内容机会 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.deps import get_current_user_id
from app.models.content_opportunity import ContentOpportunity
from app.models.semantic import Semantic
from app.engines.opportunity_engine import OpportunityEngine

router = APIRouter(prefix="/api/v1/opportunity", tags=["内容机会"])


@router.get("", summary="内容机会列表")
def list_opportunities(
    status: Optional[str] = "open",
    opportunity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 通过 semantic.user_id 过滤（ContentOpportunity 没有直接的 user_id）
    semantics = db.query(Semantic).filter(Semantic.user_id == user_id).all()
    semantic_ids = [s.id for s in semantics]

    query = db.query(ContentOpportunity).filter(ContentOpportunity.question_id.in_(semantic_ids))
    if status:
        query = query.filter(ContentOpportunity.status == status)
    if opportunity_type:
        query = query.filter(ContentOpportunity.opportunity_type == opportunity_type)

    items = query.order_by(ContentOpportunity.priority_score.desc()).all()

    # 关联语义问题文本
    semantic_map = {s.id: s.question for s in semantics}
    result = []
    for opp in items:
        result.append({
            "id": opp.id,
            "question_id": opp.question_id,
            "question_text": semantic_map.get(opp.question_id, ""),
            "opportunity_type": opp.opportunity_type,
            "priority_score": opp.priority_score,
            "evidence": __import__("json").loads(opp.evidence_json or "{}"),
            "status": opp.status,
            "created_at": opp.created_at.isoformat() if opp.created_at else None,
        })

    return {"code": 0, "message": "success", "data": {"items": result}}


@router.post("/scan", summary="触发内容机会扫描")
def scan_opportunities(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    engine = OpportunityEngine(db)
    result = engine.scan(user_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/{opp_id}/dismiss", summary="忽略内容机会")
def dismiss_opportunity(
    opp_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    engine = OpportunityEngine(db)
    if engine.dismiss(opp_id, user_id):
        return {"code": 0, "message": "已忽略"}
    raise HTTPException(status_code=404, detail="机会不存在或已处理")
```

#### 步骤 4：注册路由和模型

- `backend/app/api/__init__.py`：注册 `opportunity_router`
- `backend/app/main.py`：`app.include_router(opportunity_router)`
- `backend/app/models/__init__.py`：注册 `ContentOpportunity`

#### 步骤 5：数据库迁移加表

在 `backend/scripts/migrate_v2.py` 的 `migrate()` 函数中，新增表创建（在 AsyncTask 表之后）：

```python
    # ===== ContentOpportunity 表 =====
    print("[ContentOpportunity] 内容机会表")
    ensure_table(conn, "geo_content_opportunity", """
        CREATE TABLE IF NOT EXISTS geo_content_opportunity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            doctor_id INTEGER,
            question_id INTEGER NOT NULL,
            opportunity_type TEXT NOT NULL,
            priority_score REAL DEFAULT 0.0,
            evidence_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_question ON geo_content_opportunity(question_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_type ON geo_content_opportunity(opportunity_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp_status ON geo_content_opportunity(status)")
    conn.commit()
```

然后重新运行迁移脚本。

#### T07 验证

```bash
cd backend
python -c "from app.models.content_opportunity import ContentOpportunity; print('模型OK')"
python -c "from app.engines.opportunity_engine import OpportunityEngine; print('引擎OK')"
python -c "from app.api.opportunity import router; print('API OK')"
python -m scripts.migrate_v2  # 确认新表创建
```

#### T07 完成标准

- [ ] ContentOpportunity 模型和表已创建
- [ ] 扫描引擎能根据监测数据生成 missing_mention / missing_citation / low_rank 类型机会
- [ ] 机会列表 API 可按状态和类型过滤
- [ ] 同一语义+同一类型不会重复创建 open 状态的机会
- [ ] 机会可以被忽略（dismiss）

---

### T08：文章生成引擎升级（LLM 驱动）

**目标**：替换当前 `article_template.py` 的纯字符串拼接，用 LLM 生成高质量、合规的医疗科普文章。

**前置读取**：
1. `backend/app/engines/article_template.py` — 当前模板引擎
2. `backend/app/api/template.py` — 模板API
3. `backend/app/models/article.py` — ArticleDraft 模型
4. `backend/app/engines/semantic_generator.py` — 参考 LLM 调用方式

#### 步骤 1：新建文章生成引擎

**新建文件**：`backend/app/engines/article_generator.py`

```python
"""
LLM 驱动的文章生成引擎 — 基于语义问题和医生资料生成合规医疗科普文章。

合规规则（强制）：
1. 只做健康科普，不做具体诊疗建议
2. 不编造数据、治愈率、有效率
3. 不使用"最佳/第一/根治/百分百"等绝对化用语
4. 必须包含"以上内容仅供科普参考，具体诊疗请遵医嘱"免责声明
5. 基于医生真实资料，不编造资历
"""
import json
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

from app.models.semantic import Semantic
from app.models.doctor import DoctorProfile
from app.models.content_opportunity import ContentOpportunity
from app.adapters import adapter_factory

logger = logging.getLogger(__name__)


@dataclass
class GeneratedArticle:
    title: str
    intro: str
    sections: list = field(default_factory=list)  # [{"heading": "", "content": ""}]
    conclusion: str
    tags: list = field(default_factory=list)
    meta_description: str = ""
    full_text: str = ""


SYSTEM_PROMPT = """你是一个资深医疗科普内容创作专家，擅长将专业医学知识转化为患者易懂的科普文章。

严格遵守以下规则：
1. 只做健康科普，不做具体诊疗建议，不推荐具体药物剂量
2. 不编造数据、治愈率、有效率、患者人数
3. 不使用"最佳/第一/根治/百分百/包治"等绝对化用语
4. 必须基于医生真实资料（医院/科室/职称/专长），不编造资历
5. 文章末尾必须包含免责声明："以上内容仅供科普参考，具体诊疗请遵医嘱。"
6. 语言通俗易懂，避免专业术语堆砌，必要时用括号解释
7. 结构清晰：标题→引言→分点正文→就诊建议→免责声明→标签

输出严格的 JSON 格式（不要输出 markdown 代码块，不要输出其他文字）：
{
  "title": "文章标题（包含关键词，15-30字）",
  "intro": "引言段落（100-200字，医生自我介绍+患者痛点引入）",
  "sections": [
    {"heading": "小标题1", "content": "段落内容（200-400字）"},
    {"heading": "小标题2", "content": "段落内容（200-400字）"},
    {"heading": "小标题3", "content": "段落内容（200-400字）"}
  ],
  "conclusion": "总结+就诊建议+免责声明（100-200字）",
  "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "meta_description": "SEO描述（80-120字）"
}"""


class ArticleGenerator:
    """LLM 驱动的文章生成引擎"""

    def __init__(self, platform_code: str = None):
        self.platform_code = platform_code

    def _get_adapter(self):
        if self.platform_code:
            return adapter_factory.get_adapter(self.platform_code)
        platforms = adapter_factory.get_enabled_platforms()
        if platforms:
            return adapter_factory.get_adapter(platforms[0])
        return None

    def generate(self, semantic: Semantic, profile: DoctorProfile,
                 opportunity: ContentOpportunity = None) -> GeneratedArticle:
        """
        生成文章。

        Args:
            semantic: 语义问题对象
            profile: 医生资料对象
            opportunity: 关联的内容机会（可选，用于在文章中针对性解决问题）
        """
        adapter = self._get_adapter()
        if not adapter:
            logger.warning("无可用AI平台，使用模板兜底")
            return self._fallback_generate(semantic, profile)

        # 构建用户 prompt
        opportunity_info = ""
        if opportunity:
            opp_type_names = {
                "missing_mention": "AI回答中较少提及该医生，需要通过内容提升曝光",
                "missing_citation": "AI回答中有提及但缺少权威来源引用，需要发布到可引用平台",
                "low_rank": "医生在AI推荐中排名靠后，需要优化内容质量和关键词",
            }
            opportunity_info = f"\n内容机会：{opp_type_names.get(opportunity.opportunity_type, '')}"
            try:
                evidence = json.loads(opportunity.evidence_json or "{}")
                opportunity_info += f"\n机会证据：{json.dumps(evidence, ensure_ascii=False)}"
            except:
                pass

        user_prompt = f"""医生信息：
姓名：{profile.real_name or ''}
职称：{profile.title or ''}
地域：{profile.province or ''}{profile.city or ''}
医院：{profile.hospital or ''}
科室：{profile.department or ''}
专长：{profile.specialty or ''}

患者问题：{semantic.question}
问题分类：{semantic.category or 'general'}{opportunity_info}

请根据以上信息，生成一篇面向患者的医疗科普文章。"""

        try:
            result = adapter.query(user_prompt, system_prompt=SYSTEM_PROMPT)
            if not result.success:
                logger.warning(f"文章生成LLM调用失败: {result.error}")
                return self._fallback_generate(semantic, profile)

            # 解析 JSON
            response_text = result.answer.strip()
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()

            data = json.loads(response_text)

            # 构建全文
            sections_text = "\n\n".join(
                f"## {s.get('heading', '')}\n{s.get('content', '')}"
                for s in data.get("sections", [])
            )
            full_text = (
                f"{data.get('title', '')}\n\n"
                f"{data.get('intro', '')}\n\n"
                f"{sections_text}\n\n"
                f"{data.get('conclusion', '')}\n\n"
                f"{' '.join(data.get('tags', []))}"
            )

            # 强制追加免责声明（如果 LLM 没加）
            if "仅供科普参考" not in full_text and "具体诊疗请遵医嘱" not in full_text:
                full_text += "\n\n以上内容仅供科普参考，具体诊疗请遵医嘱。"

            return GeneratedArticle(
                title=data.get("title", semantic.question),
                intro=data.get("intro", ""),
                sections=data.get("sections", []),
                conclusion=data.get("conclusion", ""),
                tags=data.get("tags", []),
                meta_description=data.get("meta_description", ""),
                full_text=full_text,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"文章生成JSON解析失败: {e}")
            return self._fallback_generate(semantic, profile)
        except Exception as e:
            logger.warning(f"文章生成异常: {type(e).__name__}: {e}")
            return self._fallback_generate(semantic, profile)

    def _fallback_generate(self, semantic: Semantic, profile: DoctorProfile) -> GeneratedArticle:
        """LLM 不可用时的模板兜底（比旧模板更通用）"""
        city = profile.city or ""
        hospital = profile.hospital or ""
        department = profile.department or ""
        name = profile.real_name or ""
        title_name = profile.title or ""

        article_title = f"{semantic.question}？{department}医生解答"
        intro = (
            f"我是{city}{hospital}{department}{name}医生（{title_name}）。"
            f"在日常接诊中，很多患者都会问：{semantic.question}？"
            f"今天就来统一解答这个问题。"
        )
        sections = [
            {"heading": "为什么会出现这个问题？", "content": "这个问题的成因比较复杂，通常与以下因素有关：首先是生理因素...（此处请根据专业知识补充具体内容）；其次是生活方式因素...；此外还可能与环境和遗传因素有关。建议患者到正规医院进行详细检查以明确原因。"},
            {"heading": "如何规范应对？", "content": "面对这个问题，建议采取以下措施：第一，及时就医，在专业医生指导下进行检查和诊断；第二，遵医嘱进行规范治疗，不要自行用药或尝试偏方；第三，调整生活方式，保持规律作息和健康饮食；第四，定期复查，监测病情变化。"},
            {"heading": "日常注意事项", "content": "在日常生活中，需要注意以下几点：保持良好的个人卫生习惯；避免过度劳累和精神紧张；注意饮食均衡，避免刺激性食物；适当进行体育锻炼，增强体质；如有不适及时就诊，不要拖延。"},
        ]
        conclusion = (
            f"总结一下，{semantic.question}是一个需要重视的问题。"
            f"建议患者及时到{city}{hospital}{department}就诊，在{name}医生的指导下进行规范治疗。"
            f"以上内容仅供科普参考，具体诊疗请遵医嘱。"
        )
        tags = [f"#{city}{department}", f"#{semantic.question.replace('？','').replace('?','')}", f"#{hospital}", "#健康科普", "#就医指南"]

        full_text = (
            f"{article_title}\n\n{intro}\n\n"
            + "\n\n".join(f"## {s['heading']}\n{s['content']}" for s in sections)
            + f"\n\n{conclusion}\n\n{' '.join(tags)}"
        )

        return GeneratedArticle(
            title=article_title, intro=intro, sections=sections,
            conclusion=conclusion, tags=tags, meta_description="", full_text=full_text
        )


# 全局单例
article_generator = ArticleGenerator()
```

#### 步骤 2：修改 template.py API

**修改文件**：`backend/app/api/template.py`

先 Read 确认当前内容，然后将文章生成接口改为调用新的 `ArticleGenerator`。

核心改动：
```python
# 旧：调用 article_template_engine.generate()
# 新：调用 article_generator.generate()

from app.engines.article_generator import article_generator

@router.get("/article/{semantic_id}", summary="生成文章（LLM驱动）")
def generate_article(
    semantic_id: int,
    opportunity_id: Optional[int] = None,  # 可选：关联内容机会
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    semantic = db.query(Semantic).filter(...).first()
    profile = db.query(DoctorProfile).filter(...).first()
    opportunity = None
    if opportunity_id:
        opportunity = db.query(ContentOpportunity).filter(...).first()

    result = article_generator.generate(semantic, profile, opportunity)
    return {"code": 0, "message": "success", "data": {
        "title": result.title,
        "intro": result.intro,
        "sections": result.sections,
        "conclusion": result.conclusion,
        "tags": result.tags,
        "meta_description": result.meta_description,
        "full_text": result.full_text,
    }}
```

**注意**：保留旧的 `article_template_engine` 作为 fallback（新引擎内部已经调用了），不要删除。

#### 步骤 3：前端 API 更新

**修改文件**：`frontend/src/api/index.ts`

在 `templateApi` 中添加 `opportunity_id` 参数支持：
```typescript
export const templateApi = {
  generateArticle: (semanticId: number, opportunityId?: number) =>
    request.get(`/template/article/${semanticId}`, { params: opportunityId ? { opportunity_id: opportunityId } : {} }),
}
```

#### 步骤 4：前端 ContentHub 增加内容机会 Tab

**修改文件**：`frontend/src/pages/ContentHub.tsx`

这个文件有 28KB，先 Read 确认当前的 Tab 结构，然后：
1. 新增"内容机会"Tab（在文章列表 Tab 旁边）
2. Tab 内调用 `opportunityApi.list()` 展示机会卡片列表
3. 每张卡片显示：问题文本、机会类型、优先级、证据摘要、"一键生成文章"按钮
4. 点击"一键生成文章"调用 `templateApi.generateArticle(semanticId, opportunityId)`，生成后跳转到文章编辑

**需要新增的 API 封装**（在 `frontend/src/api/index.ts`）：
```typescript
export const opportunityApi = {
  list: (params?: { status?: string; opportunity_type?: string }) =>
    request.get('/opportunity', { params }),
  scan: () => request.post('/opportunity/scan'),
  dismiss: (id: number) => request.post(`/opportunity/${id}/dismiss`),
}
```

#### T08 验证

```bash
cd backend
python -c "from app.engines.article_generator import article_generator; print('文章生成引擎OK')"
python -c "from app.api.template import router; print('template API OK')"
```

#### T08 完成标准

- [ ] ArticleGenerator 可以正常导入和调用
- [ ] LLM 可用时生成结构化文章（标题/引言/分点正文/总结/标签）
- [ ] LLM 不可用时降级为模板生成
- [ ] 生成的文章包含免责声明
- [ ] 文章生成 API 支持传入 opportunity_id
- [ ] 前端内容中心有"内容机会"Tab，可展示机会列表
- [ ] 可以从内容机会一键生成文章

---

### T09：生图适配器框架（配置留空）

**目标**：建立 AI 生图的适配器框架和配置项，但不实际接入 API（Seedream Key 暂时没有）。后续填了 Key 就能用。

#### 步骤 1：新增配置项

**修改文件**：`backend/app/config.py`

在配置类中添加（在 QWEN 配置之后）：
```python
    # AI生图（Seedream，配置留空，后续填入Key即可启用）
    SEEDREAM_API_KEY: str = ""
    SEEDREAM_BASE_URL: str = ""
    SEEDREAM_MODEL: str = "seedream-4.0"
```

在 `get_enabled_platforms` 方法之后，新增：
```python
    @property
    def image_generation_enabled(self) -> bool:
        """AI生图是否已配置"""
        return bool(self.SEEDREAM_API_KEY and self.SEEDREAM_BASE_URL)
```

#### 步骤 2：新建生图适配器基类

**新建文件**：`backend/app/adapters/image_base.py`

```python
"""AI 生图适配器基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageResult:
    """生图结果"""
    success: bool
    image_url: str = ""
    error: str = ""
    prompt: str = ""
    size: str = "1024x1024"
    style: str = "default"


class BaseImageAdapter(ABC):
    """AI 生图适配器抽象基类"""

    @abstractmethod
    def generate(self, prompt: str, size: str = "1024x1024",
                 style: str = "default") -> ImageResult:
        """
        生成图片

        Args:
            prompt: 生图提示词
            size: 图片尺寸（1024x1024 / 1024x1536 / 1536x1024）
            style: 风格（default / realistic / anime / oil_painting）
        """
        pass

    @abstractmethod
    def get_platform_code(self) -> str:
        """返回平台代码"""
        pass
```

#### 步骤 3：新建 Seedream 适配器（框架，未实际接入）

**新建文件**：`backend/app/adapters/image_seedream.py`

```python
"""
Seedream 生图适配器（框架版 — API 调用逻辑预留，配置留空时返回未配置错误）

使用方法：
1. 在 backend/.env 中配置 SEEDREAM_API_KEY / SEEDREAM_BASE_URL / SEEDREAM_MODEL
2. 本适配器会自动检测配置并启用
3. 实际 API 调用逻辑需要根据 Seedream 官方文档补充（当前为框架占位）
"""
import logging
from app.config import settings
from app.adapters.image_base import BaseImageAdapter, ImageResult

logger = logging.getLogger(__name__)


class SeedreamImageAdapter(BaseImageAdapter):
    """Seedream 生图适配器"""

    def get_platform_code(self) -> str:
        return "seedream"

    def generate(self, prompt: str, size: str = "1024x1024",
                 style: str = "default") -> ImageResult:
        # 检查配置
        if not settings.image_generation_enabled:
            return ImageResult(
                success=False,
                error="Seedream 生图未配置，请在 .env 中设置 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL",
                prompt=prompt, size=size, style=style
            )

        # TODO: 实际 API 调用逻辑
        # 参考 OpenAI 兼容接口的调用方式：
        # import requests
        # response = requests.post(
        #     f"{settings.SEEDREAM_BASE_URL}/images/generations",
        #     headers={"Authorization": f"Bearer {settings.SEEDREAM_API_KEY}"},
        #     json={"model": settings.SEEDREAM_MODEL, "prompt": prompt, "size": size, "n": 1}
        # )
        # result = response.json()
        # return ImageResult(success=True, image_url=result["data"][0]["url"], ...)

        logger.warning("Seedream 适配器已配置但 API 调用逻辑未实现（框架占位）")
        return ImageResult(
            success=False,
            error="Seedream 适配器框架已就绪，API 调用逻辑待实现",
            prompt=prompt, size=size, style=style
        )
```

#### 步骤 4：注册到工厂

**修改文件**：`backend/app/adapters/factory.py`

先 Read 确认当前工厂结构，然后添加：
```python
from app.adapters.image_base import BaseImageAdapter
from app.adapters.image_seedream import SeedreamImageAdapter

# 在 AdapterFactory 类中添加：
class AdapterFactory:
    # ... 现有代码 ...

    _image_adapter = None

    def get_image_adapter(self) -> BaseImageAdapter | None:
        """获取生图适配器（当前仅 Seedream，未配置时返回 None）"""
        if self._image_adapter is None:
            if settings.image_generation_enabled:
                self._image_adapter = SeedreamImageAdapter()
        return self._image_adapter
```

#### 步骤 5：新建生图 API（框架）

**新建文件**：`backend/app/api/image.py`

```python
"""AI 生图 API（框架版 — 配置留空时返回未配置提示）"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_id
from app.adapters import adapter_factory
from app.config import settings

router = APIRouter(prefix="/api/v1/image", tags=["AI生图"])


class ImageGenerateRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    style: str = "default"


@router.post("/generate", summary="生成图片")
def generate_image(
    data: ImageGenerateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if not settings.image_generation_enabled:
        raise HTTPException(status_code=400, detail="AI生图未配置，请联系管理员配置 Seedream API Key")

    adapter = adapter_factory.get_image_adapter()
    if not adapter:
        raise HTTPException(status_code=400, detail="无可用的生图适配器")

    result = adapter.generate(data.prompt, data.size, data.style)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {"code": 0, "message": "success", "data": {
        "image_url": result.image_url,
        "prompt": result.prompt,
        "size": result.size,
        "style": result.style,
    }}


@router.get("/status", summary="生图配置状态")
def get_image_status():
    return {"code": 0, "message": "success", "data": {
        "enabled": settings.image_generation_enabled,
        "platform": "seedream" if settings.image_generation_enabled else None,
        "model": settings.SEEDREAM_MODEL if settings.image_generation_enabled else None,
    }}
```

#### 步骤 6：注册路由

- `backend/app/api/__init__.py`：注册 `image_router`
- `backend/app/main.py`：`app.include_router(image_router)`

#### T09 验证

```bash
cd backend
python -c "from app.adapters.image_seedream import SeedreamImageAdapter; print('生图适配器OK')"
python -c "from app.api.image import router; print('生图API OK')"
# 测试未配置时的行为
python -c "
from app.config import settings
print(f'生图已配置: {settings.image_generation_enabled}')
# 应该是 False（因为 .env 中没有 SEEDREAM_API_KEY）
"
```

#### T09 完成标准

- [ ] config.py 新增 SEEDREAM 配置项（默认空）
- [ ] BaseImageAdapter 抽象基类已创建
- [ ] SeedreamImageAdapter 框架已创建（未配置时返回明确错误）
- [ ] adapter_factory 支持 get_image_adapter()
- [ ] 生图 API 已注册，未配置时返回 400 错误
- [ ] /image/status 接口返回配置状态
- [ ] 后续填入 SEEDREAM_API_KEY 和 SEEDREAM_BASE_URL 后，补充 TODO 中的 API 调用逻辑即可使用

---

## 5. Session 划分与执行顺序

### 推荐：3 个 Session 串行执行

| Session | 负责任务 | 预计文件数 | 前置依赖 |
|---|---|---|---|
| **Session 1** | T01（Workspace+AsyncTask+Worker）+ T02（Distribution状态机）+ T03（分析器修复）+ 数据库迁移 | 后端约 12 个文件 | 无 |
| **Session 2** | T04（采集异步化）+ T05（任务API+前端任务中心） | 后端 3 个 + 前端 4 个 | 依赖 Session 1 |
| **Session 3** | T06（P0联调验收）+ T07（内容机会）+ T08（文章生成升级）+ T09（生图框架） | 后端约 10 个 + 前端修改 | 依赖 Session 1+2 |

### 每个 Session 的执行流程

1. **开始前**：Read `docs/EXECUTION_GUIDE.md`，找到自己负责的任务单元
2. **执行前**：Read 任务单元中列出的"前置读取"文件，确认当前代码状态
3. **执行中**：按步骤逐一修改/新建文件，每完成一个文件运行语法检查
4. **完成后**：运行任务单元的"验证"步骤，全部通过后标记完成
5. **遇到问题**：在文档末尾"问题记录"区追加，不要自行猜测修改方案

### 关键规则

- **不要跳步**：T01 没完成不要开始 T04（T04 依赖 AsyncTask）
- **每个 Session 结束前必须运行验证步骤**
- **Session 2 开始前确认 Session 1 的所有验证通过**
- **Session 3 的 T06 是 P0 总验收，必须通过后才能继续 T07-T09**

---

## 6. 常见问题排查

### Q1: 启动 Worker 时提示 "No module named 'app.worker'"
A: 确认在 `backend/` 目录下执行，且 `backend/app/worker/__init__.py` 文件存在。

### Q2: 数据库迁移脚本报错 "duplicate column name"
A: 说明列已经存在，脚本的 `ensure_column` 函数应该先检查再添加。确认 `PRAGMA table_info` 查询逻辑正确。

### Q3: Worker 启动后任务一直是 queued 不执行
A: 检查：1) Worker 进程是否真的在运行；2) `task_registry` 中是否注册了对应 task_type；3) `collector_tasks.py` 是否被 import（在 worker.py 中有 `import app.worker.collector_tasks`）。

### Q4: 前端任务中心页面空白
A: 检查：1) 路由是否注册；2) `TaskCenter.tsx` 是否有语法错误（运行 `npx tsc --noEmit`）；3) API 是否返回正确数据。

### Q5: LLM 分析器调用失败
A: 检查 `.env` 中 GLM/MiniMax 的 API Key 是否有效。LLM 分析器复用现有文本适配器，如果文本采集正常但分析失败，检查 prompt 是否过长（截断到 3000 字符）。

### Q6: 修改 model 后数据库没有新列
A: 表结构变更必须通过 `scripts/migrate_v2.py` 执行，SQLAlchemy 的 `create_all` 不会自动添加新列到已存在的表。

### Q7: 前端调用 API 返回 401
A: 检查 token 是否有效，`localStorage` 中的 `geo_token` 是否存在。本地开发如果 IAM 未配置，可以临时在 `deps.py` 中注释掉验证逻辑返回 `user_id=1`（但不要提交这种代码）。

---

## 7. 完成检查表

### P0 完成检查
- [ ] T01: 数据库迁移成功，Workspace/AsyncTask 表已创建，Worker 可启动
- [ ] T02: Distribution 状态机可用，非法流转被拒绝
- [ ] T03: 分析器 bug 已修复，证据字段已保存
- [ ] T04: 采集接口异步化，不再阻塞
- [ ] T05: 任务中心页面可用，自动刷新
- [ ] T06: P0 联调验收通过，无回归

### P1 完成检查
- [ ] T07: 内容机会识别可用，能生成 missing_mention/missing_citation/low_rank 机会
- [ ] T08: 文章生成引擎 LLM 驱动，内容中心有内容机会 Tab
- [ ] T09: 生图适配器框架就绪，配置项留空

### 全局检查
- [ ] 所有后端模块 `python -c "import ..."` 无错误
- [ ] 前端 `npx tsc --noEmit` 无错误
- [ ] 数据库迁移脚本可幂等运行
- [ ] 现有功能（仪表盘/语义库/内容中心/数据中心）无回归
- [ ] 没有删除任何旧表、旧字段、旧 API
- [ ] 所有新表都有 workspace_id 字段
- [ ] 代码中没有硬编码的敏感信息（API Key 等）

---

## 8. 问题记录

> 执行过程中发现的方案遗漏或错误，记录在这里，不要自行修改方案。

| 日期 | 任务单元 | 问题描述 | 解决方案 |
|---|---|---|---|
| 2026-09-14 | T01/T02 | T01 迁移脚本在数据库中为 `geo_article_distribution` 表添加了 6 个新列（scheduled_at/failed_reason/retry_count/publish_mode/external_task_id/verified_at），但 `models/distribution.py` 中没有对应的 SQLAlchemy Column，导致 T02 的 DistributionService 和 API 访问这些字段时报 AttributeError | 在 `models/distribution.py` 中补充了 6 个新列的 Column 定义，同时将 `status` 默认值从 "published" 改为 "draft"，`published_at` 改为 nullable=True（状态机模式下创建时不一定已发布） |
| 2026-09-14 | T01/T03 | T01 迁移脚本在数据库中为 `geo_monitor_record` 表添加了 6 个新列（mention_evidence/recommendation_evidence/citation_urls/analyzer_version/raw_sources_json/is_recommendation），但 `models/monitor.py` 中没有对应的 SQLAlchemy Column，导致 T03 的 collector.py 保存这些字段时报错 | 在 `models/monitor.py` 中补充了 6 个新列的 Column 定义 |
| 2026-09-14 | T03 | `geo_aeo_analyzer.py` 的 `_extract_rank` 方法中"按条目计数"兜底逻辑：当回答中没有列表结构时，`re.split` 返回单元素列表，`enumerate` 的 i=0，代码 `return i if i > 0 else 1` 仍返回 1，与手册注释"无法确定排名，返回 None（不再默认1）"及手册自带的单元测试预期（无序列表 rank=None）矛盾 | 在"按条目计数"逻辑前增加 `if len(items) > 1` 守卫，仅当回答中确实存在列表结构（split 后多个元素）时才适用条目计数；单元素（无列表结构）直接 fall through 到 `return None` |
| 2026-09-14 | T06 | T06 端到端测试中 Worker 执行 geo_refresh 任务时报 `AttributeError: 'Settings' object has no attribute 'brand_aliases'`。原因是 `engines/collector.py` 第 23 行 `AnswerParser(settings.brand_aliases)` 访问了 `config.py` 中未定义的配置项，导致采集引擎初始化失败（预存 bug，非 T04/T05 引入） | 在 `config.py` 的 Settings 类"监测配置"区补充 `BRAND_ALIASES: List[str] = []` 配置项，pydantic-settings 自动从 .env 解析（逗号分隔或 JSON 数组） |
| 2026-09-14 | T08 | T08 验证 ArticleGenerator 时发现 `config.py` 缺少 LLM 配置项（`LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`/`LLM_TEMPERATURE`），但 `engines/llm_analyzer.py` 和 `engines/article_generator.py` 均引用了这些配置项，导致访问时抛 `AttributeError`（预存 bug，非 T08 引入）。ArticleGenerator 因有 try/except 能降级到模板，但 LLM 分析器会直接失败 | 在 `config.py` 的 Settings 类补充 LLM 配置区：`LLM_API_KEY: str = ""`、`LLM_BASE_URL: str = ""`、`LLM_MODEL: str = ""`、`LLM_TEMPERATURE: float = 0.7` |
| 2026-09-14 | T08 | 配置 GLM API Key 后端到端测试时发现 `article_generator.py` 的 `_generate_with_llm` 方法使用 `litellm` 库调用 LLM，但项目 Python 3.11 环境中未安装 `litellm`，导致每次都走模板降级路径（`No module named 'litellm'`）。而项目已有完整的 `adapter_factory` 体系（GLM/MiniMax 均已配置），`llm_analyzer.py` 就是用的 adapter_factory | 将 `article_generator.py` 的 `_generate_with_llm` 方法从 `litellm.completion()` 改为 `adapter_factory.get_adapter(platforms[0]).query(prompt, system_prompt=...)`，与 LLM 分析器保持一致的调用方式，无需额外依赖。修改后 LLM 文章生成正常（来源=llm，正文 1131 字，JSON 解析成功） |

---

**文档版本**：v1.0
**创建日期**：2026-09-14
**适用项目**：GEO（C:\Users\jenac\Desktop\GEO）
**执行范围**：P0 全部 + P1 的 T07/T08/T09
