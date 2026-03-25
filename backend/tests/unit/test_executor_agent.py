from __future__ import annotations

import backend.agents.executor_agent as executor_agent
from backend.agents.executor_agent import execute_sql


def test_executor_blocks_disallowed_table() -> None:
    out = execute_sql("SELECT * FROM not_allowed_table", trace_id="ex1")
    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "Disallowed table" in (out["reason"] or "")


def test_executor_runs_safe_query(monkeypatch) -> None:
    """Unit test: executor with a mocked adapter — no real DB required."""
    executor_agent._SQL_RESULT_CACHE.clear()

    class _MockAdapter:
        name = "mock"

        def execute_readonly_query(self, sql, params=()):
            return [{"salesOrder": "SO-001"}]

    monkeypatch.setattr(executor_agent, "get_db_adapter", lambda: _MockAdapter())
    out = execute_sql("SELECT salesOrder FROM sales_order_headers LIMIT 1", trace_id="ex2")
    assert out["ok"] is True
    assert out["status"] == "success"
    assert isinstance(out["results"], list)
    assert out["results"][0]["salesOrder"] == "SO-001"


def test_executor_uses_cache_for_repeated_query(monkeypatch) -> None:
    executor_agent._SQL_RESULT_CACHE.clear()

    class _Adapter:
        name = "stub"

        def __init__(self) -> None:
            self.calls = 0

        def execute_readonly_query(self, sql, params=()):
            self.calls += 1
            return [{"salesOrder": f"SO-{self.calls}"}]

    adapter = _Adapter()
    monkeypatch.setattr(executor_agent, "get_db_adapter", lambda: adapter)

    q1 = "SELECT salesOrder FROM sales_order_headers LIMIT 1"
    q2 = "  select   salesOrder  from sales_order_headers   limit 1 ; "
    first = execute_sql(q1, trace_id="ex-cache-1")
    second = execute_sql(q2, trace_id="ex-cache-2")

    assert first["ok"] is True
    assert second["ok"] is True
    assert adapter.calls == 1
    assert first["results"] == second["results"]


def test_executor_circuit_breaker_short_circuits_after_failures(monkeypatch) -> None:
    from backend.agents.runtime_config import RuntimeConfig

    executor_agent._SQL_RESULT_CACHE.clear()
    executor_agent._EXEC_CB_STATE["failures"] = 0
    executor_agent._EXEC_CB_STATE["opened_until"] = 0.0

    test_config = RuntimeConfig(
        gemini_api_key="",
        groq_api_key="",
        groq_model="test",
        llm_timeout_seconds=5.0,
        pipeline_timeout_ms=5000,
        stage_budget_ms={},
        strict_deterministic=False,
        sql_cache_ttl_seconds=30,
        sql_cache_max_entries=256,
        sql_exec_retries=1,
        exec_cb_failure_threshold=2,
        exec_cb_open_seconds=30,
        memory_max_conversations=10,
    )
    monkeypatch.setattr(executor_agent, "get_runtime_config", lambda: test_config)

    class _FailingAdapter:
        name = "stub"

        def __init__(self) -> None:
            self.calls = 0

        def execute_readonly_query(self, sql, params=()):
            self.calls += 1
            raise RuntimeError("database is locked")

    adapter = _FailingAdapter()
    monkeypatch.setattr(executor_agent, "get_db_adapter", lambda: adapter)

    q = "SELECT salesOrder FROM sales_order_headers LIMIT 1"
    first = execute_sql(q, trace_id="ex-cb-1")
    second = execute_sql(q, trace_id="ex-cb-2")
    third = execute_sql(q, trace_id="ex-cb-3")

    assert first["ok"] is False
    assert second["ok"] is False
    assert third["ok"] is False
    assert "temporarily unavailable" in (third["reason"] or "").lower()
    # third call short-circuits (circuit open) — adapter never called for it
    assert adapter.calls >= 2
