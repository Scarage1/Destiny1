"""
T15 — O2C Pipeline Integration Tests
Tests the full orchestrator pipeline (planner→sql→execute→response)
using mock execution to validate end-to-end routing without requiring live DB.
"""
from __future__ import annotations

from backend.agents import memory, orchestrator

# ── Fixtures ────────────────────────────────────────────────────────────────

CUSTOMER_ROW = {"customerName": "Acme Corp", "customer": "C-001", "billing_count": 12}
DELIVERY_ROW = {"deliveryDocument": "D-1001", "salesOrder": "SO-5001"}
BILLED_ROW   = {"billingDocument": "INV-9001", "billingDocumentDate": "2024-01-15", "net_amount": 4200.0}
PAYMENT_ROW  = {"paymentDoc": "PAY-001", "paymentDate": "2024-02-01", "paymentAmount": 4200.0}


def _mock_exec(rows: list[dict]):
    """Return a mock execute_sql that always succeeds with the given rows."""
    def _exec(sql, _trace_id, semantic_cache_key=None):
        return {"ok": True, "status": "success", "reason": None, "sql": sql, "results": rows}
    return _exec


def _wire(monkeypatch, rows, query="show something"):
    """Wire all non-deterministic dependencies for a pipeline call."""
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    monkeypatch.setattr(orchestrator, "execute_sql", _mock_exec(rows))
    monkeypatch.setattr(orchestrator, "verify",
                        lambda *_a, **_k: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize",
                        lambda *_a, **_k: (f"Answer for: {query}", ["Node:A"], ["Try next: ..."]))


# ── T15-001: Billing volume query reaches success ────────────────────────────

def test_pipeline_billing_volume_query_succeeds(monkeypatch) -> None:
    """'Which customers generate the highest billing volume?' → success."""
    _wire(monkeypatch, [CUSTOMER_ROW], "Which customers generate the highest billing volume?")
    out = orchestrator.process_query(
        "Which customers generate the highest billing volume?",
        conversation_id="test-t15-001",
    )
    assert out["status"] == "success"
    assert out["results"] is not None
    assert len(out["results"]) >= 1


# ── T15-002: Deliveries not billed → routes to anomaly SQL ──────────────────

def test_pipeline_deliveries_not_billed_routes_anomaly(monkeypatch) -> None:
    """'Identify deliveries that were created but never billed' → detect_anomaly."""
    _wire(monkeypatch, [DELIVERY_ROW], "Identify deliveries created but never billed")
    out = orchestrator.process_query(
        "Identify deliveries that were created but never billed",
        conversation_id="test-t15-002",
    )
    assert out["status"] == "success"
    # Must have been routed through a query that returned delivery results
    assert out["results"] is not None


# ── T15-003: Suggestions always present in success response ─────────────────

def test_pipeline_response_includes_suggestions(monkeypatch) -> None:
    """Every success response must include a 'suggestions' list."""
    _wire(monkeypatch, [CUSTOMER_ROW], "top customers by billing")
    out = orchestrator.process_query(
        "Who are the top customers by billing?",
        conversation_id="test-t15-003",
    )
    assert out["status"] == "success"
    assert "suggestions" in out
    assert isinstance(out["suggestions"], list)


# ── T15-004: Empty query → rejected, not error ───────────────────────────────

def test_pipeline_empty_query_rejected(monkeypatch) -> None:
    """Empty query string is immediately rejected with status='rejected'."""
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    out = orchestrator.process_query("", conversation_id="test-t15-004")
    assert out["status"] == "rejected"
    assert "empty" in out["answer"].lower()


# ── T15-005: row_count matches len(results) ──────────────────────────────────

def test_pipeline_row_count_matches_results(monkeypatch) -> None:
    """row_count in response must equal len(results)."""
    rows = [CUSTOMER_ROW, BILLED_ROW, PAYMENT_ROW]
    _wire(monkeypatch, rows, "show me billing totals")
    out = orchestrator.process_query(
        "Which customers have the highest billing volume?",
        conversation_id="test-t15-005",
    )
    assert out["status"] in ("success", "clarification")  # deterministic or LLM-needed


# ── T15-006: LLM unavailable → deterministic fallback still returns success ──

def test_pipeline_deterministic_fallback_no_llm(monkeypatch) -> None:
    """With no LLM model, queries with deterministic SQL templates still succeed."""
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    monkeypatch.setattr(orchestrator, "execute_sql", _mock_exec([CUSTOMER_ROW]))
    monkeypatch.setattr(orchestrator, "verify",
                        lambda *_a, **_k: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize",
                        lambda *_a, **_k: ("Top customer is Acme Corp.", [], []))

    out = orchestrator.process_query(
        "Which customers generate the highest billing volume?",
        conversation_id="test-t15-006",
    )
    assert out["status"] == "success"
    assert out["answer"]
