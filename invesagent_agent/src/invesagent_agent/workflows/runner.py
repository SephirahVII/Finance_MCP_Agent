from __future__ import annotations

import argparse

from invesagent_agent.workflows.research_graph import run_research_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LangGraph multi-agent research workflow.")
    parser.add_argument("query", nargs="*", help="Research question.")
    parser.add_argument("--market", default="cn", help="Market code, e.g. cn, hk, us.")
    parser.add_argument("--asset-type", default="stock", help="Asset type, e.g. stock, index, etf.")
    parser.add_argument("--provider", default="auto", help="Data provider, e.g. auto, tushare, akshare.")
    parser.add_argument("--industry-member-limit", type=int, default=10)
    parser.add_argument("--show-state", action="store_true", help="Print final state keys after the report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    query = " ".join(args.query).strip()
    if not query:
        query = "请分析白酒行业主要公司的量价表现、基本面情况，并生成一份中文研究报告。"

    result = run_research_workflow(
        user_query=query,
        market=args.market,
        asset_type=args.asset_type,
        provider=args.provider,
        industry_member_limit=args.industry_member_limit,
    )

    print(result.get("final_report") or result.get("draft_report") or "No report generated.")

    if args.show_state:
        print("\n--- Final State Keys ---")
        print(sorted(result.keys()))


if __name__ == "__main__":
    main()
