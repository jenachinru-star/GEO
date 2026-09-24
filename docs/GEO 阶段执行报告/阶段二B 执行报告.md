## 阶段二 B 执行完成报告

**Git commit**: `cf4ed0f` — 16 files changed, 416 insertions(+), 60 deletions(-)

### 13 项修复状态

表格

| 编号 | 修复项                    | 状态 | 改动文件                                                     |
| ---- | ------------------------- | ---- | ------------------------------------------------------------ |
| B1   | knowledge 检索 level 越权 | ✅    | 新建 `utils/level_guard.py` + `api/knowledge.py`             |
| B2   | RAG 问答 level 越权       | ✅    | `api/rag.py`                                                 |
| B3   | 视频 status 无用户隔离    | ✅    | 新建 `models/video_task.py` + `api/video.py` + `database.py` |
| B4   | 生图无配额 + 不记用量     | ✅    | `worker/image_tasks.py` + `usage_logger.py`(支持显式 cost)   |
| B5   | 生视频无配额 + 不记用量   | ✅    | `api/video.py`（配额检查 402 + succeeded 记用量，usage_logged 去重） |
| B6   | PDF 导出同步阻塞          | ✅    | 新建 `worker/export_tasks.py` + `api/asset_export.py` + `worker/worker.py` |
| B7   | 导出 HTML XSS             | ✅    | `api/asset_export.py`（markdown_to_html 统一 html.escape）   |
| B8   | 导出无配额 + 大文件       | ✅    | `api/asset_export.py`（check_quota + 20 万字上限）           |
| B9   | DEBUG=True 默认           | ✅    | `config.py`（默认 False+is_debug）+ `database.py` + `main.py` |
| B10  | 无 API 速率限制           | ✅    | 新建 `middleware/rate_limit.py` + `main.py`（每 IP 120 次 / 分） |
| B11  | 用量队列无界 OOM          | ✅    | `usage_logger.py`（maxsize=10000 + 丢弃计数）                |
| B12  | SQLite 未开 WAL           | ✅    | `database.py`（WAL + NORMAL + busy_timeout=5000）            |
| B13  | adapter 无重试            | ✅    | `adapters/openai_compatible.py` + `adapters/image_seedream.py`（max_retries=2） |

### 验证结果

表格

| 验证项                | 结果                                                         |
| --------------------- | ------------------------------------------------------------ |
| 后端完整 import       | ✅ `from app.main import app` 通过，43 路由                   |
| level_guard 功能      | ✅ 普通用户 confidential→internal，admin 保持 confidential    |
| XSS 转义              | ✅ `<script>` 和 `<b>` 均被转义                               |
| VideoTask 表          | ✅ 已创建，含 usage_logged 字段（14 列）                      |
| WAL 模式              | ✅ `PRAGMA journal_mode` 返回 `wal`                           |
| 用量队列              | ✅ maxsize=10000，满时丢弃 + warning                          |
| 后端启动              | ✅ 无 ERROR，DB 初始化 / 用量日志 / 定时任务 / 2 Worker 均正常 |
| 健康检查              | ✅ 200 OK                                                     |
| 速率限制              | ✅ 健康检查不限流，中间件正常注册                             |
| asset_export 任务注册 | ✅ Worker 已注册，8 种任务类型                                |
| 前端 tsc              | ⚠️ 7 个预先存在的错误（AssetDetail/AssetHub/UsageDashboard），与本次改动无关 |

### 执行中与手册的偏差（已确认方案）

1. **配额接口**：手册写的 `quota_checker.check()` 不存在，实际用 `check_quota(db, user_id)`（抛 QuotaError）。生图固定 0.1 元 / 次、生视频 0.5 元 / 次，通过 `estimated_cost` 显式传入（usage_logger 已增强支持）。
2. **B6 函数适配**：手册引用的 `build_html_content` 不存在，改用 `build_markdown_content` → `markdown_to_html` → weasyprint。`include_*` 参数保留在 payload 中但暂不使用。
3. **B5 去重**：VideoTask 加 `usage_logged` 布尔字段，防止轮询重复记用量。
4. **B8 上限**：20 万字（手册原 10 万字，已确认放宽）。
5. **B10 中间件**：首次实现时缺少 `app` 参数和错误的 `__call__` 签名，已修复为继承 `BaseHTTPMiddleware` + `dispatch` 方法。

### 未完成项 / 后续建议

- 前端 tsc 的 7 个预先存在错误未修复（不在本次范围内）
- `MODEL_PRICING` 未添加 seedream/seedance 条目（通过显式 `estimated_cost` 绕过，如需价格表统一管理可后续补充）
- `build_markdown_content` 的 `include_*` 可选参数未实现（payload 已预留，后续可扩展）