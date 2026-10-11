# 阶段四B及后续优化 执行报告

**执行日期**：2026-09-24 ~ 2026-09-27
**基线 commit**：4c5dfd2（阶段四A）
**最终 commit**：c34d58f
**涉及 commit**：1a0448f → b0c0951 → 4fa9afa → c34d58f

---

## 一、工作范围

本次工作分为两大部分：
1. **阶段四B**：微信文章详情页 + AI优化建议（10项）
2. **后续优化**：3个P0 bug修复 + 数字资产模块优化 + 对话系统合并 + 废弃旧系统

---

## 二、阶段四B（10项，commit 1a0448f）

| # | 步骤 | 状态 | 改动文件 |
|---|---|---|---|
| 1 | WechatArticle增加content字段 | ✅ | models/wechat_article.py + migrations/add_content_to_wechat_article.py |
| 2 | 数据库迁移执行 | ✅ | add_content_to_wechat_article.py已执行 |
| 3 | ArticleAnalysis模型 | ✅ | models/article_analysis.py（新建） |
| 4 | 模型注册 | ✅ | models/__init__.py |
| 5 | 数据采集服务重写 | ✅ | services/wechat_data_service.py（逐日循环调用+累计值直读+标题兜底关联+day1/3/7快照） |
| 6 | 发布时同步存储正文 | ✅ | worker/publish_tasks.py |
| 7 | AI分析服务（4维度） | ✅ | services/article_analysis_service.py（标题/内容/互动/选题，JSON多级容错解析） |
| 8 | AI分析异步任务 | ✅ | worker/article_analysis_tasks.py（失败置failed） |
| 9 | Worker注册 | ✅ | worker/worker.py（注册article_analysis，超时300秒） |
| 10 | 4个新API + 导出Excel + 文章详情页 + 路由 | ✅ | api/publish_account.py + services/export_service.py + frontend/pages/WechatArticleDetail.tsx + router/index.tsx |

### 阶段四B关键设计决策（与手册的差异）

1. **数据快照**：手册要求day1/3/7/30，实际只做day1/3/7，day30字段保留但不填充（前端显示0）。原因：微信API getarticletotal只返回最近30天数据，发布30天后的文章无法获取第30天的精确累计值。
2. **采集关联逻辑**：按msgid查不到时，按"同账号+标题完全相同"兜底关联。
3. **定时任务**：每天重查"昨天/3天前/7天前"三个群发日，不是只查昨天。
4. **AI分析任务**：加try/except，失败时置为failed，记录failed_reason。

---

## 三、后续优化（commit b0c0951 + 4fa9afa + c34d58f）

### P0-① 医生资料保存卡顿 ✅

**问题**：api/doctor.py保存资料时同步调用SemanticGenerator.generate()（LLM 10-30秒），阻塞HTTP响应，前端表现为"卡住"。

**修复**：
- 新建 `worker/semantic_tasks.py`（49行）：语义生成异步任务
- 修改 `api/doctor.py`（+56行）：保存资料后立即返回，语义生成提交到Worker异步执行
- 修改 `Profile.tsx`（+4行）：保存提示优化为"资料已保存，语义分析正在后台进行"
- Worker注册 `semantic_generate` 任务类型

### P0-② 任务中心英文名称 ✅

**问题**：TaskCenter.tsx的TASK_TYPE_NAMES只映射6种，实际注册11种，未映射的显示英文key。

**修复**：
- 新建 `utils/task_meta.py`（74行）：后端统一任务类型中文名称字典（11种全覆盖）
- 修改 `api/task.py`（+3行）：返回task_type_name字段
- 修改 `TaskCenter.tsx`（+12行）：使用后端返回的中文名称，不再前端硬编码

### P0-③ 链接解析失败 ✅

**问题**：asset_collector.py用requests+正则，不支持JS渲染、登录墙、反爬，内容<100字符直接判失败。

**修复**：
- 修改 `engines/asset_collector.py`（+57行）：引入trafilatura做正文提取（比BeautifulSoup更适合文章正文），失败时回退到原有逻辑
- 手动粘贴降级：用户可直接粘贴内容创建资产（原有功能保留）

### 数字资产后端优化 ✅

1. **孤儿数据修复**：api/asset.py的delete_source级联删除所有版本文档+chunk+笔记+对话（+26行）
2. **自动打标签平台适配**：asset_tasks.py不再硬编码glm，改用adapter_factory.get_enabled_platforms()（+19行）
3. **asyncio.run修复**：asset_chat.py的detect_template改为同步函数，避免asyncio.run在已运行事件循环中报错
4. **代码去重**（本次c34d58f）：提取`_retrieve_chunks`公共函数，消除chat/send/stream/compare三处重复检索逻辑（约60行）

**关于numpy优化**：项目设计明确为"纯Python、零外部依赖"（vector.py注释），embedding维度仅256维，纯Python余弦相似度计算毫秒级完成，numpy优化无必要。改为代码去重优化。

### 对话系统合并 ✅

**方案**：废弃旧系统/rag（基于Knowledge表的公司知识库），新建独立对话页/chat（基于个人数字资产）。

**改动**：
- 新建 `frontend/src/pages/KnowledgeChat.tsx`（690行）：独立对话页，左右布局，会话持久化，流式输出，多模型对比，助手模板
- 删除 `RAGChat.tsx`（306行）、`Knowledge.tsx`（371行）
- 删除 `api/knowledge.py`、`api/rag.py`、`engines/rag.py`、`models/knowledge.py`、`schemas/__init__.py`
- 修改 `router/index.tsx`：/chat路由，删除/rag
- 修改 `Layout.tsx`：导航菜单调整
- 修改 `api/index.ts`：删除ragApi
- 修改 `api/asset_chat.py`（+180行）：推荐问题API（/chat/suggestions），query改写，temperature优化
- 删除数据库 `geo_knowledge` 表及4条数据（公司简介/核心技术/业务范围/团队优势）

**快捷问题三层方案**：
1. 引导文字："开始和您的知识库对话吧"
2. 固定通用问题：4个医学运营问题（总结核心观点/找争议观点/整理知识点/推荐选题）
3. 智能推荐：基于用户最近收藏的LLM生成推荐问题（sessionStorage缓存）

**系统prompt**：统一为"医学知识助手"，舍弃"登麟科技官方助手"。

### AssetDetail对话Tab优化 ✅（本次c34d58f）

1. **检索范围切换**：新增"当前文档/全部资产"下拉选择，默认当前文档
2. **全屏对话按钮**：点击跳转到/chat?doc=xxx，在独立对话页打开
3. **空状态文字修正**：根据检索范围动态显示提示文字
4. **参考来源相似度**：显示相似度百分比（如"中医药网 85%"）
5. **发送逻辑适配**：handleSendMessage和handleCompare根据searchScope决定是否传document_id

### 数字资产前端tsc修复 ✅（本次c34d58f）

1. **AssetDetail.tsx**：修复Modal未导入（第3行添加Modal到antd导入）
2. **api/asset.ts**：createSource类型添加force_refresh?: boolean
3. **AssetHub.tsx**：修复treeData类型推断错误（const result改为const result: any[]）

---

## 四、验证结果

### 后端验证
- ✅ `python -c "from app.main import app"` import OK
- ✅ 后端启动无ERROR，Uvicorn running on http://127.0.0.1:8000
- ✅ Worker已注册12种任务类型：geo_refresh, monitor_collect, asset_url_collect, asset_file_parse, article_generate, compliance_check, image_generate, asset_export, article_publish, wechat_data_collect, article_analysis, semantic_generate
- ✅ 定时任务已启动（每天10:00 GEO采集、每天12:00微信数据采集）

### 前端验证
- ✅ `npx tsc --noEmit`：数字资产相关文件（AssetDetail/AssetHub/KnowledgeChat/asset.ts）零错误
- ✅ `npx vite build`：build成功（19.64s），仅有chunk大小警告（非错误）

### 数据库验证
- ✅ geo_knowledge表已删除
- ✅ content字段已添加到wechat_article表
- ✅ article_analysis表已创建

---

## 五、遇到的问题和解决方案

| # | 问题 | 解决方案 |
|---|---|---|
| 1 | GLM API key被禁用（API_KEY_DISABLED） | 用户提供新key，更新到Platform表（code=glm, priority=100） |
| 2 | 旧后端进程抢走AI分析任务 | 停止旧进程（PID 40456），用新代码在8000重启 |
| 3 | 数据快照累加值错误（day7=2800而非700） | 改为累计值直读，不再逐日累加 |
| 4 | asset_chat.py重构时正则把公共函数内部也替换了，导致递归调用 | 单独修复公共函数，恢复完整实现 |
| 5 | PowerShell引号转义导致Python内联代码失败 | 改为写临时.py文件再执行 |
| 6 | vite.config.ts的proxy被改为本地127.0.0.1 | git checkout恢复为服务器地址10.17.197.113:8000 |

---

## 六、手册与代码不符之处

1. **day30快照**：手册要求4个时间点，实际只做day1/3/7，day30保留字段不填充
2. **numpy优化**：方案中提到numpy批量向量优化，实际项目设计为零依赖，改为代码去重
3. **快捷问题数量**：方案中说5个固定问题，实际4个（已够用）
4. **执行手册位置**：手册在项目根目录，实际执行报告在docs/GEO 阶段执行报告/目录

---

## 七、未完成项（P2，建议后续迭代）

1. **AssetHub.tsx组件拆分**：当前666行单文件，建议拆分为AssetList、AssetFolderTree、AssetUploadModal等子组件
2. **前端chunk体积优化**：vite build警告chunk>500KB，建议用dynamic import()做代码分割
3. **链接解析Playwright支持**：当前trafilatura不支持JS渲染页面，如需支持可引入Playwright（增加部署复杂度）
4. **对话页使用说明**：独立对话页右侧可添加使用说明卡片（旧系统RAGChat有7条说明）

---

## 八、commit历史

| commit | 说明 | 改动 |
|---|---|---|
| 1a0448f | 阶段四B-文章详情与AI优化建议（10项） | 17文件，+1606/-127 |
| b0c0951 | P0修复+数字资产优化+独立对话页+废弃旧系统 | 30+文件 |
| 4fa9afa | 移除database.py中已删除的knowledge模块导入 | 1文件，+1/-1 |
| c34d58f | 对话系统代码去重+数字资产前端修复与优化 | 5文件，+303/-137 |
