# Provider 能力矩阵

更新时间：2026-09-14

## 1. 验证等级

- documented：官方文档明确支持；
- smoke_verified：已使用当前项目配置完成最小调用；
- experiment_verified：已在影子问题中验证返回结构和稳定性；
- unknown：不能假设；
- unsupported：明确不支持。

## 2. 当前矩阵

| 能力 | 项目当前 GLM 代理 | 智谱官方公开 API | 当前结论 |
|---|---|---|---|
| 普通 Chat | smoke_verified | documented | 可用于 chat 模型认知基准 |
| 实际模型标识 | glm-5.3-flash 已返回 | 官方公开文档当前示例/枚举主要到 GLM-5.2 系列 | 代理模型别名需单独管理 |
| 请求 ID | smoke_verified | documented | 可用于请求追踪 |
| Token Usage | smoke_verified | documented | 可记录成本基础数据 |
| Web Search API | unknown | documented | 当前未配置独立 Search API 地址 |
| Web Search in Chat | unsupported（本次实测） | documented | 代理接受参数但没有执行联网 |
| 结构化 web_search 来源 | unsupported（本次实测） | documented | 响应无 web_search/sources，不能计算 AEO |
| 地区控制 | unknown | 部分搜索参数可控制范围 | 需实验验证 |
| 消费者智谱清言等价性 | unknown | 未发现等价保证 | 不可宣称等价 |
| 计费 | unknown | 官方有独立价格说明 | 代理计费需项目方确认 |
| 数据保留/训练 | unknown | 需按账号协议确认 | 不发送患者敏感信息 |

## 3. 当前环境事实

- GLM_API_KEY 与 GLM_BASE_URL 已配置。
- GLM_MODEL=glm-5.3-flash。
- Base URL Host 是项目自建/代理 IP，不在本文保存完整地址。
- 普通 Chat 冒烟问题要求只返回固定文本，调用成功。
- 返回模型标识 glm-5.3-flash。
- usage 包含 prompt_tokens、completion_tokens、total_tokens 及明细字段。
- Web Search in Chat 单次能力探测中，端点接受 tools 参数但响应没有 web_search/sources，正文明确说明无法实时联网。
- 本次联网探测消耗 837 tokens（prompt 37、completion 800，其中 reasoning 531）。

## 4. 官方文档事实

智谱官方文档把联网能力分为 Web Search API、Web Search in Chat 和 Search Agent。Web Search API 返回标题、URL、摘要等结构化数据；Web Search in Chat 可把搜索结果融入生成回答并返回 web_search 信息。

官方资料：

- 联网搜索概览：https://docs.bigmodel.cn/cn/guide/tools/web-search
- 对话补全：https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8
- Web Search API：https://docs.bigmodel.cn/api-reference/%E5%B7%A5%E5%85%B7-api/%E7%BD%91%E7%BB%9C%E6%90%9C%E7%B4%A2

## 5. 能力探测计划

### Probe A：普通 Chat

已完成。验证文本、模型、ID、usage 和基本成功状态。

### Probe B：参数兼容性（已完成）

当前代理接受 web_search extra_body，没有返回参数错误。

### Probe C：来源结构（未通过）

使用智谱公开 API 文档查询进行一次探测。响应顶层只有 choices、model、request_id、usage 等字段，没有 web_search/sources；回答声明无法实时联网。因此当前代理不能注册 grounded_search。

### Probe D：可重复性

同一查询运行三次，记录成功率、来源域名、URL 重合和响应模型。

### Probe E：医疗问题

只使用医生公开职业信息，不使用患者病例。验证搜索来源是否能定位公开医院/医生页面，并人工核对来源相关性。

## 6. 判定规则

- Probe B 不通过：当前 GLM 仅注册 chat 能力。
- B 通过但无 URL：仍仅算 chat，不计算来源引用；当前实测属于此情况。
- 有 URL 但无法关联回答：记录 raw sources，不计目标引用。
- 代理返回稳定结构化来源且人工核验通过：注册 grounded_search，但显示“GLM 代理搜索”，不称“智谱清言前台”。
- 代理行为与官方文档不一致：以实测代理契约为准并独立记录版本。

## 7. 尚需项目方确认

- 该代理服务的维护方和 SLA；
- glm-5.3-flash 与官方模型的映射；
- 是否转发/实现官方 web_search 参数；
- 每 Token 或每请求价格；
- 日/月预算；
- 输入输出的保存、训练和删除政策。

## 8. 当前注册结论

- provider=glm_proxy；
- mode=chat；
- chat=true；
- grounded_search=false；
- structured_sources=false；
- consumer_equivalent=false/unknown；
- 可以运行普通模型认知影子实验；
- 不允许使用该端点生成 AEO 来源引用指标。
