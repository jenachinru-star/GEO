# AI 可见度影子实验

本工具与正式 Collector、MonitorRecord 和 AsyncTask 隔离。默认 dry-run，不会调用 API；只有显式 --execute 才调用 GLM。

在 backend 目录执行示例：

    python -m experiments.visibility.run_shadow --profile-id 2 --mode chat --samples 3

真实单题冒烟：

    python -m experiments.visibility.run_shadow --profile-id 2 --mode chat --samples 1 --question-id B01 --execute

联网能力探测：

    python -m experiments.visibility.run_shadow --profile-id 2 --mode grounded_search --samples 1 --question-id B03 --execute --allow-unverified-grounded

当前 GLM 代理已实测没有执行 Web Search、也没有返回结构化来源，因此 grounded_search 默认被阻止。上述参数只允许以后重新做单次能力探测，不能把结果作为 AEO。

注意：执行前必须确认医生对象、代理计费和请求数量。实验产物位于项目 artifacts/shadow，已被 Git 忽略，可能包含完整模型回答，禁止直接提交。

真实执行会生成 observations.jsonl、provider-errors.jsonl、review-sheet.csv 和 summary.json。人工按 shadow-annotation-guide.md 填写 review-sheet.csv 后，可运行：

    python -m experiments.visibility.compare_analysis PATH_TO_REVIEW_SHEET
