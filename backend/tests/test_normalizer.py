import pytest

from backend.ingestion.normalizer import (
    clean_record,
    normalize_customer,
    normalize_sales_order_item,
    sanitize_date,
    sanitize_number,
)


def test_sanitize_date() -> None:
    # SAP Format
    assert sanitize_date("/Date(1615420800000)/") == "2021-03-11T00:00:00+00:00"
    # Basic string ISO
    assert sanitize_date("2021-03-11T00:00:00Z") == "2021-03-11T00:00:00+00:00"
    assert sanitize_date("2021-03-11") == "2021-03-11T00:00:00+00:00"
    # YYYYMMDD SAP flat format
    assert sanitize_date("20210311") == "2021-03-11T00:00:00+00:00"
    # Nulls / empies
    assert sanitize_date("") is None
    assert sanitize_date(None) is None
    # Unparseable fallback
    assert sanitize_date("invalid_date") == "invalid_date"

def test_sanitize_number() -> None:
    assert sanitize_number("1.50") == 1.5
    assert sanitize_number("42") == 42
    assert sanitize_number("") is None
    assert sanitize_number("   ") is None
    assert sanitize_number("abc") == "abc" # Fallback

def test_clean_record() -> None:
    raw = {
        "creationDate": "/Date(1615420800000)/",
        "netAmount": "100.25",
        "description": "  hello  ",
        "emptyString": "   ",
        "skipField": 10
    }
    cleaned = clean_record(raw)
    assert cleaned["creationDate"] == "2021-03-11T00:00:00+00:00"
    assert cleaned["netAmount"] == 100.25
    assert cleaned["description"] == "hello"
    assert cleaned["emptyString"] is None
    assert cleaned["skipField"] == 10

def test_normalize_payload_schema_enforcement() -> None:
    raw_customer = {
        "businessPartner": "101000",
        "businessPartnerName": "Acme Corp"
    }
    result = normalize_customer(raw_customer)

    # Assert specific prefix enforced ID is in payload
    assert result["id"] == "Customer:101000"
    assert result["businessPartnerName"] == "Acme Corp"

    # Compound keys
    raw_item = {
        "salesOrder": "SO99",
        "salesOrderItem": "0010"
    }
    res_item = normalize_sales_order_item(raw_item)
    assert res_item["id"] == "SalesOrderItem:SO99-0010"

def test_validation_failure_on_missing_or_bad_id() -> None:
    # Test missing primary key rejection
    raw_customer_missing = {
        "businessPartnerName": "Acme Corp"
        # Missing 'businessPartner'
    }
    with pytest.raises(ValueError, match="Missing required primary key 'businessPartner' for Customer"):
        normalize_customer(raw_customer_missing)

    # Test empty string primary key rejection
    raw_item_empty = {
        "salesOrder": "SO99",
        "salesOrderItem": "   " # Whitespace only
    }
    with pytest.raises(ValueError, match="Missing required primary key 'salesOrderItem' for SalesOrderItem"):
        normalize_sales_order_item(raw_item_empty)
