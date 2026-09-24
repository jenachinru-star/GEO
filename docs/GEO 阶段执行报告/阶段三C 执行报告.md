# 阶段三 C 执行报告：用量统计优化与明细功能

## 1. 6 项修复状态

表格

| 编号 | 修复项                        | 状态 | 说明                                           |
| ---- | ----------------------------- | ---- | ---------------------------------------------- |
| C1   | 管理员可切换查看任意用户用量  | ✅    | 后端 + 前端完整实现                            |
| C2   | 新增用量明细列表页面          | ✅    | 后端补充筛选参数，前端 10 列表格 + 分页 + 筛选 |
| C3   | 平台统计表格完善（3 列→7 列） | ✅    | 后端补充成功率 / 平均耗时，前端 7 列表格       |
| C4   | 用量趋势图                    | ✅    | ECharts 折线图，支持 7/30/90 天切换            |
| C5   | 任务类型分布饼图              | ✅    | ECharts 环形饼图，支持 7/30/90 天切换          |
| C6   | 费用预估 + 异常告警提示       | ✅    | 今日消耗 / 本月预估 / 用量突增告警             |

## 2. C1 管理员切换用户功能实现方式

**后端**（`usage_governance.py`）：

- `get_my_quota` 增加 `target_user_id: Optional[int] = Query(None)` 参数
- 管理员传入 `target_user_id` 时，校验目标用户存在后切换 `view_user_id`
- 管理员查看自己时不限额（limit=-1），查看其他用户时显示该用户的真实配额
- 返回新增 `view_user_id` 和 `target_user`（含 user_id/username/email）字段
- 普通用户传入 `target_user_id` 会被静默忽略（安全）

**前端**（`UsageGovernance.tsx`）：

- 新增 `viewUserId` state（null = 看自己）
- `loadAll` 改用 `request.get('/usage/quota/my', { params: { target_user_id } })` 直接调用
- `useEffect` 依赖 `viewUserId`，切换时自动重新加载
- "本月 AI 用量" 卡片标题旁新增 `Select` 下拉（仅管理员可见），选项含 "我自己"+ 所有用户
- 查看其他用户时：标题变为 "查看用户：xxx"，隐藏 AI 模型开关卡片，显示 info Alert 提示

## 3. 改动文件与行号

### 后端

**`backend/app/api/usage_governance.py`**（+37 行）

- 第 2 行：新增 `Query` 导入
- 第 107-167 行：`get_my_quota` 函数重写，支持 `target_user_id`

**`backend/app/api/usage.py`**（+34 行）

- 第 474-501 行：`get_my_logs` 新增 `platform`/`task_type` 筛选参数（C2）
- 第 450-490 行：`get_my_by_platform` 重写，新增成功率（`success_rate`）和平均耗时（`avg_latency_ms`）计算，参考管理员接口做法在 Python 层计算避免 SQLite 兼容性问题（C3）

### 前端

**`frontend/src/pages/UsageGovernance.tsx`**（+426/-43 行，共 634 行）

- 第 4 行：新增 `Select, Alert` 组件导入
- 第 7-8 行：新增 `request` default import 和 `ReactECharts` 导入
- 第 18-33 行：新增 `taskTypeNames` 任务类型中文映射（14 种）
- 第 44-61 行：新增 8 组 state（用量明细 7 个 + 平台统计 2 个 + 趋势 2 个 + 任务类型 2 个）
- 第 97-151 行：新增 4 个加载函数 + 4 个 useEffect（loadUsageLogs/loadPlatformStats/loadTrend/loadTaskType）
- 第 217-229 行：新增 `logColumns` 10 列表格列定义
- 第 231-289 行：新增 `formatTokens` 工具函数 + `trendOption` 趋势图配置 + `taskTypeOption` 饼图配置
- 第 291-309 行：新增 C6 计算逻辑（todayCost/todayTokens/estimatedMonthlyCost/abnormalDays）
- 第 329-344 行：C1 用户切换下拉
- 第 347-377 行：C6 Descriptions 新增今日消耗 / 本月预估 + 异常告警 Alert
- 第 370-407 行：C3 平台统计 7 列表格（原 3 列 "各平台本月消耗" 替换）
- 第 411-445 行：C1 查看其他用户时隐藏模型开关 + 提示
- 第 447-491 行：C4+C5 趋势图 + 饼图 Row（各占 14/10 列）
- 第 493-547 行：C2 用量明细卡片（天数筛选 + 平台筛选 + 10 列表格 + 分页）

## 4. 新建函数 / 组件列表

**后端新函数 / 参数**：

- `get_my_quota(target_user_id)` — 新增参数
- `get_my_logs(platform, task_type)` — 新增筛选参数
- `get_my_by_platform()` — 重写，新增 success_rate/avg_latency_ms 字段

**前端新 state（13 个）**： `viewUserId`, `usageLogs`, `logsTotal`, `logsPage`, `logsPageSize`, `logsDays`, `logsLoading`, `logsPlatform`, `platformStats`, `platformDays`, `trendData`, `trendDays`, `taskTypeData`, `taskTypeDays`

**前端新函数（4 个）**： `loadUsageLogs()`, `loadPlatformStats()`, `loadTrend()`, `loadTaskType()`

**前端新配置对象（3 个）**： `logColumns`, `trendOption`, `taskTypeOption`

**前端新计算变量（5 个）**： `todayStr`, `todayCost`, `todayTokens`, `estimatedMonthlyCost`, `abnormalDays`

## 5. 验证结果

表格

| 验证项                               | 结果                                                  |
| ------------------------------------ | ----------------------------------------------------- |
| 后端 import 检查                     | ✅ `from app.main import app` 通过                     |
| 前端 tsc 检查（UsageGovernance.tsx） | ✅ 无类型错误（修复了 1 个 Text type 空字符串问题）    |
| 前端 tsc 检查（其他文件）            | ⚠️ AssetDetail.tsx/AssetHub.tsx 有历史错误，非本次引入 |
| Git 工作区                           | ✅ 提交前干净，仅 3 个目标文件被修改                   |

**功能验证需在浏览器中手动确认**（需登录账号）：

- 管理员登录→用量管理→切换下拉选择用户→显示该用户配额和各平台用量，模型开关隐藏
- 普通用户登录→看不到切换下拉
- 用量明细表格显示时间 / 平台 / 模型 / 任务类型 / Token / 费用 / 耗时 / 状态，支持天数和平台筛选、分页
- 各平台调用对比表格有 7 列（平台 / 模型 / 总 Token / 调用次数 / 成功率 / 平均耗时 / 估算成本）
- Token 消耗趋势折线图、任务类型 Token 分布饼图正常渲染
- 本月 AI 用量卡片显示今日消耗、本月预估，异常时显示告警

## 6. Git Commit

```
commit 80908f6c85c0416d5b08d12899d17c15fe3538f6
Author: ...
Date:   ...

    feat: 阶段三C-用量统计优化与明细功能（6项）

 3 files changed, 454 insertions(+), 43 deletions(-)
```

## 7. 遇到的问题与说明

1. **用户端接口字段名与管理员端不一致**：`/my/trend` 和 `/my/by-task-type` 返回 `tokens` 字段（而非管理员端的 `total_tokens`），图表配置已适配。这是历史设计，本次未改动后端字段名以保持兼容性。
2. **管理员查看其他用户时 C2-C6 明细数据限制**：因 `/my/*` 接口不支持 `target_user_id`，查看其他用户时趋势图 / 饼图 / 用量明细会隐藏或显示 "暂不支持明细数据" 提示。配额卡片（C1）正常显示目标用户数据。后续阶段可考虑为 `/my/*` 接口增加管理员切换能力。
3. **C3 成功率 / 平均耗时计算方式**：参考管理员 `/by-platform` 接口的做法，在 Python 层单独查询成功次数和总延迟，避免 SQLite 下复杂聚合函数的兼容性问题。每个平台模型组合会多 2 次查询，数据量小时无性能问题。
4. **前端 tsc 历史错误**：`AssetDetail.tsx`（2 个）和 `AssetHub.tsx`（3 个）存在类型错误，均为之前阶段引入，与本次阶段三 C 无关，未处理。
5. **`usageGovernanceApi.getMyQuota()` 未修改**：因该方法不支持传参，C1 中直接改用 `request.get()` 调用，保留原 API 方法不变以避免影响其他可能的调用方。