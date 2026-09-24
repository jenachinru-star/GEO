# 阶段三A执行手册：平台配置统一 + UserPlatformPref全链路 + 后端补丁

> 本手册包含11项修复，分3组：UserPlatformPref全链路5项、Platform表生效3项、后端临时补丁3项。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 后端路径：C:\Users\jenac\Desktop\GEO\backend
- 前端路径：C:\Users\jenac\Desktop\GEO\frontend
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：a0f2d99（工作区必须干净）
- 执行模式：按需确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个）

## 当前平台配置系统的混乱状态（必须理解）

项目目前有**三套平台配置系统**，互相不统一：

| 配置源 | 位置 | 实际生效？ | 谁在读 |
|--------|------|-----------|--------|
| .env | backend/.env | ✅ 唯一实际生效 | adapter_factory（所有LLM调用） |
| Platform表 | geo_platform表 | ❌ 完全不生效 | 只有管理员CRUD接口，adapter_factory不读 |
| UserPlatformPref表 | user_platform_pref表 | ⚠️ 部分生效 | 只有collector.py查（阶段二A修复），其他引擎不查 |

**核心问题**：
1. 用户在前端停用 deepseek 后，collector 不调用了（阶段二A已修），但**语义生成、语义延伸、文章生成、LLM分析、RAG问答**仍然调用 deepseek
2. 管理员在 PlatformConfig 页面修改平台配置（改base_url/api_key/model），**完全不生效**，因为 adapter_factory 只读 .env
3. 前端 PlatformConfig.tsx 文案写"数据库配置优先于.env配置"，与实际完全相反

## 11项修复总览

### 第一组：UserPlatformPref全链路（5项）

| 编号 | 修复项 | 涉及文件 |
|------|--------|---------|
| D1 | semantic_generator 查用户平台开关 | engines/semantic_generator.py |
| D2 | semantic_extender 查用户平台开关 | engines/semantic_extender.py |
| D3 | article_generator 查用户平台开关 | engines/article_generator.py |
| D4 | llm_analyzer 查用户平台开关 | engines/llm_analyzer.py |
| D5 | rag 查用户平台开关 | engines/rag.py |

### 第二组：Platform表生效（3项）

| 编号 | 修复项 | 涉及文件 |
|------|--------|---------|
| D6 | adapter_factory 支持从Platform表读取（数据库优先，.env兜底） | adapters/factory.py |
| D7 | 数据迁移：从.env同步平台配置到Platform表 | migrations/sync_platform_from_env.py |
| D8 | 前端PlatformConfig文案修正+管理员修改后调用reload | PlatformConfig.tsx + api/platform.py |

### 第三组：后端临时补丁（3项）

| 编号 | 修复项 | 涉及文件 |
|------|--------|---------|
| D9 | usage.py 新增用量导出接口 | api/usage.py |
| D10 | article.py 列表加 keyword 搜索 | api/article.py |
| D11 | article.py 列表返回统计字段 | api/article.py |

## 执行顺序

严格按 D1→D2→...→D11 的顺序执行。每完成一项做一次静态检查，全部完成后统一启动验证。

---

## 第一组：UserPlatformPref全链路（5项）

> **通用模式**：每个引擎的 `generate()` / `analyze()` 方法中，获取平台列表后，查询 UserPlatformPref 表过滤用户停用的平台。与阶段二A collector.py 的修复模式一致。

### D1：semantic_generator 查用户平台开关

**根因**：`semantic_generator.py:87` 中 `platforms = adapter_factory.get_enabled_platforms()` 只从.env读取，不查用户级开关。用户停用 deepseek 后，语义生成仍然调用 deepseek。

**改动**：

**文件**：`backend/app/engines/semantic_generator.py`

新session先 Read 整个文件，确认 `generate()` 方法的结构和 user_id 的来源。然后在获取平台列表后加过滤：

```python
# 在 generate() 方法中，获取 platforms 后加
from app.models.user_platform_pref import UserPlatformPref

if user_id:
    disabled = {
        pref.platform_code for pref in
        db.query(UserPlatformPref).filter(
            UserPlatformPref.user_id == user_id,
            UserPlatformPref.enabled == False
        ).all()
    }
    if disabled:
        logger.info(f"用户 [{user_id}] 已停用平台: {disabled}，语义生成时跳过")
        platforms = [p for p in platforms if p not in disabled]

if not platforms:
    raise ValueError("没有已启用的AI平台，请在设置中启用至少一个平台")
```

**注意**：
- 新session确认 semantic_generator 的 generate() 方法是否有 db 和 user_id 参数。如果没有，需要从调用方传入。
- semantic_generator 可能被 semantic_api.py 调用，新session确认调用链，确保 user_id 能传进来。
- 如果 platforms 过滤后为空，应抛异常或返回错误，不要静默返回空结果。

**验证**：用户停用 deepseek 后触发生成语义，日志显示"已停用平台"，不出现 deepseek 调用。

---

### D2：semantic_extender 查用户平台开关

**根因**：`semantic_extender.py:160` 中 `platforms = adapter_factory.get_enabled_platforms()` 不查用户开关。

**改动**：

**文件**：`backend/app/engines/semantic_extender.py`

与D1相同的模式。新session先 Read 文件，确认 `extend()` 方法的结构，加 UserPlatformPref 过滤。

**注意**：semantic_extender 的 `_get_adapter()` 方法（第108行）可能直接取 `platforms[0]`，阶段一补丁已经加了 failover。新session确认当前代码，确保过滤后 platforms 不为空。

**验证**：同D1。

---

### D3：article_generator 查用户平台开关

**根因**：`article_generator.py:92` 中 `platforms = adapter_factory.get_enabled_platforms()` 不查用户开关。第97行 `adapter = adapter_factory.get_adapter(platforms[0])` 直接取第一个平台。

**改动**：

**文件**：`backend/app/engines/article_generator.py`

新session先 Read `_generate_with_llm()` 方法（约第88-120行），加 UserPlatformPref 过滤：

```python
# 获取 platforms 后加过滤
from app.models.user_platform_pref import UserPlatformPref

if user_id:
    disabled = { ... }  # 同D1
    platforms = [p for p in platforms if p not in disabled]

if not platforms:
    # 回退到模板生成（article_generator 有模板兜底逻辑）
    logger.warning("没有已启用的AI平台，使用模板兜底")
    return self._generate_from_template(semantic, profile, opportunity)
```

**注意**：article_generator 有 LLM 优先、模板兜底的逻辑。如果用户停用了所有平台，应该回退到模板生成，而不是报错。新session确认 `_generate_from_template()` 方法的存在和签名。

**验证**：用户停用所有平台后生成文章，应回退到模板生成，不报错。

---

### D4：llm_analyzer 查用户平台开关

**根因**：`llm_analyzer.py:66` 中 `platforms = adapter_factory.get_enabled_platforms()` 不查用户开关。第68行 `return adapter_factory.get_adapter(platforms[0])` 直接取第一个。

**改动**：

**文件**：`backend/app/engines/llm_analyzer.py`

新session先 Read `_get_adapter()` 方法（约第60-70行），加 UserPlatformPref 过滤。

**注意**：llm_analyzer 是在 collector.py 的采集过程中调用的（`llm_analyzer.analyze(answer, ...)`），user_id 需要从 collector 传进来。新session确认调用链，确保 user_id 能传递。

如果 llm_analyzer 的 `analyze()` 方法没有 user_id 参数，需要：
1. 给 `analyze()` 加 user_id 参数
2. collector.py 调用时传入 user_id

**验证**：用户停用 deepseek 后采集，LLM分析环节不调用 deepseek。

---

### D5：rag 查用户平台开关

**根因**：`rag.py:110` 中 `adapter = adapter_factory.get_adapter(platform_code)`，platform_code 从请求参数传入，不查用户开关。用户停用 deepseek 后，RAG问答仍然可以选择 deepseek。

**改动**：

**文件**：`backend/app/engines/rag.py`

新session先 Read `generate_answer()` 方法（约第100-130行），加 UserPlatformPref 过滤：

```python
# 在选择 adapter 前加
from app.models.user_platform_pref import UserPlatformPref

if user_id:
    disabled = { ... }  # 同D1
    if platform_code in disabled:
        # 用户停用了请求的平台，自动回退到第一个启用的平台
        enabled = [p for p in adapter_factory.get_enabled_platforms() if p not in disabled]
        if enabled:
            platform_code = enabled[0]
            logger.info(f"用户 [{user_id}] 已停用原平台，自动回退到 {platform_code}")
        else:
            raise ValueError("没有已启用的AI平台")
```

**注意**：rag.py 可能被 api/rag.py 调用，新session确认 user_id 能传进来。

**验证**：用户停用 deepseek 后用 deepseek 做RAG问答，应自动回退到其他启用的平台。

---

## 第二组：Platform表生效（3项）

> **设计原则**：数据库优先，.env兜底。Platform表有数据时从Platform表读取，Platform表为空或读取失败时回退到.env。这样既支持管理员在前端管理配置，又保证.env作为安全兜底。

### D6：adapter_factory 支持从Platform表读取

**根因**：`factory.py` 的 `_init_adapters()` 完全从.env读取，不读Platform表。管理员在前端修改Platform表完全不生效。

**修复目标**：
1. 新增 `load_from_db(db)` 方法，从Platform表读取配置并初始化适配器
2. `_init_adapters()` 保持从.env读取（作为兜底）
3. 新增 `reload_from_db(db)` 方法，管理员修改配置后调用
4. main.py 启动时调用 `load_from_db()`（如果Platform表有数据）

**改动1：factory.py 新增 load_from_db 和 reload_from_db**

**文件**：`backend/app/adapters/factory.py`

在 AdapterFactory 类中新增方法：

```python
    def load_from_db(self, db):
        """从Platform表读取配置并初始化适配器（数据库优先）

        如果Platform表有启用的平台配置，用数据库配置覆盖.env配置。
        如果Platform表为空，保持.env配置不变。
        """
        from app.models.platform import Platform
        from app.adapters.openai_compatible import OpenAICompatibleAdapter

        try:
            db_platforms = db.query(Platform).filter(Platform.status == True).all()
            if not db_platforms:
                logger.info("Platform表为空，使用.env配置")
                return

            logger.info(f"从Platform表读取 {len(db_platforms)} 个平台配置")
            new_adapters = {}
            for p in db_platforms:
                try:
                    adapter = OpenAICompatibleAdapter(
                        api_key=p.api_key,
                        base_url=p.base_url,
                        model=p.model,
                        temperature=p.temperature or 0.3,
                        max_tokens=p.max_tokens or 2000,
                        timeout=p.timeout or 120,
                    )
                    adapter.platform_code = p.code
                    new_adapters[p.code] = adapter
                    logger.info(f"  平台 {p.code} 已从数据库加载")
                except Exception as e:
                    logger.error(f"  平台 {p.code} 加载失败: {e}，回退到.env配置")
                    # 回退到.env配置
                    env_adapter = self._adapters.get(p.code)
                    if env_adapter:
                        new_adapters[p.code] = env_adapter

            self._adapters = new_adapters
            logger.info(f"Platform表配置加载完成，共 {len(self._adapters)} 个平台")
        except Exception as e:
            logger.error(f"从Platform表加载配置失败，保持.env配置: {e}")

    def reload_from_db(self, db):
        """重新从Platform表加载配置（管理员修改后调用）"""
        # 先重置为.env配置
        self._adapters = {}
        self._init_adapters()
        # 再从数据库加载覆盖
        self.load_from_db(db)
```

**改动2：main.py 启动时调用 load_from_db**

**文件**：`backend/app/main.py`

新session先 Read lifespan 函数，在数据库初始化后、Worker启动前加：

```python
# 在 init_db() 之后加
from app.adapters import adapter_factory
from app.database import SessionLocal
db = SessionLocal()
try:
    adapter_factory.load_from_db(db)
finally:
    db.close()
```

**注意**：
- OpenAICompatibleAdapter 是所有文本平台的通用适配器（DeepSeek/GLM/MiniMax/Doubao都继承它），所以可以统一用 OpenAICompatibleAdapter 初始化。
- 但如果某个平台有特殊逻辑（如 DoubaoAdapter 有特殊的 header），需要用对应的子类。新session确认各个适配器类的继承关系，如果都是 OpenAICompatibleAdapter 的子类且没有特殊逻辑，可以统一用 OpenAICompatibleAdapter。
- api_key 在 Platform 表中是明文存储的。阶段一已经有 `app/utils/crypto.py` 加密工具，但 Platform 表当前没有加密。本阶段先保持明文（与.env一致），加密留到后续优化。
- 生图/生视频适配器（SeedreamImageAdapter/SeedanceVideoAdapter）仍然从.env读取，不在Platform表管理范围内（Platform表只管理文本LLM平台）。

**验证**：
- Platform表为空时，adapter_factory使用.env配置（与之前行为一致）
- Platform表有数据时，adapter_factory使用数据库配置
- 修改Platform表后调用reload_from_db，适配器配置更新

---

### D7：数据迁移：从.env同步平台配置到Platform表

**根因**：Platform表当前0行数据。需要把.env中的平台配置同步到Platform表，作为初始数据。

**修复目标**：创建迁移脚本，从.env读取已配置的平台，写入Platform表（幂等，已存在则跳过）。

**改动**：

**文件**：`backend/migrations/sync_platform_from_env.py`（新建）

```python
"""从.env同步平台配置到Platform表（幂等迁移）

运行方式：
    cd backend
    C:\\Users\\jenac\\miniconda3\\python.exe -m migrations.sync_platform_from_env
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.platform import Platform
from app.config import settings

# 平台配置映射（.env字段 -> Platform表字段）
PLATFORM_CONFIG_MAP = {
    "deepseek": {
        "name": "DeepSeek",
        "api_key": settings.DEEPSEEK_API_KEY,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "model": settings.DEEPSEEK_MODEL,
    },
    "glm": {
        "name": "GLM",
        "api_key": settings.GLM_API_KEY,
        "base_url": settings.GLM_BASE_URL,
        "model": settings.GLM_MODEL,
    },
    "minimax": {
        "name": "MiniMax",
        "api_key": settings.MINIMAX_API_KEY,
        "base_url": settings.MINIMAX_BASE_URL,
        "model": settings.MINIMAX_MODEL,
        "timeout": settings.MINIMAX_TIMEOUT,
    },
    "doubao": {
        "name": "豆包",
        "api_key": settings.DOUBAO_API_KEY,
        "base_url": settings.DOUBAO_BASE_URL,
        "model": settings.DOUBAO_MODEL or "doubao-seed-1.6",
    },
}


def run_migration():
    # 确保表存在
    Base.metadata.create_all(bind=engine, tables=[Platform.__table__])

    db = SessionLocal()
    try:
        synced = 0
        skipped = 0
        for code, config in PLATFORM_CONFIG_MAP.items():
            if not config["api_key"] or not config["base_url"]:
                print(f"  跳过 {code}: .env中未配置")
                skipped += 1
                continue

            existing = db.query(Platform).filter(Platform.code == code).first()
            if existing:
                print(f"  跳过 {code}: 已存在（id={existing.id}）")
                skipped += 1
                continue

            p = Platform(
                code=code,
                name=config["name"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                status=True,
                priority=100,
                timeout=config.get("timeout", 120),
                max_tokens=settings.MONITOR_MAX_TOKENS,
                temperature=settings.MONITOR_TEMPERATURE,
                platform_type="openai_compatible",
            )
            db.add(p)
            synced += 1
            print(f"  同步 {code}: {config['name']} ({config['model']})")

        db.commit()
        print(f"\n✅ 同步完成：新增 {synced} 个，跳过 {skipped} 个")
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始从.env同步平台配置到Platform表...")
    run_migration()
```

然后在手册的验证步骤中，让新session运行这个脚本：
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m migrations.sync_platform_from_env
```

**注意**：
- 迁移脚本是幂等的，已存在的平台会跳过
- 运行后Platform表应有4条数据（deepseek/glm/minimax/doubao，取决于.env配置了哪些）
- 运行后需要重启后端，让adapter_factory从Platform表加载配置

**验证**：运行迁移脚本后，查询Platform表应有数据；重启后端后adapter_factory从Platform表加载。

---

### D8：前端PlatformConfig文案修正+管理员修改后调用reload

**根因**：
1. `PlatformConfig.tsx` 文案写"数据库配置优先于.env配置"，但实际是.env唯一生效
2. 管理员修改Platform表后，没有调用adapter_factory.reload_from_db()，修改不生效

**修复目标**：
1. 前端文案修正为"数据库配置优先，.env兜底"
2. 后端平台配置CRUD接口中，修改/删除后调用adapter_factory.reload_from_db()
3. 前端修改成功后提示"配置已生效"

**改动1：后端 api/platform.py 加 reload**

**文件**：`backend/app/api/platform.py`

新session先 Read 整个文件，找到创建/更新/删除平台的接口，在操作成功后加：

```python
# 在创建/更新/删除平台成功后，db.commit() 之后加
from app.adapters import adapter_factory
adapter_factory.reload_from_db(db)
logger.info(f"平台配置已变更，adapter_factory已重新加载")
```

**注意**：reload_from_db 需要 db session，新session确认接口中的 db 变量可用。

**改动2：前端 PlatformConfig.tsx 文案修正**

**文件**：`frontend/src/components/PlatformConfig.tsx`

新session先 Read 文件，找到"数据库配置优先于.env配置"的文案，改为：
```
数据库配置优先，.env兜底（修改后立即生效，无需重启）
```

同时，修改成功后的提示从"保存成功"改为"配置已生效"。

**验证**：
- 管理员在前端修改平台配置（如改model名），保存后立即生效，不需要重启
- 前端文案显示"数据库配置优先，.env兜底"

---

## 第三组：后端临时补丁（3项）

### D9：usage.py 新增用量导出接口

**根因**：阶段二C的C1中，UsageDashboard的导出按钮调用 `exportApi.exportUsage()`，但后端没有 `/usage/export` 接口。前端临时禁用了按钮。

**修复目标**：后端新增用量导出接口，前端启用导出按钮。

**改动1：后端 usage.py 新增导出接口**

**文件**：`backend/app/api/usage.py`

新session先 Read 文件末尾，新增导出接口：

```python
@router.get("/export", summary="导出用量统计为Excel")
def export_usage(
    days: int = Query(30, description="导出最近N天的数据"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出用量统计为Excel文件"""
    from app.models.usage import LlmUsageLog
    from datetime import datetime, timedelta
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    # 管理员可导出所有用户，普通用户只导出自己的
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    is_admin = user and user.role == "admin"

    query = db.query(LlmUsageLog)
    if not is_admin:
        query = query.filter(LlmUsageLog.user_id == user_id)

    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(LlmUsageLog.created_at >= start_date)
    logs = query.order_by(LlmUsageLog.created_at.desc()).all()

    # 生成Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "用量统计"
    ws.append(["时间", "用户ID", "平台", "模型", "任务类型", "prompt_tokens", "completion_tokens", "total_tokens", "耗时(ms)", "成功"])
    for log in logs:
        ws.append([
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
            log.user_id,
            log.platform,
            log.model,
            log.task_type,
            log.prompt_tokens,
            log.completion_tokens,
            log.total_tokens,
            log.latency_ms,
            "是" if log.success else "否",
        ])

    # 自适应列宽
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)

    # 输出为文件流
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"用量统计_{days}天_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

**注意**：
- 新session确认 LlmUsageLog 模型的字段名（prompt_tokens/completion_tokens/total_tokens/latency_ms等），如果字段名不同需要调整。
- 导出接口走 `downloadFile`（带token），所以需要确认前端 exportApi.exportUsage 的URL路径正确。
- openpyxl 应该已经安装（项目有Excel导出功能），新session确认依赖。

**改动2：前端启用导出按钮**

**文件**：`frontend/src/pages/UsageDashboard.tsx`

新session先 Read 文件，找到被禁用的导出按钮，移除 disabled 和 Tooltip，恢复正常点击。

同时在 `api/index.ts` 的 exportApi 中确认 exportUsage 方法存在（阶段二C可能已经加了但被注释）。

**验证**：管理员点击导出Excel，下载包含用量数据的xlsx文件；普通用户只能导出自己的数据。

---

### D10：article.py 列表加 keyword 搜索

**根因**：阶段二C的C6中，ContentHub搜索只过滤当前页，因为后端 article.py 列表接口不支持 keyword 参数。前端临时用拉全量本地过滤。

**修复目标**：后端 article.py 列表接口加 keyword 参数，支持标题和内容搜索。前端改回后端搜索。

**改动1：后端 article.py 加 keyword**

**文件**：`backend/app/api/article.py`

```python
# before（第17-29行）
def get_articles(
    semantic_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id)
    if semantic_id:
        query = query.filter(ArticleDraft.semantic_id == semantic_id)
    if status:
        query = query.filter(ArticleDraft.status == status)

# after
def get_articles(
    semantic_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = Query(None, description="搜索关键词（标题+内容）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = db.query(ArticleDraft).filter(ArticleDraft.user_id == user_id)
    if semantic_id:
        query = query.filter(ArticleDraft.semantic_id == semantic_id)
    if status:
        query = query.filter(ArticleDraft.status == status)
    if keyword:
        query = query.filter(
            ArticleDraft.title.like(f"%{keyword}%") |
            ArticleDraft.content.like(f"%{keyword}%")
        )
```

**改动2：前端 ContentHub 改回后端搜索**

**文件**：`frontend/src/pages/ContentHub.tsx`

新session先 Read 文件，找到阶段二C加的全量本地过滤逻辑，改回后端搜索：
- fetchData 传 keyword 参数给后端
- 搜索时 fetchData(1, keyword)
- 翻页时 fetchData(page, keyword)
- 移除 page_size=1000 的全量拉取

**注意**：新session确认前端 articleApi.list 是否支持 keyword 参数。如果 api/index.ts 中的 articleApi.list 不支持 keyword，需要加上。

**验证**：搜索关键词后翻页，结果保持搜索条件，包含全量匹配。

---

### D11：article.py 列表返回统计字段

**根因**：阶段二C的C7中，ContentHub统计只算当前页，因为后端 article.py 列表只返回 total，不返回 published_count/draft_count 等统计字段。前端临时用全量本地统计。

**修复目标**：后端 article.py 列表接口返回统计字段（total/published_count/draft_count/consistent_count）。前端直接使用。

**改动**：

**文件**：`backend/app/api/article.py`

```python
# before（第30-40行）
    total = query.count()
    items = query.order_by(ArticleDraft.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0, "message": "success",
        "data": {
            "total": total,
            "items": [ArticleOut.model_validate(i).model_dump() for i in items],
            "page": page, "page_size": page_size
        }
    }

# after
    total = query.count()
    # 统计各状态数量（基于过滤后的全量数据，不只当前页）
    published_count = query.filter(ArticleDraft.status == "published").count()
    draft_count = query.filter(ArticleDraft.status == "draft").count()
    consistent_count = query.filter(ArticleDraft.entity_consistent == True).count()

    items = query.order_by(ArticleDraft.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0, "message": "success",
        "data": {
            "total": total,
            "published_count": published_count,
            "draft_count": draft_count,
            "consistent_count": consistent_count,
            "items": [ArticleOut.model_validate(i).model_dump() for i in items],
            "page": page, "page_size": page_size
        }
    }
```

**注意**：
- 新session确认 ArticleDraft 模型的 status 字段取值（published/draft等）和 entity_consistent 字段是否存在。
- 如果状态取值不同，需要调整过滤条件。
- 前端 ContentHub 改回使用后端返回的统计字段，移除本地统计逻辑。

**验证**：翻页时统计数字保持不变，反映全量数据。

---

## 全部完成后的统一验证

11项全部修改完成后，按以下步骤统一验证：

### 1. 运行平台配置迁移脚本
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m migrations.sync_platform_from_env
```
确认Platform表有4条数据。

### 2. 后端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
```

### 3. 前端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npx tsc --noEmit
```

### 4. 启动后端
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m uvicorn app.main:app --port 8000
```
确认日志显示"从Platform表读取 N 个平台配置"。

### 5. 功能验证清单（用 liujinru 账号）

| 验证项 | 操作 | 预期 |
|--------|------|------|
| D1-D5 用户平台开关 | 停用deepseek后触发生成语义/延伸/文章/分析/RAG | 日志显示"已停用平台"，不调用deepseek |
| D6 Platform表生效 | Platform表有数据时启动后端 | 日志显示从Platform表加载，适配器使用数据库配置 |
| D7 迁移脚本 | 运行迁移脚本 | Platform表新增4条数据，幂等不重复 |
| D8 管理员修改生效 | 管理员在前端改model名保存 | 立即生效，不需重启，日志显示reload |
| D9 用量导出 | 管理员点击导出Excel | 下载xlsx文件，包含用量数据 |
| D10 文章搜索 | ContentHub搜索后翻页 | 结果保持搜索条件，全量匹配 |
| D11 文章统计 | ContentHub翻页 | 统计数字不变，反映全量 |

### 6. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段三A-平台配置统一+UserPlatformPref全链路+后端补丁（11项）"
```

---

## 注意事项

1. **D1-D5 UserPlatformPref全链路**：每个引擎的 user_id 传递方式可能不同，新session必须先 Read 每个引擎的调用链，确认 user_id 能从API层传到引擎层。如果传不进来，需要修改方法签名加 user_id 参数。
2. **D6 Platform表生效是最大改动**：涉及adapter_factory重构，必须仔细测试。如果Platform表加载失败，应自动回退到.env配置，不能崩溃。
3. **D7 迁移脚本必须运行**：运行后Platform表才有数据，D6才能生效。新session在验证步骤中必须运行迁移脚本。
4. **D8 管理员修改后reload**：reload_from_db会重置所有适配器，正在进行中的LLM调用可能受影响。但考虑到管理员修改配置是低频操作，可以接受。
5. **D9 导出接口**：新session确认 LlmUsageLog 模型的字段名，如果字段名不同需要调整。
6. **D10/D11 前端改回后端搜索/统计**：需要移除阶段二C加的全量本地过滤/统计逻辑，改回正常的分页请求。
7. **每完成一项做一次静态检查**，不要全部改完才检查。
8. **Platform表的api_key是明文**：与.env一致，本阶段不做加密。加密留到后续优化。

## 最终输出

完成后输出报告：
1. 11项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. Platform表迁移结果（新增几条数据）
4. 验证结果
5. git commit hash
6. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的文件，确认当前代码状态。
