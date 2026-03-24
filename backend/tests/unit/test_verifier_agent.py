from __future__ import annotations

from backend.agents.verifier_agent import verify


def test_verifier_warns_on_empty_trace_flow() -> None:
    result = verify(
        {"intent": "trace_flow", "entity_id": "INV1"},
        [],
        trace_id="v1",
    )
    assert result["status"] == "warning"
    assert any("No flow records" in w for w in result["warnings"])


def test_verifier_ok_on_regular_results() -> None:
    result = verify(
        {"intent": "analyze"},
        [{"salesOrder": "SO-1"}],
        trace_id="v2",
    )
    assert result["status"] == "ok"
    assert result["warnings"] == []
