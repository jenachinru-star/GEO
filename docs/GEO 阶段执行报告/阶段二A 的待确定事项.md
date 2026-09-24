## 审查发现的待讨论问题

### 问题 1：2.3 Worker 轮询的多线程竞态（重要）

**现状**：`main.py` 第 117 行启动了 **2 个内嵌 Worker 线程**（`for i in range(2)`）。 **手册方案**：用全局变量 `_last_executed_user` 记录上一次执行的用户，实现轮询。 **问题**：两个 Worker 线程同时读写这个全局变量，存在竞态条件 —— 线程 A 读了值还没写回，线程 B 也读了同一个旧值，导致轮询失效。

**建议方案 A（推荐）**：加 `threading.Lock` 保护 `_last_executed_user` 的读写，实现简单且准确。 **方案 B**：用 `threading.local()` 每个线程独立维护，但两个线程可能同时执行同一用户的任务，轮询效果打折。 **方案 C**：不加锁接受小概率不准确。

> 我倾向 **方案 A**，加锁成本极低。

------

### 问题 2：2.6/2.7/2.8 前端异步化的实际范围

我搜索了整个前端 `src` 目录：

表格

| 功能            | 前端调用点                                                | 结论                                |
| --------------- | --------------------------------------------------------- | ----------------------------------- |
| 文章生成（2.6） | `ContentHub.tsx` 第 148 行、第 335 行，共 2 处            | **需要改前端**，改为投递任务 + 轮询 |
| 合规检查（2.7） | **无任何调用点**，`api/index.ts` 中也没有 `complianceApi` | 前端未接入，**只需后端改造**        |
| 生图（2.8）     | **无任何调用点**，`api/index.ts` 中也没有 `imageApi`      | 前端未接入，**只需后端改造**        |

**建议**：2.6 做完整的前后端异步化；2.7/2.8 只做后端异步化（前端还没接入这两个功能，改了也没地方用）。手册注意事项第 1 条也说 "前端改动过于复杂可留到阶段二 C"，这里 2.7/2.8 是根本没有前端代码。

------

### 问题 3：2.7 合规检查的 adapter 选择逻辑

**原代码**（`compliance.py` 第 82 行）：

```
adapter = adapter_factory.get_adapter("glm") or adapter_factory.get_adapter("doubao")
```

有 glm→doubao 的回退逻辑。

**手册代码**写死了用 `glm`，没有回退。

**建议**：保持原有的回退逻辑，glm 不可用时自动用 doubao。

------

### 问题 4：2.2 并发改造中 `_failed_platforms` 熔断的线程安全

`query_single_platform` 中 `self._failed_platforms` 是实例级 `set`，并发调用时 4 个线程可能同时 `add`。

- CPython 的 GIL 保证单次 `set.add()` 原子操作，不会崩溃
- 但逻辑上：平台 A 在第一个线程中失败被标记熔断，第二个线程可能已经在调用平台 A 了（并发同时发出），这是并发的正常现象，影响极小（最多多一次失败调用）

**建议**：不加锁，接受这个极小的竞态。并发的目的就是同时发出请求，"一个失败后其他线程跳过" 在并发首轮中意义不大，后续语义采集时熔断仍然有效。

------

### 问题 5：2.4 user_seq 用 `created_at` 还是 `id` 排序

**手册方案**：`AsyncTask.created_at < t.created_at` 计数 + 1。 **问题**：SQLite 的 DateTime 精度到秒，同一秒内创建的多个任务 `created_at` 相同，会导致序号重复（都是 N）。

**建议**：改用 `AsyncTask.id < t.id` 来计数。id 是全局自增主键，天然保证顺序且唯一，同一用户的任务 id 递增等价于创建时间递增。这比 created_at 更可靠。

------

### 问题 6：新增任务类型的超时配置

`worker.py` 的 `TASK_TIMEOUT_BY_TYPE` 目前只有 4 种类型。新增的 `article_generate`、`compliance_check`、`image_generate` 会落到默认的 600 秒。

- 文章生成：10-120 秒，600 秒够
- 合规检查：5-30 秒，600 秒够
- 生图：5-30 秒，600 秒够

**建议**：在 `TASK_TIMEOUT_BY_TYPE` 中显式新增这三种类型，文章生成给 900 秒（留足余量），合规和生图给 300 秒。这样更清晰，也方便后续调整。

------

### 问题 7：2.6 文章生成 GET→POST 的兼容性

接口从 `GET /template/article/{semantic_id}` 改为 `POST`，这是 breaking change。我已确认前端只有 ContentHub.tsx 两处调用，会同步修改 `api/index.ts` 中的 `templateApi.generateArticle` 为 POST。

**确认**：没有其他地方（如外部脚本、测试）调用这个 GET 接口吧？如果有需要同步通知。

------

### 问题 8：2.9 定时采集与 2.1 的联动

`collector_tasks.py` 中已有 `handle_geo_refresh` → `collect_all_semantics(user_id)` → `collect_one_semantic(...)`。2.1 修改后 `collect_all_semantics` 会把 `user_id` 传给 `collect_one_semantic`，所以定时采集投递的 `geo_refresh` 任务会**自动受益于用户平台过滤**，不需要额外改动。这一点确认无误。

------

## 请确认

以上 8 个问题，我的建议方案汇总：

1. **方案 A**：加锁保护 `_last_executed_user`
2. **2.6 改前端，2.7/2.8 只改后端**
3. **保持 glm→doubao 回退逻辑**
4. **不加锁，接受熔断的小竞态**
5. **用 id 而非 created_at 计算 user_seq**
6. **TASK_TIMEOUT_BY_TYPE 新增 3 种类型**
7. GET→POST 同步改前端（确认无其他调用方）
8. 联动确认无误

请回复是否同意这些方案，或者有不同意见，讨论清楚后我立即开始按 2.1→2.9 顺序执行。