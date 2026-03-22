from typing import NewType
from pydantic import BaseModel, Field, model_validator


# -----------------------------------------------------------------------------
# Strict Type Definitions (for mypy static analysis)
# -----------------------------------------------------------------------------
CustomerId = NewType("CustomerId", str)
AddressId = NewType("AddressId", str)
SalesOrderId = NewType("SalesOrderId", str)
SalesOrderItemId = NewType("SalesOrderItemId", str)
DeliveryId = NewType("DeliveryId", str)
DeliveryItemId = NewType("DeliveryItemId", str)
InvoiceId = NewType("InvoiceId", str)
PaymentId = NewType("PaymentId", str)
ProductId = NewType("ProductId", str)
JournalEntryId = NewType("JournalEntryId", str)


# -----------------------------------------------------------------------------
# Base Models
# -----------------------------------------------------------------------------
class Node(BaseModel):
    """Generic Node base model."""

    id: str = Field(..., description="Canonical ID of the entity")


class Edge(BaseModel):
    """Generic Edge base model."""

    source_id: str = Field(..., description="Canonical ID of the source node")
    target_id: str = Field(..., description="Canonical ID of the target node")


# -----------------------------------------------------------------------------
# Domain Entities (Nodes)
# -----------------------------------------------------------------------------
class Customer(Node):
    id: CustomerId = Field(pattern=r"^Customer:")


class Address(Node):
    id: AddressId = Field(pattern=r"^Address:")


class SalesOrder(Node):
    id: SalesOrderId = Field(pattern=r"^SalesOrder:")


class SalesOrderItem(Node):
    id: SalesOrderItemId = Field(pattern=r"^SalesOrderItem:")


class Delivery(Node):
    id: DeliveryId = Field(pattern=r"^Delivery:")


class DeliveryItem(Node):
    id: DeliveryItemId = Field(pattern=r"^DeliveryItem:")


class Invoice(Node):
    id: InvoiceId = Field(pattern=r"^BillingDocument:")


class Payment(Node):
    id: PaymentId = Field(pattern=r"^Payment:")


class Product(Node):
    id: ProductId = Field(pattern=r"^Product:")


class JournalEntry(Node):
    id: JournalEntryId = Field(pattern=r"^JournalEntry:")


# -----------------------------------------------------------------------------
# Domain Relationships (Edges)
# -----------------------------------------------------------------------------
class Placed(Edge):
    """(Customer)-[:PLACED]->(SalesOrder)"""

    source_id: CustomerId = Field(pattern=r"^Customer:")
    target_id: SalesOrderId = Field(pattern=r"^SalesOrder:")


class HasItem(Edge):
    """
    (SalesOrder)-[:HAS_ITEM]->(SalesOrderItem) OR
    (Delivery)-[:HAS_ITEM]->(DeliveryItem)
    """

    source_id: str = Field(pattern=r"^(SalesOrder|Delivery):")
    target_id: str = Field(pattern=r"^(SalesOrderItem|DeliveryItem):")

    @model_validator(mode="after")
    def validate_pairs(self) -> "HasItem":
        # Enforce strict pairing rules
        src = self.source_id
        tgt = self.target_id
        if src.startswith("SalesOrder:") and not tgt.startswith(
            "SalesOrderItem:"
        ):
            raise ValueError("SalesOrder source must target SalesOrderItem")
        if src.startswith("Delivery:") and not tgt.startswith("DeliveryItem:"):
            raise ValueError("Delivery source must target DeliveryItem")
        return self


class RefersTo(Edge):
    """(SalesOrderItem)-[:REFERS_TO]->(Product)"""

    source_id: SalesOrderItemId = Field(pattern=r"^SalesOrderItem:")
    target_id: ProductId = Field(pattern=r"^Product:")


class FulfilledBy(Edge):
    """(SalesOrder)-[:FULFILLED_BY]->(Delivery)"""

    source_id: SalesOrderId = Field(pattern=r"^SalesOrder:")
    target_id: DeliveryId = Field(pattern=r"^Delivery:")


class BilledBy(Edge):
    """(Delivery)-[:BILLED_BY]->(Invoice)"""

    source_id: DeliveryId = Field(pattern=r"^Delivery:")
    target_id: InvoiceId = Field(pattern=r"^BillingDocument:")


class SettledBy(Edge):
    """(Invoice)-[:SETTLED_BY]->(Payment)"""

    source_id: InvoiceId = Field(pattern=r"^BillingDocument:")
    target_id: PaymentId = Field(pattern=r"^Payment:")


class PostedTo(Edge):
    """(Invoice)-[:POSTED_TO]->(JournalEntry)"""

    source_id: InvoiceId = Field(pattern=r"^BillingDocument:")
    target_id: JournalEntryId = Field(pattern=r"^JournalEntry:")
