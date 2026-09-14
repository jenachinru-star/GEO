# 当前代码基线

记录时间：2026-09-14  
基线提交：daa81c0  
前一功能提交：ca5d931  
工作分支：main

## 1. 用途

本文件记录阶段 A 开始时的代码和运行事实。后续验收以此为对照，不把历史问题误判为新改造回归。

## 2. 项目组成

- 后端：FastAPI、SQLAlchemy、SQLite、APScheduler、OpenAI Python SDK。
- 前端：React 18、TypeScript、Vite、Ant Design、ECharts、Zustand、Axios。
- CLI：Go、Cobra。
- 部署：已有 Dockerfile、docker-compose 和本地启动脚本。
- AI Provider：运行环境识别到 GLM、MiniMax；本阶段只获准并验证 GLM 最小调用。

## 3. 当前产品链路

当前主链为 IAM 登录 → 医生资料 → Semantic → GEO 刷新/异步任务 → MonitorRecord → Dashboard/DataCenter → ArticleDraft/ContentOpportunity → 生图/分发。

旧企业品牌链仍存在：Question、旧 Monitor、Content、Knowledge/RAG、Competitor、Export 和 CLI。

## 4. ca5d931 已提前实现的 V2 内容

最新代码已经加入 Workspace/WorkspaceMember、AsyncTask、ContentOpportunity、Worker、LLM Analyzer、生图适配器、分发服务和任务中心。它们需要在正式继续扩建前与 design-v2 重新对账。

当前实现仍属于过渡版，而非最终 V2，原因包括：

- Workspace 仅建表，注释明确“不强制过滤”；
- AsyncTask 是通用任务壳，尚未替代 MonitorRun/Observation；
- 医生采集仍写旧 MonitorRecord；
- 数据库迁移仍使用 scripts/migrate_v2.py，而不是 Alembic；
- API 内嵌 Scheduler 和 Worker 线程默认启用；
- 旧模块仍注册全部业务路由；
- 新任务/机会功能建立在旧 user_id 和旧监测模型之上。

因此后续不重复删除这些代码，而是评估每部分：保留、补强、迁移或回退。

## 5. 构建基线

- Python：python -m compileall -q app 通过。
- FastAPI OpenAPI：可生成，当前共 64 个路径。
- 前端：npm run build 通过，转换 3695 个模块。
- 前端仍有两个超大 Chunk：约 618.85 kB 和 1052.15 kB，Vite 发出大于 500 kB 警告。
- Go：go test ./... 通过，但两个包均显示 no test files。
- 仓库当前没有标准 pytest/Vitest/Playwright 测试套件；backend/scripts 下的 verify/test 脚本不能替代自动化测试基线。

## 6. GLM 冒烟基线

- 配置状态：已配置。
- 配置模型：glm-5.3-flash。
- Base URL：非智谱公开文档标准域名，属于项目自建或代理端点；本文件不记录完整地址。
- 最小普通 Chat 调用：成功。
- 响应模型标识：glm-5.3-flash。
- 响应包含 ID 和 Token usage 字段。
- 尚未证明：联网搜索、结构化来源 URL、地区控制、官方消费者产品等价性、实际计费规则。

## 7. 基线保护规则

- 阶段 A 实验不写 geo_monitor_record、geo_async_task 或其他正式业务表。
- 不修改已有医生、Semantic、ArticleDraft 和 Distribution。
- 不执行 migrate_v2.py。
- 不运行可能清理或重建测试数据的脚本。
- 实验产物写入 artifacts/shadow 并忽略提交；只有匿名/脱敏 fixtures 可入库。
