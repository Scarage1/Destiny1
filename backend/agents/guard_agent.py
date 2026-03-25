from __future__ import annotations

from .observability import log_event

try:
    from ..guardrails import REJECTION_RESPONSE, check_domain_relevance
except ImportError:
    from guardrails import REJECTION_RESPONSE, check_domain_relevance


ALLOWED_INTENTS = {"trace_flow", "detect_anomaly", "status_lookup", "analyze"}
INTENT_ENTITY_RULES = {
    "trace_flow": {"invoice", "sales_order", "delivery", "payment", None},
    "detect_anomaly": {None, "sales_order", "invoice", "delivery", "payment", "customer", "product"},
    "status_lookup": {"invoice", "sales_order", "delivery", "payment", None},
    "analyze": {None, "customer", "product", "invoice", "sales_order", "delivery", "payment"},
}


def guard(user_query: str, plan: dict, trace_id: str) -> tuple[bool, str | None]:
    """Guard agent: domain checks + schema-aware intent controls."""
    is_relevant, reason = check_domain_relevance(user_query)
    if not is_relevant:
        rejection = reason or REJECTION_RESPONSE
        log_event(trace_id, "guard_reject", {"reason": rejection})
        return False, rejection

    intent = plan.get("intent")
    entity_type = plan.get("entity_type")

    if intent not in ALLOWED_INTENTS:
        msg = "Unsupported intent for this system."
        log_event(trace_id, "guard_reject", {"reason": msg, "intent": intent})
        return False, msg

    allowed_entities = INTENT_ENTITY_RULES.get(intent, {None})
    if entity_type not in allowed_entities:
        msg = f"Entity type '{entity_type}' is not valid for intent '{intent}'."
        log_event(trace_id, "guard_reject", {"reason": msg, "intent": intent, "entity_type": entity_type})
        return False, msg

    log_event(trace_id, "guard_pass", {"intent": intent, "entity_type": entity_type})
    return True, None
