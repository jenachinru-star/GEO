## 阶段三 A 执行完成报告

**commit hash**: `e537de6`（21 files changed, +401 / -56）

### 11 项修复状态

表格

| 编号 | 修复项                               | 状态 | 涉及文件                                                   |
| ---- | ------------------------------------ | ---- | ---------------------------------------------------------- |
| D1   | semantic_generator 查用户平台开关    | ✅    | `engines/semantic_generator.py`, `api/doctor.py`           |
| D2   | semantic_extender 查用户平台开关     | ✅    | `engines/semantic_extender.py`, `api/semantic.py`          |
| D3   | article_generator 查用户平台开关     | ✅    | `engines/article_generator.py`, `worker/article_tasks.py`  |
| D4   | llm_analyzer 查用户平台开关          | ✅    | `engines/llm_analyzer.py`, `engines/collector.py`          |
| D5   | rag 查用户平台开关                   | ✅    | `engines/rag.py`, `api/rag.py`                             |
| D6   | adapter_factory 支持 Platform 表读取 | ✅    | `adapters/factory.py`, `main.py`, `api/platforms.py`       |
| D7   | 数据迁移脚本                         | ✅    | `migrations/sync_platform_from_env.py`（新建）             |
| D8   | 前端文案修正 + 管理员 reload         | ✅    | `components/PlatformConfig.tsx`                            |
| D9   | usage.py 用量导出接口                | ✅    | `api/usage.py`, `api/index.ts`, `pages/UsageDashboard.tsx` |
| D10  | article.py 列表 keyword 搜索         | ✅    | `api/article.py`, `pages/ContentHub.tsx`                   |
| D11  | article.py 列表返回统计字段          | ✅    | `api/article.py`, `pages/ContentHub.tsx`                   |

### 关键设计决策

1. **D1-D5 user_id 传递方式**：D1/D2/D3 通过构造函数传入（`__init__(db, user_id)`），D4/D5 通过方法参数传入（`analyze(..., db, user_id)` / `generate_answer(..., user_id)`），因为 llm_analyzer 是全局单例不能存用户态。
2. **D6 数据库优先 .env 兜底**：`load_from_db()` 仅在 Platform 表有启用数据时覆盖，表空或加载失败时保持 .env 配置不变。所有文本平台统一用 `OpenAICompatibleAdapter` 初始化（4 个平台均继承它且无特殊逻辑）。
3. **D3 空平台回退**：article_generator 过滤后无可用平台时返回 `None`，外层 `generate()` 自动降级到模板生成，不报错。
4. **D5 RAG 平台回退**：用户请求了已停用的平台时，自动回退到第一个启用的平台并打日志。

### Platform 表迁移结果

运行迁移脚本后新增 **4 条** 数据：deepseek、glm、minimax、doubao。幂等设计，重复运行跳过已存在记录。

### 验证结果

- ✅ 后端 `from app.main import app` import 通过
- ✅ 迁移脚本运行成功，Platform 表 4 条数据
- ✅ `adapter_factory.load_from_db()` 加载成功，4 个平台从数据库读取
- ✅ 前端本次修改的 4 个文件无 TS 新错误（AssetDetail/AssetHub 的 5 个 TS 错误为之前阶段遗留，不在本次范围）

### 遗留事项

- 前端 `AssetDetail.tsx` / `AssetHub.tsx` 有 5 个 TS 错误（`Modal` 未导入、`force_refresh` / `selectable` 类型不匹配），是阶段二资产模块遗留，本次未触碰。
- Platform 表 api_key 为明文存储，与 .env 一致，加密留到后续优化。
- 功能级验证（停用平台后实际触发 LLM 调用、管理员修改配置后热更新、导出 Excel 下载）需启动后端用 liujinru 账号在浏览器中操作验证。