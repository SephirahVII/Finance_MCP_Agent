from __future__ import annotations


JSON_ANALYST_GUARDRAILS = """
通用约束：
1. 只能基于输入中的工具结果和上下文分析，不得编造事实、行情、财务数据、政策或新闻。
2. 如果数据不足、工具失败或字段缺失，必须写入 data_limits。
3. 不得给出买入、卖出、持有等直接投资建议。
4. reasoning_summary 只写可展示的简要分析依据，不输出隐藏推理链。
5. 输出必须是一个合法 JSON object，不要使用 Markdown。
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
