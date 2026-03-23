"""
Data ingestion pipeline: reads JSONL files from the raw dataset
and loads them into SQLite tables.
"""

import json
import os
from pathlib import Path
from typing import Any, Callable

try:
    from .database import get_db, init_schema, DB_PATH
    from .ingestion.normalizer import (
        normalize_customer,
        normalize_delivery,
        normalize_delivery_item,
        normalize_invoice,
        normalize_journal_entry,
        normalize_payment,
        normalize_product,
        normalize_sales_order,
        normalize_sales_order_item,
    )
except ImportError:
    from database import get_db, init_schema, DB_PATH
    from ingestion.normalizer import (
        normalize_customer,
        normalize_delivery,
        normalize_delivery_item,
        normalize_invoice,
        normalize_journal_entry,
        normalize_payment,
        normalize_product,
        normalize_sales_order,
        normalize_sales_order_item,
    )

RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "sap-o2c-data"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

# Mapping: directory name -> (table name, column mapping)
# column mapping: source_field -> db_column (None = skip)
ENTITY_MAP = {
    "sales_order_headers": {
        "table": "sales_order_headers",
        "columns": {
            "salesOrder": "salesOrder",
            "salesOrderType": "salesOrderType",
            "salesOrganization": "salesOrganization",
            "distributionChannel": "distributionChannel",
            "organizationDivision": "organizationDivision",
            "soldToParty": "soldToParty",
            "creationDate": "creationDate",
            "totalNetAmount": "totalNetAmount",
            "overallDeliveryStatus": "overallDeliveryStatus",
            "transactionCurrency": "transactionCurrency",
            "requestedDeliveryDate": "requestedDeliveryDate",
            "customerPaymentTerms": "customerPaymentTerms",
        },
    },
    "sales_order_items": {
        "table": "sales_order_items",
        "columns": {
            "salesOrder": "salesOrder",
            "salesOrderItem": "salesOrderItem",
            "salesOrderItemCategory": "salesOrderItemCategory",
            "material": "material",
            "requestedQuantity": "requestedQuantity",
            "requestedQuantityUnit": "requestedQuantityUnit",
            "netAmount": "netAmount",
            "transactionCurrency": "transactionCurrency",
            "materialGroup": "materialGroup",
            "productionPlant": "productionPlant",
            "storageLocation": "storageLocation",
        },
    },
    "sales_order_schedule_lines": {
        "table": "sales_order_schedule_lines",
        "columns": {
            "salesOrder": "salesOrder",
            "salesOrderItem": "salesOrderItem",
            "scheduleLine": "scheduleLine",
            "confirmedDeliveryDate": "confirmedDeliveryDate",
            "orderQuantityUnit": "orderQuantityUnit",
            "confdOrderQtyByMatlAvailCheck": "confdOrderQtyByMatlAvailCheck",
        },
    },
    "outbound_delivery_headers": {
        "table": "outbound_delivery_headers",
        "columns": {
            "deliveryDocument": "deliveryDocument",
            "actualGoodsMovementDate": "actualGoodsMovementDate",
            "creationDate": "creationDate",
            "deliveryBlockReason": "deliveryBlockReason",
            "overallGoodsMovementStatus": "overallGoodsMovementStatus",
            "overallPickingStatus": "overallPickingStatus",
            "shippingPoint": "shippingPoint",
        },
    },
    "outbound_delivery_items": {
        "table": "outbound_delivery_items",
        "columns": {
            "deliveryDocument": "deliveryDocument",
            "deliveryDocumentItem": "deliveryDocumentItem",
            "actualDeliveryQuantity": "actualDeliveryQuantity",
            "plant": "plant",
            "referenceSdDocument": "referenceSdDocument",
            "referenceSdDocumentItem": "referenceSdDocumentItem",
            "storageLocation": "storageLocation",
        },
    },
    "billing_document_headers": {
        "table": "billing_document_headers",
        "columns": {
            "billingDocument": "billingDocument",
            "billingDocumentType": "billingDocumentType",
            "creationDate": "creationDate",
            "billingDocumentDate": "billingDocumentDate",
            "billingDocumentIsCancelled": "billingDocumentIsCancelled",
            "cancelledBillingDocument": "cancelledBillingDocument",
            "totalNetAmount": "totalNetAmount",
            "transactionCurrency": "transactionCurrency",
            "companyCode": "companyCode",
            "fiscalYear": "fiscalYear",
            "accountingDocument": "accountingDocument",
            "soldToParty": "soldToParty",
        },
    },
    "billing_document_items": {
        "table": "billing_document_items",
        "columns": {
            "billingDocument": "billingDocument",
            "billingDocumentItem": "billingDocumentItem",
            "material": "material",
            "billingQuantity": "billingQuantity",
            "billingQuantityUnit": "billingQuantityUnit",
            "netAmount": "netAmount",
            "transactionCurrency": "transactionCurrency",
            "referenceSdDocument": "referenceSdDocument",
            "referenceSdDocumentItem": "referenceSdDocumentItem",
        },
    },
    "billing_document_cancellations": {
        "table": "billing_document_cancellations",
        "columns": {
            "billingDocument": "billingDocument",
            "billingDocumentType": "billingDocumentType",
            "creationDate": "creationDate",
            "billingDocumentDate": "billingDocumentDate",
            "billingDocumentIsCancelled": "billingDocumentIsCancelled",
            "cancelledBillingDocument": "cancelledBillingDocument",
            "totalNetAmount": "totalNetAmount",
            "transactionCurrency": "transactionCurrency",
            "companyCode": "companyCode",
            "fiscalYear": "fiscalYear",
            "accountingDocument": "accountingDocument",
            "soldToParty": "soldToParty",
        },
    },
    "journal_entry_items_accounts_receivable": {
        "table": "journal_entry_items",
        "columns": {
            "companyCode": "companyCode",
            "fiscalYear": "fiscalYear",
            "accountingDocument": "accountingDocument",
            "accountingDocumentItem": "accountingDocumentItem",
            "glAccount": "glAccount",
            "referenceDocument": "referenceDocument",
            "transactionCurrency": "transactionCurrency",
            "amountInTransactionCurrency": "amountInTransactionCurrency",
            "postingDate": "postingDate",
            "documentDate": "documentDate",
            "accountingDocumentType": "accountingDocumentType",
            "customer": "customer",
            "financialAccountType": "financialAccountType",
            "clearingDate": "clearingDate",
            "clearingAccountingDocument": "clearingAccountingDocument",
            "profitCenter": "profitCenter",
        },
    },
    "payments_accounts_receivable": {
        "table": "payments",
        "columns": {
            "companyCode": "companyCode",
            "fiscalYear": "fiscalYear",
            "accountingDocument": "accountingDocument",
            "accountingDocumentItem": "accountingDocumentItem",
            "clearingDate": "clearingDate",
            "clearingAccountingDocument": "clearingAccountingDocument",
            "amountInTransactionCurrency": "amountInTransactionCurrency",
            "transactionCurrency": "transactionCurrency",
            "customer": "customer",
            "invoiceReference": "invoiceReference",
            "postingDate": "postingDate",
            "documentDate": "documentDate",
            "glAccount": "glAccount",
            "financialAccountType": "financialAccountType",
            "profitCenter": "profitCenter",
        },
    },
    "business_partners": {
        "table": "business_partners",
        "columns": {
            "businessPartner": "businessPartner",
            "customer": "customer",
            "businessPartnerCategory": "businessPartnerCategory",
            "businessPartnerFullName": "businessPartnerFullName",
            "businessPartnerName": "businessPartnerName",
            "creationDate": "creationDate",
            "organizationBpName1": "organizationBpName1",
        },
    },
    "business_partner_addresses": {
        "table": "business_partner_addresses",
        "columns": {
            "businessPartner": "businessPartner",
            "cityName": "cityName",
            "country": "country",
            "district": "district",
            "postalCode": "postalCode",
            "region": "region",
            "streetName": "streetName",
            "houseNumber": "houseNumber",
        },
    },
    "customer_company_assignments": {
        "table": "customer_company_assignments",
        "columns": {
            "customer": "customer",
            "companyCode": "companyCode",
            "reconciliationAccount": "reconciliationAccount",
            "customerAccountGroup": "customerAccountGroup",
            "paymentTerms": "paymentTerms",
        },
    },
    "customer_sales_area_assignments": {
        "table": "customer_sales_area_assignments",
        "columns": {
            "customer": "customer",
            "salesOrganization": "salesOrganization",
            "distributionChannel": "distributionChannel",
            "division": "division",
            "currency": "currency",
            "customerPaymentTerms": "customerPaymentTerms",
            "incotermsClassification": "incotermsClassification",
            "incotermsLocation1": "incotermsLocation1",
            "shippingCondition": "shippingCondition",
        },
    },
    "products": {
        "table": "products",
        "columns": {
            "product": "product",
            "productType": "productType",
            "creationDate": "creationDate",
            "grossWeight": "grossWeight",
            "weightUnit": "weightUnit",
            "netWeight": "netWeight",
            "productGroup": "productGroup",
            "baseUnit": "baseUnit",
            "division": "division",
        },
    },
    "product_descriptions": {
        "table": "product_descriptions",
        "columns": {
            "product": "product",
            "language": "language",
            "productDescription": "productDescription",
        },
    },
    "plants": {
        "table": "plants",
        "columns": {
            "plant": "plant",
            "plantName": "plantName",
            "valuationArea": "valuationArea",
            "salesOrganization": "salesOrganization",
            "distributionChannel": "distributionChannel",
            "division": "division",
            "language": "language",
        },
    },
}

# Optional schema-backed normalization mapping (T3).
NORMALIZER_MAP: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "business_partners": normalize_customer,
    "sales_order_headers": normalize_sales_order,
    "sales_order_items": normalize_sales_order_item,
    "outbound_delivery_headers": normalize_delivery,
    "outbound_delivery_items": normalize_delivery_item,
    "billing_document_headers": normalize_invoice,
    "journal_entry_items_accounts_receivable": normalize_journal_entry,
    "payments_accounts_receivable": normalize_payment,
    "products": normalize_product,
}


def _parse_value(val):
    """Normalize a JSON value for SQLite insertion."""
    if val is None:
        return None
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, dict):
        return json.dumps(val)
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        # Try numeric conversion
        try:
            return float(val) if "." in val else val
        except ValueError:
            return val
    return val


def load_entity(
    entity_dir: str,
    table: str,
    columns: dict[str, str],
    rejects: list[dict[str, Any]],
) -> dict[str, int]:
    """Load all JSONL files from an entity directory into a SQLite table."""
    dir_path = RAW_DATA_DIR / entity_dir
    if not dir_path.exists():
        print(f"  ⚠ Directory not found: {entity_dir}")
        return {"loaded": 0, "errors": 0, "rejected": 0}

    jsonl_files = sorted(dir_path.glob("*.jsonl"))
    if not jsonl_files:
        print(f"  ⚠ No JSONL files in: {entity_dir}")
        return {"loaded": 0, "errors": 0, "rejected": 0}

    db_columns = list(columns.values())
    placeholders = ", ".join(["?"] * len(db_columns))
    col_names = ", ".join(db_columns)
    insert_sql = (
        f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    )

    total = 0
    errors = 0
    rejected = 0
    normalizer = NORMALIZER_MAP.get(entity_dir)

    with get_db() as conn:
        for jf in jsonl_files:
            with open(jf, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if normalizer is not None:
                            try:
                                record = normalizer(record)
                            except Exception as norm_error:
                                rejected += 1
                                rejects.append(
                                    {
                                        "entity": entity_dir,
                                        "file": jf.name,
                                        "line": line_num,
                                        "reason": f"normalization_failed: {norm_error}",
                                    }
                                )
                                continue

                        values = []
                        for src_field, db_col in columns.items():
                            raw_val = record.get(src_field)
                            values.append(_parse_value(raw_val))
                        conn.execute(insert_sql, values)
                        total += 1
                    except Exception as e:
                        errors += 1
                        rejects.append(
                            {
                                "entity": entity_dir,
                                "file": jf.name,
                                "line": line_num,
                                "reason": f"ingestion_failed: {e}",
                            }
                        )
                        if errors <= 3:
                            print(f"  ⚠ Error in {jf.name}:{line_num}: {e}")

    return {"loaded": total, "errors": errors, "rejected": rejected}


def run_ingestion():
    """Execute full ingestion pipeline."""
    print("=" * 60)
    print("SAP O2C Data Ingestion Pipeline")
    print("=" * 60)

    # Remove existing DB for clean load
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"✓ Removed existing database: {DB_PATH}")

    # Create schema
    init_schema()
    print("✓ Database schema created")

    # Load each entity
    total_records = 0
    total_errors = 0
    total_rejected = 0
    rejects: list[dict[str, Any]] = []
    entity_stats: dict[str, dict[str, int | str]] = {}

    for entity_dir, config in ENTITY_MAP.items():
        result = load_entity(
            entity_dir, config["table"], config["columns"], rejects
        )
        total_records += result["loaded"]
        total_errors += result["errors"]
        total_rejected += result["rejected"]
        entity_stats[entity_dir] = {
            "table": config["table"],
            "loaded": result["loaded"],
            "errors": result["errors"],
            "rejected": result["rejected"],
        }
        print(
            f"  ✓ {config['table']}: {result['loaded']} records "
            f"(errors={result['errors']}, rejected={result['rejected']})"
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "database": str(DB_PATH),
        "total_loaded": total_records,
        "total_errors": total_errors,
        "total_rejected": total_rejected,
        "normalized_entities": sorted(NORMALIZER_MAP.keys()),
        "entities": entity_stats,
    }

    summary_path = PROCESSED_DIR / "ingestion_summary.json"
    rejects_path = PROCESSED_DIR / "normalization_rejects.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rejects_path.write_text(json.dumps(rejects, indent=2), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Total records loaded: {total_records}")
    print(f"Total errors: {total_errors}")
    print(f"Total rejected: {total_rejected}")
    print(f"Database: {DB_PATH}")
    print(f"Summary: {summary_path}")
    print(f"Reject report: {rejects_path}")
    print(f"{'=' * 60}")

    return summary


if __name__ == "__main__":
    run_ingestion()
