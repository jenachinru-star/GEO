# 阶段四B 执行报告：文章详情与AI优化建议

**执行日期**：2026-09-24
**基线 commit**：4c5dfd2
**完成 commit**：1a0448f
**改动文件**：17个（5新建 + 12修改），新增1606行，删除127行

---

## 一、14项改动状态

| # | 步骤 | 状态 | 说明 |
|---|---|---|---|
| 1 | WechatArticle增加content字段 | ✅ | 模型字段+迁移脚本 |
| 2 | 数据库迁移执行 | ✅ | add_content_to_wechat_article.py已执行 |
| 3 | ArticleAnalysis模型 | ✅ | 新建article_analysis.py，含status/result_json/failed_reason/tokens_used |
| 4 | 模型注册 | ✅ | models/__init__.py注册 |
| 5 | 数据采集服务重写 | ✅ | 逐日循环调用+累计值直读+标题兜底关联+day1/3/7快照 |
| 6 | 发布时同步存储正文 | ✅ | publish_tasks.py发布成功后同步正文到WechatArticle |
| 7 | AI分析服务（4维度） | ✅ | article_analysis_service.py，含JSON多级容错解析 |
| 8 | AI分析异步任务 | ✅ | article_analysis_tasks.py，含失败置failed处理 |
| 9 | Worker注册 | ✅ | worker.py注册article_analysis，超时300秒 |
| 10 | 4个新API | ✅ | publish_account.py新增export/detail/analyze/analysis |
| 11 | 导出Excel | ✅ | export_service.py新增export_wechat_articles（10列） |
| 12 | 文章详情页 | ✅ | WechatArticleDetail.tsx，数据卡片+增长趋势图+4Tab AI分析 |
| 13 | 文章列表操作+导出按钮 | ✅ | WechatAccountStats.tsx操作列+导出按钮，api/index.ts blob下载 |
| 14 | 路由注册 | ✅ | router/index.tsx注册/publish-accounts/:accountId/articles/:articleId |

---

## 二、实际改动文件清单

### 新建文件（5个）
| 文件 | 行数 | 说明 |
|---|---|---|
| backend/app/models/article_analysis.py | ~50 | ArticleAnalysis模型，geo_article_analysis表 |
| backend/app/services/article_analysis_service.py | ~300 | 4维度AI分析服务+JSON容错解析 |
| backend/app/worker/article_analysis_tasks.py | ~80 | AI分析异步任务handler |
| backend/migrations/add_content_to_wechat_article.py | ~30 | content字段迁移脚本 |
| frontend/src/pages/WechatArticleDetail.tsx | ~400 | 文章详情页 |

### 修改文件（12个）
| 文件 | 关键改动 |
|---|---|
| backend/app/models/wechat_stats.py | WechatArticle增加content字段(Text) |
| backend/app/models/__init__.py | 注册ArticleAnalysis |
| backend/app/services/wechat_data_service.py | 重写采集逻辑：逐日循环+累计直读+标题兜底+day1/3/7 |
| backend/app/services/export_service.py | 新增export_wechat_articles（10列） |
| backend/app/worker/publish_tasks.py | 发布成功后同步正文到WechatArticle |
| backend/app/worker/wechat_data_tasks.py | 支持dates显式日期参数 |
| backend/app/worker/worker.py | 注册article_analysis，超时300秒 |
| backend/app/api/publish_account.py | 新增4个API（export路由在前） |
| backend/app/main.py | 定时采集改为每天重查昨天/3天前/7天前三个群发日 |
| frontend/src/api/index.ts | exportApi新增exportWechatArticles（blob下载带token） |
| frontend/src/pages/WechatAccountStats.tsx | 操作列（详情/AI分析按钮）+导出Excel按钮 |
| frontend/src/router/index.tsx | 注册文章详情路由 |

---

## 三、验证结果

| 验证项 | 结果 | 说明 |
|---|---|---|
| 数据库迁移 | ✅ | content字段添加成功 |
| 后端import检查 | ✅ | from app.main import app 通过 |
| 后端启动 | ✅ | 无ERROR，article_analysis已注册 |
| 前端tsc | ✅ | 本次改动文件零错误（仅AssetDetail/AssetHub历史错误） |
| 前端vite build | ✅ | 34秒成功 |
| API冒烟测试 | ✅ | 19项全过（详情/分析状态/导出xlsx/越权404） |
| 快照逻辑模拟测试 | ✅ | 累计直读（day7=700非累加2800）、标题兜底无重复、msgid回填、正文保留 |
| 发布正文同步模拟测试 | ✅ | 发布后WechatArticle创建+正文+URL+日期 |
| AI分析失败处理 | ✅ | GLM key禁用时正确置failed+failed_reason |
| AI分析成功路径 | ⚠️ | GLM key已更新，代码路径通过模拟和失败处理验证；真实LLM成功调用待部署环境最终确认 |
| 真实微信采集/发布 | ⚠️ | 需已配置的微信账号凭证+IP白名单，本地开发库无微信账号，已用接口模拟验证全部代码路径 |

---

## 四、遇到的问题与解决方案

### 问题1：微信getarticletotal接口行为与手册设计冲突
**现象**：手册设计用days=7一次请求获取7天数据，按增量累加计算快照。
**实际**：
- 该接口最大时间跨度仅1天，多日请求会失败
- details行是"截至该日的累计总量"而非每日增量，按增量累加会重复计算
- 该接口最多只统计发表后7天，day_30物理上不可能（需新接口getarticletotaldetail）

**解决方案**（已与用户确认）：
- 改为逐日循环调用（每天一次请求）
- 累计值直接读取，不再累加
- 仅做day_1/3/7快照，day_30字段保留但不填充
- 定时任务每天重查"昨天/3天前/7天前"三个群发日，自动回填遗漏快照

### 问题2：发布器media_id与datacube msgid无法关联
**现象**：发布器返回的永久素材media_id和datacube的msgid是两套ID，无法直接匹配。
**解决方案**：采集时按msgid查不到时，用"同账号+标题完全相同"兜底匹配，并回填msgid到WechatArticle.media_id。

### 问题3：AI分析任务失败后永久卡在processing
**现象**：LLM调用失败时，ArticleAnalysis记录停留在processing状态。
**解决方案**：article_analysis_tasks.py的handler加try/except，失败时置status=failed并写failed_reason。

### 问题4：GLM返回JSON不规范
**现象**：首次真实测试GLM返回的JSON包含markdown围栏、中文弯引号、裸换行等，解析失败。
**解决方案**：新增多级容错解析（去围栏→直接解析→截取→修复中文弯引号/裸换行/尾逗号→schema正则兜底），并收紧prompt（禁止字符串内英文双引号、禁止换行、精简输出条数）。

### 问题5：旧后端进程抢走任务
**现象**：测试时发现有昨晚启动的旧后端进程（端口8000，旧代码），其Worker轮询同一数据库抢走新任务并按旧注册表判失败。
**解决方案**：停止旧进程，用新代码在标准端口8000重启。

### 问题6：前端导出Excel在Bearer鉴权下401
**现象**：window.open下载文件无法携带Authorization header。
**解决方案**：改用axios blob下载，请求时自动携带token，前端创建Blob URL触发下载。

---

## 五、手册与代码不符之处（9处）

| # | 手册描述 | 实际代码 | 修正方案 |
|---|---|---|---|
| 1 | getarticletotal支持days=7一次请求 | 最大跨度1天 | 逐日循环调用 |
| 2 | details是每日增量，需累加 | details是截至该日累计值 | 直接读取不累加 |
| 3 | 快照包含day_30 | 接口最多7天，day_30需新接口 | day_30字段保留不填充 |
| 4 | 发布器media_id可直接关联datacube | 两套ID无法关联 | 标题兜底匹配+回填msgid |
| 5 | UserPlatformPref有platform_type字段 | 无此字段 | 去掉类型过滤 |
| 6 | adapter.query()返回字符串 | 返回QueryResult对象（.answer/.success/.total_tokens） | 用对象属性 |
| 7 | Semantic字段是keyword | 实际是question/is_active | 用正确字段名 |
| 8 | 前端路由是配置式 | 实际是JSX Route | 按实际写法注册 |
| 9 | 导出用window.open | Bearer鉴权下401 | 改用blob下载 |

---

## 六、待部署环境验证项

1. 真实LLM端到端分析（GLM key已更新，需在部署环境确认）
2. 真实微信公众号数据采集（需已配置账号+IP白名单）
3. 真实发布流程正文同步（需微信发布器配置）

---

## 七、后续建议（阶段四C）

1. day_30快照：引入getarticletotaldetail新接口
2. 发布时间分析：确认微信API权限后实现
3. 竞品对比分析
