from __future__ import annotations

from backend.graph_builder import build_graph, get_relationship_diagnostics, reset_graph_cache
from backend.ingest import run_ingestion


def _graph_fingerprint() -> tuple[int, int, int, int]:
    """Return deterministic graph fingerprint for idempotency verification."""
    reset_graph_cache()
    graph = build_graph()

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    unique_node_ids = len(set(graph.nodes()))
    unique_edge_keys = len({(u, v, d.get("relationship")) for u, v, d in graph.edges(data=True)})
    return node_count, edge_count, unique_node_ids, unique_edge_keys


def test_repeated_ingestion_produces_stable_graph_shape() -> None:
    run_ingestion()
    first = _graph_fingerprint()

    run_ingestion()
    second = _graph_fingerprint()

    assert first == second, f"Graph fingerprint changed between runs: {first} != {second}"


def test_relationship_diagnostics_non_negative_and_consistent() -> None:
    run_ingestion()
    diagnostics = get_relationship_diagnostics()

    expected_keys = {
        "customer_to_sales_order_missing_customer",
        "sales_order_item_missing_sales_order",
        "sales_order_item_missing_product",
        "delivery_item_missing_sales_order",
        "billing_item_missing_delivery",
        "billing_header_missing_journal_entry",
        "journal_entry_missing_payment",
    }

    orphan_counts = diagnostics["orphan_counts"]

    assert set(orphan_counts.keys()) == expected_keys
    assert all(v >= 0 for v in orphan_counts.values())
    assert diagnostics["total_orphan_links"] == sum(orphan_counts.values())
