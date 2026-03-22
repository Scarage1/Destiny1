import pytest
from pydantic import ValidationError

from backend.app.models.graph_schema import (
    Customer,
    Placed,
    FulfilledBy,
    HasItem,
    Edge,
    CustomerId,
    SalesOrderId,
    DeliveryId,
)


def test_node_instantiation_valid() -> None:
    cust = Customer(id=CustomerId("Customer:123"))
    assert cust.id == "Customer:123"


def test_node_instantiation_invalid_prefix() -> None:
    with pytest.raises(ValidationError):
        # Purposely bypass MyPy's strict checks using casting
        # to test Pydantic's runtime regex constraints
        Customer(id=CustomerId("Delivery:123"))


def test_edge_instantiation_valid() -> None:
    placed = Placed(
        source_id=CustomerId("Customer:123"),
        target_id=SalesOrderId("SalesOrder:456"),
    )
    assert placed.source_id == "Customer:123"
    assert placed.target_id == "SalesOrder:456"


def test_prevent_customer_fulfilled_by_delivery() -> None:
    # Constraints requirement: preventing a Customer
    # from being [:FULFILLED_BY] a Delivery
    with pytest.raises(ValidationError):
        FulfilledBy(
            source_id=SalesOrderId("Customer:123"),
            target_id=DeliveryId("Delivery:456"),
        )


def test_has_item_polymorphic_valid() -> None:
    # SalesOrder -> SalesOrderItem
    edge1 = HasItem(source_id="SalesOrder:1", target_id="SalesOrderItem:1-1")
    assert edge1.source_id == "SalesOrder:1"

    # Delivery -> DeliveryItem
    edge2 = HasItem(source_id="Delivery:1", target_id="DeliveryItem:1-1")
    assert edge2.source_id == "Delivery:1"


def test_has_item_polymorphic_invalid_pairing() -> None:
    # SalesOrder -> DeliveryItem (Mismatch)
    with pytest.raises(
        ValidationError, match="SalesOrder source must target SalesOrderItem"
    ):
        HasItem(source_id="SalesOrder:1", target_id="DeliveryItem:1-1")

    # Delivery -> SalesOrderItem (Mismatch)
    with pytest.raises(
        ValidationError, match="Delivery source must target DeliveryItem"
    ):
        HasItem(source_id="Delivery:1", target_id="SalesOrderItem:1-1")


def test_generic_edge_requires_canonical_ids() -> None:
    with pytest.raises(ValidationError):
        # Missing target_id
        Edge(source_id="Customer:1")  # type: ignore
