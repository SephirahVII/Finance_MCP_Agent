from __future__ import annotations


JSON_ANALYST_GUARDRAILS = """
要求：
1. 只基于输入上下文和工具返回结果分析，不得编造数据、公司事实或行业事件。
2. 工具返回为空、权限不足、网络错误或样本不足时，必须在 data_limits 中说明。
3. 不得给出买入、卖出、持有等直接投资建议。
4. 区分数据事实、解释性判断和风险提示。
5. 输出必须是合法 JSON object，不要使用 Markdown。
""".strip()


ANALYST_JSON_SCHEMA = """
{
  "summary": "string",
  "key_findings": ["string"],
  "strengths": ["string"],
  "risks": ["string"],
  "data_limits": ["string"],
  "confidence": "low|medium|high",
  "reasoning_summary": ["string"]
}
""".strip()
