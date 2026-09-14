# 当前数据库清单

记录时间：2026-09-14  
数据库：backend/data/geo.db  
数据库类型：SQLite

## 1. 表和行数

| 表 | 行数 |
|---|---:|
| geo_article_distribution | 3 |
| geo_article_draft | 3 |
| geo_async_task | 4 |
| geo_competitor | 0 |
| geo_competitor_record | 0 |
| geo_content | 0 |
| geo_content_opportunity | 11 |
| geo_doctor_profile | 2 |
| geo_knowledge | 4 |
| geo_monitor_record | 139 |
| geo_platform | 0 |
| geo_question | 10 |
| geo_schema_version | 1 |
| geo_semantic | 24 |
| geo_subscription | 0 |
| geo_user | 3 |
| geo_workspace | 3 |
| geo_workspace_member | 3 |

## 2. 医生资料候选

- profile_id=1，user_id=1：张医生，深圳市第一人民医院，妇科，深圳；语义 12 条。
- profile_id=2，user_id=3：Jena，深圳市妇幼保健院，妇科，深圳市；语义 12 条。

首批影子实验只能在用户确认后选定其中一份。进入提交的金标准 fixtures 应使用 profile_key 或匿名测试身份，避免把生产数据库 ID 当永久标识。

## 3. 已落地的过渡表

geo_workspace、geo_workspace_member、geo_async_task 已由手写迁移创建；每个现有用户当前存在一个 Workspace/Member。它们尚未成为所有业务查询的强制边界。

geo_content_opportunity 使用 ORM 创建并引用 Workspace、DoctorProfile、Semantic。现有数据 11 条。

## 4. 关键结构风险

1. geo_monitor_record.question_id 仍外键引用 geo_question，但医生记录同时使用 semantic_id，并曾把 Semantic ID 写入 question_id。
2. 唯一约束仍是 question_id + platform_code + detect_date + detect_round，没有 run_id、mode、model 和 sample_index。
3. geo_monitor_record 没有成功/失败状态，仍可能把平台异常混入未提及。
4. Workspace 表已有，但 DoctorProfile、Semantic、ArticleDraft、Distribution 等仍以 user_id 为主要所有权。
5. Question、Content、Knowledge、Competitor 等旧表没有 Workspace/user 所有权。
6. AsyncTask.workspace_id 可空，payload/result/error 为无 Schema 的 Text JSON。
7. Workspace 手写建表缺少 ORM 中声明的外键约束。
8. 数据库通过 geo_schema_version 和脚本迁移，不具备 Alembic revision、downgrade 和跨数据库演练。
9. DateTime 字段与手写 TEXT 时间混用。

## 5. 迁移限制

- 不得把旧全局数据平均分配给三个 Workspace。
- 医生 MonitorRecord 只有 semantic_id 可验证时才可迁移。
- 旧平台失败文本必须识别并标记失败，不能迁移成成功回答。
- 迁移前先在 backup 副本演练并输出行数对账。
- 当前数据库不能作为 PostgreSQL 兼容已经成立的证据。
