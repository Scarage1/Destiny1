from __future__ import annotations

from backend.agents.guard_agent import guard
from backend.guardrails import REJECTION_RESPONSE


def test_guard_allows_o2c_query() -> None:
    ok, reason = guard(
        "Show sales orders delivered but not billed",
        {"intent": "detect_anomaly", "entity_type": None},
        trace_id="g1",
    )
    assert ok is True
    assert reason is None


def test_guard_rejects_off_topic_query() -> None:
    ok, reason = guard(
        "Write a poem about mountains",
        {"intent": "analyze", "entity_type": None},
        trace_id="g2",
    )
    assert ok is False
    assert reason == REJECTION_RESPONSE


def test_guard_enforces_intent_whitelist() -> None:
    ok, reason = guard(
        "show all data",
        {"intent": "unknown_intent", "entity_type": None},
        trace_id="g3",
    )
    assert ok is False
    assert "Unsupported intent" in (reason or "")


def test_guard_rejects_status_lookup_for_unsupported_entity_type() -> None:
    ok, reason = guard(
        "status of product P-100",
        {"intent": "status_lookup", "entity_type": "product"},
        trace_id="g4",
    )
    assert ok is False
    assert "not valid" in (reason or "")
