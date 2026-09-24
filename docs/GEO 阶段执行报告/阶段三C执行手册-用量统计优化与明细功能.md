# 阶段三C执行手册：用量统计优化与明细功能

> 本手册优化"用量管理"页面：管理员可切换查看任意用户用量，新增用量明细列表/趋势图/任务类型饼图，完善平台统计表格（3列→7列），增加费用预估/异常告警。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 后端路径：C:\Users\jenac\Desktop\GEO\backend
- 前端路径：C:\Users\jenac\Desktop\GEO\frontend
- 技术栈：后端 Python FastAPI + SQLAlchemy + SQLite，前端 React 18 + TypeScript + Ant Design
- 操作系统：Windows
- git 基线：P0修复后的最新commit（工作区必须干净）
- 执行模式：按需确认
- Python 路径：C:\Users\jenac\miniconda3\python.exe（必须用这个）

## 当前用量统计页面状态（必须理解）

项目有两个用量相关页面：

| 页面 | 前端文件 | 角色 | 内容 |
|------|---------|------|------|
| 用量统计 | pages/UsageDashboard.tsx | 仅管理员 | 总Token/成本/调用次数/活跃用户 + 趋势图 + 任务类型分布 + 各平台调用对比 + 用户排行 |
| 用量管理 | pages/UsageGovernance.tsx | 所有用户 | 本月AI用量（配额/已消耗） + 各平台本月消耗 + AI模型开关 + 用户管理（管理员） |

**两个页面的定位（方案A，分两步走）**：
- **用量统计（UsageDashboard）** = 管理员的系统运营监控中心（全局视角，已有功能完整，阶段四再升级）
- **用量管理（UsageGovernance）** = 个人用量与模型管理中心（所有用户，本次阶段三C优化）

**重要说明（已审查确认，不是bug）**：
- 管理员cczh（user_id=6）账号本月没有发起LLM调用，所以"用量管理"页面显示¥0.00是**正确的**，不是bug。
- 普通用户有调用记录，所以能正常看到用量。
- 数据来源：`GET /usage/quota/my` → `get_my_quota()` → `get_monthly_cost(db, user_id)`，按当前登录用户+本月时间统计 `LlmUsageLog.estimated_cost` 总和，逻辑正确。

**后端接口**（`api/usage.py`）：
- 管理员接口：`/overview`, `/trend`, `/by-task-type`, `/by-platform`, `/by-user`, `/logs`, `/export`
- 用户接口：`/my/overview`, `/my/trend`, `/my/by-task-type`, `/my/by-platform`, `/my/logs`
- 配额接口（`api/usage_governance.py`）：`/quota/my`, `/quota/admin/users` 等

## 阶段三C修复总览（6项）

| 编号 | 修复项 | 类型 | 涉及文件 |
|------|--------|------|---------|
| C1 | 管理员可切换查看任意用户用量 | 新功能 | 后端usage_governance.py + 前端UsageGovernance.tsx |
| C2 | 新增用量明细列表页面 | 新功能 | 前端UsageGovernance.tsx + 后端/my/logs（已有） |
| C3 | 平台统计表格完善（3列→7列） | 优化 | 后端usage.py + 前端UsageGovernance.tsx |
| C4 | 用量趋势图 | 新功能 | 前端UsageGovernance.tsx + 后端/my/trend（已有） |
| C5 | 任务类型分布饼图 | 新功能 | 前端UsageGovernance.tsx + 后端/my/by-task-type（已有） |
| C6 | 费用预估+异常告警提示 | 优化 | 前端UsageGovernance.tsx |

## 执行顺序

严格按 C1→C2→...→C6 的顺序执行。每完成一项做一次静态检查。

---

## C1：管理员可切换查看任意用户用量

### 目标

在"用量管理"页面，管理员可以通过下拉选择切换查看任意用户的用量数据（配额/已消耗/各平台用量）。普通用户只能查看自己的用量，看不到切换下拉。

### 背景

- 当前"用量管理"页面的所有数据都来自当前登录用户（`get_current_user_id`）
- 管理员cczh账号本月没有调用，所以看到¥0.00（正确，但管理员可能想查看其他用户的用量）
- 管理员需要去"用量统计"页面才能看到全局数据，但那里没有个人用量明细

### 后端改动

**文件**：`backend/app/api/usage_governance.py`

**第一步：Read确认当前代码**

Read `usage_governance.py` 的 `get_my_quota` 函数（约第107行），确认当前实现。同时确认文件顶部的导入（`Optional`, `HTTPException`, `User`, `LlmUsageLog` 等是否已导入）。

**第二步：修改 `get_my_quota` 函数，增加 `target_user_id` 参数**

```python
# before（约第107-149行）
@router.get("/quota/my", summary="获取我的配额和当月用量")
def get_my_quota(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """当前用户的配额 + 当月费用 + 各平台用量明细"""
    quota = ensure_user_quota(db, user_id)
    used = get_monthly_cost(db, user_id)
    is_admin = _is_admin(db, user_id)
    # ... 管理员不限额逻辑 ...
    # ... by_platform查询（按user_id） ...
    return {"code": 0, "message": "success", "data": {...}}

# after
@router.get("/quota/my", summary="获取我的配额和当月用量")
def get_my_quota(
    target_user_id: Optional[int] = Query(None, description="管理员可指定查看的用户ID"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """当前用户的配额 + 当月费用 + 各平台用量明细
    管理员可传 target_user_id 查看指定用户的用量；普通用户忽略该参数。
    """
    is_admin = _is_admin(db, user_id)

    # 管理员可切换查看目标用户，普通用户只能看自己
    view_user_id = user_id
    if is_admin and target_user_id and target_user_id != user_id:
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        view_user_id = target_user_id

    quota = ensure_user_quota(db, view_user_id)
    used = get_monthly_cost(db, view_user_id)

    # 管理员查看自己时不限额，查看其他用户时显示该用户的配额
    if is_admin and view_user_id == user_id:
        limit = -1
        pct = 0
    else:
        limit = quota.monthly_cost_limit
        pct = round(used / limit * 100, 1) if limit and limit > 0 else 0

    # 各平台当月用量（按view_user_id统计）
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(
        LlmUsageLog.platform,
        func.sum(LlmUsageLog.total_tokens).label("tokens"),
        func.sum(LlmUsageLog.estimated_cost).label("cost"),
    ).filter(
        LlmUsageLog.user_id == view_user_id,
        LlmUsageLog.created_at >= month_start,
    ).group_by(LlmUsageLog.platform).all()

    by_platform = [{
        "platform": r.platform,
        "tokens": int(r.tokens or 0),
        "cost": round(float(r.cost or 0), 4),
    } for r in rows]

    # 获取目标用户信息（用于前端显示）
    target_user_info = None
    if view_user_id != user_id:
        tu = db.query(User).filter(User.id == view_user_id).first()
        if tu:
            target_user_info = {"user_id": tu.id, "username": tu.username, "email": tu.email or ""}

    return {"code": 0, "message": "success", "data": {
        "monthly_limit": limit,
        "used_cost": round(used, 4),
        "usage_pct": pct,
        "warn_threshold": quota.warn_threshold,
        "is_admin": is_admin,
        "by_platform": by_platform,
        "view_user_id": view_user_id,
        "target_user": target_user_info,
    }}
```

**注意**：
- 新session先Read `usage_governance.py` 的完整代码，确认 `get_my_quota` 的实际实现和行号
- 确认 `Optional` 已从 `typing` 导入，`HTTPException` 已从 `fastapi` 导入，`User` 模型已导入
- 如果 `_is_admin` 函数不存在或名称不同，确认实际的管理员判断方式
- `func` 需要从 `sqlalchemy` 导入（确认已导入）

**第三步：确认管理员用户列表接口**

UsageGovernance.tsx 已调用 `usageGovernanceApi.adminListUsers()` 获取所有用户列表。新session确认这个接口返回的字段（是否包含 `user_id`/`id` 和 `username`），如果字段名不同，前端需要适配。

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

**第一步：Read确认当前代码**

Read UsageGovernance.tsx 的完整代码，确认：
- `loadAll` 函数的实现（第29-55行）
- "本月AI用量"卡片的渲染（第133-165行）
- `usageGovernanceApi.getMyQuota` 的调用方式
- `isAdmin` 的判断方式（`quota?.is_admin`）

**第二步：新增state**

```tsx
const [viewUserId, setViewUserId] = useState<number | null>(null)  // null表示看自己
const [allUsersList, setAllUsersList] = useState<any[]>([])
```

**第三步：修改loadAll函数，支持传target_user_id**

```tsx
const loadAll = async () => {
  setLoading(true)
  try {
    // 加载配额（管理员可传target_user_id）
    const quotaParams = viewUserId ? { target_user_id: viewUserId } : {}
    const qt = await request.get('/usage/quota/my', { params: quotaParams })
    setQuota(qt.data)

    // 加载平台列表
    const pf = await usageGovernanceApi.getAvailablePlatforms()
    setPlatforms(pf.data.platforms || [])

    // 管理员加载额外数据
    if (qt.data.is_admin) {
      const [users, report, allU] = await Promise.all([
        usageGovernanceApi.adminListUsersQuota(),
        usageGovernanceApi.adminUsageReport(),
        usageGovernanceApi.adminListUsers(),
      ])
      setAdminUsers(users.data.users || [])
      setAdminReport(report.data.items || [])
      setAllUsersList(allU.data.users || [])
    }
  } catch (e) {
    console.error('加载失败', e)
  } finally {
    setLoading(false)
  }
}
```

**注意**：原来的 `loadAll` 用的是 `usageGovernanceApi.getMyQuota()`，新session确认 `api/index.ts` 中这个方法是否支持传参。如果不支持，改为直接用 `request.get('/usage/quota/my', { params })`。

**第四步：在"本月AI用量"卡片标题旁加用户切换下拉（仅管理员可见）**

```tsx
<Card
  title={
    <Space>
      <DollarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
      <Title level={4} style={{ margin: 0 }}>
        {quota?.target_user ? `查看用户：${quota.target_user.username}` : '本月AI用量'}
      </Title>
      {isAdmin && (
        <Select
          value={viewUserId}
          onChange={(val) => { setViewUserId(val); }}
          style={{ width: 180, marginLeft: 16 }}
          placeholder="切换查看用户"
          allowClear
          options={[
            { value: null, label: '我自己' },
            ...allUsersList.map(u => ({ value: u.user_id || u.id, label: u.username }))
          ]}
        />
      )}
    </Space>
  }
>
```

**第五步：viewUserId变化时重新加载**

```tsx
// 修改useEffect，把viewUserId加入依赖
useEffect(() => { loadAll() }, [viewUserId])
```

**第六步：管理员查看其他用户时，隐藏模型开关部分**

管理员查看其他用户时，不应该修改该用户的模型开关。在"AI模型开关"卡片上加条件渲染：

```tsx
{(!quota?.target_user) && (
  <Card title={<Space><ApiOutlined /> AI模型开关</Space>} style={{ marginBottom: 20 }}>
    {/* 现有模型开关内容 */}
  </Card>
)}
{quota?.target_user && (
  <Alert
    message="查看其他用户模式"
    description="当前正在查看其他用户的用量数据，模型开关和用户管理仅在查看自己时可用。"
    type="info"
    showIcon
    style={{ marginBottom: 20 }}
  />
)}
```

**注意**：
- 新session先Read UsageGovernance.tsx的完整代码，确认现有结构，在合适的位置加
- 确认 `api/index.ts` 中 `usageGovernanceApi.getMyQuota` 和 `adminListUsers` 的定义
- 确认 `adminListUsers` 返回的用户列表字段名（`user_id` 还是 `id`）
- 导入需要的组件：Select, Alert（确认已导入）
- 管理员查看其他用户时，C2-C6的明细列表/趋势图/饼图暂时只显示自己的数据（因为 `/my/*` 接口不支持target_user_id），可以在这些卡片上加提示"查看其他用户时暂不支持明细数据"

### 验证

1. 管理员登录，"用量管理"页面的"本月AI用量"卡片标题旁出现用户切换下拉
2. 选择某个用户，页面显示该用户的配额和各平台用量
3. 选择"我自己"（或清空），回到自己的用量
4. 普通用户登录，看不到切换下拉
5. 管理员查看其他用户时，模型开关部分隐藏，显示提示

---

## C2：新增用量明细列表页面

### 目标

在"用量管理"页面新增一个**用量明细列表**，显示当前用户每次LLM调用的详细记录，让用户可以看到每个任务消耗了多少token、花了多少钱。

### 后端接口

后端已有 `/usage/my/logs` 接口（`api/usage.py:474`），返回字段：
- `id`：记录ID
- `platform`：平台（glm/minimax/deepseek/doubao等）
- `model`：模型名称
- `prompt_tokens`：输入Token
- `completion_tokens`：输出Token
- `total_tokens`：总Token
- `estimated_cost`：估算成本
- `task_type`：任务类型（geo_refresh/geo_collect/semantic_gen/article_gen等）
- `success`：是否成功
- `latency_ms`：耗时（毫秒）
- `created_at`：调用时间

接口支持参数：`page`, `page_size`, `days`（默认7天）。

**需要确认**：新session先Read `/my/logs` 接口，确认返回字段和分页格式。如果字段有缺失，需要补充。

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

在"AI模型开关"卡片下方，新增一个"用量明细"卡片：

```tsx
// 1. 新增state
const [usageLogs, setUsageLogs] = useState<any[]>([])
const [logsTotal, setLogsTotal] = useState(0)
const [logsPage, setLogsPage] = useState(1)
const [logsPageSize, setLogsPageSize] = useState(20)
const [logsDays, setLogsDays] = useState(7)
const [logsLoading, setLogsLoading] = useState(false)
const [logsPlatform, setLogsPlatform] = useState<string | undefined>(undefined)
const [logsTaskType, setLogsTaskType] = useState<string | undefined>(undefined)

// 2. 新增加载函数
const loadUsageLogs = async (page = 1, pageSize = 20, days = 7, platform?: string, taskType?: string) => {
  setLogsLoading(true)
  try {
    const params: any = { page, page_size: pageSize, days }
    if (platform) params.platform = platform
    if (taskType) params.task_type = taskType
    const res: any = await request.get('/usage/my/logs', { params })
    setUsageLogs(res.data.items || [])
    setLogsTotal(res.data.total || 0)
  } catch (e) {
    console.error('加载用量明细失败', e)
  } finally {
    setLogsLoading(false)
  }
}

// 3. 在useEffect中调用
useEffect(() => {
  loadUsageLogs(logsPage, logsPageSize, logsDays, logsPlatform, logsTaskType)
}, [logsPage, logsPageSize, logsDays, logsPlatform, logsTaskType])

// 4. 任务类型映射
const taskTypeNames: Record<string, string> = {
  geo_refresh: 'GEO刷新',
  geo_collect: 'GEO采集',
  semantic_gen: '语义生成',
  semantic_extend: '语义延伸',
  article_gen: '文章生成',
  compliance_check: '合规检查',
  image_gen: '生图',
  video_gen: '生视频',
  rag_query: 'RAG问答',
  http_request: 'HTTP请求',
  asset_url_collect: '资产采集',
}

// 5. 表格列定义
const logColumns = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
  { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (v: string) => <Tag color="blue">{platformNames[v] || v}</Tag> },
  { title: '模型', dataIndex: 'model', key: 'model', width: 150, ellipsis: true },
  { title: '任务类型', dataIndex: 'task_type', key: 'task_type', width: 110, render: (v: string) => <Tag>{taskTypeNames[v] || v || '未知'}</Tag> },
  { title: '输入Token', dataIndex: 'prompt_tokens', key: 'prompt_tokens', width: 90, render: (v: number) => v?.toLocaleString() || 0 },
  { title: '输出Token', dataIndex: 'completion_tokens', key: 'completion_tokens', width: 90, render: (v: number) => v?.toLocaleString() || 0 },
  { title: '总Token', dataIndex: 'total_tokens', key: 'total_tokens', width: 90, render: (v: number) => <Text strong>{v?.toLocaleString() || 0}</Text> },
  { title: '费用', dataIndex: 'estimated_cost', key: 'estimated_cost', width: 90, render: (v: number) => <Text type={v > 0 ? 'danger' : ''}>¥{v ? v.toFixed(4) : '0.0000'}</Text> },
  { title: '耗时', dataIndex: 'latency_ms', key: 'latency_ms', width: 80, render: (v: number) => v ? `${(v/1000).toFixed(1)}s` : '-' },
  { title: '状态', dataIndex: 'success', key: 'success', width: 70, render: (v: boolean) => v ? <Tag color="green">成功</Tag> : <Tag color="red">失败</Tag> },
]

// 6. 在页面渲染中加（在AI模型开关卡片下方）
<Card
  title={<Space><ApiOutlined /> 用量明细</Space>}
  style={{ marginBottom: 20 }}
  extra={
    <Space>
      <Select
        value={logsDays}
        onChange={setLogsDays}
        style={{ width: 120 }}
        options={[
          { value: 1, label: '今天' },
          { value: 7, label: '最近7天' },
          { value: 30, label: '最近30天' },
          { value: 90, label: '最近90天' },
        ]}
      />
      <Select
        value={logsPlatform}
        onChange={setLogsPlatform}
        allowClear
        placeholder="平台筛选"
        style={{ width: 130 }}
        options={Object.entries(platformNames).map(([k, v]) => ({ value: k, label: v }))}
      />
    </Space>
  }
>
  <Table
    dataSource={usageLogs}
    columns={logColumns}
    rowKey="id"
    loading={logsLoading}
    pagination={{
      current: logsPage,
      pageSize: logsPageSize,
      total: logsTotal,
      showSizeChanger: true,
      showQuickJumper: true,
      showTotal: (total) => `共 ${total} 条记录`,
      onChange: (page, pageSize) => { setLogsPage(page); setLogsPageSize(pageSize) },
    }}
    scroll={{ x: 1200 }}
    size="small"
  />
</Card>
```

**注意**：
- 新session先Read UsageGovernance.tsx的完整代码，确认现有结构，在合适的位置加
- 确认 `api/index.ts` 中是否有对应的API方法，如果没有用 `request.get` 直接调用
- 确认 `/usage/my/logs` 接口是否支持 `platform` 和 `task_type` 筛选参数，如果不支持需要在后端加
- 导入需要的组件：Select, Tag, Text等（确认已导入）

**后端补充（如果需要）**：

如果 `/my/logs` 接口不支持 `platform` 和 `task_type` 筛选，在 `api/usage.py` 的 `get_my_logs` 函数中加：

```python
# 在函数参数中加
platform: Optional[str] = Query(None),
task_type: Optional[str] = Query(None),

# 在查询过滤中加
if platform:
    query = query.filter(LlmUsageLog.platform == platform)
if task_type:
    query = query.filter(LlmUsageLog.task_type == task_type)
```

---

## C3：平台统计表格完善（3列→7列）

### 目标

把"用量管理"页面的"各平台本月消耗"表格，从只有3列（平台/Token/费用），完善为和管理员"各平台调用对比"一致的完整表格（平台/模型/总Token/调用次数/成功率/平均耗时/估算成本）。

### 后端接口

后端已有 `/usage/my/by-platform` 接口（`api/usage.py:450`），返回字段：
- `platform`：平台
- `model`：模型
- `tokens`：总Token
- `cost`：费用
- `calls`：调用次数

**缺少的字段**：成功率、平均耗时。

### 后端改动

**文件**：`backend/app/api/usage.py`

修改 `get_my_by_platform` 函数（约第450行），增加成功率和平均耗时的计算：

```python
# before（约第459-470行）
rows = db.query(
    LlmUsageLog.platform,
    LlmUsageLog.model,
    func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("tokens"),
    func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("cost"),
    func.count(LlmUsageLog.id).label("calls"),
).filter(
    LlmUsageLog.created_at >= start_date,
    LlmUsageLog.user_id == current_user_id,
).group_by(LlmUsageLog.platform, LlmUsageLog.model).all()

result = [{"platform": r.platform, "model": r.model, "tokens": int(r.tokens or 0), "cost": float(r.cost or 0), "calls": int(r.calls or 0)} for r in rows]

# after
rows = db.query(
    LlmUsageLog.platform,
    LlmUsageLog.model,
    func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("tokens"),
    func.coalesce(func.sum(LlmUsageLog.estimated_cost), 0).label("cost"),
    func.count(LlmUsageLog.id).label("calls"),
    func.coalesce(func.sum(func.case((LlmUsageLog.success == True, 1), else_=0)), 0).label("success_calls"),
    func.coalesce(func.avg(LlmUsageLog.latency_ms), 0).label("avg_latency"),
).filter(
    LlmUsageLog.created_at >= start_date,
    LlmUsageLog.user_id == current_user_id,
).group_by(LlmUsageLog.platform, LlmUsageLog.model).all()

result = []
for r in rows:
    calls = int(r.calls or 0)
    success_calls = int(r.success_calls or 0)
    result.append({
        "platform": r.platform,
        "model": r.model,
        "tokens": int(r.tokens or 0),
        "cost": float(r.cost or 0),
        "calls": calls,
        "success_rate": round(success_calls / calls * 100, 1) if calls > 0 else 0,
        "avg_latency_ms": float(r.avg_latency or 0),
    })
```

**注意**：
- 新session先Read `get_my_by_platform` 的实际代码，确认字段名和查询结构
- `func.case` 的语法可能因SQLAlchemy版本不同而有差异，新session确认实际写法
- 如果 `LlmUsageLog.success` 字段不存在或类型不同，调整查询

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

修改"各平台本月消耗"卡片（约第167-185行），改为完整的7列表格：

```tsx
// before
<Card title="各平台本月消耗">
  {quota.by_platform?.length ? (
    <Table
      dataSource={quota.by_platform}
      columns={[
        { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{platformNames[v] || v}</Tag> },
        { title: 'Token', dataIndex: 'tokens', key: 'tokens' },
        { title: '费用', dataIndex: 'cost', key: 'cost', render: (v: number) => `¥${v.toFixed(4)}` },
      ]}
      rowKey="platform"
      size="small"
      pagination={false}
    />
  ) : (
    <Empty description="本月暂无用量" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  )}
</Card>

// after
<Card
  title="各平台调用对比"
  extra={
    <Select
      value={platformDays}
      onChange={setPlatformDays}
      style={{ width: 120 }}
      options={[
        { value: 7, label: '最近7天' },
        { value: 30, label: '最近30天' },
        { value: 90, label: '最近90天' },
      ]}
    />
  }
>
  {platformStats?.length ? (
    <Table
      dataSource={platformStats}
      columns={[
        { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (v: string) => <Tag color="blue">{platformNames[v] || v}</Tag> },
        { title: '模型', dataIndex: 'model', key: 'model', width: 150, ellipsis: true },
        { title: '总Token', dataIndex: 'tokens', key: 'tokens', width: 100, render: (v: number) => v >= 10000 ? `${(v/10000).toFixed(1)}万` : v.toLocaleString() },
        { title: '调用次数', dataIndex: 'calls', key: 'calls', width: 90 },
        { title: '成功率', dataIndex: 'success_rate', key: 'success_rate', width: 80, render: (v: number) => <Text type={v >= 90 ? 'success' : v >= 70 ? 'warning' : 'danger'}>{v}%</Text> },
        { title: '平均耗时', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms', width: 90, render: (v: number) => v ? `${(v/1000).toFixed(1)}s` : '-' },
        { title: '估算成本', dataIndex: 'cost', key: 'cost', width: 100, render: (v: number) => `¥${v.toFixed(4)}` },
      ]}
      rowKey={(record) => `${record.platform}-${record.model}`}
      size="small"
      pagination={false}
      scroll={{ x: 800 }}
    />
  ) : (
    <Empty description="暂无用量数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  )}
</Card>
```

**需要新增的state和加载函数**：

```tsx
const [platformStats, setPlatformStats] = useState<any[]>([])
const [platformDays, setPlatformDays] = useState(30)

const loadPlatformStats = async (days: number) => {
  try {
    const res: any = await request.get('/usage/my/by-platform', { params: { days } })
    setPlatformStats(res.data || [])
  } catch (e) {
    console.error('加载平台统计失败', e)
  }
}

useEffect(() => { loadPlatformStats(platformDays) }, [platformDays])
```

**注意**：
- 新session先Read UsageGovernance.tsx的完整代码，确认"各平台本月消耗"卡片的实际位置
- 原来的 `quota.by_platform` 数据来自 `getMyQuota()`，现在改为直接调用 `/usage/my/by-platform` 接口，数据更准确（含成功率/平均耗时）
- 卡片标题从"各平台本月消耗"改为"各平台调用对比"，和管理员页面一致

---

## C4：用量趋势图

### 目标

在"用量管理"页面新增**Token消耗趋势图**，让用户可以看到自己最近N天的Token消耗趋势。

### 后端接口

后端已有 `/usage/my/trend` 接口（`api/usage.py:399`），返回按日期的统计：
- `date`：日期
- `tokens`：总Token
- `cost`：费用
- `calls`：调用次数

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

在"各平台调用对比"卡片上方（或旁边），新增"Token消耗趋势"卡片：

```tsx
// 1. 新增state
const [trendData, setTrendData] = useState<any[]>([])
const [trendDays, setTrendDays] = useState(30)

// 2. 新增加载函数
const loadTrend = async (days: number) => {
  try {
    const res: any = await request.get('/usage/my/trend', { params: { days } })
    setTrendData(res.data || [])
  } catch (e) {
    console.error('加载趋势数据失败', e)
  }
}

useEffect(() => { loadTrend(trendDays) }, [trendDays])

// 3. 渲染
<Card
  title="Token消耗趋势"
  extra={
    <Select value={trendDays} onChange={setTrendDays} style={{ width: 120 }}>
      <Select.Option value={7}>最近7天</Select.Option>
      <Select.Option value={30}>最近30天</Select.Option>
      <Select.Option value={90}>最近90天</Select.Option>
    </Select>
  }
  style={{ marginBottom: 20 }}
>
  {/* 复用UsageDashboard.tsx中的趋势图组件/方式 */}
  {/* 新session先Read UsageDashboard.tsx，找到趋势图的实现方式，复制过来 */}
  {/* 数据用trendData，X轴是date，Y轴是tokens */}
</Card>
```

**注意**：
- 新session先Read `UsageDashboard.tsx`，找到管理员页面的"Token消耗趋势"图是怎么实现的（用的什么图表库，ECharts还是其他）
- 复用同样的图表组件和样式，只改数据源为 `trendData`
- 如果项目没有ECharts依赖，用Ant Design的简单方式实现
- 趋势图和任务类型分布饼图放在同一行（Row+Col布局，各占一半），参考管理员页面的布局

---

## C5：任务类型分布饼图

### 目标

在"用量管理"页面新增**任务类型Token分布**饼图，让用户可以看到自己的Token主要消耗在哪些任务类型上（采集/语义生成/文章生成等）。

### 后端接口

后端已有 `/usage/my/by-task-type` 接口（`api/usage.py:427`），返回按任务类型的统计：
- `task_type`：任务类型
- `tokens`：总Token
- `cost`：费用
- `calls`：调用次数

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

在"Token消耗趋势"卡片旁边，新增"任务类型Token分布"卡片：

```tsx
// 1. 新增state
const [taskTypeData, setTaskTypeData] = useState<any[]>([])
const [taskTypeDays, setTaskTypeDays] = useState(30)

// 2. 新增加载函数
const loadTaskType = async (days: number) => {
  try {
    const res: any = await request.get('/usage/my/by-task-type', { params: { days } })
    setTaskTypeData(res.data || [])
  } catch (e) {
    console.error('加载任务类型分布失败', e)
  }
}

useEffect(() => { loadTaskType(taskTypeDays) }, [taskTypeDays])

// 3. 渲染
<Card
  title="任务类型Token分布"
  extra={
    <Select value={taskTypeDays} onChange={setTaskTypeDays} style={{ width: 120 }}>
      <Select.Option value={7}>最近7天</Select.Option>
      <Select.Option value={30}>最近30天</Select.Option>
      <Select.Option value={90}>最近90天</Select.Option>
    </Select>
  }
  style={{ marginBottom: 20 }}
>
  {/* 复用UsageDashboard.tsx中的饼图组件/方式 */}
  {/* 数据用taskTypeData，name是task_type（用taskTypeNames映射为中文），value是tokens */}
</Card>
```

**注意**：
- 新session先Read `UsageDashboard.tsx`，找到管理员页面的"任务类型Token分布"饼图是怎么实现的
- 复用同样的图表组件和样式，只改数据源为 `taskTypeData`
- 任务类型名称用 `taskTypeNames` 映射为中文（在C2中已定义）
- 趋势图和任务类型分布饼图放在同一行（Row+Col布局，各占一半）

---

## C6：费用预估+异常告警提示

### 目标

在"用量管理"页面的"本月AI用量"卡片中，增加：
1. **费用预估**：按当前消耗速度预估本月总费用
2. **异常告警**：某天消耗突增时高亮提示
3. **今日消耗**：显示今日的Token和费用

### 前端改动

**文件**：`frontend/src/pages/UsageGovernance.tsx`

修改"本月AI用量"卡片（约第137-164行），增加费用预估和今日消耗：

```tsx
// before
<Card>
  <div style={{ marginBottom: 12 }}>
    <Space>
      <DollarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
      <Title level={4} style={{ margin: 0 }}>本月AI用量</Title>
    </Space>
  </div>
  <Descriptions column={1} size="small">
    <Descriptions.Item label="月度配额">
      {quota.monthly_limit < 0 ? '无限' : `¥${quota.monthly_limit}`}
    </Descriptions.Item>
    <Descriptions.Item label="已消耗">
      <Text strong>¥{quota.used_cost.toFixed(2)}</Text>
      {quota.usage_pct >= 80 && <Tag color="orange" style={{ marginLeft: 8 }}>接近上限</Tag>}
      {quota.usage_pct >= 100 && <Tag color="red" style={{ marginLeft: 8 }}>已用尽</Tag>}
    </Descriptions.Item>
  </Descriptions>
  <Progress ... />
  ...
</Card>

// after
<Card>
  <div style={{ marginBottom: 12 }}>
    <Space>
      <DollarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
      <Title level={4} style={{ margin: 0 }}>本月AI用量</Title>
    </Space>
  </div>
  <Descriptions column={1} size="small">
    <Descriptions.Item label="月度配额">
      {quota.monthly_limit < 0 ? '无限' : `¥${quota.monthly_limit}`}
    </Descriptions.Item>
    <Descriptions.Item label="已消耗">
      <Text strong style={{ fontSize: 18 }}>¥{quota.used_cost.toFixed(2)}</Text>
      {quota.usage_pct >= 80 && <Tag color="orange" style={{ marginLeft: 8 }}>接近上限</Tag>}
      {quota.usage_pct >= 100 && <Tag color="red" style={{ marginLeft: 8 }}>已用尽</Tag>}
    </Descriptions.Item>
    <Descriptions.Item label="今日消耗">
      <Text>¥{todayCost.toFixed(4)}</Text>
      <Text type="secondary" style={{ marginLeft: 8 }}>{todayTokens.toLocaleString()} Token</Text>
    </Descriptions.Item>
    <Descriptions.Item label="本月预估">
      <Text>¥{estimatedMonthlyCost.toFixed(2)}</Text>
      {estimatedMonthlyCost > quota.monthly_limit && quota.monthly_limit > 0 && (
        <Tag color="red" style={{ marginLeft: 8 }}>预计超支</Tag>
      )}
    </Descriptions.Item>
  </Descriptions>
  <Progress ... />
  {/* 异常告警提示 */}
  {abnormalDays.length > 0 && (
    <Alert
      message="用量异常提醒"
      description={`检测到 ${abnormalDays.length} 天用量突增：${abnormalDays.map(d => d.date).join('、')}，请确认是否为正常使用`}
      type="warning"
      showIcon
      style={{ marginTop: 12 }}
    />
  )}
  ...
</Card>
```

**需要新增的计算逻辑**：

```tsx
// 今日消耗（从trendData获取今天的数据）
const todayStr = new Date().toISOString().split('T')[0]
const todayCost = trendData.find(d => d.date === todayStr)?.cost || 0
const todayTokens = trendData.find(d => d.date === todayStr)?.tokens || 0

// 本月预估（按当前日均消耗 * 本月天数）
const now = new Date()
const dayOfMonth = now.getDate()
const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
const dailyAvgCost = dayOfMonth > 0 ? quota.used_cost / dayOfMonth : 0
const estimatedMonthlyCost = dailyAvgCost * daysInMonth

// 异常告警（某天消耗超过过去7天平均值的2倍）
const abnormalDays = trendData.filter((d, i) => {
  if (i < 7) return false
  const prev7Days = trendData.slice(i - 7, i)
  const avg = prev7Days.reduce((sum, x) => sum + (x.tokens || 0), 0) / 7
  return (d.tokens || 0) > avg * 2 && (d.tokens || 0) > 1000
})
```

**注意**：
- 新session先Read UsageGovernance.tsx的"本月AI用量"卡片的实际代码，确认现有结构
- `todayCost` 和 `todayTokens` 从 `trendData`（C4加载的趋势数据）中获取今天的数据
- 异常告警的阈值（2倍）可以根据实际情况调整
- 导入需要的组件：Alert（确认已导入）

---

## 全部完成后的统一验证

6项全部修改完成后，按以下步骤统一验证：

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
确认无ERROR，所有接口正常。

### 4. 功能验证清单

| 验证项 | 操作 | 预期 |
|--------|------|------|
| C1 管理员切换用户 | 管理员登录→用量管理→切换下拉选择用户 | 显示该用户的配额和各平台用量，模型开关隐藏 |
| C1 普通用户无切换 | 普通用户登录→用量管理 | 看不到用户切换下拉 |
| C2 用量明细列表 | 用量管理→用量明细 | 显示每次调用的时间/平台/模型/任务类型/Token/费用/耗时/状态，支持筛选/分页 |
| C3 平台统计完善 | 用量管理→各平台调用对比 | 表格有7列（平台/模型/总Token/调用次数/成功率/平均耗时/估算成本） |
| C4 用量趋势图 | 用量管理→Token消耗趋势 | 显示最近N天的Token消耗折线图，支持切换天数 |
| C5 任务类型分布 | 用量管理→任务类型Token分布 | 显示饼图，各任务类型的Token占比 |
| C6 费用预估+告警 | 用量管理→本月AI用量 | 显示今日消耗/本月预估，异常时显示告警提示 |

### 5. 管理员页面不受影响
用管理员账号登录，确认"用量统计"页面功能正常，没有被本次改动影响。

### 6. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段三C-用量统计优化与明细功能（6项）"
```

---

## 注意事项

1. **C1的后端改动需要谨慎**：修改 `get_my_quota` 函数时，确保不影响普通用户的正常使用（普通用户传 `target_user_id` 会被忽略）。新session先Read完整代码再修改。

2. **前端改动较大**：UsageGovernance.tsx会新增很多内容（用户切换/明细列表/趋势图/饼图/费用预估）。新session必须先Read完整文件，理解现有结构，然后逐步添加，不要一次性重写整个文件。

3. **复用管理员页面的图表组件**：C4和C5的图表，先Read UsageDashboard.tsx，找到管理员页面的趋势图和饼图是怎么实现的，复用同样的组件和样式，只改数据源。

4. **后端接口大部分已存在**：`/my/overview`, `/my/trend`, `/my/by-task-type`, `/my/by-platform`, `/my/logs` 都已存在。只需要在C1中修改配额接口，在C2/C3中可能需要补充少量字段。

5. **两个页面的定位**：
   - 用量统计（UsageDashboard）：管理员全局视角，保持不变，阶段四再升级为系统运营监控中心
   - 用量管理（UsageGovernance）：个人用量与模型管理，本次优化
   - 管理员可以访问两个页面，普通用户只能访问用量管理

6. **管理员查看其他用户时的限制**：C2-C6的明细列表/趋势图/饼图暂时只显示自己的数据（因为 `/my/*` 接口不支持 `target_user_id`）。可以在这些卡片上加提示"查看其他用户时暂不支持明细数据"。后续阶段再完善。

7. **每完成一项做一次静态检查**：确保import不报错，tsc无错误。

8. **如果遇到不确定的事项**：记录下来，在报告中说明，不要自行猜测修改。

## 最终输出

完成后输出报告：
1. 6项修复的状态（✅/⚠️/❌）
2. C1管理员切换用户功能的实现方式
3. 每项实际改动的文件和行号
4. 新建的函数/组件列表
5. 验证结果（普通用户视角和管理员视角）
6. git commit hash
7. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的文件，确认当前代码状态。重点先Read `usage_governance.py` 的 `get_my_quota` 函数和 `UsageGovernance.tsx` 的完整代码。
