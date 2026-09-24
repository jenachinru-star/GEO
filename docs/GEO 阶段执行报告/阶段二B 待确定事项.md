## 需要讨论的问题

### 问题 1（最关键）：配额检查接口完全不匹配 — 影响 B4/B5/B8

**手册写的接口**（不存在）：

```
from app.utils.quota_checker import quota_checker
quota_ok, quota_msg = quota_checker.check(user_id, "image_generate", estimated_tokens=500)
```

**实际代码中的接口**：

```
from app.services.quota_checker import check_quota, QuotaError
check_quota(db, user_id)  # 失败抛 QuotaError，按月费用（元）计算，不是按token
```

实际配额系统查的是 `LlmUsageLog.estimated_cost` 当月累计 vs `UserQuota.monthly_cost_limit`。

**衍生问题**：生图 / 生视频记用量时 `platform="seedream"/"seedance"`，但 `settings.MODEL_PRICING` 里没有这两个平台的价格，导致 `estimated_cost=0`，配额检查永远不会触发。

**我的建议方案**：

- B4/B5/B8 统一用实际的 `check_quota(db, user_id)`（失败抛 `QuotaError`，捕获后返回 402）
- 在 `MODEL_PRICING` 中补充 seedream/seedance 的价格（比如生图按次固定成本、生视频按次固定成本），让用量能计入月费用
- 或者给生图 / 生视频每次设置一个固定 `estimated_cost` 值（不走价格表）

**请确认**：用哪种方式？seedream/seedance 的每次成本设多少合适？

------

### 问题 2：B6 export_tasks.py 引用了不存在的函数

手册写 `from app.api.asset_export import build_html_content, build_markdown_content`，但实际代码中：

- 只有 `build_markdown_content(doc, notes)`（2 个参数，总是包含摘要 + 总结 + 笔记）
- 只有 `markdown_to_html(md_content, title)`（2 个参数）
- **没有** `build_html_content` 函数，也没有 `include_summary/include_notes/include_abstract` 可选参数

**我的建议方案**：export_tasks.py 中直接调用 `build_markdown_content(doc, notes)` → `markdown_to_html(md, doc.title)` → weasyprint。`include_*` 参数暂时忽略（现有函数不支持），后续如需再扩展 `build_markdown_content` 的签名。

**请确认**：是否接受这个适配？还是需要给 `build_markdown_content` 加上 `include_*` 参数？

------

### 问题 3：B5 视频用量记录会重复

手册在 `get_video_status` 中写 `if result.status == "succeeded" and local_task.finished_at:` 就记用量。但用户每次轮询 status 都会触发，如果任务已完成，每次查询都会重复写一条 usage_log。

**我的建议方案**：在 VideoTask 模型加一个 `usage_logged` 布尔字段，记完用量后置 True，后续查询跳过。或者只在本次查询中状态**刚从 running 变为 succeeded** 时才记录（比较 `local_task.status` 旧值）。

**请确认**：用哪种去重方式？

------

### 问题 4：B8 文档大小限制检查哪个字段

手册写 `if doc.content and len(doc.content) > 100000`，但实际 `build_markdown_content` 导出时只用了 `doc.summary[:1000]` 和 `doc.ai_summary`，**没有用 `doc.content`（全文）**。所以即使 `doc.content` 有 10 万字，导出的实际内容也很小。

**我的建议方案**：大小限制检查 `doc.content`（原始全文长度），作为预防性限制；同时这也合理 —— 全文越大，AI 总结和导出的潜在成本越高。

**请确认**：检查 `doc.content` 还是检查导出后的实际内容大小？

------

以上 4 个问题确认后，我就按 B1→B13 顺序逐项执行，每完成一项做一次静态检查。其余 9 项（B1/B2/B3/B7/B9/B10/B11/B12/B13）手册与代码一致，无疑问。