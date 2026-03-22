"""
SQLite database manager for the SAP O2C dataset.
Handles schema creation, connection management, and query execution.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "o2c.db"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_readonly_query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a read-only SQL query and return results as list of dicts."""
    # Safety: reject write operations
    sql_upper = sql.strip().upper()
    write_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE", "MERGE"]
    for kw in write_keywords:
        if sql_upper.startswith(kw):
            raise ValueError(f"Write operations are not allowed: {kw}")

    with get_db() as conn:
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def get_schema_description() -> str:
    """Generate a human-readable schema description for LLM prompting."""
    with get_db() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        schema_parts = []
        for table in tables:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            col_descs = [f"  {col[1]} ({col[2]})" for col in columns]

            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]

            schema_parts.append(f"Table: {table} ({count} rows)\n" + "\n".join(col_descs))

        return "\n\n".join(schema_parts)


# Schema definitions for all O2C tables
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sales_order_headers (
    salesOrder TEXT PRIMARY KEY,
    salesOrderType TEXT,
    salesOrganization TEXT,
    distributionChannel TEXT,
    organizationDivision TEXT,
    soldToParty TEXT,
    creationDate TEXT,
    totalNetAmount REAL,
    overallDeliveryStatus TEXT,
    transactionCurrency TEXT,
    requestedDeliveryDate TEXT,
    customerPaymentTerms TEXT
);

CREATE TABLE IF NOT EXISTS sales_order_items (
    salesOrder TEXT,
    salesOrderItem TEXT,
    salesOrderItemCategory TEXT,
    material TEXT,
    requestedQuantity REAL,
    requestedQuantityUnit TEXT,
    netAmount REAL,
    transactionCurrency TEXT,
    materialGroup TEXT,
    productionPlant TEXT,
    storageLocation TEXT,
    PRIMARY KEY (salesOrder, salesOrderItem)
);

CREATE TABLE IF NOT EXISTS sales_order_schedule_lines (
    salesOrder TEXT,
    salesOrderItem TEXT,
    scheduleLine TEXT,
    confirmedDeliveryDate TEXT,
    orderQuantityUnit TEXT,
    confdOrderQtyByMatlAvailCheck REAL,
    PRIMARY KEY (salesOrder, salesOrderItem, scheduleLine)
);

CREATE TABLE IF NOT EXISTS outbound_delivery_headers (
    deliveryDocument TEXT PRIMARY KEY,
    actualGoodsMovementDate TEXT,
    creationDate TEXT,
    deliveryBlockReason TEXT,
    overallGoodsMovementStatus TEXT,
    overallPickingStatus TEXT,
    shippingPoint TEXT
);

CREATE TABLE IF NOT EXISTS outbound_delivery_items (
    deliveryDocument TEXT,
    deliveryDocumentItem TEXT,
    actualDeliveryQuantity REAL,
    plant TEXT,
    referenceSdDocument TEXT,
    referenceSdDocumentItem TEXT,
    storageLocation TEXT,
    PRIMARY KEY (deliveryDocument, deliveryDocumentItem)
);

CREATE TABLE IF NOT EXISTS billing_document_headers (
    billingDocument TEXT PRIMARY KEY,
    billingDocumentType TEXT,
    creationDate TEXT,
    billingDocumentDate TEXT,
    billingDocumentIsCancelled INTEGER,
    cancelledBillingDocument TEXT,
    totalNetAmount REAL,
    transactionCurrency TEXT,
    companyCode TEXT,
    fiscalYear TEXT,
    accountingDocument TEXT,
    soldToParty TEXT
);

CREATE TABLE IF NOT EXISTS billing_document_items (
    billingDocument TEXT,
    billingDocumentItem TEXT,
    material TEXT,
    billingQuantity REAL,
    billingQuantityUnit TEXT,
    netAmount REAL,
    transactionCurrency TEXT,
    referenceSdDocument TEXT,
    referenceSdDocumentItem TEXT,
    PRIMARY KEY (billingDocument, billingDocumentItem)
);

CREATE TABLE IF NOT EXISTS billing_document_cancellations (
    billingDocument TEXT PRIMARY KEY,
    billingDocumentType TEXT,
    creationDate TEXT,
    billingDocumentDate TEXT,
    billingDocumentIsCancelled INTEGER,
    cancelledBillingDocument TEXT,
    totalNetAmount REAL,
    transactionCurrency TEXT,
    companyCode TEXT,
    fiscalYear TEXT,
    accountingDocument TEXT,
    soldToParty TEXT
);

CREATE TABLE IF NOT EXISTS journal_entry_items (
    companyCode TEXT,
    fiscalYear TEXT,
    accountingDocument TEXT,
    accountingDocumentItem TEXT,
    glAccount TEXT,
    referenceDocument TEXT,
    transactionCurrency TEXT,
    amountInTransactionCurrency REAL,
    postingDate TEXT,
    documentDate TEXT,
    accountingDocumentType TEXT,
    customer TEXT,
    financialAccountType TEXT,
    clearingDate TEXT,
    clearingAccountingDocument TEXT,
    profitCenter TEXT,
    PRIMARY KEY (accountingDocument, accountingDocumentItem)
);

CREATE TABLE IF NOT EXISTS payments (
    companyCode TEXT,
    fiscalYear TEXT,
    accountingDocument TEXT,
    accountingDocumentItem TEXT,
    clearingDate TEXT,
    clearingAccountingDocument TEXT,
    amountInTransactionCurrency REAL,
    transactionCurrency TEXT,
    customer TEXT,
    invoiceReference TEXT,
    postingDate TEXT,
    documentDate TEXT,
    glAccount TEXT,
    financialAccountType TEXT,
    profitCenter TEXT,
    PRIMARY KEY (accountingDocument, accountingDocumentItem)
);

CREATE TABLE IF NOT EXISTS business_partners (
    businessPartner TEXT PRIMARY KEY,
    customer TEXT,
    businessPartnerCategory TEXT,
    businessPartnerFullName TEXT,
    businessPartnerName TEXT,
    creationDate TEXT,
    organizationBpName1 TEXT
);

CREATE TABLE IF NOT EXISTS business_partner_addresses (
    businessPartner TEXT PRIMARY KEY,
    cityName TEXT,
    country TEXT,
    district TEXT,
    postalCode TEXT,
    region TEXT,
    streetName TEXT,
    houseNumber TEXT
);

CREATE TABLE IF NOT EXISTS customer_company_assignments (
    customer TEXT,
    companyCode TEXT,
    reconciliationAccount TEXT,
    customerAccountGroup TEXT,
    paymentTerms TEXT,
    PRIMARY KEY (customer, companyCode)
);

CREATE TABLE IF NOT EXISTS customer_sales_area_assignments (
    customer TEXT,
    salesOrganization TEXT,
    distributionChannel TEXT,
    division TEXT,
    currency TEXT,
    customerPaymentTerms TEXT,
    incotermsClassification TEXT,
    incotermsLocation1 TEXT,
    shippingCondition TEXT,
    PRIMARY KEY (customer, salesOrganization, distributionChannel, division)
);

CREATE TABLE IF NOT EXISTS products (
    product TEXT PRIMARY KEY,
    productType TEXT,
    creationDate TEXT,
    grossWeight REAL,
    weightUnit TEXT,
    netWeight REAL,
    productGroup TEXT,
    baseUnit TEXT,
    division TEXT
);

CREATE TABLE IF NOT EXISTS product_descriptions (
    product TEXT,
    language TEXT,
    productDescription TEXT,
    PRIMARY KEY (product, language)
);

CREATE TABLE IF NOT EXISTS plants (
    plant TEXT PRIMARY KEY,
    plantName TEXT,
    valuationArea TEXT,
    salesOrganization TEXT,
    distributionChannel TEXT,
    division TEXT,
    language TEXT
);

CREATE INDEX IF NOT EXISTS idx_soi_salesorder ON sales_order_items(salesOrder);
CREATE INDEX IF NOT EXISTS idx_soi_material ON sales_order_items(material);
CREATE INDEX IF NOT EXISTS idx_odi_refdoc ON outbound_delivery_items(referenceSdDocument);
CREATE INDEX IF NOT EXISTS idx_odi_plant ON outbound_delivery_items(plant);
CREATE INDEX IF NOT EXISTS idx_bdi_refdoc ON billing_document_items(referenceSdDocument);
CREATE INDEX IF NOT EXISTS idx_bdi_material ON billing_document_items(material);
CREATE INDEX IF NOT EXISTS idx_bdh_accdoc ON billing_document_headers(accountingDocument);
CREATE INDEX IF NOT EXISTS idx_bdh_soldto ON billing_document_headers(soldToParty);
CREATE INDEX IF NOT EXISTS idx_soh_soldto ON sales_order_headers(soldToParty);
CREATE INDEX IF NOT EXISTS idx_jei_refdoc ON journal_entry_items(referenceDocument);
CREATE INDEX IF NOT EXISTS idx_jei_customer ON journal_entry_items(customer);
CREATE INDEX IF NOT EXISTS idx_pay_customer ON payments(customer);
CREATE INDEX IF NOT EXISTS idx_pay_clearing ON payments(clearingAccountingDocument);
"""


def init_schema():
    """Create all tables and indexes."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
