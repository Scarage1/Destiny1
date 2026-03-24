from __future__ import annotations

from backend.agents.validator_agent import validate_plan_for_execution


def test_validator_requires_id_for_status_lookup() -> None:
    ok, reason = validate_plan_for_execution(
        "status of invoice",
        {"intent": "status_lookup", "entity_type": "invoice", "entity_id": None, "metric": None, "operation": "list"},
        "t1",
    )
    assert ok is False
    assert "document ID" in (reason or "")


def test_validator_accepts_generic_billing_flow_request() -> None:
    ok, reason = validate_plan_for_execution(
        "trace full flow of billing document",
        {"intent": "trace_flow", "entity_type": None, "entity_id": None, "metric": None, "operation": "trace"},
        "t2",
    )
    assert ok is True
    assert reason is None


def test_validator_blocks_unsupported_deterministic_request() -> None:
    ok, reason = validate_plan_for_execution(
        "Show weekly trend of customer churn",
        {
            "intent": "analyze",
            "entity_type": "customer",
            "entity_id": None,
            "metric": None,
            "operation": "list",
            "group_by": "customer",
        },
        "t3",
    )
    assert ok is False
    assert "deterministically" in (reason or "").lower()


def test_validator_rejects_malformed_entity_id() -> None:
    ok, reason = validate_plan_for_execution(
        "trace invoice INV' OR 1=1 --",
        {
            "intent": "trace_flow",
            "entity_type": "invoice",
            "entity_id": "INV' OR 1=1 --",
            "metric": None,
            "operation": "trace",
        },
        "t4",
    )
    assert ok is False
    assert "invalid" in (reason or "").lower()


def test_validator_allows_model_fallback_for_non_deterministic_nl_query() -> None:
    ok, reason = validate_plan_for_execution(
        "who bought what from us",
        {
            "intent": "analyze",
            "entity_type": "customer",
            "entity_id": None,
            "metric": None,
            "operation": "list",
            "group_by": "customer",
        },
        "t5",
        allow_model_fallback=True,
    )
    assert ok is True
    assert reason is None


def test_validator_accepts_customer_product_relationship_query_deterministically() -> None:
    ok, reason = validate_plan_for_execution(
        "which customer ordered which product",
        {
            "intent": "analyze",
            "entity_type": "customer",
            "entity_id": None,
            "metric": None,
            "operation": "list",
            "group_by": "customer",
        },
        "t6",
    )
    assert ok is True
    assert reason is None
