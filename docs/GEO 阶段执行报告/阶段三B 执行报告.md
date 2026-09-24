## 阶段三 B 执行完成报告

**Git Commit**: `8f88b95`（基线 `e537de6` → `8f88b95`，14 个文件，+526/-13 行）

### 8 项修复状态

表格

| 编号 | 修复项                                                    | 状态 | 涉及文件                                                     |
| ---- | --------------------------------------------------------- | ---- | ------------------------------------------------------------ |
| E1   | PublishAccount 模型加 app_id/app_secret 字段 + 数据库迁移 | ✅    | `models/publish_account.py`, `database.py`                   |
| E2   | 微信公众号官方 API 发布器                                 | ✅    | `publishers/wechat.py`（新建）                               |
| E3   | 知乎 / 百家号 / 小红书发布器框架                          | ✅    | `publishers/zhihu.py`, `baijiahao.py`, `xiaohongshu.py`（新建） |
| E4   | 发布器工厂注册所有平台                                    | ✅    | `publishers/factory.py`                                      |
| E5   | 发布执行异步任务 + worker 注册                            | ✅    | `worker/publish_tasks.py`（新建）, `worker/worker.py`        |
| E6   | Distribution API 加一键发布接口                           | ✅    | `api/distribution.py`                                        |
| E7   | Distribution 前端一键发布按钮 + 进度展示                  | ✅    | `pages/Distribution.tsx`, `api/index.ts`                     |
| E8   | 发布账号表单动态字段 + 后端加密                           | ✅    | `pages/PublishAccounts.tsx`, `api/publish_account.py`        |

### 新建文件（5 个）

- `backend/app/publishers/wechat.py` — 微信公众号发布器（kind=api）
- `backend/app/publishers/zhihu.py` — 知乎发布器框架（kind=manual）
- `backend/app/publishers/baijiahao.py` — 百家号发布器框架（kind=manual）
- `backend/app/publishers/xiaohongshu.py` — 小红书发布器框架（kind=manual）
- `backend/app/worker/publish_tasks.py` — article_publish 异步任务处理器

### 验证结果

表格

| 验证项                                                  | 结果          |
| ------------------------------------------------------- | ------------- |
| 后端 `from app.main import app`                         | ✅ 通过        |
| 数据库迁移（app_id/app_secret 字段）                    | ✅ 已确认存在  |
| 工厂 `get_publisher('wechat')` 返回 WechatPublisher     | ✅ kind=api    |
| 工厂 `get_publisher('zhihu'/'baijiahao'/'xiaohongshu')` | ✅ kind=manual |
| 任务类型注册包含 `article_publish`                      | ✅             |
| 前端 `Distribution.tsx` / `PublishAccounts.tsx` TS 编译 | ✅ 无错误      |

### 与手册的适配调整（执行中发现的差异）

1. **PublishResult 字段**：实际是 `platform_code`（非`platform`），`external_id`（映射`publish_id`），无`message`字段（放入`raw_response`）
2. **BasePublisher 抽象方法**：实际是 `check_status`（非`get_status`），WechatPublisher 已实现
3. **ManualPublisher 构造函数**：需要`platform_code`参数，三个子类均定义了`__init__`调用`super().__init__()`
4. **模型类名**：实际是 `ArticleDistribution`（非`Distribution`），`ArticleDraft`无`full_text`/`author`字段
5. **AsyncTask**：补充了`workspace_id`（通过`get_user_workspace_id`获取），与现有 recollect 接口保持一致

### 已知限制 / 后续优化项

1. **微信发布是异步的**：提交后返回`publish_id`，文章 URL 需通过`check_status`轮询获取，当前`publish_url`返回空字符串
2. **封面图**：微信图文发布需要`thumb_media_id`，当前留空使用默认封面
3. **其他平台**：知乎 / 百家号 / 小红书继承 ManualPublisher（半自动），未实现自动发布（需 cookie 模拟登录，风险高）
4. **前端 tsc 遗留错误**：`AssetDetail.tsx`/`AssetHub.tsx`有 3 个之前阶段遗留的 TS 错误，非本次引入
5. **实际发布验证**：需要用户提供有效的微信公众号 AppID/AppSecret，并将账号标记为 "valid" 后才能端到端测试