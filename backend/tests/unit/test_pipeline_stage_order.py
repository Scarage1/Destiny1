from __future__ import annotations

import backend.agents.observability as obs
import backend.agents.orchestrator as orchestrator
from backend.agents.runtime_config import RuntimeConfig


def test_pipeline_stage_order_for_successful_deterministic_query(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(obs, "LOG_PATH", tmp_path / "agent_events.log")
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    out = orchestrator.process_query("Trace invoice INV123", conversation_id="stage-order-c1")

    assert out["status"] in {"success", "clarification", "blocked", "error"}
    events = obs.get_trace(out["trace_id"])
    stages = [e.get("stage") for e in events]

    # Required deterministic pipeline stages before terminal response.
    required = [
        "request",
        "planner",
        "guard_pass",
        "validator_pass",
        "query_agent",
    ]

    for stage in required:
        assert stage in stages

    req_idx = stages.index("request")
    planner_idx = stages.index("planner")
    guard_idx = stages.index("guard_pass")
    validator_idx = stages.index("validator_pass")
    query_idx = stages.index("query_agent")

    assert req_idx < planner_idx < guard_idx < validator_idx < query_idx


def test_pipeline_stage_order_in_strict_mode_logs_disable_before_planner(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(obs, "LOG_PATH", tmp_path / "agent_events.log")

    strict_cfg = RuntimeConfig(
        gemini_api_key="dummy",
        groq_api_key="dummy",
        groq_model="llama-test-model",
        llm_timeout_seconds=20.0,
        pipeline_timeout_ms=8000,
        stage_budget_ms={
            "planner": 700,
            "guard": 120,
            "validator": 120,
            "query_agent": 300,
            "execution": 2500,
            "verification": 300,
            "response": 2200,
        },
        strict_deterministic=True,
        sql_cache_ttl_seconds=30,
        sql_cache_max_entries=256,
        sql_exec_retries=1,
        exec_cb_failure_threshold=3,
        exec_cb_open_seconds=20,
        memory_max_conversations=2000,
    )
    monkeypatch.setattr(orchestrator, "get_runtime_config", lambda: strict_cfg)

    out = orchestrator.process_query("Trace invoice INV123", conversation_id="stage-order-c2")

    assert out["status"] in {"success", "clarification", "blocked", "error"}
    events = obs.get_trace(out["trace_id"])
    stages = [e.get("stage") for e in events]

    assert "request" in stages
    assert "llm_disabled_strict_mode" in stages
    assert "planner" in stages

    req_idx = stages.index("request")
    llm_disabled_idx = stages.index("llm_disabled_strict_mode")
    planner_idx = stages.index("planner")
    assert req_idx < llm_disabled_idx < planner_idx


def test_pipeline_stage_order_guard_reject_short_circuits_later_stages(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(obs, "LOG_PATH", tmp_path / "agent_events.log")
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    out = orchestrator.process_query("Write a poem about mountains", conversation_id="stage-order-c3")

    assert out["status"] == "rejected"
    events = obs.get_trace(out["trace_id"])
    stages = [e.get("stage") for e in events]

    assert "request" in stages
    assert "planner" in stages
    assert "guard_reject" in stages
    assert "validator_pass" not in stages
    assert "query_agent" not in stages
    assert "execution" not in stages

    req_idx = stages.index("request")
    planner_idx = stages.index("planner")
    reject_idx = stages.index("guard_reject")
    assert req_idx < planner_idx < reject_idx
