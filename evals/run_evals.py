from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parent
BENCHMARK_CASE_DIRS = {
    "l1": ROOT / "cases",
    "l2": ROOT / "benchmarks" / "l2_integration",
    "l3": ROOT / "benchmarks" / "l3_quality",
}
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
for package_src in (
    WORKSPACE_ROOT / "invesagent_agent" / "src",
    WORKSPACE_ROOT / "invesagent_mcp" / "src",
    WORKSPACE_ROOT / "invesagent_rag" / "src",
):
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))

from evals.evaluators.efficiency import evaluate_efficiency
from evals.evaluators.llm_judge import evaluate_llm_judge
from evals.evaluators.memory import evaluate_memory
from evals.evaluators.output_quality import evaluate_output_quality
from evals.evaluators.quality import evaluate_report_quality
from evals.evaluators.rag import evaluate_rag
from evals.evaluators.route import evaluate_route
from evals.evaluators.task_plan import evaluate_task_plan
from evals.evaluators.tool_calls import evaluate_tool_calls
from evals.evaluators.trajectory import evaluate_trajectory
from evals.fixtures.fake_rag import fake_retrieve_policy_evidence
from evals.fixtures.mock_llm import install_mock_llm
from evals.fixtures.mock_tool_client import EvalMockToolClient
from evals.schemas import EvalCase
from invesagent_agent.workflows.chat_graph import run_chat_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run InvesAgent eval harness.")
    parser.add_argument(
        "--benchmark",
        choices=["l1", "l2", "l3", "all"],
        default="l1",
        help=(
            "Benchmark layer. l1 is deterministic workflow regression; "
            "l2 is integration-oriented tool/RAG benchmark; l3 is report quality benchmark."
        ),
    )
    parser.add_argument("--cases-dir", default=None)
    parser.add_argument("--results-dir", default=str(ROOT / "results"))
    parser.add_argument("--category", default=None, help="Run only one category.")
    parser.add_argument("--case-id", default=None, help="Run only one case id.")
    parser.add_argument(
        "--real-tools",
        action="store_true",
        help="Use the project default tool client instead of EvalMockToolClient.",
    )
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Do not patch AgentRuntime LLM calls with deterministic mock responses.",
    )
    parser.add_argument(
        "--real-rag",
        action="store_true",
        help="Do not patch macro policy retrieval with fake RAG hits.",
    )
    parser.add_argument(
        "--llm-judge",
        action="store_true",
        help="Run optional LLM-as-Judge for L3 quality cases.",
    )
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def load_cases(cases_dir: Path, benchmark: str) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in sorted(cases_dir.glob("*.json")):
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, list):
            raise ValueError(f"case file must contain a list: {path}")
        for item in values:
            item = {**item, "benchmark": benchmark}
            cases.append(EvalCase.from_dict(item))
    return cases


def load_benchmark_cases(args: argparse.Namespace) -> list[EvalCase]:
    if args.cases_dir:
        return load_cases(Path(args.cases_dir), args.benchmark)

    benchmarks = ["l1", "l2", "l3"] if args.benchmark == "all" else [args.benchmark]
    cases: list[EvalCase] = []
    for benchmark in benchmarks:
        cases.extend(load_cases(BENCHMARK_CASE_DIRS[benchmark], benchmark))
    return cases


def install_eval_patches(*, real_llm: bool, real_rag: bool) -> None:
    if not real_llm:
        install_mock_llm()
    if not real_rag:
        import invesagent_agent.agents.macro_policy_analyst as macro_policy_analyst

        macro_policy_analyst._retrieve_policy_evidence = fake_retrieve_policy_evidence


def run_case(case: EvalCase, *, real_tools: bool, llm_judge: bool) -> dict[str, Any]:
    tool_client = None if real_tools else EvalMockToolClient()
    result = run_chat_workflow(
        user_query=case.query,
        messages=case.messages,
        task_memory=case.task_memory,
        tool_client=tool_client,
    )
    expected = case.expected
    scores = {
        "route": evaluate_route(result, expected),
        "task_plan": evaluate_task_plan(result, expected),
        "trajectory": evaluate_trajectory(result, expected),
        "tool_calls": evaluate_tool_calls(result, expected),
        "memory": evaluate_memory(result, expected),
        "rag": evaluate_rag(result, expected),
        "output_quality": evaluate_output_quality(result, expected),
        "efficiency": evaluate_efficiency(result, expected),
        "quality": evaluate_report_quality(result, expected),
        "llm_judge": evaluate_llm_judge(result, expected, enabled=llm_judge),
    }
    passed = all(item.get("passed") for item in scores.values())
    research_state = result.get("research_state", {})
    return {
        "id": case.id,
        "category": case.category,
        "benchmark": case.benchmark,
        "passed": passed,
        "scores": scores,
        "conversation_route": result.get("conversation_route"),
        "required_agents": research_state.get("required_agents", [])
        if isinstance(research_state, dict)
        else [],
        "tool_calls": research_state.get("tool_calls", []) if isinstance(research_state, dict) else [],
        "trace": research_state.get("trace", []) if isinstance(research_state, dict) else result.get("trace", []),
        "warnings": result.get("warnings", []),
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories = sorted({item["category"] for item in results})
    by_category = {}
    for category in categories:
        items = [item for item in results if item["category"] == category]
        by_category[category] = {
            "total": len(items),
            "passed": sum(1 for item in items if item["passed"]),
            "failed": sum(1 for item in items if not item["passed"]),
        }
    benchmarks = sorted({item.get("benchmark", "unknown") for item in results})
    by_benchmark = {}
    for benchmark in benchmarks:
        items = [item for item in results if item.get("benchmark", "unknown") == benchmark]
        by_benchmark[benchmark] = {
            "total": len(items),
            "passed": sum(1 for item in items if item["passed"]),
            "failed": sum(1 for item in items if not item["passed"]),
            "pass_rate": round(
                sum(1 for item in items if item["passed"]) / max(len(items), 1),
                4,
            ),
        }
    metric_names = sorted({name for item in results for name in item["scores"]})
    metrics = {}
    for name in metric_names:
        values = [
            float(item.get("scores", {}).get(name, {}).get("score", 0.0))
            for item in results
        ]
        metrics[name] = round(sum(values) / max(len(values), 1), 4)
    return {
        "total": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "pass_rate": round(sum(1 for item in results if item["passed"]) / max(len(results), 1), 4),
        "by_category": by_category,
        "by_benchmark": by_benchmark,
        "metrics": metrics,
    }


def write_summary_markdown(path: Path, summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    lines = [
        "# InvesAgent Eval Summary",
        "",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Pass rate: {summary['pass_rate']:.2%}",
        "",
        "## Metric Averages",
        "",
    ]
    lines.extend(f"- {name}: {score:.4f}" for name, score in summary["metrics"].items())
    lines.extend(["", "## Benchmarks", ""])
    for name, item in summary.get("by_benchmark", {}).items():
        lines.append(
            f"- {name}: {item['passed']}/{item['total']} passed ({item['pass_rate']:.2%})"
        )
    lines.extend(["", "## Cases", ""])
    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- {status} `{item['id']}` ({item.get('benchmark')}/{item['category']})")
        if not item["passed"]:
            failed = [
                name
                for name, score in item.get("scores", {}).items()
                if not score.get("passed")
            ]
            if item.get("error"):
                failed.append(str(item["error"]))
            lines.append(f"  - failed evaluators: {', '.join(failed)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    install_eval_patches(real_llm=args.real_llm, real_rag=args.real_rag)

    cases = load_benchmark_cases(args)
    if args.category:
        cases = [case for case in cases if case.category == args.category]
    if args.case_id:
        cases = [case for case in cases if case.id == args.case_id]

    results = []
    for case in cases:
        try:
            results.append(run_case(case, real_tools=args.real_tools, llm_judge=args.llm_judge))
        except Exception as exc:
            if args.fail_on_error:
                raise
            results.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "scores": {},
                }
            )

    summary = summarize(results)
    output_dir = Path(args.results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_path = output_dir / "latest.json"
    summary_path = output_dir / "summary.md"
    latest_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_summary_markdown(summary_path, summary, results)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"results: {latest_path}")
    print(f"summary: {summary_path}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
