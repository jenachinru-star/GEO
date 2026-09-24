# 阶段四A 执行报告：微信公众号数据采集与账号概览

> **执行日期**：2026-09-23
> **基线 commit**：80908f6（阶段三C）
> **本次 commit**：`4c5dfd2` — feat: 阶段四A-微信公众号数据采集与账号概览（8项）
> **改动规模**：12 个文件，+1187 / -14
> **Python**：C:\Users\jenac\miniconda3\python.exe

---

## 一、总体结论

阶段四A的**全部代码改动已按手册 13 个步骤完成并提交**。在当前环境可验证的范围内，所有代码级检查均通过：数据库迁移、后端 import、后端启动与定时任务注册、前端打包、5 个新 API 的空数据/隔离/守卫逻辑、微信发布器改造。

**有 2 个纯环境配置问题阻断了"真实数据采集"的正向验证**（不是代码缺陷，需要你在微信后台/部署配置上处理，详见第五节）。处理后无需再改代码，即可走通"验证 → 手动采集 → 图表/文章数据展示"全流程。

---

## 二、8 项交付物状态

| # | 交付项 | 状态 | 说明 |
|---|--------|------|------|
| 1 | 3 张数据表 + 迁移脚本 | ✅ 完成 | 账号每日统计 / 文章基本信息 / 文章数据快照，迁移已执行、表结构已核对 |
| 2 | 数据采集服务 `wechat_data_service.py` | ✅ 完成 | token、4 个 datacube 接口、素材列表、采集汇总入库；微信连通性与错误处理已验证 |
| 3 | 异步任务 `wechat_data_tasks.py` + Worker 注册 | ✅ 完成 | 新任务类型 `wechat_data_collect` 已出现在 Worker 注册列表 |
| 4 | 定时采集任务（每天 02:00） | ✅ 完成 | 启动日志确认注册，自动为所有已验证微信账号投递前一天数据 |
| 5 | 5 个新 API | ✅ 完成 | 概览/趋势/文章列表/手动采集/真实验证，HTTP 层逐一测试通过 |
| 6 | 前端账号数据概览页 + 路由 + 入口按钮 | ✅ 完成 | 页面打包通过；空数据态、汇总卡片、双趋势图、文章表格、"数据"按钮就位 |
| 7 | 微信发布器完善（封面图 + 真实 URL 轮询） | ✅ 完成 | `_upload_image`、`_upload_news` 封面参数、发布后 5 次轮询取真实 URL |
| 8 | 发布账号真实验证 `verify-real` | ✅ 完成 | 微信调用官方 API 真实校验，成功/失败均落库并返回明确信息；其他平台仍手动标记 |

---

## 三、实际改动文件与行号

### 新建文件（5 个）

| 文件 | 行数 | 内容 |
|------|------|------|
| `backend/app/models/wechat_stats.py` | 75 | `WechatAccountStats`（L20-48）、`WechatArticle`（L51-65）、`WechatArticleStats`（L68-75） |
| `backend/app/services/wechat_data_service.py` | 348 | `WechatDataService`：token L30-42、`verify_credentials` L45-52、用户增减 L55-73、累计用户 L76-94、图文每日 L97-115、图文总数据 L118-136、素材列表 L139-152、`collect_and_store` L155-348 |
| `backend/app/worker/wechat_data_tasks.py` | 39 | `handle_wechat_data_collect` L18-36；L39 注册到 task_registry |
| `backend/migrations/add_wechat_stats_tables.py` | 24 | `upgrade()` L13-22，`Base.metadata.create_all` 建 3 表（幂等） |
| `frontend/src/pages/WechatAccountStats.tsx` | 244 | 概览卡片、近 30 天汇总、粉丝/阅读双 ECharts 趋势图、文章分页表格、手动采集（5 秒后刷新） |

### 修改文件（7 个）

| 文件 | 关键行号 | 改动 |
|------|---------|------|
| `backend/app/models/__init__.py` | L40（导入）、L76-78（`__all__`） | 注册 3 个新模型 |
| `backend/app/worker/worker.py` | L39（导入模块）、L68（超时 300s） | 注册 `wechat_data_collect` 任务类型与 5 分钟超时 |
| `backend/app/main.py` | L121-170（新函数）、L207-219（注册 + 打印） | 新增 `scheduled_collect_wechat_data`；lifespan 中注册 cron（hour=2, id=`daily_wechat_data_collect`） |
| `backend/app/api/publish_account.py` | L2、L7-12（导入）；L159-189 verify-real、L191-255 overview、L257-297 trend、L299-346 articles、L348-390 collect | 5 个新端点，全部校验 `user_id` 隔离 |
| `backend/app/publishers/wechat.py` | L41-79 `_upload_image`；L82 起 `_upload_news`（L83 加 `cover_url`、L95 上传封面、thumb_media_id 生效）；L159 取 cover_url；L173-194 轮询真实 URL | 封面图上传（URL/二进制）+ 发布后 5 次×3 秒轮询 |
| `frontend/src/pages/PublishAccounts.tsx` | L8/L10（图标与 useNavigate 导入）、L34（navigate）、L70-90（handleVerify 区分真实/手动）、L143-150（"数据"按钮）、验证按钮传 platform | 微信账号显示"数据"按钮并跳转概览页；微信走真实验证 |
| `frontend/src/router/index.tsx` | L25（懒加载）、L61（路由） | 注册 `publish-accounts/:accountId/stats` 路由 |

> 注：手册改动清单写的是 `frontend/src/App.tsx`，但本项目 App.tsx 只挂载 `@/router`，路由实际在 `frontend/src/router/index.tsx`，故路由改在该文件（详见第四节·更正 1）。

---

## 四、手册与实际代码不符之处（已做必要机械更正）

执行中发现手册 3 处与代码现状不符。这些**不涉及设计偏离**，是满足你给定验证清单（图表渲染 / 数据刷新 / tsc 通过）的唯一正确处理，已按正确方式落地：

1. **路由位置（步骤 11）**：手册要求改 `App.tsx`，实际路由集中在 `frontend/src/router/index.tsx`。已在该文件注册懒加载（L25）与嵌套路由（L61），未改动 App.tsx。

2. **响应取值（步骤 10、13）**：axios 响应拦截器（`frontend/src/api/index.ts` L80-89）已 `return response.data`，即 `await request.*()` 直接得到响应体 `{code, message, data}`，不是完整 axios response。手册页面写的 `res.data?.data` 会取到 undefined，导致页面永久空白、图表无数据。已改为：
   - 概览/趋势：`setOverview(res.data)` / `setTrendData(res.data)`
   - 文章：`res.data?.items`、`res.data?.total`
   - 真实验证（步骤 13）：`res.data?.valid`、`res.data?.error`

3. **缺少 `Select` 导入（步骤 10）**：页面趋势卡片使用了 `<Select>/<Select.Option>`（7/30/90 天切换），但手册的 antd 导入清单没有 `Select`，会直接导致 `tsc` 报错。已在导入中补上 `Select`，并移除了手册里未使用的 `DatePicker / Spin / Alert` 导入。

---

## 五、阻断真实数据采集的 2 个环境问题（需你处理）

### 阻断 1：`ENCRYPT_KEY` 未持久化，已存 AppSecret 无法解密

- **现象**：`app/config.py` L85 中 `ENCRYPT_KEY` 默认 `""`，`backend/.env` 也未配置。此时 `app/utils/crypto.py` L11-13 会在**每个进程启动时随机生成**内存密钥。数据库中"层次智慧"的 AppSecret（140 字符）是**之前某次会话用另一个随机密钥**加密的，当前进程解密静默返回空（`decrypt` 失败不抛异常），采集因此报"账号未配置 AppID 和 AppSecret"。
- **影响**：数据采集、真实验证、以及阶段三B的微信发布都会受影响；更关键的是，**即使现在重新录入 Secret，后端一重启又会失效**。
- **建议修复（涉及部署配置与密钥，我未擅自改动）**：
  1. 生成固定密钥：
     `C:\Users\jenac\miniconda3\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  2. 在 `backend/.env` 增加一行：`ENCRYPT_KEY=<上一步生成的密钥>`
  3. 重启后端，在"发布账号管理"里**重新录入一次"层次智慧"的 AppSecret**（用新固定密钥重新加密）。

### 阻断 2：本机出口 IP 不在微信公众号 IP 白名单

- **现象**：调用 token 接口，微信返回 `errcode 40164: invalid ip 58.250.109.138, not in whitelist`。
- **建议修复**：登录微信公众平台 → **设置与开发 → 基本配置 → IP 白名单**，添加当前出口 IP `58.250.109.138`；生产部署时还需添加**服务器的固定出口 IP**。家用宽带 IP 可能随光猫重启变化，变更后需同步更新白名单。

> 两个问题都处理后：在发布账号页点"验证"应提示成功 → 点"手动采集数据（最近 7 天）"，约 1-2 分钟后粉丝/阅读趋势图与文章列表即显示真实数据。代码侧无需再改动。

---

## 六、验证结果明细

| 验证项 | 结果 | 证据 |
|--------|------|------|
| 1. 数据库迁移 | ✅ 通过 | 脚本输出 3 表创建完成；离线核对 `geo_wechat_account_stats`(16 列)、`geo_wechat_article`(12 列)、`geo_wechat_article_stats`(17 列) 均存在 |
| 2. 后端 import | ✅ 通过 | `from app.main import app` → `import OK` |
| 3. 后端启动 | ✅ 通过 | 无 ERROR；日志确认"定时任务已启动（10:00）"与"微信公众号数据定时采集已启动（02:00）"；Worker 注册类型列表含 `wechat_data_collect` |
| 4. 前端 tsc | ⚠️ 本次文件零错误 | 我新增/修改的文件无任何 TS 错误；**另有 6 个错误在未改动的 `AssetDetail.tsx`/`AssetHub.tsx`**（阶段二C commit a0f2d99 遗留，HEAD 即存在，手册范围外，未擅改） |
| 5. 前端打包 | ✅ 通过 | `npx vite build` → `✓ built in 30.06s`，仅有 chunk >500kB 的既有体积警告 |
| 6. API 空数据态 | ✅ 通过 | overview 返回 `has_data:false`；trend 返回空数组；articles 返回空列表（均 HTTP 200） |
| 7. 用户隔离 / 鉴权 | ✅ 通过 | 他人访问账号 → 404；不存在账号 → 404；未带 Token → 401 |
| 8. 真实验证逻辑 | ✅ 通过 | 假 AppID 调 verify-real → `valid:false` + errcode 40013，账号置 expired；非微信平台调 verify-real → 400 |
| 9. 采集守卫逻辑 | ✅ 通过 | 未验证账号调 collect → 400"账号未验证，请先验证账号" |
| 10. 微信 API 连通性 | ✅ 通过 / 见阻断 2 | 请求构造正确，微信正常返回结构化 errcode/errmsg；错误处理链路（verify_credentials → False）正常 |
| 11. 真实数据正向采集 | ⛔ 被阻断 | 受第五节 2 个环境问题阻断，待你处理后即可验证 |

---

## 七、其他说明

- 测试期间创建的临时账号、临时脚本、启动日志、`frontend/dist` 构建产物均已清理，工作区中本次涉及的跟踪文件在提交后保持干净。
- `startup_error.log`、`startup_test.log`（2026-09-18 早期会话遗留）非本次产物，未做改动。
- 严格遵守"不修改手册范围外代码"：阶段二C 遗留的 6 个 tsc 错误、以及 `ENCRYPT_KEY` 基础设施缺口，均只记录、未自行修改，方案已在本报告给出，待你确认后处理。

---

**报告结束。**
