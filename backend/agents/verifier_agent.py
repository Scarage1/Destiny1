from __future__ import annotations

from typing import Any

from .observability import log_event
try:
    from ..db_adapter import get_db_adapter
except ImportError:
    from db_adapter import get_db_adapter


def verify(plan: dict[str, Any], results: list[dict[str, Any]], trace_id: str) -> dict[str, Any]:
    """Verifier agent: sanity-check query outputs before response synthesis."""
    warnings: list[str] = []

    intent = plan.get("intent")

    if intent == "trace_flow" and plan.get("entity_id") and len(results) == 0:
        warnings.append("No flow records found for requested entity.")

    if intent == "trace_flow" and results:
        expected = {"salesOrder", "deliveryDocument", "billingDocument", "accountingDocument", "paymentDocument"}
        actual = set(results[0].keys())
        if not expected.intersection(actual):
            warnings.append("Trace flow result is missing expected flow columns.")

    if intent == "detect_anomaly":
        try:
            total_rows = get_db_adapter().execute_readonly_query(
                "SELECT COUNT(*) AS c FROM sales_order_headers"
            )
            total_orders = int(total_rows[0]["c"]) if total_rows else 0
            if total_orders > 0 and len(results) > (total_orders * 0.5):
                warnings.append("Anomaly result count exceeds 50% of total orders.")
        except Exception:
            warnings.append("Could not compute anomaly baseline for sanity check.")

    status = "ok" if not warnings else "warning"
    out = {"status": status, "warnings": warnings}
    log_event(trace_id, "verification", out)
    return out
