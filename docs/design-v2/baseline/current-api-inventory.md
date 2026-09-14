# 当前 API 清单

记录时间：2026-09-14  
OpenAPI 路径数：64

## 1. 路由分组

| 分组 | 当前路径范围 | V2 处置 |
|---|---|---|
| 健康/文档 | /、/api/health、/docs、/openapi.json | 拆 live/ready，生产限制文档 |
| Auth | /api/v1/auth/* | 改 provider+sub、共享 state、服务端会话 |
| Doctor | /api/v1/doctor/* | 迁移 Workspace、Schema、证据、版本 |
| Semantic | /api/v1/semantic/* | 迁移 Question V2，移除 add-paid 假逻辑 |
| GEO | /api/v1/geo/* | 由 MonitorRun/Observation/Dashboard V2 替代 |
| Task | /api/v1/task/* | 评估保留为 Worker 基础，补幂等/恢复/隔离 |
| Opportunity | /api/v1/opportunity/* | 迁移到证据化 ContentOpportunity |
| Article/Template/Image | 对应 /api/v1 路由 | 合并到 Content/ToolTask 审核链 |
| Distribution | /api/v1/distribution/* | 迁移 URL 验证、Webhook 和归因 |
| Dashboard | /api/v1/dashboard/* | 新口径聚合，返回 n/N/coverage |
| Monitor | /api/v1/monitor/* | 旧品牌链，隔离/只读/归档 |
| Content | /api/v1/content/* | 旧 Content，停止新写入 |
| Knowledge/RAG | /api/v1/knowledge/*、/rag/* | 普通用户隔离，评估证据库或归档 |
| Competitor | /api/v1/competitor/* | 旧全局数据隔离，由检测实体演进 |
| Export | /api/v1/export/* | Workspace、异步、安全转义 |
| System/Tools | /api/v1/system/*、/tools/* | 管理权限和最小信息披露 |

## 2. 当前新增路径

最近提交新增或扩展了 Task、Opportunity、Image 和 Distribution 等能力，但仍是 /api/v1，并未实现 design-v2 中定义的 /api/v2 契约。

## 3. 验证方式

本清单通过 app.openapi().paths 生成，而不是只遍历 app.routes。当前 FastAPI 版本会把 include_router 表示为内部 IncludedRouter，直接读取顶层 path 会漏报业务路由。

## 4. 后续输出

阶段 B 开始前生成机器可读 OpenAPI 快照。每个 PR 对比路径、方法、认证、请求和响应 Schema，未经评审不得悄然破坏 V1。
