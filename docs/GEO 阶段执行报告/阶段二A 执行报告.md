# 阶段二 A 执行报告：核心架构修复与异步化改造

## 一、9 项修复状态总览

表格

| 编号 | 修复项                          | 严重度 | 状态   | 改动文件数     |
| ---- | ------------------------------- | ------ | ------ | -------------- |
| 2.1  | 用户停用平台后 collector 仍调用 | P1     | ✅ 完成 | 1              |
| 2.2  | 采集 4 平台串行→并发            | P1     | ✅ 完成 | 1              |
| 2.3  | Worker 全局 FIFO→按用户轮询     | P1     | ✅ 完成 | 1              |
| 2.4  | 任务编号全局自增→用户级序号     | P2     | ✅ 完成 | 2              |
| 2.5  | minimax 单独配置超时            | P2     | ✅ 完成 | 3              |
| 2.6  | 文章生成同步阻塞→异步任务       | P1     | ✅ 完成 | 5（含 1 新建） |
| 2.7  | 合规检查同步阻塞→异步任务       | P1     | ✅ 完成 | 3（含 1 新建） |
| 2.8  | 生图同步阻塞→异步任务           | P1     | ✅ 完成 | 3（含 1 新建） |
| 2.9  | 定时采集不走队列→投递 AsyncTask | P1     | ✅ 完成 | 1              |

## 二、每项实际改动详情

### 2.1 用户停用平台过滤

- **文件**：`backend/app/engines/collector.py`
- `collect_one_semantic()`：加 `user_id` 参数，查询 `UserPlatformPref` 过滤停用平台
- `collect_one_question()`：同上
- `collect_all_semantics()`：调用时传入 `user_id=user_id`

### 2.2 采集 4 平台并发

- **文件**：`backend/app/engines/collector.py`
- `collect_one_semantic()` 中平台循环替换为 `ThreadPoolExecutor(max_workers=len(platforms))` 并发调用
- 仅 API 调用并发，LLM 分析（`llm_analyzer.analyze`）仍在主线程串行
- 移除平台间 `time.sleep(1)`，结果按 `platforms` 顺序处理保证记录顺序一致

### 2.3 Worker 按用户轮询

- **文件**：`backend/app/worker/worker.py`
- 新增 `_last_executed_user` 和 `_last_user_lock = threading.Lock()`
- `claim_next_task()`：查所有 queued 任务，优先选与上一次执行用户不同的任务，加锁保护读写
- `TASK_TIMEOUT_BY_TYPE` 新增：`article_generate=600`, `compliance_check=300`, `image_generate=300`

### 2.4 用户级任务序号

- **文件**：`backend/app/api/task.py`、`frontend/src/pages/TaskCenter.tsx`
- `get_task()` 和 `list_tasks()` 返回新增 `user_seq` 字段
- 用 `AsyncTask.id < t.id` 计数（比 created_at 更可靠，避免同秒重复）
- 前端任务列显示 `{类型名} #{user_seq || id}`

### 2.5 minimax 单独超时

- **文件**：`backend/app/config.py`、`backend/app/adapters/openai_compatible.py`、`backend/app/adapters/factory.py`
- `config.py`：新增 `MINIMAX_TIMEOUT: int = 60`
- `openai_compatible.py`：`__init__` 新增 `timeout: int = 120` 参数
- `factory.py`：MiniMaxAdapter 初始化传入 `timeout=settings.MINIMAX_TIMEOUT`
- **验证**：`adapter_factory.get_adapter('minimax').client.timeout` → 60 ✅

### 2.6 文章生成异步化

- **新建**：`backend/app/worker/article_tasks.py` — `handle_article_generate` 处理函数

- `worker.py`：导入 `article_tasks`

- `template.py`：接口从 `GET /article/{semantic_id}` 改为 `POST`，投递 `article_generate` 任务，返回 task_id

- `frontend/src/api/index.ts`：`templateApi.generateArticle` 改为 POST

- ```
  frontend/src/pages/ContentHub.tsx
  ```

  ：

  - 新增 `articlePollTimerRef` 和 `pollArticleTask()` 轮询函数（3 秒间隔）
  - `handleGenerateTemplate()` 和 `handleGenerateFromOpportunity()` 改为投递任务后轮询
  - 组件卸载时 `useEffect` 清除定时器（防内存泄漏）

### 2.7 合规检查异步化

- **新建**：`backend/app/worker/compliance_tasks.py` — `handle_compliance_check` 处理函数
- 保持原有的 `glm → doubao` 回退逻辑
- `worker.py`：导入 `compliance_tasks`
- `compliance.py`：`POST /check` 改为投递 `compliance_check` 任务，无规则 / 无 LLM 时快速失败不投递
- **前端**：无调用点（`api/index.ts` 中无 complianceApi），仅后端改造

### 2.8 生图异步化

- **新建**：`backend/app/worker/image_tasks.py` — `handle_image_generate` 处理函数
- `worker.py`：导入 `image_tasks`
- `image.py`：`POST /generate` 改为投递 `image_generate` 任务，未配置时快速失败不投递
- **前端**：无调用点，仅后端改造

### 2.9 定时采集走队列

- **文件**：`backend/app/main.py`
- `scheduled_collect()`：从查 `Question` 表改为查 `Semantic` 表获取有启用语义的用户
- 从直接同步采集改为投递 `geo_refresh` AsyncTask，由 Worker 执行
- 新增：医生资料检查、防重复投递检查（已有 queued/running 任务则跳过）
- 移除不再使用的 `CollectorEngine` 和 `Question` 导入

## 三、验证结果

表格

| 验证项            | 结果                                                         |
| ----------------- | ------------------------------------------------------------ |
| 后端完整 import   | ✅ `from app.main import app` OK，43 条路由                   |
| 前端 tsc --noEmit | ✅ **0 新增错误**（7 个已有错误在 AssetDetail/AssetHub/UsageDashboard，与本次无关） |
| 任务类型注册      | ✅ 7 种全部注册：`article_generate`, `compliance_check`, `image_generate`, `geo_refresh`, `monitor_collect`, `asset_url_collect`, `asset_file_parse` |
| minimax 超时      | ✅ timeout=60                                                 |
| 每项静态检查      | ✅ 9 项全部通过 import 检查                                   |

## 四、Git 提交

- **Commit**：`b4067a1`
- **分支**：`main`
- **变更**：16 files changed, 507 insertions(+), 156 deletions(-)
- **新建文件**：`article_tasks.py`、`compliance_tasks.py`、`image_tasks.py`

## 五、讨论确认的方案 deviations（与手册不同之处）

1. **2.3 加锁**：手册未提多线程锁，实际 2 个 Worker 线程共享 `_last_executed_user`，已加 `threading.Lock`
2. **2.4 用 id 而非 created_at**：避免 SQLite 秒级精度导致序号重复
3. **2.6/2.7/2.8 前端范围**：2.7/2.8 前端无调用点，仅后端改造；2.6 完整前后端改造
4. **2.7 adapter 回退**：保持原有的 `glm → doubao` 回退，不写死 glm
5. **2.6 超时配置**：article_generate=600 秒（非 900），compliance_check=300，image_generate=300

## 六、后续运行时验证建议

代码层面已全部通过静态验证，以下需在运行时确认（用 liujinru 账号）：

1. 停用 deepseek 后触发采集 → 日志显示 "已停用平台"，无 deepseek 调用
2. 触发采集 → 日志显示 "并发模式，4 个平台"，单语义 < 50 秒
3. 用户 A 发多个任务后用户 B 发任务 → 用户 B 任务被优先认领
4. 任务中心显示 "GEO/AEO 刷新 #N"（用户级序号）
5. 点击生成文章 → 立即返回 task_id，3 秒轮询，完成后渲染文章
6. 手动触发定时采集 → 日志显示 "共投递 N 个采集任务"