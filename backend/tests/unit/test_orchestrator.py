from __future__ import annotations

import backend.agents.memory as memory
import backend.agents.orchestrator as orchestrator
from backend.agents.runtime_config import RuntimeConfig


def test_orchestrator_rejection_flow(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze"})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (False, "blocked"))

    out = orchestrator.process_query("tell me a joke", conversation_id="c1")
    assert out["status"] == "rejected"
    assert out["answer"] == "blocked"


def test_orchestrator_error_when_query_agent_fails(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze"})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))

    def _boom(*_args, **_kwargs):
        raise RuntimeError("query failed")

    monkeypatch.setattr(orchestrator, "generate_sql", _boom)

    out = orchestrator.process_query("show data", conversation_id="c2")
    assert out["status"] == "error"
    assert "Failed to generate query" in out["answer"]


def test_orchestrator_success_flow_with_mocks(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze", "entity_type": None, "entity_id": None})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "generate_sql", lambda *_args, **_kwargs: "SELECT salesOrder FROM sales_order_headers LIMIT 1")
    monkeypatch.setattr(
        orchestrator,
        "execute_sql",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 1;",
            "results": [{"salesOrder": "SO-1"}],
        },
    )
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("show one order", conversation_id="c3")
    assert out["status"] == "success"
    assert out["result_columns"] == ["salesOrder"]
    assert out["referenced_nodes"] == ["SalesOrder:SO-1"]


def test_orchestrator_includes_stage_latencies_in_agent_trace(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze", "entity_type": None, "entity_id": None})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "generate_sql", lambda *_args, **_kwargs: "SELECT salesOrder FROM sales_order_headers LIMIT 1")
    monkeypatch.setattr(
        orchestrator,
        "execute_sql",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 1;",
            "results": [{"salesOrder": "SO-1"}],
        },
    )
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("show one order", conversation_id="c8")
    stage_latencies = out.get("agent_trace", {}).get("stage_latencies_ms", {})
    assert out["status"] == "success"
    assert isinstance(stage_latencies, dict)
    assert "planner" in stage_latencies


def test_orchestrator_passes_semantic_cache_key_to_executor(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze", "entity_type": None, "entity_id": None})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "generate_sql", lambda *_args, **_kwargs: "SELECT salesOrder FROM sales_order_headers LIMIT 1")

    captured: dict[str, str | None] = {"semantic_cache_key": None}

    def _exec(_sql, _trace_id, semantic_cache_key=None):
        captured["semantic_cache_key"] = semantic_cache_key
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 1;",
            "results": [{"salesOrder": "SO-1"}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("show one order", conversation_id="c9")
    assert out["status"] == "success"
    assert isinstance(captured["semantic_cache_key"], str)
    assert len(captured["semantic_cache_key"] or "") == 24


def test_orchestrator_fallback_model_uses_runtime_config(monkeypatch) -> None:
    cfg = RuntimeConfig(
        gemini_api_key="",
        groq_api_key="groq-test-key",
        groq_model="llama-test-model",
        llm_timeout_seconds=20.0,
        pipeline_timeout_ms=8000,
        stage_budget_ms={
            "planner": 700,
            "guard": 120,
            "validator": 120,
            "query_agent": 300,
            "execution": 2500,
            "verification": 300,
            "response": 2200,
        },
        strict_deterministic=False,
        sql_cache_ttl_seconds=30,
        sql_cache_max_entries=256,
        sql_exec_retries=1,
        exec_cb_failure_threshold=3,
        exec_cb_open_seconds=20,
        memory_max_conversations=2000,
    )
    monkeypatch.setattr(orchestrator, "get_runtime_config", lambda: cfg)

    fallback_model = orchestrator._get_fallback_model()

    assert fallback_model is not None
    assert getattr(fallback_model, "provider", None) == "groq"
    assert getattr(fallback_model, "api_key", None) == "groq-test-key"
    assert getattr(fallback_model, "model_name", None) == "llama-test-model"


def test_orchestrator_strict_mode_disables_reasoning_model(monkeypatch) -> None:
    strict_cfg = RuntimeConfig(
        gemini_api_key="dummy",
        groq_api_key="dummy",
        groq_model="test-model",
        llm_timeout_seconds=20.0,
        pipeline_timeout_ms=8000,
        stage_budget_ms={
            "planner": 700,
            "guard": 120,
            "validator": 120,
            "query_agent": 300,
            "execution": 2500,
            "verification": 300,
            "response": 2200,
        },
        strict_deterministic=True,
        sql_cache_ttl_seconds=30,
        sql_cache_max_entries=256,
        sql_exec_retries=1,
        exec_cb_failure_threshold=3,
        exec_cb_open_seconds=20,
        memory_max_conversations=2000,
    )

    monkeypatch.setattr(orchestrator, "get_runtime_config", lambda: strict_cfg)
    monkeypatch.setattr(orchestrator, "_get_model", lambda: object())
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: object())
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {"intent": "analyze", "entity_type": None, "entity_id": None})
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))

    captured_model: dict[str, object | None] = {"model": object()}

    def _query_agent(_plan, _query, model, _trace_id, **_kwargs):
        captured_model["model"] = model
        return "SELECT salesOrder FROM sales_order_headers LIMIT 1"

    monkeypatch.setattr(orchestrator, "generate_sql", _query_agent)
    monkeypatch.setattr(
        orchestrator,
        "execute_sql",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 1;",
            "results": [{"salesOrder": "SO-1"}],
        },
    )
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("show one order", conversation_id="c10")
    assert out["status"] == "success"
    assert captured_model["model"] is None


def test_orchestrator_returns_clarification_for_low_confidence_plan(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {
        "intent": "trace_flow",
        "entity_type": None,
        "entity_id": None,
        "metric": None,
        "operation": "trace",
        "filters": [],
        "group_by": None,
        "limit": 20,
        "time_range": None,
        "confidence": 0.5,
        "clarification": "Please provide the invoice id.",
        "follow_up": False,
        "verification": "required",
    })

    out = orchestrator.process_query("trace invoice", conversation_id="c5")
    assert out["status"] == "clarification"
    assert "Please provide" in out["answer"]


def test_orchestrator_returns_clarification_for_invalid_plan(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {
        "intent": "unknown_intent",
    })

    out = orchestrator.process_query("anything", conversation_id="c6")
    assert out["status"] == "clarification"
    assert "clarification" in out["answer"].lower()


def test_orchestrator_returns_clarification_when_validator_blocks(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {
        "intent": "status_lookup",
        "entity_type": "invoice",
        "entity_id": None,
        "metric": None,
        "operation": "list",
        "filters": [],
        "group_by": None,
        "limit": 20,
        "time_range": None,
        "confidence": 0.95,
        "clarification": None,
        "follow_up": False,
        "verification": "required",
    })
    monkeypatch.setattr(
        orchestrator,
        "validate_plan_for_execution",
        lambda *_args, **_kwargs: (False, "Please provide the exact document ID for status lookup."),
    )

    out = orchestrator.process_query("status of invoice", conversation_id="c4")
    assert out["status"] == "clarification"
    assert "exact document ID" in out["answer"]


def test_orchestrator_calls_query_agent_without_model(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)
    monkeypatch.setattr(orchestrator, "planner_plan", lambda *_args, **_kwargs: {
        "intent": "trace_flow",
        "entity_type": "invoice",
        "entity_id": "INV123",
        "metric": None,
        "operation": "trace",
        "filters": [],
        "group_by": None,
        "limit": 20,
        "time_range": None,
        "confidence": 0.95,
        "clarification": None,
        "follow_up": False,
        "verification": "required",
    })
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))

    def _assert_model_none(_plan, _query, model, _trace_id, **_kwargs):
        assert model is None
        return "SELECT salesOrder FROM sales_order_headers LIMIT 1"

    monkeypatch.setattr(orchestrator, "generate_sql", _assert_model_none)
    monkeypatch.setattr(
        orchestrator,
        "execute_sql",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 1;",
            "results": [{"salesOrder": "SO-1"}],
        },
    )
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("trace invoice INV123", conversation_id="c7")
    assert out["status"] == "success"


def test_orchestrator_resolves_metric_follow_up_from_conversation(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()

    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"salesOrder": "SO-9001", "net_amount": 4200.0}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("SO-9001 has 4200 net amount.", ["SalesOrder:SO-9001"]))

    first = orchestrator.process_query("highest order", conversation_id="conv-follow")
    second = orchestrator.process_query("net amount", conversation_id="conv-follow")

    assert first["status"] == "clarification"
    assert second["status"] == "success"
    assert captured["sql"] is not None
    assert "from sales_order_headers" in (captured["sql"] or "").lower()


def test_orchestrator_passes_reasoning_model_to_planner_and_query(monkeypatch) -> None:
    fake_model = object()
    captured: dict[str, object | None] = {"planner_model": None, "query_model": None}

    monkeypatch.setattr(orchestrator, "_get_model", lambda: fake_model)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    def _planner(_query, _context, model, _trace_id, **_kwargs):
        captured["planner_model"] = model
        return {
            "intent": "analyze",
            "entity_type": "customer",
            "entity_id": None,
            "metric": None,
            "operation": "list",
            "filters": [],
            "group_by": "customer",
            "limit": 20,
            "time_range": None,
            "confidence": 0.9,
            "clarification": None,
            "follow_up": False,
            "verification": "required",
        }

    def _query_agent(_plan, _query, model, _trace_id, **_kwargs):
        captured["query_model"] = model
        return "SELECT salesOrder FROM sales_order_headers LIMIT 20"

    monkeypatch.setattr(orchestrator, "planner_plan", _planner)
    monkeypatch.setattr(orchestrator, "generate_sql", _query_agent)
    monkeypatch.setattr(orchestrator, "validate_plan_for_execution", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(orchestrator, "guard", lambda *_args, **_kwargs: (True, None))
    monkeypatch.setattr(
        orchestrator,
        "execute_sql",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": "SELECT salesOrder FROM sales_order_headers LIMIT 20;",
            "results": [{"salesOrder": "SO-1"}],
        },
    )
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("show customers and their sales orders", conversation_id="conv-nl")

    assert out["status"] == "success"
    assert captured["planner_model"] is fake_model
    assert captured["query_model"] is fake_model


def test_orchestrator_handles_highest_ordered_product_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"product": "SKU-1", "quantity": 72.0, "quantity_unit": "PC"}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("SKU-1 has quantity 72 PC.", ["Product:SKU-1"]))

    out = orchestrator.process_query("highest ordered product", conversation_id="conv-product-rank")

    assert out["status"] == "success"
    assert "sales_order_items" in (captured["sql"] or "").lower()
    assert "requestedquantity" in (captured["sql"] or "").lower()


def test_orchestrator_handles_typo_heavy_highest_sold_product_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"product": "SKU-1", "quantity": 72.0, "quantity_unit": "PC"}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("SKU-1 has quantity 72 PC.", ["Product:SKU-1"]))

    out = orchestrator.process_query("tellme abot the highest selled product", conversation_id="conv-product-typo")

    assert out["status"] == "success"
    assert "sales_order_items" in (captured["sql"] or "").lower()
    assert "requestedquantity" in (captured["sql"] or "").lower()


def test_orchestrator_handles_unpaid_invoices_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"billingDocument": "INV-1", "customer": "CUST-1", "net_amount": 4200.0}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("INV-1 is still unpaid.", ["BillingDocument:INV-1"]))

    out = orchestrator.process_query("show unpaid invoices", conversation_id="conv-unpaid-invoices")

    assert out["status"] == "success"
    assert "billing_document_headers" in (captured["sql"] or "").lower()
    assert "clearingdate is null" in (captured["sql"] or "").lower()


def test_orchestrator_handles_pending_delivery_orders_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"salesOrder": "SO-1", "overallDeliveryStatus": "A", "net_amount": 1200.0}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("SO-1 is still pending delivery.", ["SalesOrder:SO-1"]))

    out = orchestrator.process_query("orders pending delivery", conversation_id="conv-pending-delivery")

    assert out["status"] == "success"
    assert "sales_order_headers" in (captured["sql"] or "").lower()
    assert "overalldeliverystatus" in (captured["sql"] or "").lower()


def test_orchestrator_handles_customer_product_relationship_query(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"customerName": "Acme", "customer": "CUST-1", "salesOrder": "SO-1", "product": "MAT-1", "productDescription": "Widget"}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("Acme ordered Widget in sales order SO-1.", ["Customer:CUST-1", "SalesOrder:SO-1", "Product:MAT-1"]))

    out = orchestrator.process_query("who bought what from us", conversation_id="conv-customer-products")

    assert out["status"] == "success"
    assert "sales_order_items" in (captured["sql"] or "").lower()
    assert "product_descriptions" in (captured["sql"] or "").lower()


def test_orchestrator_resolves_typo_heavy_price_follow_up_from_context(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    executed_sql: list[str] = []

    def _exec(sql, _trace_id, semantic_cache_key=None):
        executed_sql.append(sql)
        if "requestedQuantity" in sql:
            return {
                "ok": True,
                "status": "success",
                "reason": None,
                "sql": sql,
                "results": [{"product": "SKU-QTY", "quantity": 72.0, "quantity_unit": "PC"}],
            }
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"product": "SKU-PRICE", "net_amount": 4200.0}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("ok", ["Product:SKU-1"]))

    first = orchestrator.process_query("what is highest order product", conversation_id="conv-price-typo")
    second = orchestrator.process_query("whichnhas highest price", conversation_id="conv-price-typo")

    assert first["status"] == "success"
    assert second["status"] == "success"
    assert len(executed_sql) == 2
    assert "requestedquantity" in executed_sql[0].lower()
    assert "from billing_document_items" in executed_sql[1].lower()


def test_orchestrator_handles_top_selling_item_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"product": "SKU-1", "quantity": 72.0, "quantity_unit": "PC"}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("SKU-1 has quantity 72 PC.", ["Product:SKU-1"]))

    out = orchestrator.process_query("top selling item", conversation_id="conv-top-selling-item")

    assert out["status"] == "success"
    assert "sales_order_items" in (captured["sql"] or "").lower()


def test_orchestrator_handles_who_paid_the_most_without_clarification(monkeypatch) -> None:
    memory.CONVERSATION_MEMORY.clear()
    monkeypatch.setattr(orchestrator, "_get_model", lambda: None)
    monkeypatch.setattr(orchestrator, "_get_fallback_model", lambda: None)

    captured: dict[str, str | None] = {"sql": None}

    def _exec(sql, _trace_id, semantic_cache_key=None):
        captured["sql"] = sql
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": sql,
            "results": [{"customerName": "Acme Corp", "customer": "C-1", "paid_amount": 4200.0}],
        }

    monkeypatch.setattr(orchestrator, "execute_sql", _exec)
    monkeypatch.setattr(orchestrator, "verify", lambda *_args, **_kwargs: {"status": "ok", "warnings": []})
    monkeypatch.setattr(orchestrator, "synthesize", lambda *_args, **_kwargs: ("Acme Corp paid 4200.", ["Customer:C-1"]))

    out = orchestrator.process_query("who paid the most", conversation_id="conv-paid-most")

    assert out["status"] == "success"
    assert "from payments" in (captured["sql"] or "").lower()
