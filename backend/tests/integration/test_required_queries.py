from __future__ import annotations

from backend.database import execute_readonly_query
from backend.ingest import run_ingestion


def setup_module() -> None:
    """Ensure database is freshly loaded for integration query checks."""
    run_ingestion()


def test_top_products_by_billing_document_count_query() -> None:
    rows = execute_readonly_query(
        """
        SELECT
            bdi.material AS product,
            COUNT(DISTINCT bdi.billingDocument) AS billing_document_count
        FROM billing_document_items bdi
        GROUP BY bdi.material
        ORDER BY billing_document_count DESC, product ASC
        LIMIT 10
        """
    )

    assert len(rows) > 0
    assert all(row["billing_document_count"] >= 1 for row in rows)

    counts = [row["billing_document_count"] for row in rows]
    assert counts == sorted(counts, reverse=True)


def test_full_billing_flow_trace_query() -> None:
    rows = execute_readonly_query(
        """
        SELECT
            bdh.billingDocument,
            odi.referenceSdDocument AS salesOrder,
            bdi.referenceSdDocument AS deliveryDocument,
            bdh.accountingDocument AS journalEntry,
            p.accountingDocument AS paymentDocument
        FROM billing_document_headers bdh
        JOIN billing_document_items bdi
          ON bdi.billingDocument = bdh.billingDocument
        LEFT JOIN outbound_delivery_items odi
          ON odi.deliveryDocument = bdi.referenceSdDocument
        LEFT JOIN journal_entry_items je
          ON je.accountingDocument = bdh.accountingDocument
        LEFT JOIN payments p
          ON p.accountingDocument = je.clearingAccountingDocument
        ORDER BY bdh.billingDocument
        LIMIT 50
        """
    )

    assert len(rows) > 0
    assert all(row["billingDocument"] is not None for row in rows)

    # At least some traces should include upstream delivery or order links.
    assert any(row["deliveryDocument"] is not None for row in rows)
    assert any(row["salesOrder"] is not None for row in rows)


def test_broken_or_incomplete_flow_detection_query() -> None:
    delivered_not_billed = execute_readonly_query(
        """
        SELECT DISTINCT odi.referenceSdDocument AS salesOrder
        FROM outbound_delivery_items odi
        LEFT JOIN billing_document_items bdi
          ON bdi.referenceSdDocument = odi.deliveryDocument
        WHERE odi.referenceSdDocument IS NOT NULL
          AND bdi.billingDocument IS NULL
        ORDER BY salesOrder
        LIMIT 100
        """
    )

    billed_without_delivery = execute_readonly_query(
        """
        SELECT DISTINCT bdi.referenceSdDocument AS deliveryDocument
        FROM billing_document_items bdi
        LEFT JOIN outbound_delivery_headers odh
          ON odh.deliveryDocument = bdi.referenceSdDocument
        WHERE bdi.referenceSdDocument IS NOT NULL
          AND odh.deliveryDocument IS NULL
        ORDER BY deliveryDocument
        LIMIT 100
        """
    )

    assert isinstance(delivered_not_billed, list)
    assert isinstance(billed_without_delivery, list)
    assert all("salesOrder" in row for row in delivered_not_billed)
    assert all("deliveryDocument" in row for row in billed_without_delivery)
