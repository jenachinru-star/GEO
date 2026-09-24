# 阶段二C执行手册：前端P1修复（13项）

> 本手册包含13项前端P1修复，全部是用户高频路径上的硬伤（功能崩溃/数据错误/资源泄漏）。

## 项目信息

- 项目路径：C:\Users\jenac\Desktop\GEO
- 前端路径：C:\Users\jenac\Desktop\GEO\frontend
- 技术栈：React 18 + TypeScript + Ant Design 5 + Zustand + Axios + Vite
- 操作系统：Windows
- git 基线：cf4ed0f（工作区必须干净）
- 执行模式：按需确认

## 13项修复总览

| 编号 | 修复项 | 严重度 | 涉及文件 |
|------|--------|--------|---------|
| C1 | UsageDashboard导出按钮调用不存在的方法 | P1 | api/index.ts + UsageDashboard.tsx |
| C2 | Profile页llms.txt下载路径404 | P1 | Profile.tsx |
| C3 | AssetDetail发布后跳转404 | P1 | AssetDetail.tsx |
| C4 | AssetHub翻页丢失搜索关键词 | P1 | AssetHub.tsx |
| C5 | AssetHub星标收藏筛选失效 | P1 | AssetHub.tsx |
| C6 | ContentHub搜索只过滤当前页 | P1 | ContentHub.tsx |
| C7 | ContentHub统计只算当前页 | P1 | ContentHub.tsx |
| C8 | AccountSettings假保存（只弹窗不调接口） | P1 | AccountSettings.tsx |
| C9 | clearAuth登出未清业务状态 | P1 | store/useStore.ts |
| C10 | Knowledge/RAG普通用户可选confidential级别 | P1 | Knowledge.tsx + RAGChat.tsx |
| C11 | Monitor/DataCenter/Settings重复点击采集并发定时器泄漏 | P1 | Monitor.tsx + DataCenter.tsx + Settings.tsx |
| C12 | downloadFile未处理后端JSON错误响应 | P1 | api/index.ts |
| C13 | Settings页Swagger文档生产环境暴露 | P1 | Settings.tsx + 后端main.py |

## 执行顺序

严格按 C1→C2→...→C13 的顺序执行。每完成一项做一次 `npx tsc --noEmit` 检查，全部完成后统一启动前端验证。

---

## C1：UsageDashboard导出按钮调用不存在的方法

**根因**：`UsageDashboard.tsx:76` 调用 `exportApi.exportUsage(days)`，但 `api/index.ts` 的 `exportApi` 中没有 `exportUsage` 方法（只有 exportMonitor/Questions/Knowledge/Content/Report/DoctorReport）。点击"导出Excel"会抛 `exportApi.exportUsage is not a function`。

**修复目标**：在 exportApi 中新增 exportUsage 方法，调用后端用量导出接口。

**改动1：api/index.ts 新增 exportUsage**

**文件**：`frontend/src/api/index.ts`

在 `exportApi` 对象中（第195-205行）新增：

```typescript
// after（在 exportDoctorReport 后面加）
  exportUsage: (days: number = 30) => downloadFile(`/usage/export?days=${days}`, `用量统计_${days}天_${Date.now()}.xlsx`),
```

**注意**：新session必须先确认后端是否有 `/usage/export` 接口。如果后端没有这个接口，需要：
- 方案A：后端新增用量导出接口（超出前端范围，需后端配合）
- 方案B：前端移除导出按钮（如果后端不支持）

新session先 Read 后端 `api/usage.py` 确认是否有导出接口。如果没有，在 UsageDashboard.tsx 中给按钮加 `disabled` 并提示"功能开发中"，同时记录为待后端实现项。

**改动2：UsageDashboard.tsx 确认调用参数**

**文件**：`frontend/src/pages/UsageDashboard.tsx`

新session先 Read 第76行附近，确认调用方式，确保与新增的方法签名匹配。

**验证**：`npx tsc --noEmit` 无新增错误；点击导出按钮不抛异常。

---

## C2：Profile页llms.txt下载路径404

**根因**：`Profile.tsx:146` 中 `fetch('/api/v1/template/llms.txt')` 缺少 `/geo` 前缀。前端 base 是 `/geo`，所有API都应走 `/geo/api/v1`。

**修复目标**：路径改为 `/geo/api/v1/template/llms.txt`。

**改动**：

**文件**：`frontend/src/pages/Profile.tsx`

新session先 Read 第140-150行，找到 fetch 调用：

```typescript
// before
fetch('/api/v1/template/llms.txt')

// after
fetch('/geo/api/v1/template/llms.txt')
```

**注意**：如果这段代码是用 `window.open` 或创建 `<a>` 标签下载，同样要改路径。新session确认实际代码后修改。

**验证**：点击下载llms.txt，浏览器Network中请求URL应为 `/geo/api/v1/template/llms.txt`，返回200。

---

## C3：AssetDetail发布后跳转404

**根因**：`AssetDetail.tsx:194` 中 `handlePublish` 成功后 `navigate('/asset/published')`，但实际路由是 `/published`（router中没有 `/asset/published`）。

**修复目标**：改为 `navigate('/published')`。

**改动**：

**文件**：`frontend/src/pages/AssetDetail.tsx`

新session先 Read 第190-200行，找到 navigate 调用：

```typescript
// before
navigate('/asset/published')

// after
navigate('/published')
```

**验证**：发布成功后跳转到已发布列表页，不白屏。

---

## C4：AssetHub翻页丢失搜索关键词

**根因**：`AssetHub.tsx:448` 中翻页 `onChange={(p) => fetchData(p)}` 只传了页码，没传当前 keyword。`fetchData` 第二参 kw 默认 `''`，翻到第2页时搜索词被清空。

**修复目标**：翻页时传入当前 keyword。

**改动**：

**文件**：`frontend/src/pages/AssetHub.tsx`

新session先 Read 第440-455行，找到 Pagination 的 onChange：

```typescript
// before
onChange={(p) => fetchData(p)}

// after
onChange={(p) => fetchData(p, keyword)}
```

**注意**：新session确认 `fetchData` 函数的签名和 `keyword` 变量的作用域，确保 keyword 在当前闭包中可用。

**验证**：搜索关键词后翻页，列表保持搜索结果，不被清空。

---

## C5：AssetHub星标收藏筛选失效

**根因**：`AssetHub.tsx:263` 中"星标收藏"节点的 `key='starred'` 被当作 `folder_id` 传给后端。`fetchData` 只判 `selectedFolder !== 'all'` 就传 `folder_id`，点"星标收藏"会发 `folder_id=starred`，后端无此文件夹，列表为空。

**修复目标**：单独处理 starred 分支，不传 folder_id，改为传 `starred=true`（或前端过滤）。

**改动**：

**文件**：`frontend/src/pages/AssetHub.tsx`

新session先 Read `fetchData` 函数（约第50-100行）和文件夹选择逻辑（约第250-270行），然后修改：

```typescript
// fetchData 中（before）
const params: any = { page, page_size }
if (selectedFolder !== 'all') {
  params.folder_id = selectedFolder
}

// fetchData 中（after）
const params: any = { page, page_size }
if (selectedFolder === 'starred') {
  params.starred = true  // 星标收藏单独传参
} else if (selectedFolder !== 'all') {
  params.folder_id = selectedFolder
}
```

**注意**：新session必须先确认后端是否支持 `starred=true` 参数。如果后端不支持：
- 方案A：后端新增 starred 过滤参数（需后端配合）
- 方案B：前端拉取全部后本地过滤 star 字段（简单但分页不准确）
- 方案C：星标收藏功能暂时禁用，提示"功能开发中"

新session先 Read 后端 `api/asset.py` 确认是否支持 starred 过滤。如果不支持，用方案B（前端本地过滤）作为临时方案，并记录待后端实现。

**验证**：点击"星标收藏"，列表显示已星标的文档，不为空。

---

## C6：ContentHub搜索只过滤当前页

**根因**：`ContentHub.tsx` 中关键词搜索是在当前页数据上用 `filter()` 过滤，不是走后端搜索。翻到第2页后搜索，只在第2页数据中过滤，结果不完整。

**修复目标**：搜索应走后端接口（带 keyword 参数），或在全量数据上过滤。

**改动**：

**文件**：`frontend/src/pages/ContentHub.tsx`

新session先 Read 搜索相关代码（搜索输入框的 onChange/onSearch、fetchData 函数），确认当前实现。

**方案A（推荐）**：搜索走后端，fetchData 加 keyword 参数：
```typescript
// fetchData 中加 keyword 参数
const fetchData = (page = 1, kw = '') => {
  setKeyword(kw)
  articleApi.list({ page, page_size, keyword: kw }).then(...)
}

// 搜索时
onSearch={(value) => fetchData(1, value)}

// 翻页时（同C4）
onChange={(p) => fetchData(p, keyword)}
```

**注意**：新session必须先确认后端文章列表接口是否支持 keyword 搜索参数。如果不支持，用方案B：

**方案B**：前端拉取全部文章（page_size=1000），在全量数据上搜索和分页。但这会影响性能，仅作为临时方案。

新session先 Read 后端 `api/article.py` 的列表接口确认是否支持 keyword。如果支持，用方案A；如果不支持，用方案B并记录待后端实现。

**验证**：搜索关键词后，结果包含所有匹配的文章（不只当前页）。

---

## C7：ContentHub统计只算当前页

**根因**：`ContentHub.tsx` 中文章统计（总数、已发布数、待发布数等）是基于当前页数据计算的，不是全量。翻到第2页时统计数字会变，数据错误。

**修复目标**：统计应基于后端返回的 total 或全量数据。

**改动**：

**文件**：`frontend/src/pages/ContentHub.tsx`

新session先 Read 统计相关代码（统计卡片的渲染、数据来源），确认当前实现。

**方案A（推荐）**：如果后端列表接口返回了统计数据（如 total、published_count 等），直接用后端返回的统计：
```typescript
// 从接口响应中取统计
const { total, items, published_count, draft_count } = res.data
setStats({ total, published: published_count, draft: draft_count })
```

**方案B**：如果后端不返回统计，新增一个统计接口（需后端配合），或前端拉取全量后计算。

新session先 Read 后端 `api/article.py` 的列表接口返回结构，确认是否有统计字段。如果没有，用方案B（前端拉全量计算）作为临时方案，并记录待后端优化。

**验证**：翻页时统计数字保持不变，反映全量数据。

---

## C8：AccountSettings假保存

**根因**：`AccountSettings.tsx` 中 `handleSaveProfile` 只弹了个 `message.success('保存成功')`，没有调用任何后端接口。用户修改资料后点击保存，实际没有保存。

**修复目标**：实现真实的保存逻辑，调用后端用户资料更新接口。

**改动**：

**文件**：`frontend/src/pages/AccountSettings.tsx`

新session先 Read 整个文件，确认：
1. 表单字段有哪些（用户名、邮箱、密码、头像等）
2. 是否有对应的后端API（userApi.updateProfile 或 authApi.update）
3. handleSaveProfile 的当前实现

然后修改 `handleSaveProfile`：

```typescript
// before（假保存）
const handleSaveProfile = async () => {
  message.success('保存成功')
}

// after（真实保存）
const handleSaveProfile = async () => {
  try {
    setSaving(true)
    // 调用后端更新接口（具体API名新session确认）
    await userApi.updateProfile({
      name: formData.name,
      email: formData.email,
      // ... 其他字段
    })
    message.success('保存成功')
    // 更新全局用户信息
    const user = useAppStore.getState().user
    useAppStore.getState().setAuth(useAppStore.getState().token!, { ...user, ...formData })
  } catch (e) {
    message.error('保存失败')
  } finally {
    setSaving(false)
  }
}
```

**注意**：
- 新session必须先确认后端是否有用户资料更新接口。如果没有，需要后端新增（超出前端范围）。
- 如果后端没有更新接口，前端至少要实现密码修改接口（如果有的话），其他字段的保存按钮加 disabled 提示"功能开发中"。
- 新session先 Read `api/index.ts` 确认有哪些用户相关API。

**验证**：修改资料后点击保存，调用后端接口，刷新页面后资料保持修改后的值。

---

## C9：clearAuth登出未清业务状态

**根因**：`store/useStore.ts:44-48` 的 `clearAuth` 只清了 token 和 user，没有清 systemInfo、platformList、doctorProfile、semantics。换账号登录后，旧用户的业务数据在重新拉取前短暂可见。

**修复目标**：clearAuth 中一并重置所有业务状态。

**改动**：

**文件**：`frontend/src/store/useStore.ts`

```typescript
// before（第44-48行）
  clearAuth: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({ token: null, user: null })
  },

// after
  clearAuth: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({
      token: null,
      user: null,
      systemInfo: null,
      platformList: [],
      doctorProfile: null,
      semantics: [],
    })
  },
```

**验证**：登出后再登录另一个账号，旧用户的语义/平台信息不残留。

---

## C10：Knowledge/RAG普通用户可选confidential级别

**根因**：`Knowledge.tsx:268` 和 `RAGChat.tsx:266` 中，知识库访问级别（public/internal/confidential）的下拉框对所有用户开放，普通用户可以选择 confidential 级别检索/问答。后端B1/B2已加了服务端降级，但前端也应该按角色禁用。

**修复目标**：普通用户的级别选择器禁用 confidential 选项（或隐藏），admin 可见全部。

**改动1：Knowledge.tsx**

**文件**：`frontend/src/pages/Knowledge.tsx`

新session先 Read 第260-275行，找到级别选择器：

```typescript
// before
<Select value={level} onChange={setLevel}>
  <Option value="public">公开</Option>
  <Option value="internal">内部</Option>
  <Option value="confidential">机密</Option>
</Select>

// after
const user = useAppStore((s) => s.user)
const isAdmin = user?.role === 'admin'

<Select value={level} onChange={setLevel}>
  <Option value="public">公开</Option>
  <Option value="internal">内部</Option>
  <Option value="confidential" disabled={!isAdmin}>机密（仅管理员）</Option>
</Select>
```

**改动2：RAGChat.tsx**

**文件**：`frontend/src/pages/RAGChat.tsx`

同样修改，新session先 Read 第260-275行确认实际代码。

**验证**：普通用户登录后，confidential 选项显示为禁用状态；admin 可正常选择。

---

## C11：Monitor/DataCenter/Settings重复点击采集并发定时器泄漏

**根因**：`Monitor.tsx:89`、`DataCenter.tsx:71`、`Settings.tsx` 中，点击"采集"/"手动刷新"会启动 `setInterval` 轮询任务状态，但没有在启动新轮询前清除旧的。重复点击会启动多个定时器并发轮询，内存泄漏+重复弹窗。

**修复目标**：启动新轮询前，先 `clearInterval` 旧的。

**改动1：Monitor.tsx**

**文件**：`frontend/src/pages/Monitor.tsx`

新session先 Read 第80-100行，找到轮询启动逻辑：

```typescript
// before（大致结构）
const startPolling = (taskId: number) => {
  pollTimerRef.current = setInterval(async () => {
    // 轮询任务状态
  }, 3000)
}

// after
const startPolling = (taskId: number) => {
  // 启动前先清旧定时器
  if (pollTimerRef.current) {
    clearInterval(pollTimerRef.current)
    pollTimerRef.current = null
  }
  pollTimerRef.current = setInterval(async () => {
    // 轮询任务状态
  }, 3000)
}
```

同时确保组件卸载时清除定时器（useEffect cleanup）：
```typescript
useEffect(() => {
  return () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
    }
  }
}, [])
```

**改动2：DataCenter.tsx**

同样修改，新session先 Read 第65-80行确认实际代码。

**改动3：Settings.tsx**

同样修改，新session先 Grep 搜索 `setInterval` 找到采集轮询逻辑。

**验证**：快速连续点击"采集"3次，Network中只有一个轮询请求在跑（不是3个）；组件卸载后轮询停止。

---

## C12：downloadFile未处理后端JSON错误响应

**根因**：`api/index.ts:174-193` 的 `downloadFile` 固定把响应当 Excel blob 处理。如果后端返回 401/500 的 JSON 错误，`new Blob([blob])` 会把错误 JSON 当 xlsx 下载，用户得到损坏文件且无错误提示。

**修复目标**：检查响应 content-type，如果是 JSON 则解析错误并提示。

**改动**：

**文件**：`frontend/src/api/index.ts`

```typescript
// before（第174-193行）
const downloadFile = (url: string, filename: string) => {
  return request.get(url, {
    responseType: 'blob',
    timeout: 120000
  }).then((blob: any) => {
    const file = new Blob([blob], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(file)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    message.success('导出成功')
  }).catch(() => {
    message.error('导出失败')
  })
}

// after
const downloadFile = (url: string, filename: string) => {
  return request.get(url, {
    responseType: 'blob',
    timeout: 120000
  }).then(async (response: any) => {
    // 检查是否是JSON错误响应
    const contentType = response.headers?.['content-type'] || ''
    if (contentType.includes('application/json')) {
      // 读取blob内容解析JSON
      const text = await response.data.text()
      try {
        const err = JSON.parse(text)
        message.error(err.detail || err.message || '导出失败')
      } catch {
        message.error('导出失败')
      }
      return
    }

    // 正常文件下载
    const file = new Blob([response.data], {
      type: contentType || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(file)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    message.success('导出成功')
  }).catch(() => {
    message.error('导出失败')
  })
}
```

**注意**：新session确认 `request.get` 返回的是完整 response 还是直接 data。如果 axios 配置了 `transformResponse` 或拦截器改变了返回结构，需要相应调整。从代码看 `request` 实例的响应拦截器可能已经返回了 `res.data`，新session先 Read 响应拦截器确认。

**验证**：模拟后端返回JSON错误（如配额不足402），前端应显示错误提示，不下载损坏文件。

---

## C13：Settings页Swagger文档生产环境暴露

**根因**：`Settings.tsx:179` 中 `window.open('/docs')` 打开 Swagger API 文档。生产环境暴露接口文档有安全风险，且 `/docs` 路径可能没有 `/geo` 前缀导致404。

**修复目标**：
1. 前端：仅开发环境显示"查看API文档"按钮，生产环境隐藏
2. 后端：生产环境（APP_ENV=production）关闭 Swagger

**改动1：Settings.tsx 按环境隐藏按钮**

**文件**：`frontend/src/pages/Settings.tsx`

新session先 Read 第175-185行，找到 Swagger 按钮：

```typescript
// before
<Button onClick={() => window.open('/docs')}>查看API文档</Button>

// after
{import.meta.env.DEV && (
  <Button onClick={() => window.open('/geo/docs')}>查看API文档（仅开发环境）</Button>
)}
```

**改动2：后端 main.py 生产环境关闭 Swagger**

**文件**：`backend/app/main.py`

新session先 Read FastAPI app 初始化部分，确认当前配置：

```python
# before
app = FastAPI(title="GEO Doctor Platform", ...)

# after
app = FastAPI(
    title="GEO Doctor Platform",
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
    # ... 其他参数保持不变
)
```

**注意**：阶段二B的B9已经把 `APP_ENV` 加到了 config.py，新session确认 `settings.APP_ENV` 可用。

**验证**：
- 开发环境（npm run dev）：Settings页显示API文档按钮，点击可打开
- 生产环境（npm run build）：Settings页不显示按钮；后端 `/docs` 返回404

---

## 全部完成后的统一验证

13项全部修改完成后，按以下步骤统一验证：

### 1. 前端类型检查
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npx tsc --noEmit
```
确认无新增错误（预先存在的7个错误在 AssetDetail/AssetHub/UsageDashboard，与本次无关，不新增即可）。

### 2. 前端构建
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npm run build
```
确认构建成功。

### 3. 启动前端开发服务器
```bash
cd C:\Users\jenac\Desktop\GEO\frontend
npm run dev
```

### 4. 功能验证清单（用 liujinru 账号）

| 验证项 | 操作 | 预期 |
|--------|------|------|
| C1 用量导出 | UsageDashboard点击导出Excel | 不抛异常，调用导出接口 |
| C2 llms.txt | Profile页点击下载 | 请求URL含/geo前缀，返回200 |
| C3 发布跳转 | AssetDetail发布成功 | 跳转到/published，不白屏 |
| C4 翻页搜索 | AssetHub搜索后翻页 | 搜索结果保持，不清空 |
| C5 星标筛选 | AssetHub点击星标收藏 | 显示已星标文档，不为空 |
| C6 内容搜索 | ContentHub搜索关键词 | 结果包含全量匹配，不只当前页 |
| C7 内容统计 | ContentHub翻页 | 统计数字不变，反映全量 |
| C8 账号保存 | AccountSettings修改后保存 | 调用后端接口，刷新后保持 |
| C9 登出清状态 | 登出后换账号登录 | 旧用户语义/平台不残留 |
| C10 级别禁用 | 普通用户看Knowledge/RAG | confidential选项禁用 |
| C11 定时器防泄漏 | Monitor连续点采集3次 | 只有一个轮询在跑 |
| C12 导出错误处理 | 模拟导出失败 | 显示错误提示，不下损坏文件 |
| C13 Swagger隐藏 | 生产环境Settings页 | 不显示API文档按钮 |

### 5. git 提交
```bash
cd C:\Users\jenac\Desktop\GEO
git add -A
git commit -m "feat: 阶段二C-前端P1修复（13项）"
```

---

## 注意事项

1. **C1/C5/C6/C7/C8 需要后端配合**：新session必须先确认后端是否有对应接口。如果没有，用前端临时方案（禁用按钮/本地过滤）并记录待后端实现。
2. **C6/C7 ContentHub是关联改动**：搜索和统计都涉及数据来源，建议一起改，确保搜索走后端后统计也用后端数据。
3. **C11 三个文件都要改**：Monitor.tsx、DataCenter.tsx、Settings.tsx，不要漏掉任何一个。
4. **C12 响应拦截器确认**：新session先 Read `request` 实例的响应拦截器，确认返回的是完整 response 还是 data，再写 downloadFile 的错误处理。
5. **每完成一项做一次 tsc 检查**，不要全部改完才检查。
6. **预先存在的7个tsc错误**（AssetDetail/AssetHub/UsageDashboard）不在本次范围内，不新增即可，不需要修复。

## 最终输出

完成后输出报告：
1. 13项修复的状态（✅/⚠️/❌）
2. 每项实际改动的文件和行号
3. 哪些项需要后端配合（用了临时方案）
4. tsc检查结果（新增错误数）
5. git commit hash
6. 遇到的问题和未完成项（如果有）

---

现在开始：第一步，用 Read 工具读取所有涉及的前端文件，确认当前代码状态。
