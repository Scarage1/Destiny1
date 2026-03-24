from __future__ import annotations

from backend.agents.query_agent import generate_sql
from backend.guardrails import validate_sql_safety


def test_query_agent_generates_deterministic_sql_for_anomaly() -> None:
    sql = generate_sql(
        {"intent": "detect_anomaly", "entity_type": None, "entity_id": None},
        "find broken flows",
        model=None,
        trace_id="q1",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "billing" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_invoice_trace() -> None:
    sql = generate_sql(
        {"intent": "trace_flow", "entity_type": "invoice", "entity_id": "INV123"},
        "trace invoice INV123",
        model=None,
        trace_id="q2",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "where bdh.billingdocument = 'inv123'" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_generic_trace_flow() -> None:
    sql = generate_sql(
        {"intent": "trace_flow", "entity_type": None, "entity_id": None},
        "Trace the full flow of a billing document",
        model=None,
        trace_id="q3",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from billing_document_headers" in sql.lower()
    assert "limit 50" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_billing_flow_query_text() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None},
        "Trace the full flow of a billing document",
        model=None,
        trace_id="q4",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from billing_document_headers" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_journal_lookup_query_text() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None},
        "91150187 - Find the journal entry number linked to this?",
        model=None,
        trace_id="q5",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "accountingdocument as journalentry" in sql.lower()
    assert "where bdh.billingdocument = '91150187'" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_status_lookup_invoice() -> None:
    sql = generate_sql(
        {"intent": "status_lookup", "entity_type": "invoice", "entity_id": "INV123"},
        "show status for invoice INV123",
        model=None,
        trace_id="q6",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from billing_document_headers" in sql.lower()
    assert "where bdh.billingdocument = 'inv123'" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_customer_sales_orders() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "group_by": "customer", "operation": "list", "limit": 100},
        "show customers and their sales orders",
        model=None,
        trace_id="q6b",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_headers" in sql.lower()
    assert "left join business_partners" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_show_all_follow_up() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "group_by": "customer", "operation": "list", "limit": 100, "follow_up": True},
        "show all",
        model=None,
        trace_id="q6bb",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_headers" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_billing_documents_by_product() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "billing_documents", "group_by": "product", "operation": "list", "limit": 100},
        "show all bill document for each product",
        model=None,
        trace_id="q6c",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from billing_document_items" in sql.lower()
    assert "billingdocument" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_product_quantity_ranking() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "quantity", "group_by": "product", "operation": "max", "limit": 20},
        "highest ordered product",
        model=None,
        trace_id="q6d",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "sum(soi.requestedquantity)" in sql.lower()
    assert "from sales_order_items" in sql.lower()
    assert "as quantity" in sql.lower()


def test_query_agent_generates_deterministic_sql_for_product_order_count() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "count", "group_by": "product", "operation": "max", "limit": 20},
        "most ordered product by count",
        model=None,
        trace_id="q6e",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "count(distinct soi.salesorder)" in sql.lower()
    assert "as sales_order_count" in sql.lower()


def test_query_agent_generates_min_sql_for_cheapest_product() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "net_amount", "group_by": "product", "operation": "min", "limit": 20},
        "cheapest product",
        model=None,
        trace_id="q6f",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "order by net_amount asc" in sql.lower()


def test_query_agent_generates_quantity_sql_for_customer_purchase_ranking() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "quantity", "group_by": "customer", "operation": "max", "limit": 20},
        "which customer bought the most",
        model=None,
        trace_id="q6g",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "join sales_order_headers" in sql.lower()
    assert "as quantity" in sql.lower()


def test_query_agent_generates_paid_amount_sql_for_who_paid_the_most() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": None, "entity_id": None, "metric": "net_amount", "group_by": "customer", "operation": "max", "limit": 20},
        "who paid the most",
        model=None,
        trace_id="q6h",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from payments p" in sql.lower()
    assert "as paid_amount" in sql.lower()


def test_query_agent_generates_unpaid_invoice_sql() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": "invoice", "entity_id": None, "metric": None, "group_by": None, "operation": "list", "limit": 20},
        "show unpaid invoices",
        model=None,
        trace_id="q6i",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from billing_document_headers" in sql.lower()
    assert "left join payments p" in sql.lower()
    assert "p.clearingdate is null" in sql.lower()


def test_query_agent_generates_unpaid_customer_sql() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": "customer", "entity_id": None, "metric": None, "group_by": "customer", "operation": "list", "limit": 20},
        "customers with no payment yet",
        model=None,
        trace_id="q6j",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "count(distinct bdh.billingdocument) as unpaid_invoice_count" in sql.lower()
    assert "sum(bdh.totalnetamount)" in sql.lower()


def test_query_agent_generates_pending_delivery_order_sql() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": "sales_order", "entity_id": None, "metric": None, "group_by": "sales_order", "operation": "list", "limit": 20},
        "orders pending delivery",
        model=None,
        trace_id="q6k",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_headers" in sql.lower()
    assert "overalldeliverystatus" in sql.lower()
    assert "<> 'c'" in sql.lower()


def test_query_agent_generates_customer_product_relationship_sql() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": "customer", "entity_id": None, "metric": None, "group_by": "customer", "operation": "list", "limit": 20, "filters": [{"field": "relationship", "op": "=", "value": "customer_product"}]},
        "who bought what from us",
        model=None,
        trace_id="q6l",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_items" in sql.lower()
    assert "join sales_order_headers" in sql.lower()
    assert "left join product_descriptions" in sql.lower()
    assert "as productdescription" in sql.lower()


def test_query_agent_preserves_customer_product_relationship_for_show_all_follow_up() -> None:
    sql = generate_sql(
        {"intent": "analyze", "entity_type": "customer", "entity_id": None, "metric": None, "group_by": "customer", "operation": "list", "limit": 100, "follow_up": True, "filters": [{"field": "relationship", "op": "=", "value": "customer_product"}]},
        "show all",
        model=None,
        trace_id="q6m",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_items" in sql.lower()
    assert "productdescription" in sql.lower()


def test_query_agent_raises_for_unsupported_plan() -> None:
    try:
        generate_sql(
            {"intent": "analyze", "entity_type": None, "entity_id": None, "operation": "median"},
            "show median revenue by week",
            model=None,
            trace_id="q7",
        )
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "clarification" in str(e).lower()


def test_query_agent_never_calls_model_for_sql() -> None:
    class _Model:
        def generate_content(self, *_args, **_kwargs):
            raise AssertionError("model must not be called")

    sql = generate_sql(
        {"intent": "trace_flow", "entity_type": "invoice", "entity_id": "INV123"},
        "trace invoice INV123",
        model=_Model(),
        trace_id="q8",
    )
    assert "from billing_document_headers" in sql.lower()


def test_query_agent_prefers_deterministic_sql_for_supported_natural_language_query() -> None:
    class _Model:
        def generate_content(self, *_args, **_kwargs):
            return type(
                "Response",
                (),
                {
                    "text": """```sql
SELECT
  COALESCE(bp.businessPartnerName, bp.businessPartnerFullName, soh.soldToParty) AS customerName,
  soh.soldToParty AS customer,
  soh.salesOrder AS salesOrder
FROM sales_order_headers soh
LEFT JOIN business_partners bp ON bp.customer = soh.soldToParty
ORDER BY customer ASC, salesOrder ASC
LIMIT 25
```"""
                },
            )()

    sql = generate_sql(
        {"intent": "analyze", "entity_type": "customer", "entity_id": None, "group_by": "customer", "operation": "list"},
        "who bought what from us",
        model=_Model(),
        trace_id="q9",
    )
    ok, reason, _ = validate_sql_safety(sql)
    assert ok is True
    assert reason is None
    assert "from sales_order_items" in sql.lower()
    assert "left join product_descriptions" in sql.lower()
