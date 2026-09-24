## 阶段二 C 前端 P1 修复 — 执行报告

**Commit**: `a0f2d99` | **基线**: `cf4ed0f` | **变更**: 15 文件，+109/-39

### 1. 13 项修复状态

表格

| 编号 | 修复项                        | 状态       | 说明                                                         |
| ---- | ----------------------------- | ---------- | ------------------------------------------------------------ |
| C1   | UsageDashboard 导出按钮       | ⚠️ 临时方案 | 后端无 `/usage/export` 接口，按钮禁用 + 提示 "功能开发中"    |
| C2   | Profile 页 llms.txt 路径 404  | ✅ 已修复   | 路径加 `/geo` 前缀                                           |
| C3   | AssetDetail 发布后跳转 404    | ✅ 已修复   | `navigate('/asset/published')` → `navigate('/published')`    |
| C4   | AssetHub 翻页丢失搜索关键词   | ✅ 已修复   | 翻页时传入 `keyword`                                         |
| C5   | AssetHub 星标收藏筛选失效     | ✅ 无需改   | 后端 `asset.py:100` 已支持 `folder_id="starred"`，前端当前代码已正确传参 |
| C6   | ContentHub 搜索只过滤当前页   | ⚠️ 临时方案 | 后端不支持 keyword，前端拉全量 (page_size=1000) 本地过滤 + 分页 |
| C7   | ContentHub 统计只算当前页     | ⚠️ 临时方案 | 基于全量数据本地统计 total/published/consistent，翻页不变    |
| C8   | AccountSettings 假保存        | ✅ 已修复   | 调用后端 `PUT /auth/local/profile`，成功后更新全局 store     |
| C9   | clearAuth 登出未清业务状态    | ✅ 已修复   | 一并重置 systemInfo/platformList/doctorProfile/semantics     |
| C10  | 普通用户可选 confidential     | ✅ 已修复   | Knowledge (2 处)+RAGChat 的 confidential 选项按角色禁用，RAGChat 加自动降级 |
| C11  | 采集定时器并发泄漏            | ✅ 已修复   | Monitor/DataCenter/Settings 启动新轮询前先 `clearInterval` 旧的 |
| C12  | downloadFile 未处理 JSON 错误 | ✅ 已修复   | 检查 `blob.type`，JSON 错误时解析并提示，不下载损坏文件      |
| C13  | Swagger 生产环境暴露          | ✅ 已修复   | 前端仅 DEV 显示按钮 (路径改 /geo/docs)，后端生产环境关闭 docs_url/redoc_url |

### 2. 改动文件清单

表格

| 文件                                     | 涉及项    | 关键改动                                                     |
| ---------------------------------------- | --------- | ------------------------------------------------------------ |
| `frontend/src/api/index.ts`              | C1,C8,C12 | 新增 `localAuthApi.getProfile/updateProfile`；`downloadFile` 加 JSON 错误检测 |
| `frontend/src/pages/UsageDashboard.tsx`  | C1        | 导出按钮 disabled + Tooltip；补充 `message` import           |
| `frontend/src/pages/Profile.tsx`         | C2        | `fetch('/api/v1/...')` → `fetch('/geo/api/v1/...')`          |
| `frontend/src/pages/AssetDetail.tsx`     | C3        | 跳转路径修正                                                 |
| `frontend/src/pages/AssetHub.tsx`        | C4        | 翻页 `onChange` 传入 keyword                                 |
| `frontend/src/pages/ContentHub.tsx`      | C6,C7     | loadData 拉全量本地过滤 / 统计 / 分页；筛选变化重置 page=1   |
| `frontend/src/pages/AccountSettings.tsx` | C8        | handleSaveProfile 调真实接口 + 更新全局用户                  |
| `frontend/src/store/useStore.ts`         | C9        | clearAuth 重置 4 个业务状态                                  |
| `frontend/src/pages/Knowledge.tsx`       | C10       | 2 处级别选择器 confidential 加 `disabled={!isAdmin}`         |
| `frontend/src/pages/RAGChat.tsx`         | C10       | 级别选择器禁用 + 非 admin 自动降级 useEffect                 |
| `frontend/src/pages/Monitor.tsx`         | C11       | setInterval 前清旧定时器                                     |
| `frontend/src/pages/DataCenter.tsx`      | C11       | 同上                                                         |
| `frontend/src/pages/Settings.tsx`        | C11,C13   | 定时器防泄漏；Swagger 按钮仅 DEV 显示                        |
| `frontend/src/vite-env.d.ts`             | C13       | 新增，提供 `import.meta.env` 类型声明                        |
| `backend/app/main.py`                    | C13       | FastAPI 加 `docs_url`/`redoc_url` 环境条件                   |

### 3. 需后端配合的临时方案（3 项）

- **C1 用量导出**：后端 `usage.py` 无 `/usage/export` 接口，前端按钮已禁用。待后端新增导出接口后，在 `exportApi` 中加 `exportUsage` 并启用按钮。
- **C6 内容搜索**：后端 `article.py` 列表接口不支持 `keyword` 参数，前端拉全量本地过滤。待后端加 keyword 支持后改回后端搜索。
- **C7 内容统计**：后端只返回 `total`，不返回 `published_count`/`consistent_count`，前端全量本地统计。待后端返回统计字段后直接使用。

### 4. 验证结果

- **tsc 检查**：本次零新增错误。剩余 6 个预先存在错误（AssetDetail 3 个 + AssetHub 3 个，均为 Modal/force_refresh/selectable 类型问题），不在本次范围。
- **vite build**：✅ 成功，3713 模块，38 秒完成（`tsc && vite build` 因预先存在 tsc 错误中断，用 `vite build` 单独验证打包通过）。
- **git commit**：`a0f2d99`，15 文件变更。

### 5. 说明事项

- **C5 无需前端修改**：手册描述的 "后端无此文件夹" 已不成立 —— 后端 `asset.py` 第 74 行注释和第 100 行代码明确支持 `folder_id="starred"` 特殊值，前端当前 `params.folder_id = selectedFolder` 的写法已能正确工作。
- **C12 方案调整**：手册原方案假设 `request.get` 返回完整 response（含 headers），但实际响应拦截器返回的是 `response.data`（Blob）。因此改用 `blob.type` 判断 content-type，功能等价且符合实际代码结构。
- **C10 RAGChat 自动降级**：额外加了一个 useEffect，当普通用户的 level 因旧会话残留为 confidential 时自动重置为 public，防止禁用选项但值仍为 confidential 的边界情况。