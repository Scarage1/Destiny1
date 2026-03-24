"""
NetworkX graph builder: constructs an in-memory graph from SQLite data.
Provides graph exploration APIs (nodes, neighbors, metadata).
"""

import networkx as nx

try:
    from .database import get_db
except ImportError:
    from database import get_db

# Singleton graph instance
_graph: nx.DiGraph | None = None


def build_graph() -> nx.DiGraph:
    """Build a directed graph from all O2C entities and relationships."""
    global _graph
    G = nx.DiGraph()

    with get_db() as conn:
        # --- NODES ---

        # Customers (Business Partners)
        for row in conn.execute("SELECT * FROM business_partners").fetchall():
            bp = dict(row)
            node_id = f"Customer:{bp['businessPartner']}"
            G.add_node(
                node_id,
                type="Customer",
                label=bp.get("businessPartnerName") or bp["businessPartner"],
                **bp,
            )

        # Products
        for row in conn.execute("""
            SELECT p.*, pd.productDescription
            FROM products p
            LEFT JOIN product_descriptions pd ON p.product = pd.product AND pd.language = 'EN'
        """).fetchall():
            p = dict(row)
            node_id = f"Product:{p['product']}"
            G.add_node(
                node_id,
                type="Product",
                label=p.get("productDescription") or p["product"],
                **p,
            )

        # Plants
        for row in conn.execute("SELECT * FROM plants").fetchall():
            pl = dict(row)
            node_id = f"Plant:{pl['plant']}"
            G.add_node(
                node_id,
                type="Plant",
                label=pl.get("plantName") or pl["plant"],
                **pl,
            )

        # Sales Orders
        for row in conn.execute(
            "SELECT * FROM sales_order_headers"
        ).fetchall():
            so = dict(row)
            node_id = f"SalesOrder:{so['salesOrder']}"
            G.add_node(
                node_id,
                type="SalesOrder",
                label=f"SO-{so['salesOrder']}",
                **so,
            )

        # Sales Order Items
        for row in conn.execute("SELECT * FROM sales_order_items").fetchall():
            soi = dict(row)
            item_id = f"{soi['salesOrder']}-{soi['salesOrderItem']}"
            node_id = f"SalesOrderItem:{item_id}"
            G.add_node(
                node_id, type="SalesOrderItem", label=f"SOI-{item_id}", **soi
            )

        # Deliveries
        for row in conn.execute(
            "SELECT * FROM outbound_delivery_headers"
        ).fetchall():
            d = dict(row)
            node_id = f"Delivery:{d['deliveryDocument']}"
            G.add_node(
                node_id,
                type="Delivery",
                label=f"DLV-{d['deliveryDocument']}",
                **d,
            )

        # Delivery Items
        for row in conn.execute(
            "SELECT * FROM outbound_delivery_items"
        ).fetchall():
            di = dict(row)
            item_id = f"{di['deliveryDocument']}-{di['deliveryDocumentItem']}"
            node_id = f"DeliveryItem:{item_id}"
            G.add_node(
                node_id, type="DeliveryItem", label=f"DI-{item_id}", **di
            )

        # Billing Documents
        for row in conn.execute(
            "SELECT * FROM billing_document_headers"
        ).fetchall():
            bd = dict(row)
            node_id = f"BillingDocument:{bd['billingDocument']}"
            G.add_node(
                node_id,
                type="BillingDocument",
                label=f"INV-{bd['billingDocument']}",
                **bd,
            )

        # Billing Document Items
        for row in conn.execute(
            "SELECT * FROM billing_document_items"
        ).fetchall():
            bdi = dict(row)
            item_id = f"{bdi['billingDocument']}-{bdi['billingDocumentItem']}"
            node_id = f"BillingDocumentItem:{item_id}"
            G.add_node(
                node_id,
                type="BillingDocumentItem",
                label=f"BDI-{item_id}",
                **bdi,
            )

        # Journal Entries
        for row in conn.execute(
            "SELECT * FROM journal_entry_items"
        ).fetchall():
            je = dict(row)
            node_id = f"JournalEntry:{je['accountingDocument']}"
            if not G.has_node(node_id):
                G.add_node(
                    node_id,
                    type="JournalEntry",
                    label=f"JE-{je['accountingDocument']}",
                    **je,
                )

        # Payments
        for row in conn.execute("SELECT * FROM payments").fetchall():
            pay = dict(row)
            node_id = f"Payment:{pay['accountingDocument']}"
            if not G.has_node(node_id):
                G.add_node(
                    node_id,
                    type="Payment",
                    label=f"PAY-{pay['accountingDocument']}",
                    **pay,
                )

        # --- EDGES ---

        # Customer -> SalesOrder (PLACED)
        for row in conn.execute(
            "SELECT salesOrder, soldToParty FROM sales_order_headers WHERE soldToParty IS NOT NULL"
        ).fetchall():
            src = f"Customer:{row['soldToParty']}"
            tgt = f"SalesOrder:{row['salesOrder']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="PLACED")

        # SalesOrder -> SalesOrderItem (HAS_ITEM)
        for row in conn.execute(
            "SELECT salesOrder, salesOrderItem FROM sales_order_items"
        ).fetchall():
            src = f"SalesOrder:{row['salesOrder']}"
            tgt = f"SalesOrderItem:{row['salesOrder']}-{row['salesOrderItem']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="HAS_ITEM")

        # SalesOrderItem -> Product (REFERS_TO)
        for row in conn.execute(
            "SELECT salesOrder, salesOrderItem, material FROM sales_order_items WHERE material IS NOT NULL"
        ).fetchall():
            src = f"SalesOrderItem:{row['salesOrder']}-{row['salesOrderItem']}"
            tgt = f"Product:{row['material']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="REFERS_TO")

        # SalesOrderItem -> Plant (PRODUCED_AT)
        for row in conn.execute(
            "SELECT salesOrder, salesOrderItem, productionPlant FROM sales_order_items WHERE productionPlant IS NOT NULL"
        ).fetchall():
            src = f"SalesOrderItem:{row['salesOrder']}-{row['salesOrderItem']}"
            tgt = f"Plant:{row['productionPlant']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="PRODUCED_AT")

        # SalesOrder -> Delivery (FULFILLED_BY) via delivery items reference
        for row in conn.execute("""
            SELECT DISTINCT odi.referenceSdDocument AS salesOrder, odh.deliveryDocument
            FROM outbound_delivery_items odi
            JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument
            WHERE odi.referenceSdDocument IS NOT NULL
        """).fetchall():
            src = f"SalesOrder:{row['salesOrder']}"
            tgt = f"Delivery:{row['deliveryDocument']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="FULFILLED_BY")

        # Delivery -> DeliveryItem (HAS_ITEM)
        for row in conn.execute(
            "SELECT deliveryDocument, deliveryDocumentItem FROM outbound_delivery_items"
        ).fetchall():
            src = f"Delivery:{row['deliveryDocument']}"
            tgt = f"DeliveryItem:{row['deliveryDocument']}-{row['deliveryDocumentItem']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="HAS_ITEM")

        # DeliveryItem -> Plant (SHIPS_FROM)
        for row in conn.execute(
            "SELECT deliveryDocument, deliveryDocumentItem, plant FROM outbound_delivery_items WHERE plant IS NOT NULL"
        ).fetchall():
            src = f"DeliveryItem:{row['deliveryDocument']}-{row['deliveryDocumentItem']}"
            tgt = f"Plant:{row['plant']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="SHIPS_FROM")

        # Delivery -> BillingDocument (BILLED_BY) via billing_document_items.referenceSdDocument
        for row in conn.execute("""
            SELECT DISTINCT bdi.referenceSdDocument AS deliveryDocument, bdh.billingDocument
            FROM billing_document_items bdi
            JOIN billing_document_headers bdh ON bdi.billingDocument = bdh.billingDocument
            WHERE bdi.referenceSdDocument IS NOT NULL
        """).fetchall():
            src = f"Delivery:{row['deliveryDocument']}"
            tgt = f"BillingDocument:{row['billingDocument']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="BILLED_BY")

        # BillingDocument -> BillingDocumentItem (HAS_ITEM)
        for row in conn.execute(
            "SELECT billingDocument, billingDocumentItem FROM billing_document_items"
        ).fetchall():
            src = f"BillingDocument:{row['billingDocument']}"
            tgt = f"BillingDocumentItem:{row['billingDocument']}-{row['billingDocumentItem']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="HAS_ITEM")

        # BillingDocumentItem -> Product (FOR_PRODUCT)
        for row in conn.execute(
            "SELECT billingDocument, billingDocumentItem, material FROM billing_document_items WHERE material IS NOT NULL"
        ).fetchall():
            src = f"BillingDocumentItem:{row['billingDocument']}-{row['billingDocumentItem']}"
            tgt = f"Product:{row['material']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="FOR_PRODUCT")

        # BillingDocument -> JournalEntry (POSTED_TO)
        for row in conn.execute(
            "SELECT billingDocument, accountingDocument FROM billing_document_headers WHERE accountingDocument IS NOT NULL"
        ).fetchall():
            src = f"BillingDocument:{row['billingDocument']}"
            tgt = f"JournalEntry:{row['accountingDocument']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="POSTED_TO")

        # JournalEntry -> Payment (CLEARED_BY)
        for row in conn.execute(
            "SELECT accountingDocument, clearingAccountingDocument FROM journal_entry_items WHERE clearingAccountingDocument IS NOT NULL"
        ).fetchall():
            src = f"JournalEntry:{row['accountingDocument']}"
            tgt = f"Payment:{row['clearingAccountingDocument']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="CLEARED_BY")

        # Customer -> BillingDocument (BILLED_TO)
        for row in conn.execute(
            "SELECT billingDocument, soldToParty FROM billing_document_headers WHERE soldToParty IS NOT NULL"
        ).fetchall():
            src = f"Customer:{row['soldToParty']}"
            tgt = f"BillingDocument:{row['billingDocument']}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relationship="BILLED_TO")

    _graph = G
    return G


def get_graph() -> nx.DiGraph:
    """Get or build the graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def reset_graph_cache() -> None:
    """Reset in-memory graph singleton (useful for tests/rebuilds)."""
    global _graph
    _graph = None


def get_graph_overview() -> dict:
    """Get a summary of the graph for initial UI rendering."""
    G = get_graph()

    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append(
            {
                "id": node_id,
                "type": data.get("type", "Unknown"),
                "label": data.get("label", node_id),
            }
        )

    edges = []
    for src, tgt, data in G.edges(data=True):
        edges.append(
            {
                "source": src,
                "target": tgt,
                "relationship": data.get("relationship", "RELATED"),
            }
        )

    # Count by type
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "node_types": type_counts,
        },
    }


def get_node_details(node_id: str) -> dict | None:
    """Get full metadata for a specific node."""
    G = get_graph()
    if not G.has_node(node_id):
        return None

    data = dict(G.nodes[node_id])
    neighbors = {
        "incoming": [],
        "outgoing": [],
    }

    for pred in G.predecessors(node_id):
        edge_data = G.edges[pred, node_id]
        neighbors["incoming"].append(
            {
                "id": pred,
                "type": G.nodes[pred].get("type"),
                "label": G.nodes[pred].get("label"),
                "relationship": edge_data.get("relationship"),
            }
        )

    for succ in G.successors(node_id):
        edge_data = G.edges[node_id, succ]
        neighbors["outgoing"].append(
            {
                "id": succ,
                "type": G.nodes[succ].get("type"),
                "label": G.nodes[succ].get("label"),
                "relationship": edge_data.get("relationship"),
            }
        )

    return {
        "id": node_id,
        "properties": data,
        "neighbors": neighbors,
    }


def get_node_neighbors(node_id: str) -> dict | None:
    """Get neighbors for node expansion in the UI."""
    G = get_graph()
    if not G.has_node(node_id):
        return None

    nodes = [
        {
            "id": node_id,
            "type": G.nodes[node_id].get("type"),
            "label": G.nodes[node_id].get("label"),
        }
    ]
    edges = []

    for pred in G.predecessors(node_id):
        nodes.append(
            {
                "id": pred,
                "type": G.nodes[pred].get("type"),
                "label": G.nodes[pred].get("label"),
            }
        )
        edges.append(
            {
                "source": pred,
                "target": node_id,
                "relationship": G.edges[pred, node_id].get("relationship"),
            }
        )

    for succ in G.successors(node_id):
        nodes.append(
            {
                "id": succ,
                "type": G.nodes[succ].get("type"),
                "label": G.nodes[succ].get("label"),
            }
        )
        edges.append(
            {
                "source": node_id,
                "target": succ,
                "relationship": G.edges[node_id, succ].get("relationship"),
            }
        )

    # Deduplicate nodes
    seen = set()
    unique_nodes = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique_nodes.append(n)

    return {"nodes": unique_nodes, "edges": edges}


def get_relationship_diagnostics() -> dict:
    """Return orphan/missing-link diagnostics for relationship-critical joins.

    Diagnostics are computed from SQLite source tables and indicate rows that
    cannot be linked due to missing source/target references.
    """
    with get_db() as conn:
        checks = {
            "customer_to_sales_order_missing_customer": """
                SELECT COUNT(*) AS c
                FROM sales_order_headers so
                LEFT JOIN business_partners bp
                    ON bp.businessPartner = so.soldToParty
                WHERE so.soldToParty IS NOT NULL
                    AND bp.businessPartner IS NULL
            """,
            "sales_order_item_missing_sales_order": """
                SELECT COUNT(*) AS c
                FROM sales_order_items soi
                LEFT JOIN sales_order_headers so
                    ON so.salesOrder = soi.salesOrder
                WHERE so.salesOrder IS NULL
            """,
            "sales_order_item_missing_product": """
                SELECT COUNT(*) AS c
                FROM sales_order_items soi
                LEFT JOIN products p
                    ON p.product = soi.material
                WHERE soi.material IS NOT NULL
                    AND p.product IS NULL
            """,
            "delivery_item_missing_sales_order": """
                SELECT COUNT(*) AS c
                FROM outbound_delivery_items odi
                LEFT JOIN sales_order_headers so
                    ON so.salesOrder = odi.referenceSdDocument
                WHERE odi.referenceSdDocument IS NOT NULL
                    AND so.salesOrder IS NULL
            """,
            "billing_item_missing_delivery": """
                SELECT COUNT(*) AS c
                FROM billing_document_items bdi
                LEFT JOIN outbound_delivery_headers odh
                    ON odh.deliveryDocument = bdi.referenceSdDocument
                WHERE bdi.referenceSdDocument IS NOT NULL
                    AND odh.deliveryDocument IS NULL
            """,
            "billing_header_missing_journal_entry": """
                SELECT COUNT(*) AS c
                FROM billing_document_headers bdh
                LEFT JOIN journal_entry_items je
                    ON je.accountingDocument = bdh.accountingDocument
                WHERE bdh.accountingDocument IS NOT NULL
                    AND je.accountingDocument IS NULL
            """,
            "journal_entry_missing_payment": """
                SELECT COUNT(*) AS c
                FROM journal_entry_items je
                LEFT JOIN payments p
                    ON p.accountingDocument = je.clearingAccountingDocument
                WHERE je.clearingAccountingDocument IS NOT NULL
                    AND p.accountingDocument IS NULL
            """,
        }

        orphan_counts = {
            name: int(conn.execute(sql).fetchone()["c"])
            for name, sql in checks.items()
        }

        total_orphans = sum(orphan_counts.values())
        return {
            "orphan_counts": orphan_counts,
            "total_orphan_links": total_orphans,
        }


def get_subgraph(seed_node_ids: list[str], hops: int = 1, max_nodes: int = 200) -> dict:
    """Return a focused subgraph around seed nodes within N hops."""
    G = get_graph()
    if not seed_node_ids:
        return {
            "nodes": [],
            "edges": [],
            "stats": {
                "seed_count": 0,
                "resolved_seed_count": 0,
                "hops": hops,
                "max_nodes": max_nodes,
                "total_nodes": 0,
                "total_edges": 0,
                "trimmed": False,
            },
        }

    valid_seeds = [nid for nid in seed_node_ids if G.has_node(nid)]
    if not valid_seeds:
        return {
            "nodes": [],
            "edges": [],
            "stats": {
                "seed_count": len(seed_node_ids),
                "resolved_seed_count": 0,
                "hops": hops,
                "max_nodes": max_nodes,
                "total_nodes": 0,
                "total_edges": 0,
                "trimmed": False,
            },
        }

    undirected = G.to_undirected()
    distance_map: dict[str, int] = {}

    for seed in valid_seeds:
        lengths = nx.single_source_shortest_path_length(
            undirected,
            seed,
            cutoff=max(0, hops),
        )
        for node_id, dist in lengths.items():
            existing = distance_map.get(node_id)
            if existing is None or dist < existing:
                distance_map[node_id] = dist

    ordered_nodes = sorted(distance_map.items(), key=lambda x: (x[1], x[0]))
    trimmed = len(ordered_nodes) > max_nodes
    selected_ids = {node_id for node_id, _ in ordered_nodes[:max_nodes]}

    nodes = [
        {
            "id": node_id,
            "type": G.nodes[node_id].get("type", "Unknown"),
            "label": G.nodes[node_id].get("label", node_id),
        }
        for node_id in selected_ids
    ]

    edges = []
    for src, tgt, data in G.edges(data=True):
        if src in selected_ids and tgt in selected_ids:
            edges.append(
                {
                    "source": src,
                    "target": tgt,
                    "relationship": data.get("relationship", "RELATED"),
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "seed_count": len(seed_node_ids),
            "resolved_seed_count": len(valid_seeds),
            "hops": hops,
            "max_nodes": max_nodes,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "trimmed": trimmed,
        },
    }
