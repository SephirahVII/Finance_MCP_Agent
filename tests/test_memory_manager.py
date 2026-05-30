from __future__ import annotations

from invesagent_agent.runtime.memory import AgentMemory, MemoryManager


def test_memory_manager_migrates_legacy_flat_memory() -> None:
    state = {
        "task_memory": {
            "last_query": "分析贵州茅台",
            "last_symbols": ["600519.SH"],
        }
    }

    memory = MemoryManager(state).root()

    assert memory["session"]["last_query"] == "分析贵州茅台"
    assert memory["session"]["last_symbols"] == ["600519.SH"]
    assert memory["task"] == {}
    assert memory["agents"] == {}
    assert AgentMemory.from_value(memory).last_query == "分析贵州茅台"


def test_memory_manager_captures_agent_scoped_output() -> None:
    state = {
        "task_memory": {},
        "symbols": ["600519.SH"],
        "industry": "白酒",
        "date_ranges": {"price_volume": {"start_date": "20240101", "end_date": "20240131"}},
        "required_agents": ["data_collector", "price_volume_analyst"],
        "price_volume_analysis": {
            "date_range": {"start_date": "20240101", "end_date": "20240131"},
            "analysis": {
                "summary": "区间震荡上行",
                "key_findings": ["收益为正"],
                "risks": ["波动放大"],
                "data_limits": [],
            },
        },
        "charts": [{"symbol": "600519.SH", "relative_path": "charts/mock.html"}],
    }

    memory = MemoryManager(state).capture_agent_output("price_volume_analyst", state)

    assert memory["task"]["completed_agents"] == ["price_volume_analyst"]
    assert memory["task"]["public_outputs"]["price_volume_analyst"]["summary"] == "区间震荡上行"
    assert memory["agents"]["price_volume_analyst"]["last_indicator_config"]["ma_windows"] == [
        5,
        20,
    ]
