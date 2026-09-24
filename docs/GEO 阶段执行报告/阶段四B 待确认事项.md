我已完整阅读手册并核对了现有代码与微信官方文档，发现**手册中数据快照部分的设计与微信 API 真实行为存在重大出入**，按手册原文实现会导致快照功能失效。动手前需要和您确认几个问题。

## 一、手册代码与实际代码不符（机械适配，我计划直接修正并记录）

表格

| #    | 手册写法                                         | 实际情况                                                     | 计划处理                                        |
| ---- | ------------------------------------------------ | ------------------------------------------------------------ | ----------------------------------------------- |
| 1    | `UserPlatformPref.platform_type == "text"` 过滤  | 该表只有 `user_id/platform_code/enabled`，无 `platform_type`，查询会报错 | 去掉该过滤条件                                  |
| 2    | `adapter.query()` 返回值按 dict 取 `["content"]` | 实际返回 `QueryResult` 对象（`.answer/.success/.total_tokens`） | 改读 `.answer`，token 写入 `tokens_used`        |
| 3    | `Semantic.enabled` / `Semantic.text`             | 实际字段为 `is_active` / `question`                          | 替换字段名                                      |
| 4    | 路由以对象数组注册                               | 实际是 JSX `<Route>` 结构                                    | 按现有风格加一行 `<Route>`                      |
| 5    | 导出用 `window.open()` 下载                      | 鉴权靠 `Authorization: Bearer`（localStorage），window.open 不带 token 会 401 | 复用 api/index.ts 现成的 blob 下载（exportApi） |
| 6    | 4 个新 API 直接追加到文件末尾                    | `articles/export` 会被 `articles/{article_id}` 先匹配导致 422 | export 路由声明在 detail 路由之前               |

## 二、需要您拍板的设计问题

### 问题 1（最重要）：文章快照设计与微信 API 真实行为冲突

我核实官方文档（[getarticletotal](https://developers.weixin.qq.com/doc/service/api/wedata/news/api_getarticletotal.html)）确认：

1. **该接口最大时间跨度只有 1 天**（begin_date 必须等于 end_date）。手册用 days=7 一次请求多日 → 微信返回日期范围错误，`article_total` 为空，**文章数据根本采不到**。
2. **details 里的数值是 "截至该日的累计总量"，不是每日新增量**（官方原文："每天对应的数值为该文章到该日为止的总量，而不是当日的量"）。手册却按每日增量逐行累加 → 数据会重复计算（第 3 天的值变成 1+2+3 三天总量之和）。
3. **该接口最多只统计发表日后 7 天的数据**，**day_30 快照在这个接口下物理上不可能拿到**。

**我建议的修正方案：**

- 采集改为**逐日循环调用**（窗口内每天一次请求，默认 7 次调用）；

- details 行直接按累计值读取，不再累加；stat_date 推算出发布后第 N 天，命中 1/3/7 就存快照；

- 定时任务（现在 days=1 只查昨天，永远采不到第 3/7 天）改为每天重查「昨天 / 3 天前 / 7 天前」三个群发日，每次调用都会返回该文章截至当日的全部累计行，可自动回填遗漏的快照，每账号每天仅 3 次调用；

- day_30 的处理，请您二选一

  ：

  - **方案 A（推荐）**：本次只交付 day_1/3/7，day_30 留空（前端图上显示 0），day_30 作为阶段四 C 或补丁，届时改用微信新接口 [getarticletotaldetail](https://developers.weixin.qq.com/doc/service/api/wedata/news/api_getarticletotaldetail.html)（支持发表后 30 天，但指标体系不同：2025 年 11 月起微信全行业下线 "阅读次数 / 分享次数"，只剩人数类指标，还多了完读率、平均阅读时长等，需要单独做字段映射）。
  - **方案 B**：本次就把新接口 getarticletotaldetail 一并集成，工作量明显增加，且要处理新旧两套指标字段的映射（新接口只有 read_user/share_user/like_user/collection_user，没有 count 类字段）。

### 问题 2：发布记录与采集记录无法自动关联（会导致文章重复）

发布器拿到的是永久素材 media_id 和 publish_id，而 getarticletotal 里的 msgid（如 `202457380_1`）是另一套 ID，两者无法对应。按手册 "采集时只按 msgid 查" 会**新建重复记录**：一条有正文无数据、一条有数据无正文，从带数据的记录进详情会提示 "无正文"，AI 内容分析维度名存实亡。

**建议**：采集按 msgid 查不到时，再按「同账号 + 标题完全相同」查发布时留下的记录，找到则补上 msgid 并在原记录上挂快照（正文保留）。是否同意？

### 问题 3：AI 分析任务失败时记录会永久卡在 processing

手册任务 handler 只在成功时写库；LLM 失败后 ArticleAnalysis 仍是 processing，前端轮询 60 秒后永远停在 "分析中"。模型本身定义了 `failed/failed_reason` 字段却从未被使用。

**建议**：在 handler 外层加 try/except，失败时置为 failed 并写入原因。是否同意？

------

我的整体推荐：**问题 1 选方案 A，问题 2、问题 3 都按建议做**，这样阶段四 B 能可靠交付，day_30 和新指标体系留给阶段四 C 统一处理。请您确认或提出不同意见，确认后我立即按 14 个步骤执行。