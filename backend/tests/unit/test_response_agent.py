from __future__ import annotations

import time

from backend.agents.response_agent import synthesize


def test_synthesize_returns_nl_summary_without_model() -> None:
    plan = {"intent": "analyze"}
    results = [
        {"product": "FG-100", "billingDocumentCount": 7},
        {"product": "FG-200", "billingDocumentCount": 5},
    ]

    answer, referenced_nodes = synthesize(
        plan=plan,
        user_query="Which products are associated with the highest number of billing documents?",
        sql="SELECT product, COUNT(*) AS billingDocumentCount FROM billing_document_items GROUP BY product ORDER BY billingDocumentCount DESC LIMIT 10;",
        results=results,
        model=None,
        trace_id="trace-test-1",
    )

    assert "I found 2 matching records." in answer
    assert "FG-100" in answer
    assert "billing document count" in answer.lower()
    assert "{" not in answer
    assert set(referenced_nodes) == {"Product:FG-100", "Product:FG-200"}


def test_synthesize_empty_results_message() -> None:
    answer, referenced_nodes = synthesize(
        plan={"intent": "analyze"},
        user_query="Show missing deliveries",
        sql="SELECT * FROM outbound_delivery_headers WHERE 1=0;",
        results=[],
        model=None,
        trace_id="trace-test-2",
    )

    assert answer == "No matching records found in the dataset."
    assert referenced_nodes == []


def test_synthesize_falls_back_when_model_response_times_out() -> None:
    class SlowModel:
        def generate_content(self, _prompt, request_options=None):
            time.sleep(0.05)
            return type("Response", (), {"text": "slow answer"})()

    answer, referenced_nodes = synthesize(
        plan={"intent": "analyze"},
        user_query="Which products have the most billing documents?",
        sql="SELECT product, COUNT(*) AS billingDocumentCount FROM billing_document_items GROUP BY product ORDER BY billingDocumentCount DESC LIMIT 10;",
        results=[
            {"product": "FG-100", "billingDocumentCount": 7},
            {"product": "FG-200", "billingDocumentCount": 5},
        ],
        model=SlowModel(),
        trace_id="trace-timeout-test",
        llm_timeout_seconds=0.01,
    )

    assert "I found 2 matching records." in answer
    assert "FG-100" in answer
    assert set(referenced_nodes) == {"Product:FG-100", "Product:FG-200"}


def test_synthesize_customer_product_relationship_without_model() -> None:
    answer, referenced_nodes = synthesize(
        plan={"intent": "analyze", "entity_type": "customer", "group_by": "customer", "operation": "list"},
        user_query="who bought what from us",
        sql="SELECT customerName, customer, salesOrder, product, productDescription FROM sales_order_items LIMIT 10;",
        results=[
            {
                "customerName": "Acme Corp",
                "customer": "320000001",
                "salesOrder": "SO-100",
                "product": "FG-100",
                "productDescription": "Road Helmet",
            }
        ],
        model=None,
        trace_id="trace-test-3",
    )

    assert "Acme Corp ordered Road Helmet in sales order SO-100." in answer
    assert set(referenced_nodes) == {"Customer:320000001", "SalesOrder:SO-100", "Product:FG-100"}
