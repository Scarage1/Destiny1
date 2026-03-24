from __future__ import annotations

import backend.agents.orchestrator as orchestrator


def test_process_query_contract(monkeypatch) -> None:
    def _fake_process_query(user_query: str, conversation_id: str | None = None):
        return {
            "answer": "ok",
            "query": "SELECT 1 LIMIT 100;",
            "results": [{"x": 1}],
            "result_columns": ["x"],
            "total_results": 1,
            "referenced_nodes": [],
            "status": "success",
            "trace_id": "trace-1",
            "conversation_id": conversation_id,
            "intent": "analyze",
            "plan": {"intent": "analyze"},
            "verification": {"status": "ok", "warnings": []},
            "agent_trace": {"trace_id": "trace-1", "events": []},
        }

    monkeypatch.setattr(orchestrator, "process_query", _fake_process_query)

    result = orchestrator.process_query("show top records", conversation_id="conv-1")

    assert result["status"] == "success"
    assert result["result_columns"] == ["x"]
    assert result["conversation_id"] == "conv-1"
    assert result["intent"] == "analyze"
