# 已知缺陷基线

## 严重

1. 旧 Question/Content/Knowledge/Competitor/Monitor 数据没有 Workspace 所有权，登录不等于租户隔离。
2. 医生采集继续复用错误的 MonitorRecord.question_id 外键和旧唯一约束。
3. 普通聊天回答仍可能被描述成真实 AI 搜索可见度。
4. AEO 证据字段虽已加入，但旧数据模型和分析定义仍不足以证明来源引用。
5. Workspace 已建表但注释和查询说明其尚未强制过滤，容易形成“看似完成多租户”的安全错觉。

## 高

1. API 进程默认同时启动 APScheduler 和内嵌 Worker；多进程部署会产生重复调度/执行风险。
2. 手写 migrate_v2.py 缺少 Alembic 版本和可靠回滚。
3. 默认 SECRET_KEY/JWT_SECRET 仍可用。
4. IAM 身份仍需核验是否使用不可变 provider_subject。
5. AsyncTask 无独立 Observation、attempt、错误标准和成本字段。
6. 前端认证仍以本地 Token 为中心，旧隐藏路由仍直接可达。
7. 前端构建有约 619 kB 和 1052 kB 大 Chunk。
8. 无标准后端/前端测试套件和 CI 证据。
9. GLM 使用代理 Base URL 和非公开文档可直接核实的模型名，联网搜索能力不能假设。

## 中

1. Go CLI 没有测试，认证和错误处理需要重新核验。
2. ArticleDraft 与旧 Content 双轨仍存在。
3. Subscription 仍没有完整配额/结算闭环。
4. Platform 表为空，运行配置来自环境，存在两套配置概念。
5. 时间字段类型与时区策略不统一。

## 阶段 A 不处理项

以上缺陷本阶段只记录，不立即修复。阶段 A 只做指标、能力、样本和实验验证；确定性工程问题进入阶段 B，Workspace 和新监测模型进入阶段 C/D。
