import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

try:
    from backend.app.models.graph_schema import (
        Customer,
        SalesOrder,
        SalesOrderItem,
        Delivery,
        DeliveryItem,
        Invoice,
        Payment,
        Product,
        JournalEntry,
        Node,
    )
except ModuleNotFoundError:
    from app.models.graph_schema import (
        Customer,
        SalesOrder,
        SalesOrderItem,
        Delivery,
        DeliveryItem,
        Invoice,
        Payment,
        Product,
        JournalEntry,
        Node,
    )

T = TypeVar("T", bound=Node)

SAP_DATE_REGEX = re.compile(r"^\/Date\((\d+)\)\/$")
YMD_DATE_REGEX = re.compile(r"^(\d{4})(\d{2})(\d{2})$")

def sanitize_date(val: Any) -> Optional[str]:
    """Convert SAP /Date(ms)/ or YYYYMMDD to ISO-8601 string."""
    if not val:
        return None
    if isinstance(val, (int, float)):
        # Assume ms timestamp if it's huge, otherwise s
        ts = float(val) / 1000.0 if val > 1e11 else float(val)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    
    val_str = str(val).strip()
    if not val_str:
        return None
        
    # Check /Date(ms)/
    match = SAP_DATE_REGEX.match(val_str)
    if match:
        ms = int(match.group(1))
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()
        
    # Check YYYYMMDD
    match_ymd = YMD_DATE_REGEX.match(val_str)
    if match_ymd:
        y, m, d = match_ymd.groups()
        return f"{y}-{m}-{d}T00:00:00+00:00"
        
    # Try generic parse (already ISO or YYYY-MM-DD)
    try:
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass
        
    return val_str  # Return original if unable to parse

def sanitize_number(val: Any) -> Any:
    """Coerce string numbers to float/int optimally, handle nulls."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
        
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str # Return string if non-numeric

def clean_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply sanitizations to all applicable fields in a record."""
    cleaned = {}
    for k, v in raw.items():
        if "Date" in k or k in ["creationTime", "lastChangeDateTime"]:
            cleaned[k] = sanitize_date(v)
        elif "Amount" in k or "Quantity" in k or "Weight" in k:
            cleaned[k] = sanitize_number(v)
        else:
            # General string cleanup and null coercion
            if isinstance(v, str):
                v_strip = v.strip()
                cleaned[k] = v_strip if v_strip else None
            else:
                cleaned[k] = v
    return cleaned

def map_and_validate(raw: Dict[str, Any], model_cls: Type[T], id_prefix: str, id_keys: list[str]) -> Dict[str, Any]:
    """
    Cleans the raw record, computes the canonical id using the provided prefix and keys,
    validates it against the Pydantic schema, and returns the strictly-typed dict payload.
    """
    cleaned = clean_record(raw)
    
    # Construct canonical ID and prevent forging wildcard IDs
    id_parts = []
    for k in id_keys:
        val = str(cleaned.get(k, "")).strip()
        if not val or val == "None":
            raise ValueError(f"Missing required primary key '{k}' for {model_cls.__name__}")
        id_parts.append(val)
        
    canonical_id = f"{id_prefix}{'-'.join(id_parts)}"
    
    # Insert ID for Pydantic schema validation
    cleaned["id"] = canonical_id
    
    # Validate against Schema Contracts (T2)
    # Ensure it doesn't drop untyped raw data needed for downstream JSON storage
    validated_model = model_cls(**cleaned)
    return {**cleaned, **validated_model.model_dump(by_alias=True, exclude_none=False)}

def normalize_customer(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, Customer, "Customer:", ["businessPartner"])

def normalize_sales_order(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, SalesOrder, "SalesOrder:", ["salesOrder"])

def normalize_sales_order_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, SalesOrderItem, "SalesOrderItem:", ["salesOrder", "salesOrderItem"])

def normalize_delivery(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, Delivery, "Delivery:", ["deliveryDocument"])

def normalize_delivery_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, DeliveryItem, "DeliveryItem:", ["deliveryDocument", "deliveryDocumentItem"])

def normalize_invoice(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, Invoice, "BillingDocument:", ["billingDocument"])

def normalize_payment(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, Payment, "Payment:", ["accountingDocument"])

def normalize_product(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, Product, "Product:", ["product"])

def normalize_journal_entry(raw: Dict[str, Any]) -> Dict[str, Any]:
    return map_and_validate(raw, JournalEntry, "JournalEntry:", ["accountingDocument"])

