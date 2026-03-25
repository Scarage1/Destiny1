from __future__ import annotations

import json
import re
from typing import Any

from .observability import log_event

LLM_TIMEOUT_SECONDS = 20
SHOW_ALL_PHRASES = {
    "show all",
    "show everything",
    "show all records",
    "show all of them",
    "list them all",
    "all of them",
}
RANKING_WORDS = {"highest", "top", "most", "best"}
LOW_RANKING_WORDS = {"lowest", "least", "cheapest"}
QUANTITY_WORDS = {"quantity", "qty", "quantities", "unit", "units", "volume"}
COUNT_WORDS = {"count", "counts", "how many", "number of"}
PRICE_WORDS = {"price", "prices", "priced", "cost", "costs", "value", "worth", "expensive", "cheap", "cheaper", "cheapest"}
QUESTION_WORDS = {"which", "what", "who"}
PRODUCT_WORDS = {"product", "products", "material", "materials", "item", "items", "sku", "skus"}
CUSTOMER_WORDS = {"customer", "customers", "buyer", "buyers", "client", "clients"}
PAYMENT_WORDS = {"paid", "payment", "payments", "payer", "payers"}
PURCHASE_WORDS = {"bought", "buy", "buys", "purchase", "purchased", "purchases"}
SELLING_WORDS = {"ordered", "order", "sold", "selling", "best selling", "best-selling", "top selling", "top-selling"}
INVOICE_WORDS = {"invoice", "invoices", "billing document", "billing documents", "bill document", "bill documents", "bill doc", "bill docs"}
DELIVERY_WORDS = {"delivery", "deliveries", "shipment", "shipments"}
UNPAID_WORDS = {
    "unpaid",
    "not paid",
    "no payment",
    "without payment",
    "pending payment",
    "payment pending",
    "awaiting payment",
    "has not paid",
    "have not paid",
}
PENDING_DELIVERY_WORDS = {
    "pending delivery",
    "delivery pending",
    "not delivered",
    "undelivered",
    "awaiting delivery",
    "stuck in delivery",
}
PENDING_MOVEMENT_WORDS = {
    "pending goods movement",
    "goods movement pending",
    "not moved",
    "movement pending",
}

# Common domain-specific misspellings mapped to their canonical form.
# Applied before heuristic matching so typos don't bypass keyword detection.
_TYPO_CORRECTIONS: dict[str, str] = {
    "custmer": "customer", "customr": "customer", "custumer": "customer", "cust": "customer",
    "clinet": "client",
    "ordr": "order", "oredr": "order", "slae": "sale", "slaes": "sales",
    "invioce": "invoice", "invoic": "invoice", "invice": "invoice",
    "biiling": "billing", "biling": "billing", "billig": "billing",
    "delvry": "delivery", "delivry": "delivery", "delievry": "delivery",
    "pymnt": "payment", "paymet": "payment", "pament": "payment",
    "prodcut": "product", "prduct": "product",
    "amout": "amount", "amonut": "amount",
    "quatity": "quantity", "qauntity": "quantity",
    "tace": "trace", "trae": "trace", "trce": "trace",
    "anamoly": "anomaly", "anomaley": "anomaly",
    "unsold": "not sold", "unpayed": "unpaid", "nonpaid": "unpaid",
}


def _apply_typo_corrections(text: str) -> str:
    """Replace known domain misspellings word-by-word before heuristic matching."""
    words = text.split()
    corrected = [_TYPO_CORRECTIONS.get(w.lower().rstrip("s,."), w) for w in words]
    return " ".join(corrected)


def _is_probable_entity_id(value: str | None) -> bool:
    if not value:
        return False
    candidate = value.strip()
    if len(candidate) < 3:
        return False
    # Generic plural words are not IDs (e.g., "documents", "orders").
    if candidate.lower().endswith("s") and candidate.isalpha():
        return False
    # Prefer identifiers with at least one digit, or explicit separators.
    if any(ch.isdigit() for ch in candidate):
        return True
    return any(ch in candidate for ch in ["-", "_"])


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except Exception:
            return None

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _contains_term(text: str, term: str) -> bool:
    if " " in term or "-" in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _contains_any_term(text: str, terms: set[str] | list[str] | tuple[str, ...]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _heuristic_plan(user_query: str, context: dict[str, Any]) -> dict[str, Any]:
    # Pre-process: fix common domain misspellings so keyword matching still works
    corrected_query = _apply_typo_corrections(user_query)
    q = corrected_query.lower()
    intent = "analyze"
    operation = None
    confidence = 0.9
    clarification = None
    filters: list[dict[str, Any]] = []

    source_plan = context.get("pending_plan") or context.get("last_plan")
    if q in SHOW_ALL_PHRASES and source_plan:
        out = dict(source_plan)
        out["limit"] = 100
        out["confidence"] = max(float(source_plan.get("confidence", 0.85)), 0.93)
        out["clarification"] = None
        out["follow_up"] = True
        return out

    # ─── Intent detection ───────────────────────────────────────────────────────
    # Priority: more specific patterns first
    anomaly_sub_type = None

    _never_billed = (
        "never billed" in q or "not billed" in q or "without billing" in q
        or "created but never billed" in q or "delivery without billing" in q
    )
    _never_delivered = (
        "never delivered" in q or "not delivered" in q or "billed but not delivered" in q
        or "billed but never delivered" in q or "billed without delivery" in q
    )
    _billing_no_journal = (
        "without journal" in q or "no journal" in q or "without accounting" in q
        or "billing without journal" in q or "billing document without" in q
    )
    _orphan = "orphan" in q or "unlinked" in q or "no connection" in q
    _avg_steps = "average" in q and ("step" in q or "stage" in q or "cycle" in q)
    _bottleneck = "bottleneck" in q or "delay" in q and "pipeline" in q
    _longest_chain = "longest" in q and "chain" in q
    _cycles_detect = "cycle" in q and ("detect" in q or "redundant" in q or "loop" in q)
    _node_connectivity = "connect" in q and ("highest" in q or "most" in q) and "node" in q
    _completion_rate = "percentage" in q and ("complet" in q or "full cycle" in q)
    _incomplete_region = "region" in q and "incomplete" in q
    _incomplete_region = _incomplete_region or ("region" in q and ("broken" in q or "anomal" in q))
    _multi_delivery = "more than one delivery" in q or "multiple deliver" in q or ("linked" in q and "delivery" in q and "more" in q)
    _multi_journal = "multiple journal" in q or "more than one journal" in q or "linked to multiple" in q and "journal" in q
    _mixed_status = "both" in q and "complet" in q and ("incomplet" in q or "incomplete" in q)
    _high_value_unbi = ("high" in q or "high-value" in q) and "not billed" in q and "deliver" in q
    _pay_delay = "payment" in q and "delayed" in q or "delay" in q and "payment" in q and "billing" in q
    _customer_failure = "customer" in q and ("failure" in q or "incomplete" in q or "frequen" in q)
    _full_cycle_pct = "percentage" in q and "full cycle" in q or "what percent" in q and "complete" in q

    if _never_billed:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "deliveries_not_billed"
    elif _billing_no_journal:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "billing_without_journal"
    elif _never_delivered:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "billed_not_delivered"
    elif _orphan:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "orphan_records"
    elif _avg_steps:
        intent = "analyze"
        operation = "avg"
        anomaly_sub_type = "avg_steps_per_order"
    elif _completion_rate or _full_cycle_pct:
        intent = "analyze"
        operation = "avg"
        anomaly_sub_type = "completion_rate"
    elif _bottleneck:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "bottleneck_analysis"
    elif _longest_chain:
        intent = "analyze"
        operation = "max"
        anomaly_sub_type = "longest_chain"
    elif _cycles_detect:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "cycle_detection"
    elif _node_connectivity:
        intent = "analyze"
        operation = "max"
        anomaly_sub_type = "node_connectivity"
    elif _incomplete_region:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "incomplete_by_region"
    elif _multi_delivery:
        intent = "analyze"
        operation = "list"
        anomaly_sub_type = "multi_delivery_orders"
    elif _multi_journal:
        intent = "analyze"
        operation = "list"
        anomaly_sub_type = "multi_journal_billing"
    elif _mixed_status:
        intent = "analyze"
        operation = "list"
        anomaly_sub_type = "mixed_status_customers"
    elif _high_value_unbi:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "high_value_unbi_delivered"
    elif _pay_delay:
        intent = "detect_anomaly"
        operation = "detect"
        anomaly_sub_type = "payment_delay"
    elif _customer_failure:
        intent = "analyze"
        operation = "list"
        anomaly_sub_type = "customer_failure_rate"
    elif "broken" in q or "anomal" in q or "incomplete" in q:
        intent = "detect_anomaly"
        operation = "detect"
    elif "trace" in q or "flow" in q:
        intent = "trace_flow"
        operation = "trace"
    elif "status" in q:
        intent = "status_lookup"
        operation = "list"

    entity_type = None
    entity_id = None
    metric = None
    group_by = None
    ranking_requested = _contains_any_term(q, RANKING_WORDS)
    low_ranking_requested = _contains_any_term(q, LOW_RANKING_WORDS)
    product_query = _contains_any_term(q, PRODUCT_WORDS)
    customer_query = _contains_any_term(q, CUSTOMER_WORDS) or _contains_any_term(q, PAYMENT_WORDS)
    payment_query = _contains_any_term(q, PAYMENT_WORDS)
    purchase_query = _contains_any_term(q, PURCHASE_WORDS)
    selling_query = _contains_any_term(q, SELLING_WORDS)
    question_requested = _contains_any_term(q, QUESTION_WORDS)
    invoice_query = _contains_any_term(q, INVOICE_WORDS) or "billing" in q
    delivery_query = _contains_any_term(q, DELIVERY_WORDS)
    unpaid_query = _contains_any_term(q, UNPAID_WORDS)
    pending_delivery_query = _contains_any_term(q, PENDING_DELIVERY_WORDS)
    pending_movement_query = _contains_any_term(q, PENDING_MOVEMENT_WORDS)
    customer_product_relation_query = (
        not ranking_requested
        and not low_ranking_requested
        and (
            (purchase_query and "what" in q)
            or ((customer_query or question_requested) and product_query and (purchase_query or selling_query))
        )
    )

    invoice_match = re.search(
        r"\b(?:invoice|billing\s*document)\s*[:#-]?\s*([A-Za-z0-9_-]+)",
        user_query,
        re.IGNORECASE,
    )
    order_match = re.search(
        r"\b(?:sales\s*order|order)\s*[:#-]?\s*([A-Za-z0-9_-]+)",
        user_query,
        re.IGNORECASE,
    )

    if invoice_match and _is_probable_entity_id(invoice_match.group(1)):
        entity_type = "invoice"
        entity_id = invoice_match.group(1)
    elif order_match and _is_probable_entity_id(order_match.group(1)):
        entity_type = "sales_order"
        entity_id = order_match.group(1)
    elif any(k in q for k in ["its", "it", "that"]) and context.get("last_entity"):
        entity_type = context["last_entity"].get("type")
        entity_id = context["last_entity"].get("id")

    if unpaid_query and customer_query and (ranking_requested or low_ranking_requested):
        metric = "net_amount"
    elif (
        product_query
        and (ranking_requested or low_ranking_requested)
        and selling_query
    ):
        metric = "quantity"
    elif customer_query and (ranking_requested or low_ranking_requested) and payment_query:
        metric = "net_amount"
    elif customer_query and (ranking_requested or low_ranking_requested) and purchase_query:
        metric = "quantity"
    elif customer_query and (ranking_requested or low_ranking_requested):
        metric = "net_amount"
    elif "billing" in q and any(k in q for k in ["count", "highest", "top", "most"]):
        metric = "billing_document_count"
        operation = "max"
    elif (
        ("billing" in q or "bill" in q or "invoice" in q)
        and ("product" in q or "material" in q)
        and any(k in q for k in ["each", "per", "for each", "list", "show"])
    ):
        metric = "billing_documents"
        operation = "list"
    elif _contains_any_term(q, QUANTITY_WORDS):
        metric = "quantity"
    elif _contains_any_term(q, COUNT_WORDS):
        metric = "count"
    elif _contains_any_term(q, PRICE_WORDS):
        metric = "net_amount"
    elif "amount" in q or "revenue" in q:
        metric = "net_amount"
        operation = "sum" if "total" in q else operation
    elif "delivery" in q and any(k in q for k in ["count", "highest", "top", "most"]):
        metric = "delivery_count"
        operation = "max"

    if customer_product_relation_query or unpaid_query and customer_query:
        entity_type = entity_type or "customer"
        group_by = "customer"
    elif pending_delivery_query and "order" in q:
        entity_type = entity_type or "sales_order"
        group_by = "sales_order"
    elif pending_movement_query and delivery_query:
        entity_type = entity_type or "delivery"
    elif unpaid_query and invoice_query:
        entity_type = entity_type or "invoice"
    elif product_query:
        group_by = "product"
    elif customer_query or "partner" in q:
        group_by = "customer"
    elif "order" in q:
        group_by = "sales_order"

    if "median" in q:
        operation = "median"
    elif "average" in q or "avg" in q:
        operation = "avg"
    elif ranking_requested:
        operation = "max"
    elif low_ranking_requested:
        operation = "min"
    elif "total" in q and operation is None:
        operation = "sum"
    elif operation is None:
        operation = "list"

    pending_plan = context.get("pending_plan") or {}
    source_plan = pending_plan or context.get("last_plan") or {}
    if (
        source_plan.get("intent") == "analyze"
        and group_by is None
        and entity_id is None
        and (
            metric is not None
            or ranking_requested
            or low_ranking_requested
            or question_requested
        )
    ):
        group_by = source_plan.get("group_by") or group_by
        entity_type = source_plan.get("entity_type") or entity_type
    if (
        source_plan.get("intent") == "analyze"
        and metric is not None
        and entity_id is None
    ):
        intent = source_plan.get("intent", intent)
        entity_type = source_plan.get("entity_type") or entity_type
        entity_id = source_plan.get("entity_id") or entity_id
        group_by = group_by or source_plan.get("group_by")
        if operation in {None, "list"}:
            operation = source_plan.get("operation") or operation
        clarification = None
        confidence = max(confidence, 0.92)

    if customer_product_relation_query:
        intent = "analyze"
        clarification = None
        confidence = max(confidence, 0.94)
        operation = "list"
        filters.append({"field": "relationship", "op": "=", "value": "customer_product"})
    elif unpaid_query and (invoice_query or customer_query):
        intent = "analyze"
        clarification = None
        confidence = max(confidence, 0.94)
        if operation is None:
            operation = "list"
    elif pending_delivery_query and "order" in q or pending_movement_query and delivery_query:
        intent = "analyze"
        clarification = None
        confidence = max(confidence, 0.94)
        operation = "list"

    if intent == "status_lookup" and not entity_id or intent == "trace_flow" and not entity_id and not (
        "full flow" in q or "billing document" in q
    ):
        confidence = 0.55
        clarification = "Please provide the document or order ID to continue."
    elif any(w in q for w in ["highest", "lowest", "top", "most", "least"]) and not metric:
        confidence = 0.65
        clarification = "Please specify a metric (net amount, quantity, or count)."

    return {
        "intent": intent,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metric": metric,
        "operation": operation,
        "filters": filters,
        "group_by": group_by,
        "limit": 20,
        "time_range": None,
        "confidence": confidence,
        "clarification": clarification,
        "follow_up": bool(entity_id and context.get("last_entity")),
        "verification": "required",
        "anomaly_sub_type": anomaly_sub_type,
    }


def plan(
    user_query: str,
    context: dict[str, Any],
    model: Any | None,
    trace_id: str,
    llm_timeout_seconds: float = LLM_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Planner agent: produce structured intent for orchestration."""
    if model is None:
        out = _heuristic_plan(user_query, context)
        log_event(trace_id, "planner", {"mode": "heuristic", "plan": out})
        return out

    prompt = f"""You are a planning agent for SAP O2C analytics.
Return ONLY one compact JSON object with keys:
- intent: one of [trace_flow, detect_anomaly, status_lookup, analyze]
- entity_type: one of [invoice, sales_order, delivery, payment, customer, product, null]
- entity_id: string or null
- metric: one of [net_amount, count, quantity, revenue, billing_documents, billing_document_count, delivery_count, null]
- operation: one of [max, min, avg, sum, list, trace, detect, null]
- filters: array
- group_by: one of [product, customer, sales_order, null]
- limit: integer <= 100
- time_range: string or null
- confidence: number between 0 and 1
- clarification: string or null
- follow_up: boolean
- verification: one of [required]

Interpret casual business phrasing, shorthand, typos, and follow-up fragments.
If the user says things like "show customers and their sales orders", "show all bill docs for each product",
"highest order", "highest ordered product", "best selling product", or replies with only a metric like
"net amount", "quantity", or "count", or asks shorthand comparisons like "which has highest price",
or common business requests like "most expensive product", "who paid the most", "top customer", or
"which customer bought the most", "show unpaid invoices", "customers with no payment yet", or
"orders pending delivery", "who bought what from us", or "which customer ordered which product",
infer the closest grounded O2C intent.
Only ask for clarification when the business meaning is still genuinely ambiguous.

Conversation memory:
{json.dumps(context, default=str)}

User query:
{user_query}
"""
    try:
        response = model.generate_content(
            prompt,
            request_options={"timeout": llm_timeout_seconds},
        )
        extracted = _extract_json_object(response.text or "")
        if extracted and isinstance(extracted, dict):
            out = {
                "intent": extracted.get("intent", "analyze"),
                "entity_type": extracted.get("entity_type"),
                "entity_id": extracted.get("entity_id"),
                "metric": extracted.get("metric"),
                "operation": extracted.get("operation"),
                "filters": extracted.get("filters") or [],
                "group_by": extracted.get("group_by"),
                "limit": extracted.get("limit", 20),
                "time_range": extracted.get("time_range"),
                "confidence": float(extracted.get("confidence", 0.8)),
                "clarification": extracted.get("clarification"),
                "follow_up": bool(extracted.get("follow_up", False)),
                "verification": "required",
            }
            log_event(trace_id, "planner", {"mode": "llm", "plan": out})
            return out
    except Exception as e:
        log_event(trace_id, "planner_error", {"error": str(e)})

    out = _heuristic_plan(user_query, context)
    log_event(trace_id, "planner", {"mode": "heuristic_fallback", "plan": out})
    return out
