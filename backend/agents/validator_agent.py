from __future__ import annotations

from typing import Any

from .observability import log_event
from .query_agent import can_generate_sql_deterministically

try:
    from ..guardrails import validate_entity_id
except ImportError:
    from guardrails import validate_entity_id


def validate_plan_for_execution(
    user_query: str,
    plan: dict[str, Any],
    trace_id: str,
    allow_model_fallback: bool = False,
) -> tuple[bool, str | None]:
    """Validate whether a normalized plan can be executed deterministically."""
    intent = plan.get("intent")
    entity_type = plan.get("entity_type")
    entity_id = plan.get("entity_id")
    metric = plan.get("metric")
    operation = plan.get("operation")

    id_ok, id_reason = validate_entity_id(entity_type, entity_id)
    if not id_ok:
        log_event(
            trace_id,
            "validator_clarification",
            {"reason": id_reason, "intent": intent, "entity_type": entity_type},
        )
        return False, id_reason

    if intent == "status_lookup" and not entity_id:
        msg = "Please provide the exact document ID for status lookup."
        log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent})
        return False, msg

    if intent == "trace_flow" and not entity_id:
        q = (user_query or "").lower()
        generic_flow_requested = (
            "full flow" in q
            or ("trace" in q and "flow" in q and "billing" in q and "document" in q)
        )
        if not generic_flow_requested:
            msg = "Please provide invoice or sales order ID to trace the flow."
            log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent})
            return False, msg

    if intent == "analyze" and operation == "median":
        msg = "Median analysis is not supported yet. Please use sum, avg, max, or min."
        log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent})
        return False, msg

    if intent == "analyze" and operation in {"sum", "avg", "max", "min"} and metric is None:
        msg = "Please specify a metric (for example: net amount or billing count)."
        log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent})
        return False, msg

    if intent == "status_lookup" and entity_type not in {"invoice", "sales_order", "delivery", "payment", None}:
        msg = f"Status lookup is not supported for entity type '{entity_type}'."
        log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent, "entity_type": entity_type})
        return False, msg

    if not can_generate_sql_deterministically(plan, user_query):
        if allow_model_fallback:
            log_event(
                trace_id,
                "validator_pass",
                {"intent": intent, "entity_type": entity_type, "mode": "llm_fallback"},
            )
            return True, None
        msg = (
            "I need clarification to run this request deterministically. "
            "Try a supported request like: trace invoice <id>, status lookup by document ID, "
            "top products by billing documents, or anomaly detection."
        )
        log_event(trace_id, "validator_clarification", {"reason": msg, "intent": intent, "entity_type": entity_type})
        return False, msg

    log_event(trace_id, "validator_pass", {"intent": intent, "entity_type": entity_type})
    return True, None
