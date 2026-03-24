from __future__ import annotations

import pytest

from backend.agents.intent_schema import validate_and_normalize_plan


def test_validate_and_normalize_plan_accepts_valid_payload() -> None:
    plan = validate_and_normalize_plan(
        {
            "intent": "analyze",
            "entity_type": "customer",
            "entity_id": None,
            "metric": "net_amount",
            "operation": "sum",
            "filters": [],
            "group_by": "customer",
            "limit": 5,
            "time_range": None,
            "confidence": 0.92,
            "clarification": None,
            "follow_up": False,
            "verification": "required",
        }
    )

    assert plan["intent"] == "analyze"
    assert plan["limit"] == 5
    assert plan["confidence"] == 0.92


def test_validate_and_normalize_plan_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        validate_and_normalize_plan(
            {
                "intent": "analyze",
                "entity_type": None,
                "entity_id": None,
                "metric": None,
                "operation": "list",
                "filters": [],
                "group_by": None,
                "limit": 20,
                "time_range": None,
                "confidence": 0.8,
                "clarification": None,
                "follow_up": False,
                "verification": "required",
                "unexpected": "boom",
            }
        )


def test_validate_and_normalize_plan_rejects_invalid_intent() -> None:
    with pytest.raises(ValueError):
        validate_and_normalize_plan(
            {
                "intent": "flow_trace",
                "entity_type": None,
                "entity_id": None,
                "metric": None,
                "operation": "trace",
                "filters": [],
                "group_by": None,
                "limit": 20,
                "time_range": None,
                "confidence": 0.8,
                "clarification": None,
                "follow_up": False,
                "verification": "required",
            }
        )
