# 首批影子问题集设计

版本：shadow-questions-v1  
状态：候选，待确认首批医生

## 1. 变量

- doctor_name：目标医生公开姓名；
- hospital：当前执业医院；
- department：科室；
- city：城市；
- specialty_primary：第一专业方向；
- specialty_secondary：第二专业方向。

变量只能来自已确认公开资料。Discovery 和 Informational 问题不得在发送给待测模型的隐藏上下文中加入 doctor_name。

## 2. 分布

- Discovery：12；
- Branded：6；
- Comparison：6；
- Informational：6；
- 总计：30。

## 3. 使用规则

1. 先渲染变量并由人工检查语义自然性。
2. 每条问题单独发送，不带前一问题对话历史。
3. Chat 与 Grounded Search 分开运行。
4. 每条问题每个 mode 默认三次采样。
5. Prompt 不向模型透露“正在测试目标医生是否出现”。
6. 原始问题、渲染问题、版本和变量快照同时保存。
7. 医疗问题只用于公开信息与一般科普评估，不构成诊疗建议。

## 4. 金标准不是预设答案

问题集只定义要观察的用户意图，不预设目标医生应该被推荐。人工标注应忠实判断实际回答，不因医生是测试目标而提高评价。

## 5. 候选医生

当前数据库有两份资料：张医生和 Jena。建议先使用资料更完整的 Jena；用户确认前 JSON fixture 保持变量模板，不渲染姓名。
