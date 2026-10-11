## 发现的不符点（共 6 项）

### 1. 审计日志 API 导入了不存在的 `require_admin`

- 手册步骤 13：`from app.deps import get_current_user_id, require_admin`
- 实际 `app/deps.py` 只有 `get_current_user_id` 和 `get_current_admin_id`，**没有 `require_admin`**
- 而且审计 API 代码里实际是手动查 User.role 判断管理员，并没有用 `require_admin`
- **我的处理**：移除这个不存在的导入，保留手动判断逻辑

### 2. 审计中间件无法从 `request.state` 获取用户信息

- 手册步骤 11：`user_id = getattr(request.state, "user_id", None)`
- 实际代码中**没有任何中间件设置 `request.state.user_id`**。`get_current_user_id` 是每个 endpoint 自己解析 JWT 的；`usage_context_middleware` 虽然解析了 JWT，但只设置了 `usage_context`，没有写 `request.state`
- 后果：审计日志的 `user_id` 会永远是 null
- **我的处理**：在审计中间件里直接用 `IAMService.verify_jwt` 解析 Authorization header（和 `usage_context_middleware` 同样的做法），同时取用户名需要查一次 User 表

### 3. 全局错误处理中间件会错误拦截 HTTPException

- 手册步骤 12 的 `except Exception as e` 会捕获 FastAPI 的 `HTTPException`（401/403/404 等），把它们全部变成 500 "服务器内部错误"
- **我的处理**：在 `except Exception` 之前加一个 `except HTTPException` 直接 `raise` 重新抛出，让 FastAPI 默认处理器返回正确状态码

### 4. 中间件注册顺序写反了

- 手册步骤 14 说 "ErrorHandlerMiddleware 必须在最外层（最后 add_middleware）"，但给出的代码是先加 ErrorHandler 再加 Audit
- Starlette 中**后 add 的才是最外层**，所以正确顺序应该是先加 AuditMiddleware，再加 ErrorHandlerMiddleware
- 另外两个新中间件应该加在 `RateLimitMiddleware` 之后、`usage_context_middleware` 装饰器之前，这样 usage_context 仍在最外层（不影响用量统计）
- **我的处理**：按正确顺序注册

### 5. Pydantic 版本是 v2.13.4

- 手册步骤 10 用了 `data.dict(exclude_unset=True)`，这是 Pydantic v1 写法
- v2 应使用 `data.model_dump(exclude_unset=True)`（`.dict()` 虽能用但有 deprecation warning）
- **我的处理**：用 `model_dump`

### 6. 前端菜单结构

- 当前 Layout 没有 "内容运营" 分组，只有一个 "发布中心" 分组
- 手册建议：对标账号管理 + 竞品对比分析放 "内容运营" 分组，审计日志放 "系统管理" 分组（仅管理员可见）
- **我的处理**：新建 "内容运营" 分组放前两个页面；审计日志放在 "系统设置" 同级，仅 admin 可见（当前 filterMenuByRole 已隐藏普通用户的 /usage 和 /settings，我把 /audit-logs 也加进去）

------

## 其他确认事项

- **步骤 16/17 前端页面**：手册只给核心结构，我会参考 `WechatAccountStats.tsx` 的风格完整实现（ECharts 图表、antd 组件、request 封装、轮询逻辑）
- **竞品分析页的 "自己账号" 下拉**：只列出 platform=wechat 的 PublishAccount
- **审计日志自动记录**：登录时 user_id 还没设置（登录请求本身不带 token），所以 login 记录的 user_id 为 null 但 username 可从响应体取 —— 不过中间件拿不到响应体。我的方案是：login 操作的 user_id 为 null，username 从请求体的 email 提取（可接受，因为登录日志主要看时间和 IP）
- **数据库迁移**：migrations 目录已存在，有 `__init__.py`，按手册方式运行即可

以上 6 点你确认没问题的话，我就开始执行。有任何需要调整的请告诉我。