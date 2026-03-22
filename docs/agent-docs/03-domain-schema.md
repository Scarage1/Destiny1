# 03 - Domain Graph Schema v1

## Node types
- Customer
- Address
- SalesOrder
- SalesOrderItem
- Delivery
- DeliveryItem
- Invoice
- Payment
- Product
- JournalEntry (optional, only if dataset contains it)

## Relationship types
- (Customer)-[:PLACED]->(SalesOrder)
- (SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
- (SalesOrderItem)-[:REFERS_TO]->(Product)
- (SalesOrder)-[:FULFILLED_BY]->(Delivery)
- (Delivery)-[:HAS_ITEM]->(DeliveryItem)
- (Delivery)-[:BILLED_BY]->(Invoice)
- (Invoice)-[:SETTLED_BY]->(Payment)
- (Invoice)-[:POSTED_TO]->(JournalEntry)

## Key constraints
- Every core entity must have deterministic canonical id.
- Relationship edges must use canonical source/target ids.
- Loader must be idempotent (reruns should not duplicate entities/edges).

## Broken-flow definitions
- Delivered but not billed:
  - SalesOrder with Delivery path but no Invoice path
- Billed without delivery:
  - Invoice linked to SalesOrder without corresponding Delivery path

## Example business queries to support
1. Products with highest billing-document linkage
2. Full flow trace for given billing document
3. Broken/incomplete sales flow identification
