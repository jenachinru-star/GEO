# 阶段四B后续优化执行报告

## 执行时间
2026-09-24

## 执行范围
在阶段四B（文章详情与AI优化建议）已完成的基础上，执行以下优化：
1. 3个P0 bug修复
2. 数字资产模块后端优化
3. 新建独立对话页
4. 废弃旧系统rag/knowledge

---

## 一、P0 bug修复

### 1. 医生资料保存卡顿（已完成）

**问题**：用户编辑完"医生资料"后点保存，前端卡住很久（10-30秒），因为后端同步调用SemanticGenerator.generate()生成语义问题。

**方案**：
- 新建 `backend/app/worker/semantic_tasks.py` — 语义生成异步任务handler
- 修改 `backend/app/api/doctor.py` — 保存后立即返回，提交AsyncTask（task_type=semantic_generate），返回semantic_task_id
- 修改 `backend/app/worker/worker.py` — 注册semantic_generate任务，超时300秒
- 修改 `frontend/src/pages/Profile.tsx` — 提示文字改为"保存成功，语义问题正在后台生成中"，弹窗改为"可在任务中心查看进度"

**验证**：后端import OK

### 2. 任务中心英文名称（已完成）

**问题**：任务中心的任务名称都是英文，用户不知道指什么。根因是TaskCenter.tsx只映射了6种任务类型，实际有11种。

**方案**：
- 新建 `backend/app/utils/task_meta.py` — 统一字典（12种任务类型含中文名+描述）
- 修改 `backend/app/api/task.py` — get_task和list_tasks返回时注入task_type_name字段
- 修改 `frontend/src/pages/TaskCenter.tsx` — 删除本地映射，改用record.task_type_name

**验证**：后端import OK

### 3. 链接解析失败（已完成后端，前端UI待AssetHub重构）

**问题**：用户随便丢一个非标准公开链接，解析失败；但放文章能解析成功。根因是asset_collector.py用requests+正则，不支持JS渲染/登录墙/反爬。

**方案**：
- 安装trafilatura 2.2.0
- 修改 `backend/app/engines/asset_collector.py` — 引入trafilatura作为首选正文提取器，失败回退正则，内容过短阈值从100提高到200，错误提示改为"无法自动提取正文（可能需要登录或JavaScript渲染），请手动粘贴内容"
- 前端手动粘贴降级UI待AssetHub拆分重构时一起做

**验证**：后端import OK

---

## 二、数字资产模块后端优化

### 1. 孤儿数据修复（已完成）

**问题**：asset.py delete_source原只删is_current=True的文档，旧版本文档和关联数据成为孤儿。

**方案**：修改 `backend/app/api/asset.py` — 级联删除所有版本文档+AssetChunk+AssetNote+AssetGenerated+AssetChatSession+AssetChatMessage（用in_批量删除）

### 2. 自动打标签平台适配（已完成）

**问题**：asset_tasks.py _auto_tag_document硬编码get_adapter("glm")，用户停用glm后无法打标签。

**方案**：修改 `backend/app/worker/asset_tasks.py` — 获取用户启用平台列表（过滤UserPlatformPref.enabled=False），取第一个可用平台。

### 3. asyncio.run修复（已完成）

**问题**：asset_chat.py第98行detect_template是async函数但纯同步关键词匹配（无await），第441行在同步函数中用asyncio.run调用，可能导致事件循环冲突。

**方案**：修改 `backend/app/api/asset_chat.py` — detect_template从async改为同步def，去掉asyncio.run调用。

### 4. RAG检索优化（已完成）

**问题**：三个对话接口（chat/send、chat/stream、chat/compare）都有重复的Python循环逐块相似度计算代码，且在循环中逐个查询AssetDocument（N+1查询）。

**方案**：修改 `backend/app/api/asset_chat.py` — 三个接口都改为批量查询文档（先收集doc_ids，一次in_查询，构建doc_map），避免N+1查询。

### 5. query改写（已完成）

**问题**：RAG检索直接用用户当前消息做检索，不考虑对话上下文，多轮对话时检索质量差。

**方案**：修改 `backend/app/api/asset_chat.py` — send_message和chat_stream接口，把最近2轮对话上下文（4条消息）加入检索query，格式为"用户消息 + 上下文：用户: xxx / 助手: xxx"。

### 6. 推荐问题API（已完成）

**问题**：没有基于用户收藏内容的动态推荐问题。

**方案**：修改 `backend/app/api/asset_chat.py` — 新增GET /asset/chat/suggestions接口，取用户最近5篇已完成AssetSource标题，用LLM生成3个推荐问题。前端sessionStorage缓存。

---

## 三、前端：新建独立对话页

### KnowledgeChat.tsx（已完成）

**文件**：`frontend/src/pages/KnowledgeChat.tsx`（新建，678行）

**功能**：
- 独立对话页，路由/chat
- 三栏布局：左侧会话栏240px + 中间对话区flex + 右侧设置栏260px
- 固定4个医学通用问题：
  1. 总结我收藏的所有文章的核心观点
  2. 找出这些内容中有争议的医学观点
  3. 帮我整理一份知识点清单
  4. 基于我的收藏，推荐几个写作选题
- 动态推荐3个问题（调用/asset/chat/suggestions，sessionStorage缓存）
- 流式对话（SSE）
- 多模型对比（最多3个模型并行）
- 引用来源显示（标题+相似度百分比）
- 会话历史管理（新建/选择/删除/搜索）
- 助手模板选择（auto/general/literature/clinical/popularize）

**路由修改**：`frontend/src/router/index.tsx` — /rag改为/chat，RAGChat改为KnowledgeChat

**导航菜单**：`frontend/src/components/Layout.tsx` — 添加"智能问答"菜单项，指向/chat

**API**：`frontend/src/api/asset.ts` — 新增getChatSuggestions方法

---

## 四、废弃旧系统

### 删除的文件

**后端**：
- `backend/app/api/knowledge.py` — 知识库CRUD API
- `backend/app/api/rag.py` — RAG问答API
- `backend/app/engines/rag.py` — RAG引擎
- `backend/app/models/knowledge.py` — Knowledge模型

**前端**：
- `frontend/src/pages/RAGChat.tsx` — 旧RAG对话页
- `frontend/src/pages/Knowledge.tsx` — 旧知识库管理页

### 修改的文件

**后端**：
- `backend/app/main.py` — 移除knowledge_router和rag_router的导入与注册
- `backend/app/api/__init__.py` — 移除knowledge_router和rag_router导出
- `backend/app/models/__init__.py` — 移除Knowledge导出
- `backend/app/engines/__init__.py` — 移除RAGEngine导出
- `backend/app/api/system.py` — 移除Knowledge初始化数据（init-demo只保留Question）
- `backend/app/services/dashboard_service.py` — 移除Knowledge import
- `backend/app/services/export_service.py` — 移除Knowledge import和export_knowledge方法
- `backend/app/api/export.py` — 移除export_knowledge端点
- `backend/app/schemas/__init__.py` — 移除KnowledgeCreate/KnowledgeUpdate/KnowledgeOut和RAGQuery/RAGResponse/ChatMessage
- `backend/app/database.py` — 移除init_db中的knowledge模块导入（修复启动报错）

**前端**：
- `frontend/src/api/index.ts` — 移除knowledgeApi、ragApi、exportKnowledge
- `frontend/src/router/index.tsx` — 移除Knowledge路由

### 数据库

- 删除Knowledge表（DROP TABLE）

---

## 五、验证结果

### 后端验证
- ✅ 后端import OK：`from app.main import app` 无错误
- ✅ 所有修改文件语法正确
- ✅ 后端启动无ERROR（修复database.py后）

### 前端验证
- ✅ tsc检查：KnowledgeChat.tsx零错误
- ⚠️ AssetDetail.tsx和AssetHub.tsx有历史错误（Modal未定义、force_refresh类型错误），非本次引入，不处理
- ✅ vite build成功（2分23秒）

### Git
- ✅ commit 1：b0c0951 — feat: P0修复+数字资产优化+独立对话页+废弃旧系统（65文件，+15797/-1261）
- ✅ commit 2：4fa9afa — fix: 移除database.py中已删除的knowledge模块导入

---

## 六、遇到的问题和解决方案

### 1. PowerShell多行commit message解析错误
**问题**：git commit -m "多行message"时，PowerShell把换行拆分成多个参数，导致pathspec错误。
**解决方案**：改用单行简短commit message。

### 2. Edit工具要求完整Read文件
**问题**：对大文件（如asset_chat.py 838行）分段Read后，Edit报"File has not been read yet"。
**解决方案**：用一次Read读取整个文件（limit=1000），然后再Edit。

### 3. KnowledgeChat.tsx的tsc错误
**问题**：
- `Search`不是antd的直接导出成员（应该是Input.Search）
- `@/components/MarkdownText`模块不存在（MarkdownText是AssetDetail.tsx的局部组件）
- 参数'e'隐式any类型
**解决方案**：
- 从Input解构Search：`const { TextArea, Search } = Input`
- 在KnowledgeChat.tsx中定义局部MarkdownText组件（复用AssetDetail的实现）
- 给参数加类型：`(e: React.ChangeEvent<HTMLInputElement>)`

### 4. backend/data/目录未被gitignore
**问题**：git status显示`?? backend/data/`，数据库文件未被忽略。
**解决方案**：修改.gitignore，添加`*.db-shm`、`*.db-wal`、`backend/data/`。

### 5. 后端启动报错：cannot import name 'knowledge'
**问题**：删除models/knowledge.py后，database.py的init_db函数还在import knowledge模块，导致后端启动失败。
**解决方案**：修改database.py第48行，移除knowledge导入。commit 4fa9afa修复。

---

## 七、待完成项

1. **AssetHub.tsx拆分重构**：666行未拆分，含手动粘贴降级UI优化（链接解析失败时的手动粘贴入口）
2. **AssetDetail.tsx对话Tab优化**：
   - 检索范围切换（当前文档/全部资产）
   - 全屏按钮跳转/chat
   - 参考来源显示相似度百分比
   - 空状态文字修正
   - tsc错误修复（Modal未定义/force_refresh类型错误）
3. **前端手动粘贴降级UI**：链接解析失败时显示手动粘贴内容的入口
4. **真实功能测试**：启动后端和前端，实际测试对话、推荐问题、多模型对比等功能

---

## 八、关键设计决策记录

1. **系统prompt统一"医学知识助手"**：后端asset_chat.py已统一，不再使用"登麟科技官方助手"
2. **快捷问题**：固定4个医学通用问题 + 动态推荐3个（基于用户最近5篇资产标题LLM生成）
3. **独立对话页布局**：左侧会话栏240px + 中间对话区 + 右侧设置栏260px
4. **旧系统完全废弃**：公司知识库（Knowledge表）整个舍弃，包括level三级过滤
5. **资产详情页对话保留**：默认当前文档，可切换全部资产（待实现切换UI）
6. **RAG检索优化**：批量查询文档避免N+1，query改写加入最近2轮上下文
7. **推荐问题缓存**：前端sessionStorage缓存，避免每次进入页面都调用LLM
