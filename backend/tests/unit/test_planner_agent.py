from __future__ import annotations

from backend.agents.planner_agent import plan


def test_planner_detects_anomaly_intent() -> None:
    out = plan("Find broken flows in orders", context={}, model=None, trace_id="t1")
    assert out["intent"] == "detect_anomaly"


def test_planner_detects_incomplete_orders_as_anomaly() -> None:
    out = plan("Show incomplete orders", context={}, model=None, trace_id="t1b")
    assert out["intent"] == "detect_anomaly"


def test_planner_detects_trace_flow_intent_and_invoice_entity() -> None:
    out = plan("Trace flow for invoice INV123", context={}, model=None, trace_id="t2")
    assert out["intent"] == "trace_flow"
    assert out["entity_type"] == "invoice"
    assert out["entity_id"] == "INV123"


def test_planner_detects_status_lookup_intent() -> None:
    out = plan("What is the status of this order", context={}, model=None, trace_id="t3")
    assert out["intent"] == "status_lookup"


def test_planner_uses_followup_context() -> None:
    context = {"last_entity": {"type": "invoice", "id": "INV9"}}
    out = plan("what about its payment", context=context, model=None, trace_id="t4")
    assert out["entity_type"] == "invoice"
    assert out["entity_id"] == "INV9"


def test_planner_does_not_extract_fake_id_from_plural_phrase() -> None:
    out = plan(
        "Which products are associated with the highest number of billing documents?",
        context={},
        model=None,
        trace_id="t5",
    )
    assert out["entity_type"] is None
    assert out["entity_id"] is None


def test_planner_handles_customer_sales_order_list_query() -> None:
    out = plan(
        "show customers and their sales orders",
        context={},
        model=None,
        trace_id="t6",
    )
    assert out["intent"] == "analyze"
    assert out["group_by"] == "customer"
    assert out["operation"] == "list"


def test_planner_infers_quantity_for_highest_ordered_product() -> None:
    out = plan(
        "highest ordered product",
        context={},
        model=None,
        trace_id="t6b",
    )
    assert out["intent"] == "analyze"
    assert out["group_by"] == "product"
    assert out["metric"] == "quantity"
    assert out["clarification"] is None


def test_planner_infers_quantity_for_highest_sold_product_with_typos() -> None:
    out = plan(
        "tell me about the highest sold product",
        context={},
        model=None,
        trace_id="t6bb",
    )
    assert out["intent"] == "analyze"
    assert out["group_by"] == "product"
    assert out["metric"] == "quantity"
    assert out["clarification"] is None


def test_planner_infers_net_amount_for_most_expensive_product() -> None:
    out = plan(
        "most expensive product",
        context={},
        model=None,
        trace_id="t6bc",
    )
    assert out["group_by"] == "product"
    assert out["metric"] == "net_amount"
    assert out["operation"] == "max"


def test_planner_infers_net_amount_for_top_customer() -> None:
    out = plan(
        "top customer",
        context={},
        model=None,
        trace_id="t6bd",
    )
    assert out["group_by"] == "customer"
    assert out["metric"] == "net_amount"
    assert out["operation"] == "max"


def test_planner_infers_quantity_for_top_selling_item() -> None:
    out = plan(
        "top selling item",
        context={},
        model=None,
        trace_id="t6be",
    )
    assert out["group_by"] == "product"
    assert out["metric"] == "quantity"
    assert out["operation"] == "max"


def test_planner_infers_quantity_for_customer_bought_the_most() -> None:
    out = plan(
        "which customer bought the most",
        context={},
        model=None,
        trace_id="t6bf",
    )
    assert out["group_by"] == "customer"
    assert out["metric"] == "quantity"
    assert out["operation"] == "max"


def test_planner_infers_net_amount_for_who_paid_the_most() -> None:
    out = plan(
        "who paid the most",
        context={},
        model=None,
        trace_id="t6bg",
    )
    assert out["group_by"] == "customer"
    assert out["metric"] == "net_amount"
    assert out["operation"] == "max"


def test_planner_handles_unpaid_invoices_query() -> None:
    out = plan(
        "show unpaid invoices",
        context={},
        model=None,
        trace_id="t6bh",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "invoice"
    assert out["operation"] == "list"
    assert out["clarification"] is None


def test_planner_handles_customers_with_no_payment_yet() -> None:
    out = plan(
        "customers with no payment yet",
        context={},
        model=None,
        trace_id="t6bi",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "customer"
    assert out["group_by"] == "customer"
    assert out["operation"] == "list"
    assert out["clarification"] is None


def test_planner_handles_orders_pending_delivery() -> None:
    out = plan(
        "orders pending delivery",
        context={},
        model=None,
        trace_id="t6bj",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "sales_order"
    assert out["group_by"] == "sales_order"
    assert out["operation"] == "list"
    assert out["clarification"] is None


def test_planner_handles_who_has_not_paid() -> None:
    out = plan(
        "who has not paid",
        context={},
        model=None,
        trace_id="t6bk",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "customer"
    assert out["group_by"] == "customer"
    assert out["clarification"] is None


def test_planner_handles_who_bought_what_from_us() -> None:
    out = plan(
        "who bought what from us",
        context={},
        model=None,
        trace_id="t6bl",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "customer"
    assert out["group_by"] == "customer"
    assert out["operation"] == "list"
    assert out["filters"] == [{"field": "relationship", "op": "=", "value": "customer_product"}]
    assert out["clarification"] is None


def test_planner_handles_which_customer_ordered_which_product() -> None:
    out = plan(
        "which customer ordered which product",
        context={},
        model=None,
        trace_id="t6bm",
    )
    assert out["intent"] == "analyze"
    assert out["entity_type"] == "customer"
    assert out["group_by"] == "customer"
    assert out["operation"] == "list"
    assert out["clarification"] is None


def test_planner_resolves_quantity_follow_up_from_pending_plan() -> None:
    out = plan(
        "quantity",
        context={
            "pending_plan": {
                "intent": "analyze",
                "entity_type": None,
                "entity_id": None,
                "metric": None,
                "operation": "max",
                "filters": [],
                "group_by": "product",
                "limit": 20,
                "time_range": None,
                "confidence": 0.65,
                "clarification": "Please specify a metric (net amount, quantity, or count).",
                "follow_up": False,
                "verification": "required",
            },
        },
        model=None,
        trace_id="t6c",
    )
    assert out["metric"] == "quantity"
    assert out["group_by"] == "product"
    assert out["clarification"] is None


def test_planner_resolves_count_follow_up_from_last_plan() -> None:
    out = plan(
        "count",
        context={
            "last_plan": {
                "intent": "analyze",
                "entity_type": None,
                "entity_id": None,
                "metric": "quantity",
                "operation": "max",
                "filters": [],
                "group_by": "product",
                "limit": 20,
                "time_range": None,
                "confidence": 0.92,
                "clarification": None,
                "follow_up": False,
                "verification": "required",
            },
        },
        model=None,
        trace_id="t6d",
    )
    assert out["metric"] == "count"
    assert out["group_by"] == "product"
    assert out["clarification"] is None


def test_planner_infers_product_price_query_from_last_plan_context() -> None:
    out = plan(
        "which has highest price",
        context={
            "last_plan": {
                "intent": "analyze",
                "entity_type": None,
                "entity_id": None,
                "metric": "quantity",
                "operation": "max",
                "filters": [],
                "group_by": "product",
                "limit": 20,
                "time_range": None,
                "confidence": 0.9,
                "clarification": None,
                "follow_up": False,
                "verification": "required",
            },
        },
        model=None,
        trace_id="t6e",
    )
    assert out["metric"] == "net_amount"
    assert out["group_by"] == "product"
    assert out["operation"] == "max"
    assert out["clarification"] is None


def test_planner_infers_cheapest_product_as_min_net_amount() -> None:
    out = plan(
        "cheapest product",
        context={},
        model=None,
        trace_id="t6f",
    )
    assert out["group_by"] == "product"
    assert out["metric"] == "net_amount"
    assert out["operation"] == "min"
    assert out["clarification"] is None


def test_planner_uses_last_plan_for_show_all_follow_up() -> None:
    out = plan(
        "show all",
        context={
            "last_plan": {
                "intent": "analyze",
                "entity_type": None,
                "entity_id": None,
                "metric": "billing_documents",
                "operation": "list",
                "filters": [],
                "group_by": "product",
                "limit": 20,
                "time_range": None,
                "confidence": 0.7,
                "clarification": None,
                "follow_up": False,
                "verification": "required",
            },
        },
        model=None,
        trace_id="t7",
    )
    assert out["metric"] == "billing_documents"
    assert out["group_by"] == "product"
    assert out["limit"] == 100
