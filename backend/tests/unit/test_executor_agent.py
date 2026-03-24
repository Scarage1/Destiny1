from __future__ import annotations

import backend.agents.executor_agent as executor_agent
from backend.agents.executor_agent import execute_sql


def test_executor_blocks_disallowed_table() -> None:
    out = execute_sql("SELECT * FROM not_allowed_table", trace_id="ex1")
    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "Disallowed table" in (out["reason"] or "")


def test_executor_runs_safe_query() -> None:
    out = execute_sql("SELECT salesOrder FROM sales_order_headers LIMIT 1", trace_id="ex2")
    assert out["ok"] is True
    assert out["status"] == "success"
    assert isinstance(out["results"], list)


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
    executor_agent._SQL_RESULT_CACHE.clear()
    executor_agent._EXEC_CB_STATE["failures"] = 0
    executor_agent._EXEC_CB_STATE["opened_until"] = 0.0
    monkeypatch.setattr(executor_agent, "EXEC_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 2)
    monkeypatch.setattr(executor_agent, "EXEC_CIRCUIT_BREAKER_OPEN_SECONDS", 30)

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
    # third call should short-circuit before adapter execution
    assert adapter.calls == 4
