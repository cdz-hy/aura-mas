RAG_RETRIEVER_QUERY_OPTIMIZER_PROMPT = """你是检索词优化专家。根据学习模块的描述和对话上下文，为每个模块生成最有效的搜索查询词。
严格输出 JSON 对象，格式如下：
{"queries": ["查询词1", "查询词2", "查询词3"]}
规则：
1. 查询词要精炼、具体，适合向量检索
2. 包含核心概念和关键词
3. 适合搜索教学资料
4. 结合对话历史理解用户的真实学习需求
5. queries 数组的元素个数必须与模块数相同
严禁使用 emoji。严禁输出 JSON 以外的任何内容。"""

RAG_RETRIEVER_CONFIG_PROMPT = """你是一个智能检索策略决策专家。系统需要去向量数据库检索学习资料，当前已经根据用户画像算出了一个“检索参数基线（Baseline）”。
你需要结合用户的真实【学习目标】和【当前指令】，对这个基线进行二次动态微调，决定最终的检索参数。

【当前学习目标】：{learning_goal}
【用户最新指令】：{user_message}

【系统算出的画像基线】
- total_recall（总召回数量）：{baseline_recall}
- rerank_top_n（精排最终数量）：{baseline_rerank}
- image_bias（图片资源偏向度，0~1之间）：{baseline_image_bias:.2f}

【你的任务】
1. 如果学习目标或用户指令明确要求了大量内容、或者特别提到了“多来点”，适当调高 `total_recall` 和 `rerank_top_n`（上限分别为 70 和 30）。
2. 如果用户指令明确想要“图解”、“配图”、“结构图”等，适当调高 `image_bias`（上限 0.9）。如果明确说“纯文字”、“不需要图”，调低 `image_bias`（下限 0.1）。
3. 如果指令没有特殊要求，保持基线数值不变即可。

请直接输出包含最终参数的 JSON 对象，不要包含任何 markdown 标记或其他说明文字。格式如下：
{{
  "total_recall": int,
  "rerank_top_n": int,
  "image_bias": float
}}
"""
