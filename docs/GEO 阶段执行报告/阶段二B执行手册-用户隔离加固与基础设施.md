# 阶段二B执行手册：用户隔离加固 + 资产导出修复 + 基础设施

> 本手册包含13项修复，分3组：用户隔离加固5项、资产导出修复3项、基础设施5项。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：b4067a1（工作区必须干净）
- 执行模式：按需确认，命令行操作会弹窗确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个）

## 13项修复总览

### 第一组：用户隔离加固（5项）

| 编号 | 修复项 | 严重度 | 涉及文件 |
|------|--------|--------|---------|
| B1 | knowledge检索level越权 | P1 | knowledge.py + rag_engine.py |
| B2 | RAG问答level越权 | P1 | rag.py + rag_engine.py |
| B3 | 视频status查询无用户隔离 | P1 | video.py + 新建video_task模型 |
| B4 | 生图无配额检查+不记用量 | P1 | image_tasks.py |
| B5 | 生视频无配额+不记用量+任务不入库 | P1 | video.py + 新建video_tasks.py |

### 第二组：资产导出修复（3项）

| 编号 | 修复项 | 严重度 | 涉及文件 |
|------|--------|--------|---------|
| B6 | PDF导出weasyprint同步阻塞 | P1 | asset_export.py + 新建export_tasks.py |
| B7 | 导出HTML未转义XSS | P1 | asset_export.py |
| B8 | 导出功能无配额+大文件超时 | P2 | asset_export.py |

### 第三组：基础设施（5项）

| 编号 | 修复项 | 严重度 | 涉及文件 |
|------|--------|--------|---------|
| B9 | DEBUG=True默认开启 | P1 | config.py |
| B10 | 无API速率限制 | P1 | main.py + deps.py |
| B11 | 用量日志队列无界OOM风险 | P1 | usage_logger.py |
| B12 | SQLite未开WAL读写互斥 | P1 | database.py |
| B13 | adapter层无重试机制 | P1 | openai_compatible.py |

## 执行顺序

严格按 B1→B2→B3→B4→B5→B6→B7→B8→B9→B10→B11→B12→B13 的顺序执行。每完成一项做一次静态检查，全部完成后统一启动验证。

---

## 第一组：用户隔离加固

### B1：knowledge检索level越权

**根因**：`knowledge.py:79` 的 `search_knowledge` 接口中，`level` 参数直接从前端传入，普通用户可传 `level="confidential"` 越权检索机密级知识库。

**修复目标**：服务端按用户角色计算level上限，忽略前端越权值。

**改动1：knowledge.py search_knowledge 加角色校验**

**文件**：`backend/app/api/knowledge.py`

```python
# before（第78-85行）
@router.post("/search", summary="语义检索知识库")
def search_knowledge(query: str, level: str = "public", top_k: int = 5, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rag = RAGEngine(db)
    results = rag.search_knowledge(query, top_k=top_k, level=level)
    return {"code": 0, "message": "success", "data": [
        {"id": k.id, "title": k.title, "content": k.content, "score": float(score), "category": k.category}
        for k, score in results
    ]}

# after
@router.post("/search", summary="语义检索知识库")
def search_knowledge(query: str, level: str = "public", top_k: int = 5, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    from app.models.user import User
    from app.utils.level_guard import get_effective_level

    # 按用户角色计算实际可访问的level上限
    user = db.query(User).filter(User.id == user_id).first()
    is_admin = user and user.role == "admin"
    effective_level = get_effective_level(level, is_admin)

    rag = RAGEngine(db)
    results = rag.search_knowledge(query, top_k=top_k, level=effective_level)
    return {"code": 0, "message": "success", "data": [
        {"id": k.id, "title": k.title, "content": k.content, "score": float(score), "category": k.category}
        for k, score in results
    ]}
```

**改动2：新建 level_guard.py 工具**

**文件**：`backend/app/utils/level_guard.py`（新建）

```python
"""知识库访问级别防护工具

级别定义：
- public: 公开级，所有用户可访问
- internal: 内部级，登录用户可访问
- confidential: 机密级，仅admin可访问
"""

# 级别层级（数字越大越敏感）
LEVEL_ORDER = {"public": 0, "internal": 1, "confidential": 2}

# 普通用户可访问的最高级别
DEFAULT_MAX_LEVEL = "internal"
# admin可访问的最高级别
ADMIN_MAX_LEVEL = "confidential"


def get_effective_level(requested_level: str, is_admin: bool = False) -> str:
    """根据用户角色计算实际可访问的级别

    Args:
        requested_level: 前端请求的级别
        is_admin: 是否管理员

    Returns:
        实际生效的级别（不超过用户权限上限）
    """
    max_level = ADMIN_MAX_LEVEL if is_admin else DEFAULT_MAX_LEVEL
    max_order = LEVEL_ORDER.get(max_level, 1)
    requested_order = LEVEL_ORDER.get(requested_level, 0)

    # 如果请求的级别超过用户权限，降级到用户可访问的最高级别
    if requested_order > max_order:
        return max_level
    return requested_level
```

**验证**：
- 静态检查：`C:\Users\jenac\miniconda3\python.exe -c "from app.utils.level_guard import get_effective_level; print(get_effective_level('confidential', False))"` 应输出 `internal`
- 运行时验证：普通用户传level=confidential，实际检索结果不包含confidential级条目

---

### B2：RAG问答level越权

**根因**：`rag.py:16` 的 `rag_query` 接口中，`data.level` 直接传给 `rag.generate_answer()`，普通用户可越权用confidential级别问答。

**修复目标**：同B1，服务端按角色校验level。

**改动**：

**文件**：`backend/app/api/rag.py`

```python
# before（第13-18行）
def rag_query(data: RAGQuery, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rag = RAGEngine(db)
    history = data.history or []
    result = rag.generate_answer(data.query, data.platform, data.level, history)

# after
def rag_query(data: RAGQuery, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    from app.models.user import User
    from app.utils.level_guard import get_effective_level

    user = db.query(User).filter(User.id == user_id).first()
    is_admin = user and user.role == "admin"
    effective_level = get_effective_level(data.level, is_admin)

    rag = RAGEngine(db)
    history = data.history or []
    result = rag.generate_answer(data.query, data.platform, effective_level, history)
```

**验证**：同B1，普通用户传level=confidential时实际用internal。

---

### B3：视频status查询无用户隔离

**根因**：`video.py:57` 的 `get_video_status` 接口中，`task_id` 是外部视频平台的任务ID，没有关联到本地用户。任何登录用户传入任意task_id都能查询视频状态和URL，存在越权。

**修复目标**：视频生成任务入库（VideoTask表），status查询时校验task归属。

**改动1：新建 VideoTask 模型**

**文件**：`backend/app/models/video_task.py`（新建）

```python
"""视频生成任务模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from app.database import Base
from datetime import datetime


class VideoTask(Base):
    """视频生成任务记录"""
    __tablename__ = "video_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    external_task_id = Column(String(128), index=True, nullable=False)  # 外部平台任务ID
    prompt = Column(Text, default="")
    image_url = Column(String(512), default="")
    duration = Column(Integer, default=5)
    resolution = Column(String(20), default="720p")
    status = Column(String(20), default="pending")  # pending/running/succeeded/failed
    video_urls = Column(Text, default="[]")  # JSON数组
    error_message = Column(Text, default="")
    platform = Column(String(50), default="seedance")
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
```

**改动2：video.py generate_video 入库**

**文件**：`backend/app/api/video.py`

```python
# before（第20-54行）
@router.post("/generate", summary="提交视频生成任务")
def generate_video(
    req: GenerateVideoRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """提交视频生成异步任务，返回 task_id"""
    if not adapter_factory.is_video_configured():
        raise HTTPException(
            status_code=400,
            detail="生视频功能未配置：请在 .env 中设置 SEEDANCE_API_KEY 和 SEEDANCE_BASE_URL"
        )

    video_adapter = adapter_factory.get_video_adapter()
    if not video_adapter:
        raise HTTPException(status_code=400, detail="生视频适配器不可用")

    result = video_adapter.generate_async(
        prompt=req.prompt,
        image_url=req.image_url,
        duration=req.duration,
        resolution=req.resolution,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message or "提交视频任务失败")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": result.task_id,
            "status": result.status,
        }
    }

# after
@router.post("/generate", summary="提交视频生成任务")
def generate_video(
    req: GenerateVideoRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """提交视频生成异步任务，返回 task_id"""
    from app.models.video_task import VideoTask
    import json

    if not adapter_factory.is_video_configured():
        raise HTTPException(
            status_code=400,
            detail="生视频功能未配置：请在 .env 中设置 SEEDANCE_API_KEY 和 SEEDANCE_BASE_URL"
        )

    video_adapter = adapter_factory.get_video_adapter()
    if not video_adapter:
        raise HTTPException(status_code=400, detail="生视频适配器不可用")

    result = video_adapter.generate_async(
        prompt=req.prompt,
        image_url=req.image_url,
        duration=req.duration,
        resolution=req.resolution,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error_message or "提交视频任务失败")

    # 入库记录
    task = VideoTask(
        user_id=user_id,
        external_task_id=result.task_id,
        prompt=req.prompt,
        image_url=req.image_url or "",
        duration=req.duration,
        resolution=req.resolution,
        status=result.status or "pending",
    )
    db.add(task)
    db.commit()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": result.task_id,
            "status": result.status,
        }
    }
```

**改动3：video.py get_video_status 加用户隔离**

**文件**：`backend/app/api/video.py`

```python
# before（第57-79行）
@router.get("/status/{task_id}", summary="查询视频生成任务状态")
def get_video_status(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """查询视频生成任务状态"""
    if not adapter_factory.is_video_configured():
        raise HTTPException(status_code=400, detail="生视频功能未配置")

    video_adapter = adapter_factory.get_video_adapter()
    result = video_adapter.get_status(task_id)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": task_id,
            "status": result.status,
            "video_urls": result.video_urls,
            "error_message": result.error_message,
        }
    }

# after
@router.get("/status/{task_id}", summary="查询视频生成任务状态")
def get_video_status(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """查询视频生成任务状态（校验用户归属）"""
    from app.models.video_task import VideoTask
    from datetime import datetime
    import json

    # 先查本地记录，校验归属
    local_task = db.query(VideoTask).filter(
        VideoTask.external_task_id == task_id,
        VideoTask.user_id == user_id
    ).first()
    if not local_task:
        raise HTTPException(status_code=404, detail="视频任务不存在或不属于当前用户")

    if not adapter_factory.is_video_configured():
        raise HTTPException(status_code=400, detail="生视频功能未配置")

    video_adapter = adapter_factory.get_video_adapter()
    result = video_adapter.get_status(task_id)

    # 更新本地状态
    local_task.status = result.status or local_task.status
    if result.video_urls:
        local_task.video_urls = json.dumps(result.video_urls, ensure_ascii=False)
    if result.error_message:
        local_task.error_message = result.error_message
    if result.status in ("succeeded", "failed") and not local_task.finished_at:
        local_task.finished_at = datetime.utcnow()
    db.commit()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": task_id,
            "status": result.status,
            "video_urls": result.video_urls,
            "error_message": result.error_message,
        }
    }
```

**改动4：main.py init_db 注册 VideoTask 表**

**文件**：`backend/app/main.py` 或 `database.py` 的 init_db 中导入 VideoTask 模型。

新session先 Read main.py 的 init_db 部分，确认模型导入列表，加入 `video_task`。

**验证**：
- 静态检查：import不报错
- 运行时验证：用户A生成视频拿到task_id，用户B用同一个task_id查status应返回404

---

### B4：生图无配额检查+不记用量

**根因**：阶段二A把生图改异步了，但 `image_tasks.py` 的 `handle_image_generate` 中没有配额检查，也没有记录LLM用量。

**修复目标**：生图任务执行前检查配额，完成后记录用量。

**改动**：

**文件**：`backend/app/worker/image_tasks.py`

新session先 Read image_tasks.py 确认当前代码，然后在 `handle_image_generate` 函数中：

1. **入口加配额检查**：
```python
from app.utils.quota_checker import quota_checker
from app.usage_context import usage_context

# 配额检查
quota_ok, quota_msg = quota_checker.check(user_id, "image_generate", estimated_tokens=500)
if not quota_ok:
    raise ValueError(f"配额不足: {quota_msg}")
```

2. **设置 usage_context**：
```python
usage_context.set(user_id=user_id, task_type="image_generate", ref_id=task.id)
```

3. **完成后记用量**：
```python
from app.usage_logger import usage_logger
usage_logger.log(
    platform="seedream",
    model="seedream-4.0",
    prompt_tokens=len(prompt),
    completion_tokens=0,
    total_tokens=len(prompt),
    user_id=user_id,
    task_type="image_generate",
    ref_id=task.id,
    success=True,
)
```

**注意**：新session必须先 Read image_tasks.py 和 quota_checker.py 确认实际接口签名，再做精确修改。

**验证**：生图任务执行后，usage_log表应有对应记录；配额不足时任务应failed并提示配额不足。

---

### B5：生视频无配额+不记用量+任务不入库

**根因**：视频生成（video.py）没有配额检查，不记录用量，且任务不入库（B3已修复入库）。

**修复目标**：视频生成入口加配额检查，完成后（status查询时）记录用量。

**改动1：video.py generate_video 加配额检查**

**文件**：`backend/app/api/video.py`

在 `generate_video` 函数中，调用 `video_adapter.generate_async()` 之前加配额检查：

```python
from app.utils.quota_checker import quota_checker

# 配额检查（视频生成估算消耗较大）
quota_ok, quota_msg = quota_checker.check(user_id, "video_generate", estimated_tokens=2000)
if not quota_ok:
    raise HTTPException(status_code=402, detail=f"配额不足: {quota_msg}")
```

**改动2：video.py get_video_status 完成后记用量**

在 `get_video_status` 中，当任务状态为 succeeded 时记录用量：

```python
from app.usage_logger import usage_logger

if result.status == "succeeded" and local_task.finished_at:
    usage_logger.log(
        platform="seedance",
        model="seedance-1.0",
        prompt_tokens=len(local_task.prompt),
        completion_tokens=0,
        total_tokens=len(local_task.prompt),
        user_id=user_id,
        task_type="video_generate",
        ref_id=local_task.id,
        success=True,
    )
```

**注意**：新session必须先 Read quota_checker.py 确认实际接口签名。

**验证**：视频生成后usage_log表有记录；配额不足时返回402。

---

## 第二组：资产导出修复

### B6：PDF导出weasyprint同步阻塞

**根因**：`asset_export.py` 中PDF导出同步调用 `weasyprint.HTML(string=...).write_pdf()`，大文件耗时10-60秒，阻塞HTTP请求。

**修复目标**：PDF导出改为异步任务，投递AsyncTask后由Worker执行，前端轮询。

**改动1：新建 export_tasks.py**

**文件**：`backend/app/worker/export_tasks.py`（新建）

```python
"""资产导出相关任务的处理函数"""
import json
import logging
from sqlalchemy.orm import Session
from app.models.task import AsyncTask
from app.models.asset import AssetDocument, AssetNote
from app.worker.task_registry import register_handler, ProgressCallback

logger = logging.getLogger(__name__)


def handle_asset_export(db: Session, task: AsyncTask, on_progress: ProgressCallback = None) -> dict:
    """处理资产导出任务（PDF等耗时格式）"""
    payload = json.loads(task.payload_json or "{}")
    document_id = payload.get("document_id")
    export_format = payload.get("format", "pdf")
    include_summary = payload.get("include_summary", True)
    include_notes = payload.get("include_notes", True)
    include_abstract = payload.get("include_abstract", True)
    user_id = task.created_by

    if not document_id:
        raise ValueError("payload 中缺少 document_id")

    if on_progress:
        on_progress(1, 3, "查询资产文档")

    doc = db.query(AssetDocument).filter(
        AssetDocument.id == document_id, AssetDocument.user_id == user_id
    ).first()
    if not doc:
        raise ValueError("资产文档不存在或不属于当前用户")

    notes = db.query(AssetNote).filter(AssetNote.document_id == document_id).all()

    if on_progress:
        on_progress(2, 3, f"生成{export_format.upper()}中")

    # 复用 asset_export.py 中的内容构建函数
    from app.api.asset_export import build_html_content, build_markdown_content

    if export_format == "pdf":
        html_content = build_html_content(doc, notes, include_summary, include_notes, include_abstract)
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            # PDF存到文件，返回下载路径
            import os
            export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            filename = f"asset_{document_id}_{task.id}.pdf"
            filepath = os.path.join(export_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_bytes)
            if on_progress:
                on_progress(3, 3, "导出完成")
            return {"download_url": f"/api/v1/asset/export/download/{filename}", "filename": filename}
        except ImportError:
            raise ValueError("weasyprint未安装，无法导出PDF")
    elif export_format == "md":
        md_content = build_markdown_content(doc, notes)
        return {"content": md_content, "filename": f"{doc.title}.md"}
    else:
        raise ValueError(f"不支持的导出格式: {export_format}")


register_handler("asset_export", handle_asset_export)
```

**改动2：worker.py 导入 export_tasks**

**文件**：`backend/app/worker/worker.py`

在导入区加：`import app.worker.export_tasks  # noqa: F401`

**改动3：asset_export.py PDF分支改投递任务**

**文件**：`backend/app/api/asset_export.py`

新session先 Read asset_export.py 的导出接口（POST /export），找到PDF分支，改为：

```python
# before：同步调用weasyprint生成PDF，直接返回
# after：如果format是pdf，投递AsyncTask，返回task_id
if data.format == "pdf":
    task = AsyncTask(
        task_type="asset_export",
        status="queued",
        created_by=user_id,
        payload_json=json.dumps({
            "document_id": data.document_id,
            "format": "pdf",
            "include_summary": data.include_summary,
            "include_notes": data.include_notes,
            "include_abstract": data.include_abstract,
        }, ensure_ascii=False),
        progress_message="PDF导出等待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "PDF导出任务已提交", "data": {"task_id": task.id, "status": "queued"}}
```

md/html等轻量格式保持同步导出。

**改动4：新增下载接口**

在 asset_export.py 中新增：
```python
@router.get("/download/{filename}", summary="下载导出文件")
def download_export(filename: str, user_id: int = Depends(get_current_user_id)):
    import os
    from fastapi.responses import FileResponse
    export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "exports")
    filepath = os.path.join(export_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="导出文件不存在")
    return FileResponse(filepath, filename=filename)
```

**注意**：新session必须先 Read asset_export.py 确认实际接口代码和函数签名，再做精确修改。

**验证**：
- 静态检查：import不报错
- 运行时验证：请求PDF导出应立即返回task_id，任务中心显示"资产导出"任务，完成后result中有download_url

---

### B7：导出HTML未转义XSS

**根因**：`asset_export.py` 的 `build_html_content` 函数中，文档标题、内容、笔记等用户输入直接插入HTML，未做转义，存在存储型XSS。

**修复目标**：所有用户输入插入HTML前用 `html.escape()` 转义。

**改动**：

**文件**：`backend/app/api/asset_export.py`

新session先 Read `build_html_content` 函数，找到所有直接插入用户内容的地方，加 `html.escape()`。

```python
# before
lines.append(f"<h1>{doc.title}</h1>")
lines.append(f"<div>{doc.content}</div>")
# ... 其他直接插入用户内容的地方

# after
import html
lines.append(f"<h1>{html.escape(doc.title)}</h1>")
lines.append(f"<div>{html.escape(doc.content)}</div>")
# ... 所有用户输入都加 html.escape()
```

**注意**：`html.escape()` 会转义 `<`, `>`, `&`, `"`, `'`，确保安全。但如果内容中有意保留HTML格式（如富文本），需要用白名单消毒而非全转义。新session需判断内容来源，纯文本用escape，富文本用sanitize。

**验证**：导出包含 `<script>alert(1)</script>` 的文档，HTML中应显示为转义后的文本，不执行脚本。

---

### B8：导出功能无配额+大文件超时

**根因**：导出功能不检查配额，大文档导出（尤其是PDF）可能超时或消耗大量资源。

**修复目标**：导出入口加配额检查（轻量格式扣少量token，PDF扣较多），加文档大小限制。

**改动**：

**文件**：`backend/app/api/asset_export.py`

在导出接口入口加：

```python
from app.utils.quota_checker import quota_checker

# 配额检查
estimated = 500 if data.format in ("md", "html") else 2000  # PDF消耗更多
quota_ok, quota_msg = quota_checker.check(user_id, "asset_export", estimated_tokens=estimated)
if not quota_ok:
    raise HTTPException(status_code=402, detail=f"配额不足: {quota_msg}")

# 文档大小限制（防止超大文档导出超时）
if doc.content and len(doc.content) > 100000:  # 10万字上限
    raise HTTPException(status_code=400, detail="文档过大（超过10万字），请拆分后导出")
```

**注意**：新session必须先 Read quota_checker.py 确认实际接口签名。

**验证**：配额不足时返回402；超过10万字返回400。

---

## 第三组：基础设施

### B9：DEBUG=True默认开启

**根因**：`config.py` 中 `DEBUG: bool = True`，生产环境默认开启调试模式，会暴露SQL日志和详细错误信息。

**修复目标**：默认False，按 `APP_ENV` 判断（development=True，production=False）。

**改动**：

**文件**：`backend/app/config.py`

```python
# before
class Settings(BaseSettings):
    APP_NAME: str = "GEO Doctor Platform"
    DEBUG: bool = True
    # ...

# after
class Settings(BaseSettings):
    APP_NAME: str = "GEO Doctor Platform"
    APP_ENV: str = "development"  # development / production
    DEBUG: bool = False
    # ...

    @property
    def is_debug(self) -> bool:
        """根据APP_ENV决定是否开启调试模式"""
        return self.APP_ENV == "development"
```

然后把所有引用 `settings.DEBUG` 的地方改为 `settings.is_debug`（主要是 database.py 的 `echo=settings.DEBUG`）。

**注意**：新session先 Grep 搜索 `settings.DEBUG` 的所有引用点，逐一改为 `settings.is_debug`。

**验证**：不设置APP_ENV时DEBUG=False；设置APP_ENV=development时DEBUG=True。

---

### B10：无API速率限制

**根因**：项目没有任何API速率限制，恶意用户可暴力调用接口（尤其是LLM相关接口），导致资源耗尽。

**修复目标**：引入 `slowapi` 限流，对认证接口和LLM接口加限流。

**改动1：安装 slowapi**

```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m pip install slowapi limits
```

**改动2：main.py 注册限流中间件**

**文件**：`backend/app/main.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**改动3：对关键接口加限流装饰器**

对登录接口（auth.py）加：`@limiter.limit("5/minute")`
对LLM采集触发接口加：`@limiter.limit("10/minute")`
对导出接口加：`@limiter.limit("20/minute")`

**注意**：slowapi的装饰器需要Request对象，接口签名要加 `request: Request`。新session先 Read 要加限流的接口，确认签名后修改。

**简化方案**：如果slowapi集成复杂，可以先用一个简单的内存限流中间件：

```python
# app/middleware/rate_limit.py
import time
from collections import defaultdict
from fastapi import Request, HTTPException

class RateLimitMiddleware:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)

    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        # 清理1分钟前的记录
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < 60]
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
```

在 main.py 中注册：`app.add_middleware(RateLimitMiddleware, requests_per_minute=120)`

**建议**：先用简单中间件方案（不引入新依赖），后续再升级slowapi。

**验证**：快速连续请求超过限制时返回429。

---

### B11：用量日志队列无界OOM风险

**根因**：`usage_logger.py:46` 中 `self._queue: queue.Queue = queue.Queue()` 是无界队列，高并发下如果写入速度超过刷盘速度，队列会无限增长导致OOM。

**修复目标**：队列加 `maxsize=10000`，满时丢弃最旧记录并warning。

**改动**：

**文件**：`backend/app/usage_logger.py`

```python
# before（第40-48行）
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self._queue: queue.Queue = queue.Queue()
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

# after
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0, max_queue_size: int = 10000):
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_queue_size = max_queue_size
        self._dropped_count = 0  # 丢弃计数
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
```

然后修改 `log()` 方法，队列满时丢弃：

```python
# 在 log() 方法中，put之前检查
try:
    self._queue.put_nowait(entry)
except queue.Full:
    self._dropped_count += 1
    if self._dropped_count % 100 == 0:  # 每100条打一次warning，避免日志洪水
        logger.warning(f"用量日志队列已满（maxsize={self._max_queue_size}），已丢弃 {self._dropped_count} 条记录")
```

**验证**：队列满时不崩溃，日志显示丢弃warning。

---

### B12：SQLite未开WAL读写互斥

**根因**：`database.py` 中SQLite使用默认的journal模式（DELETE），读写互斥，并发写入时会报 `database is locked`。阶段二A的采集并发会加剧这个问题。

**修复目标**：开启WAL（Write-Ahead Logging）模式，读写不互斥，并发性能大幅提升。

**改动**：

**文件**：`backend/app/database.py`

```python
# before（第15-19行）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

# after
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# 开启WAL模式（SQLite并发性能优化）
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")  # WAL模式下可降低同步级别
        cursor.execute("PRAGMA busy_timeout=5000")  # 锁等待超时5秒
        cursor.close()
```

**注意**：
- WAL模式需要SQLite 3.7+（现代系统都满足）
- WAL模式会产生 `-wal` 和 `-shm` 文件，是正常的
- `synchronous=NORMAL` 在WAL模式下是安全的，性能更好
- `busy_timeout=5000` 避免 `database is locked` 错误

**验证**：启动后检查 `PRAGMA journal_mode` 应返回 `wal`；并发写入不再报 `database is locked`。

---

### B13：adapter层无重试机制

**根因**：`openai_compatible.py` 中 `OpenAI(client=...)` 没有设置 `max_retries`，网络抖动或代理临时不可用时直接失败。阶段一移除了collector层的双重重试，但adapter层本身也没有重试。

**修复目标**：OpenAI client设置 `max_retries=2`（共3次尝试），对429/503/500等可重试错误自动重试。

**改动**：

**文件**：`backend/app/adapters/openai_compatible.py`

```python
# before（第19-26行）
    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000,
                 timeout: int = 120):
        super().__init__(api_key, base_url, model, temperature, max_tokens)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

# after
    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.3, max_tokens: int = 2000,
                 timeout: int = 120, max_retries: int = 2):
        super().__init__(api_key, base_url, model, temperature, max_tokens)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
```

**注意**：
- OpenAI SDK的 `max_retries` 默认是2，所以实际上可能已经有重试了。新session先确认当前OpenAI SDK版本的默认值。
- 如果默认已经是2，这个改动只是显式化，没有实际变化。但显式设置更清晰。
- 重试只对可重试错误（429/500/502/503/504/网络错误）生效，对400/401等不重试。
- 阶段一的熔断机制（`_failed_platforms`）仍然有效，重试2次后如果仍然失败，会触发熔断。

**验证**：模拟代理503时，日志应显示重试（OpenAI SDK的 `Retrying request` 日志），最多3次尝试。

---

## 全部完成后的统一验证

13项全部修改完成后，按以下步骤统一验证：

### 1. 后端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -c "from app.main import app; print('import OK')"
```

### 2. 前端静态检查
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npx tsc --noEmit
```

### 3. 启动后端
```bash
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\miniconda3\python.exe -m uvicorn app.main:app --port 8000
```
确认无ERROR，路由正常注册，Worker启动正常，WAL模式开启。

### 4. 功能验证清单

| 验证项 | 操作 | 预期 |
|--------|------|------|
| B1/B2 level越权 | 普通用户传level=confidential | 实际降级为internal，不返回机密内容 |
| B3 视频status隔离 | 用户B查用户A的task_id | 返回404 |
| B4/B5 配额用量 | 生图/生视频后查usage_log | 有对应记录 |
| B6 PDF异步导出 | 请求PDF导出 | 立即返回task_id，任务中心显示导出任务 |
| B7 HTML XSS | 导出含script的文档 | HTML中转义不执行 |
| B8 导出配额 | 配额不足时导出 | 返回402 |
| B9 DEBUG默认 | 不设APP_ENV启动 | DEBUG=False，无SQL日志 |
| B10 速率限制 | 快速连续请求 | 超过限制返回429 |
| B11 队列有界 | 高并发下 | 队列满时丢弃+warning，不OOM |
| B12 WAL模式 | 启动后查PRAGMA | journal_mode=wal |
| B13 adapter重试 | 模拟503 | 日志显示重试，最多3次 |

### 5. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段二B-用户隔离加固+资产导出修复+基础设施（13项）"
```

---

## 注意事项

1. **B4/B5配额检查**：必须先 Read `quota_checker.py` 确认实际接口签名，不要凭记忆调用。
2. **B6 PDF异步导出**：是本阶段最大的改动，涉及新建export_tasks.py、改asset_export.py、新增下载接口。新session必须先 Read asset_export.py 确认实际代码结构。
3. **B7 HTML转义**：要判断内容是纯文本还是富文本，纯文本用escape，富文本用白名单消毒。不要一刀切全转义导致格式丢失。
4. **B10速率限制**：建议先用简单中间件方案（不引入新依赖），不要强行集成slowapi。
5. **B12 WAL模式**：开启后数据库目录会出现 `-wal` 和 `-shm` 文件，是正常的，不要删除。
6. **每完成一项做一次静态检查**，不要全部改完才检查。

## 最终输出

完成后输出报告：
1. 13项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. 验证结果
4. git commit hash
5. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的文件，确认当前代码状态。
