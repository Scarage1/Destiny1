from __future__ import annotations

import re
from typing import Any

from .observability import log_event

try:
    from ..guardrails import validate_sql_safety
except ImportError:
    from guardrails import validate_sql_safety


LLM_TIMEOUT_SECONDS = 8
QUERY_AGENT_SCHEMA_HINT = """
Allowed tables and important columns:
- sales_order_headers(salesOrder, soldToParty, creationDate, totalNetAmount, overallDeliveryStatus, transactionCurrency, requestedDeliveryDate)
- sales_order_items(salesOrder, salesOrderItem, material, requestedQuantity, requestedQuantityUnit, netAmount, productionPlant)
- outbound_delivery_headers(deliveryDocument, creationDate, actualGoodsMovementDate, overallGoodsMovementStatus, overallPickingStatus)
- outbound_delivery_items(deliveryDocument, referenceSdDocument, referenceSdDocumentItem, plant, storageLocation)
- billing_document_headers(billingDocument, billingDocumentDate, soldToParty, totalNetAmount, accountingDocument, transactionCurrency)
- billing_document_items(billingDocument, material, netAmount, referenceSdDocument, referenceSdDocumentItem, transactionCurrency)
- payments(accountingDocument, customer, amountInTransactionCurrency, clearingDate, clearingAccountingDocument, transactionCurrency)
- business_partners(customer, businessPartner, businessPartnerName, businessPartnerFullName)
- products(product, productType, productGroup)
- product_descriptions(product, language, productDescription)

Useful join paths:
- business_partners.customer = sales_order_headers.soldToParty
- sales_order_headers.salesOrder = outbound_delivery_items.referenceSdDocument
- outbound_delivery_items.deliveryDocument = billing_document_items.referenceSdDocument
- billing_document_headers.billingDocument = billing_document_items.billingDocument
- billing_document_headers.accountingDocument = payments.accountingDocument
- billing_document_items.material = products.product
- sales_order_items.material = products.product

Rules:
- Return one SELECT or WITH query only.
- Use only allowed tables above.
- Always include a LIMIT of 100 or less.
- Prefer business-friendly aliases like customer, salesOrder, billingDocument, product, net_amount, quantity.
""".strip()

def _escape_sql_literal(value: str) -> str:
    """Escape a value for use in a SQL string literal. Strips control chars."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", str(value))
    return cleaned.replace("'", "''")


def _extract_sql_candidate(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    fenced = re.search(r"```(?:sql)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    direct = re.search(r"((?:SELECT|WITH)\b[\s\S]*)", raw, re.IGNORECASE)
    if direct:
        return direct.group(1).strip()

    return raw


def _generate_sql_with_model(
    plan: dict[str, Any],
    user_query: str,
    model: Any,
    trace_id: str,
    llm_timeout_seconds: float,
) -> str:
    if llm_timeout_seconds <= 0:
        raise TimeoutError("No query-generation budget remaining")

    prompt = f"""You are a SQL query agent for an SAP Order-to-Cash analytics assistant.
Translate the user's request into one safe read-only SQL query.

Structured plan:
{plan}

User request:
{user_query}

{QUERY_AGENT_SCHEMA_HINT}

Return SQL only. No markdown, no explanation.
"""

    response = model.generate_content(
        prompt,
        request_options={"timeout": llm_timeout_seconds},
    )
    sql = _extract_sql_candidate(getattr(response, "text", "") or "")
    ok, reason, sanitized = validate_sql_safety(sql)
    if ok:
        log_event(trace_id, "query_agent", {"mode": "llm", "sql": sanitized})
        return sanitized

    repair_prompt = f"""The SQL below failed safety validation: {reason}

Failed SQL:
{sql}

Rewrite it into one safe SELECT/CTE query using only the allowed schema.
Return SQL only.
"""
    repair_response = model.generate_content(
        repair_prompt,
        request_options={"timeout": max(0.1, min(llm_timeout_seconds, 2.0))},
    )
    repaired_sql = _extract_sql_candidate(getattr(repair_response, "text", "") or "")
    ok, reason, sanitized = validate_sql_safety(repaired_sql)
    if ok:
        log_event(trace_id, "query_agent", {"mode": "llm_repair", "sql": sanitized})
        return sanitized

    log_event(
        trace_id,
        "query_agent_llm_rejected",
        {"reason": reason, "sql": repaired_sql or sql},
    )
    raise ValueError(
        "I understood the business question, but I couldn't produce a safe grounded query for it yet. "
        "Please mention the entities or metric you want a bit more explicitly."
    )


def _order_direction_for_operation(operation: str | None) -> str:
    return "ASC" if operation == "min" else "DESC"


def _deterministic_sql_from_plan(plan: dict[str, Any], user_query: str) -> str | None:
    intent = plan.get("intent")
    entity_type = (plan.get("entity_type") or "").lower()
    entity_id = plan.get("entity_id")
    metric = plan.get("metric")
    group_by = plan.get("group_by")
    operation = plan.get("operation")
    filters = plan.get("filters") or []
    limit = max(1, min(int(plan.get("limit") or 20), 100))

    q = (user_query or "").lower()
    unpaid_query = any(
        phrase in q
        for phrase in (
            "unpaid",
            "not paid",
            "no payment",
            "without payment",
            "pending payment",
            "payment pending",
            "awaiting payment",
            "has not paid",
            "have not paid",
        )
    )
    pending_delivery_query = any(
        phrase in q
        for phrase in (
            "pending delivery",
            "delivery pending",
            "not delivered",
            "undelivered",
            "awaiting delivery",
            "stuck in delivery",
        )
    )
    pending_movement_query = any(
        phrase in q
        for phrase in (
            "pending goods movement",
            "goods movement pending",
            "not moved",
            "movement pending",
        )
    )
    customer_product_relation_query = (
        (
            any(token in q for token in ("bought", "buy", "purchase", "purchased"))
            and "what" in q
        )
        or (
            any(token in q for token in ("customer", "customers", "who"))
            and any(token in q for token in ("product", "products", "material", "materials", "item", "items"))
            and any(token in q for token in ("bought", "buy", "purchase", "purchased", "ordered", "order"))
        )
        or any(
            isinstance(clause, dict)
            and clause.get("field") == "relationship"
            and clause.get("value") == "customer_product"
            for clause in filters
        )
    )

    if intent == "status_lookup" and entity_type == "invoice" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT
    bdh.billingDocument,
    bdh.billingDocumentType,
    bdh.billingDocumentDate,
    bdh.billingDocumentIsCancelled,
    bdh.accountingDocument,
    p.clearingAccountingDocument,
    p.clearingDate
FROM billing_document_headers bdh
LEFT JOIN payments p
    ON p.accountingDocument = bdh.accountingDocument
WHERE bdh.billingDocument = '{safe_id}'
LIMIT 20
""".strip()

    if intent == "status_lookup" and entity_type == "sales_order" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT
    soh.salesOrder,
    soh.creationDate,
    soh.overallDeliveryStatus,
    soh.requestedDeliveryDate,
    soh.totalNetAmount,
    soh.transactionCurrency
FROM sales_order_headers soh
WHERE soh.salesOrder = '{safe_id}'
LIMIT 20
""".strip()

    if intent == "status_lookup" and entity_type == "delivery" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT
    odh.deliveryDocument,
    odh.creationDate,
    odh.actualGoodsMovementDate,
    odh.overallGoodsMovementStatus,
    odh.overallPickingStatus,
    odh.deliveryBlockReason
FROM outbound_delivery_headers odh
WHERE odh.deliveryDocument = '{safe_id}'
LIMIT 20
""".strip()

    if intent == "status_lookup" and entity_type == "payment" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT
    p.accountingDocument,
    p.clearingAccountingDocument,
    p.clearingDate,
    p.amountInTransactionCurrency,
    p.transactionCurrency,
    p.customer
FROM payments p
WHERE p.accountingDocument = '{safe_id}'
LIMIT 20
""".strip()

    if intent == "analyze" and unpaid_query and group_by == "customer":
        order_direction = _order_direction_for_operation(operation)
        return f"""
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, bdh.soldToParty) AS customerName,
  bdh.soldToParty AS customer,
  COUNT(DISTINCT bdh.billingDocument) AS unpaid_invoice_count,
  ROUND(SUM(bdh.totalNetAmount), 2) AS unpaid_net_amount,
  MIN(bdh.transactionCurrency) AS transactionCurrency
FROM billing_document_headers bdh
LEFT JOIN payments p
  ON p.accountingDocument = bdh.accountingDocument
LEFT JOIN business_partners bp
  ON bp.customer = bdh.soldToParty
WHERE bdh.soldToParty IS NOT NULL
  AND (p.accountingDocument IS NULL OR p.clearingDate IS NULL)
GROUP BY bdh.soldToParty
ORDER BY unpaid_net_amount {order_direction}, unpaid_invoice_count DESC, customer ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and unpaid_query and entity_type == "invoice":
        return f"""
SELECT
  bdh.billingDocument AS billingDocument,
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, bdh.soldToParty) AS customerName,
  bdh.soldToParty AS customer,
  bdh.billingDocumentDate,
  ROUND(bdh.totalNetAmount, 2) AS net_amount,
  bdh.transactionCurrency
FROM billing_document_headers bdh
LEFT JOIN payments p
  ON p.accountingDocument = bdh.accountingDocument
LEFT JOIN business_partners bp
  ON bp.customer = bdh.soldToParty
WHERE p.accountingDocument IS NULL OR p.clearingDate IS NULL
ORDER BY bdh.billingDocumentDate DESC, billingDocument ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and pending_delivery_query and entity_type == "sales_order":
        return f"""
SELECT
  soh.salesOrder AS salesOrder,
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, soh.soldToParty) AS customerName,
  soh.soldToParty AS customer,
  soh.overallDeliveryStatus,
  soh.requestedDeliveryDate,
  ROUND(soh.totalNetAmount, 2) AS net_amount,
  soh.transactionCurrency
FROM sales_order_headers soh
LEFT JOIN business_partners bp
  ON bp.customer = soh.soldToParty
WHERE COALESCE(soh.overallDeliveryStatus, '') <> 'C'
ORDER BY soh.requestedDeliveryDate ASC, salesOrder ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and pending_movement_query and entity_type == "delivery":
        return f"""
SELECT
  odh.deliveryDocument AS deliveryDocument,
  odh.creationDate,
  odh.actualGoodsMovementDate,
  odh.overallGoodsMovementStatus,
  odh.overallPickingStatus
FROM outbound_delivery_headers odh
WHERE COALESCE(odh.overallGoodsMovementStatus, '') <> 'C'
ORDER BY odh.creationDate ASC, deliveryDocument ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and operation == "list" and group_by == "customer" and customer_product_relation_query:
        return f"""
SELECT DISTINCT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, soh.soldToParty) AS customerName,
  soh.soldToParty AS customer,
  soi.salesOrder AS salesOrder,
  soi.material AS product,
  COALESCE(pd.productDescription, soi.material) AS productDescription
FROM sales_order_items soi
JOIN sales_order_headers soh
  ON soh.salesOrder = soi.salesOrder
LEFT JOIN business_partners bp
  ON bp.customer = soh.soldToParty
LEFT JOIN product_descriptions pd
  ON pd.product = soi.material
 AND pd.language = 'EN'
WHERE soh.soldToParty IS NOT NULL
  AND soi.material IS NOT NULL
ORDER BY customer ASC, salesOrder ASC, product ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and metric == "billing_document_count" and group_by == "product":
        return """
SELECT
  bdi.material AS product,
  COUNT(DISTINCT bdi.billingDocument) AS billing_document_count
FROM billing_document_items bdi
GROUP BY bdi.material
ORDER BY billing_document_count DESC, product ASC
LIMIT 10
""".strip()

    if intent == "analyze" and metric == "billing_documents" and group_by == "product":
        return f"""
SELECT
  bdi.material AS product,
  bdi.billingDocument AS billingDocument,
  ROUND(bdi.netAmount, 2) AS net_amount,
  bdi.transactionCurrency
FROM billing_document_items bdi
WHERE bdi.material IS NOT NULL
ORDER BY product ASC, billingDocument ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and metric == "quantity" and operation in {"sum", "max", "min", "avg", "list"}:
        agg = "AVG" if operation == "avg" else "SUM"
        order_direction = _order_direction_for_operation(operation)
        if group_by == "product":
            return f"""
SELECT
  soi.material AS product,
  ROUND({agg}(soi.requestedQuantity), 2) AS quantity,
  MIN(soi.requestedQuantityUnit) AS quantity_unit
FROM sales_order_items soi
WHERE soi.material IS NOT NULL
GROUP BY soi.material
ORDER BY quantity {order_direction}, product ASC
LIMIT {limit}
""".strip()
        if group_by == "customer":
            return f"""
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, soh.soldToParty) AS customerName,
  soh.soldToParty AS customer,
  ROUND({agg}(soi.requestedQuantity), 2) AS quantity,
  MIN(soi.requestedQuantityUnit) AS quantity_unit
FROM sales_order_items soi
JOIN sales_order_headers soh
  ON soh.salesOrder = soi.salesOrder
LEFT JOIN business_partners bp
  ON bp.customer = soh.soldToParty
WHERE soh.soldToParty IS NOT NULL
GROUP BY soh.soldToParty
ORDER BY quantity {order_direction}, customer ASC
LIMIT {limit}
""".strip()
        if group_by == "sales_order":
            return f"""
SELECT
  soi.salesOrder AS salesOrder,
  ROUND({agg}(soi.requestedQuantity), 2) AS quantity,
  MIN(soi.requestedQuantityUnit) AS quantity_unit
FROM sales_order_items soi
WHERE soi.salesOrder IS NOT NULL
GROUP BY soi.salesOrder
ORDER BY quantity {order_direction}, salesOrder ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and metric == "count" and operation in {"sum", "max", "min", "list"}:
        order_direction = _order_direction_for_operation(operation)
        if group_by == "product":
            return f"""
SELECT
  soi.material AS product,
  COUNT(DISTINCT soi.salesOrder) AS sales_order_count
FROM sales_order_items soi
WHERE soi.material IS NOT NULL
GROUP BY soi.material
ORDER BY sales_order_count {order_direction}, product ASC
LIMIT {limit}
""".strip()
        if group_by == "sales_order":
            return f"""
SELECT
  soi.salesOrder AS salesOrder,
  COUNT(DISTINCT soi.salesOrderItem) AS order_item_count
FROM sales_order_items soi
WHERE soi.salesOrder IS NOT NULL
GROUP BY soi.salesOrder
ORDER BY order_item_count {order_direction}, salesOrder ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and metric in {"net_amount", "revenue"} and operation in {"sum", "max", "min", "avg"}:
        order_direction = _order_direction_for_operation(operation)
        if group_by == "customer":
            if "paid" in q or "payment" in q:
                return f"""
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, p.customer) AS customerName,
  p.customer AS customer,
  ROUND(SUM(p.amountInTransactionCurrency), 2) AS paid_amount,
  MIN(p.transactionCurrency) AS transactionCurrency
FROM payments p
LEFT JOIN business_partners bp
  ON bp.customer = p.customer
WHERE p.customer IS NOT NULL
GROUP BY p.customer
ORDER BY paid_amount {order_direction}, customer ASC
LIMIT {limit}
""".strip()
            agg = {"sum": "SUM", "max": "MAX", "min": "MIN", "avg": "AVG"}[operation]
            return f"""
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, bdh.soldToParty) AS customerName,
  bdh.soldToParty AS customer,
  ROUND({agg}(bdh.totalNetAmount), 2) AS net_amount
FROM billing_document_headers bdh
LEFT JOIN business_partners bp
  ON bp.customer = bdh.soldToParty
GROUP BY bdh.soldToParty
ORDER BY net_amount {order_direction}, customer ASC
LIMIT {limit}
""".strip()
        if group_by == "product":
            agg = {"sum": "SUM", "max": "MAX", "min": "MIN", "avg": "AVG"}[operation]
            return f"""
SELECT
  bdi.material AS product,
  ROUND({agg}(bdi.netAmount), 2) AS net_amount
FROM billing_document_items bdi
GROUP BY bdi.material
ORDER BY net_amount {order_direction}, product ASC
LIMIT {limit}
""".strip()
        if group_by == "sales_order":
            agg = {"sum": "SUM", "max": "MAX", "min": "MIN", "avg": "AVG"}[operation]
            return f"""
SELECT
  soh.salesOrder AS salesOrder,
  ROUND({agg}(soh.totalNetAmount), 2) AS net_amount
FROM sales_order_headers soh
GROUP BY soh.salesOrder
ORDER BY net_amount {order_direction}, salesOrder ASC
LIMIT {limit}
""".strip()

    if (
        intent == "analyze"
        and operation == "list"
        and group_by == "customer"
        and (
            "sales order" in q
            or "sales orders" in q
            or "their orders" in q
            or "their sales orders" in q
            or plan.get("follow_up")
        )
    ):
        return f"""
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, soh.soldToParty) AS customerName,
  soh.soldToParty AS customer,
  soh.salesOrder AS salesOrder,
  ROUND(soh.totalNetAmount, 2) AS net_amount,
  soh.transactionCurrency
FROM sales_order_headers soh
LEFT JOIN business_partners bp
  ON bp.customer = soh.soldToParty
ORDER BY customer ASC, salesOrder ASC
LIMIT {limit}
""".strip()

    if intent == "analyze" and ("top" in q or "highest" in q or "most" in q) and "delivery" in q:
        return """
SELECT
  odi.referenceSdDocument AS salesOrder,
  COUNT(DISTINCT odi.deliveryDocument) AS delivery_count
FROM outbound_delivery_items odi
WHERE odi.referenceSdDocument IS NOT NULL
GROUP BY odi.referenceSdDocument
ORDER BY delivery_count DESC, salesOrder ASC
LIMIT 10
""".strip()

    if intent == "detect_anomaly":
        return """
SELECT
    'delivery_without_billing' AS anomaly_type,
    COUNT(DISTINCT odi.referenceSdDocument) AS anomaly_count
FROM outbound_delivery_items odi
LEFT JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
WHERE odi.referenceSdDocument IS NOT NULL
    AND bdi.billingDocument IS NULL

UNION ALL

SELECT
    'billing_without_delivery' AS anomaly_type,
    COUNT(DISTINCT bdi.referenceSdDocument) AS anomaly_count
FROM billing_document_items bdi
LEFT JOIN outbound_delivery_headers odh ON odh.deliveryDocument = bdi.referenceSdDocument
WHERE bdi.referenceSdDocument IS NOT NULL
    AND odh.deliveryDocument IS NULL

LIMIT 100
""".strip()

    if intent == "trace_flow" and entity_type == "invoice" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT bdh.billingDocument,
       bdi.referenceSdDocument AS deliveryDocument,
       odi.referenceSdDocument AS salesOrder,
       bdh.accountingDocument,
       p.accountingDocument AS paymentDocument
FROM billing_document_headers bdh
LEFT JOIN billing_document_items bdi ON bdi.billingDocument = bdh.billingDocument
LEFT JOIN outbound_delivery_items odi ON odi.deliveryDocument = bdi.referenceSdDocument
LEFT JOIN payments p ON p.accountingDocument = bdh.accountingDocument
WHERE bdh.billingDocument = '{safe_id}'
LIMIT 100
""".strip()

    if intent == "trace_flow" and entity_type == "sales_order" and entity_id:
        safe_id = _escape_sql_literal(str(entity_id))
        return f"""
SELECT soh.salesOrder,
       odi.deliveryDocument,
       bdi.billingDocument,
       bdh.accountingDocument,
       p.accountingDocument AS paymentDocument
FROM sales_order_headers soh
LEFT JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
LEFT JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
LEFT JOIN billing_document_headers bdh ON bdh.billingDocument = bdi.billingDocument
LEFT JOIN payments p ON p.accountingDocument = bdh.accountingDocument
WHERE soh.salesOrder = '{safe_id}'
LIMIT 100
""".strip()

    if intent == "trace_flow" and not entity_id:
        return """
SELECT
    bdh.billingDocument,
    odi.referenceSdDocument AS salesOrder,
    bdi.referenceSdDocument AS deliveryDocument,
    bdh.accountingDocument,
    p.accountingDocument AS paymentDocument
FROM billing_document_headers bdh
JOIN billing_document_items bdi
    ON bdi.billingDocument = bdh.billingDocument
LEFT JOIN outbound_delivery_items odi
    ON odi.deliveryDocument = bdi.referenceSdDocument
LEFT JOIN payments p
    ON p.accountingDocument = bdh.accountingDocument
ORDER BY bdh.billingDocument
LIMIT 50
""".strip()

    doc_match = re.search(r"\b(\d{6,})\b", user_query or "")
    if doc_match and "journal" in q and "entry" in q:
        billing_doc = _escape_sql_literal(doc_match.group(1))
        return f"""
SELECT
    bdh.billingDocument,
    bdh.accountingDocument AS journalEntry
FROM billing_document_headers bdh
WHERE bdh.billingDocument = '{billing_doc}'
LIMIT 20
""".strip()

    if "trace" in q and "flow" in q and "billing" in q and "document" in q:
        return """
SELECT
    bdh.billingDocument,
    odi.referenceSdDocument AS salesOrder,
    bdi.referenceSdDocument AS deliveryDocument,
    bdh.accountingDocument,
    p.accountingDocument AS paymentDocument
FROM billing_document_headers bdh
JOIN billing_document_items bdi
    ON bdi.billingDocument = bdh.billingDocument
LEFT JOIN outbound_delivery_items odi
    ON odi.deliveryDocument = bdi.referenceSdDocument
LEFT JOIN payments p
    ON p.accountingDocument = bdh.accountingDocument
ORDER BY bdh.billingDocument
LIMIT 50
""".strip()

    if (
        "product" in q
        and "billing" in q
        and ("highest" in q or "top" in q or "most" in q)
    ):
        return """
SELECT
  bdi.material AS product,
  COUNT(DISTINCT bdi.billingDocument) AS billing_document_count
FROM billing_document_items bdi
GROUP BY bdi.material
ORDER BY billing_document_count DESC, product ASC
LIMIT 10
""".strip()

    return None


def can_generate_sql_deterministically(plan: dict[str, Any], user_query: str) -> bool:
    """Return whether current deterministic catalog can satisfy this request."""
    return _deterministic_sql_from_plan(plan, user_query) is not None


def generate_sql(
    plan: dict[str, Any],
    user_query: str,
    model: Any | None,
    trace_id: str,
    llm_timeout_seconds: float = LLM_TIMEOUT_SECONDS,
) -> str:
    """Query agent: deterministic templates first, constrained LLM SQL fallback second."""
    deterministic = _deterministic_sql_from_plan(plan, user_query)
    if deterministic:
        log_event(trace_id, "query_agent", {"mode": "deterministic", "sql": deterministic})
        return deterministic

    if model is not None:
        return _generate_sql_with_model(plan, user_query, model, trace_id, llm_timeout_seconds)

    raise ValueError(
        "I need clarification to run this request deterministically. "
        "Please provide a supported entity (invoice, sales order, delivery, payment) "
        "and metric when needed."
    )
