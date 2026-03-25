from __future__ import annotations

import json
import queue
import re
import threading
from typing import Any

from .observability import log_event

LLM_TIMEOUT_SECONDS = 20

try:
    from ..guardrails import validate_response_grounding
except ImportError:
    from guardrails import validate_response_grounding


ANSWER_SYNTHESIS_PROMPT = """You are a data analyst answering questions about an SAP Order-to-Cash dataset.

You are given:
1) The original question
2) The structured intent plan
3) The SQL query that was executed
4) The query results

RULES:
- Answer ONLY from provided results.
- If results are empty, return: No matching records found in the dataset.
- Mention concrete IDs/numbers from the results.
- Be concise and business-friendly.
"""


def extract_referenced_nodes(results: list[dict]) -> list[str]:
    node_ids = set()
    column_to_type = {
        "salesOrder": "SalesOrder",
        "deliveryDocument": "Delivery",
        "billingDocument": "BillingDocument",
        "accountingDocument": "JournalEntry",
        "businessPartner": "Customer",
        "soldToParty": "Customer",
        "customer": "Customer",
        "product": "Product",
        "material": "Product",
        "plant": "Plant",
        "productionPlant": "Plant",
        "paymentDocument": "Payment",
    }

    for row in results:
        for col, node_type in column_to_type.items():
            if col in row and row[col]:
                node_ids.add(f"{node_type}:{row[col]}")

    return list(node_ids)


def _humanize_column_name(column: str) -> str:
    if not column:
        return "value"
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", column)
    spaced = spaced.replace("_", " ").strip()
    return re.sub(r"\s+", " ", spaced).lower()


def _format_value(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.2f}" if not value.is_integer() else str(int(value))
    return str(value)


def _row_to_sentence(row: dict[str, Any], max_fields: int = 4) -> str:
    parts: list[str] = []
    for key, value in row.items():
        if value is None:
            continue
        parts.append(f"{_humanize_column_name(key)}: {_format_value(value)}")
        if len(parts) >= max_fields:
            break
    if not parts:
        return "No populated fields were returned for this row"
    return ", ".join(parts)


# Map technical column names to friendly entity labels
_DIMENSION_LABELS: dict[str, str] = {
    "salesorder": "Sales Order",
    "salesorderid": "Sales Order",
    "billingdocument": "Invoice",
    "billingdoc": "Invoice",
    "deliverydocument": "Delivery",
    "delivery": "Delivery",
    "businesspartner": "Customer",
    "soldtoparty": "Customer",
    "customer": "Customer",
    "customername": "Customer",
    "product": "Product",
    "material": "Product",
    "productdescription": "Product",
    "plant": "Plant",
    "paymentdocument": "Payment",
}


def _humanize_dimension_label(col: str) -> str:
    """Return a human-friendly entity label for a dimension column name."""
    normalized = col.lower().replace("_", "").replace(" ", "")
    return _DIMENSION_LABELS.get(normalized, _humanize_column_name(col))


def _deterministic_nl_summary(results: list[dict[str, Any]]) -> str:
    total = len(results)
    if total == 0:
        return "No matching records found in the dataset."

    first_row = results[0]
    columns = list(first_row.keys())
    has_customer_product_relation = (
        any(col in columns for col in ("customerName", "customer"))
        and "product" in columns
    )

    metric_candidates = [
        col
        for col in columns
        if col.lower().endswith(("count", "total", "amount", "qty", "quantity"))
        and isinstance(first_row.get(col), (int, float))
    ]
    dimension_candidates = [col for col in columns if col not in metric_candidates]

    intro = f"I found {total} matching record{'s' if total != 1 else ''}."

    if has_customer_product_relation:
        lines = [intro, "Here are the first customer-product relationships:"]
        for idx, row in enumerate(results[:5], start=1):
            customer_val = _format_value(row.get("customerName") or row.get("customer"))
            product_val = _format_value(row.get("productDescription") or row.get("product"))
            sales_order = row.get("salesOrder")
            if sales_order:
                lines.append(f"{idx}. {customer_val} ordered {product_val} in sales order {sales_order}.")
            else:
                lines.append(f"{idx}. {customer_val} ordered {product_val}.")
        return "\n".join(lines)

    if metric_candidates and dimension_candidates:
        metric_col = metric_candidates[0]
        dimension_col = dimension_candidates[0]
        entity_label = _humanize_dimension_label(dimension_col)
        metric_label = _humanize_column_name(metric_col)
        lines = [intro, f"Here are the top results ranked by {metric_label}:"]
        for idx, row in enumerate(results[:5], start=1):
            dimension_val = _format_value(row.get(dimension_col))
            metric_val = _format_value(row.get(metric_col))
            lines.append(f"{idx}. {entity_label} {dimension_val} — {metric_val} {metric_label}")
        return "\n".join(lines)

    lines = [intro, "Here are the first rows in plain language:"]
    for idx, row in enumerate(results[:5], start=1):
        lines.append(f"{idx}. {_row_to_sentence(row)}.")
    return "\n".join(lines)


def _generate_model_answer(
    model: Any,
    prompt: str,
    timeout_seconds: float,
    trace_id: str,
) -> str:
    if timeout_seconds <= 0:
        raise TimeoutError("No response budget remaining")

    result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": timeout_seconds},
            )
            result_queue.put(("ok", (response.text or "").strip()))
        except Exception as exc:  # pragma: no cover - surfaced through queue in tests
            result_queue.put(("err", exc))

    thread = threading.Thread(target=_worker, daemon=True, name=f"response-synth-{trace_id[:8]}")
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        log_event(
            trace_id,
            "response_timeout",
            {"timeout_seconds": timeout_seconds, "thread_leaked": True},
        )
        raise TimeoutError(f"Response synthesis timed out after {timeout_seconds:.2f}s")

    try:
        status, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        raise RuntimeError("Model returned no response payload") from exc

    if status == "err":
        raise payload

    return str(payload or "")


def synthesize(
    plan: dict[str, Any],
    user_query: str,
    sql: str,
    results: list[dict[str, Any]],
    model: Any | None,
    trace_id: str,
    llm_timeout_seconds: float = LLM_TIMEOUT_SECONDS,
) -> tuple[str, list[str]]:
    """Response agent: build grounded business explanation and graph references."""
    referenced_nodes = extract_referenced_nodes(results)

    if len(results) == 0:
        answer = "No matching records found in the dataset."
        log_event(trace_id, "response", {"status": "empty", "referenced_nodes": 0})
        return answer, referenced_nodes

    answer: str
    try:
        if model is None:
            raise RuntimeError("Model unavailable for synthesis")

        results_text = json.dumps(results[:50], indent=2, default=str)
        prompt = f"""{ANSWER_SYNTHESIS_PROMPT}

Intent Plan: {json.dumps(plan)}
Question: {user_query}
SQL Query: {sql}
Results ({len(results)} rows):
{results_text}
"""
        answer = _generate_model_answer(model, prompt, llm_timeout_seconds, trace_id)
    except Exception:
        answer = _deterministic_nl_summary(results)

    # Grounding hardening: ensure at least one returned ID appears in answer.
    if not validate_response_grounding(answer, results):
        answer = _deterministic_nl_summary(results)

    log_event(trace_id, "response", {"status": "success", "referenced_nodes": len(referenced_nodes)})
    return answer, referenced_nodes
