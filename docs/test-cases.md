# Required Query Test Cases

This document tracks assignment-critical integration tests implemented in [backend/tests/integration/test_required_queries.py](backend/tests/integration/test_required_queries.py).

## Query A
**Question class:** Which products are associated with the highest number of billing documents?

**Validation:**
- Query returns non-empty rows.
- `billing_document_count` is positive.
- Ordering is descending by count.

## Query B
**Question class:** Trace the full flow of a billing document (Sales Order -> Delivery -> Billing -> Journal Entry -> Payment).

**Validation:**
- Query returns non-empty rows.
- Billing document is always present.
- At least some rows include linked delivery and sales order values.

## Query C
**Question class:** Identify broken/incomplete flows.

Covered patterns:
- Delivered but not billed.
- Billed without delivery.

**Validation:**
- Both anomaly queries execute successfully.
- Result rows have expected identifier keys.
