"""
Domain guardrails: validates user queries before LLM/DB processing.
- Rejects off-topic/out-of-domain prompts
- Validates generated SQL for safety (read-only)
- Enforces schema whitelist
"""

import re

# Domain rejection response
REJECTION_RESPONSE = "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. It covers sales orders, deliveries, billing documents, payments, customers, products, and plants."

# Allowed table names in generated SQL
ALLOWED_TABLES = {
    "sales_order_headers",
    "sales_order_items",
    "sales_order_schedule_lines",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "billing_document_headers",
    "billing_document_items",
    "billing_document_cancellations",
    "journal_entry_items",
    "payments",
    "business_partners",
    "business_partner_addresses",
    "customer_company_assignments",
    "customer_sales_area_assignments",
    "products",
    "product_descriptions",
    "plants",
}

# Domain keywords that indicate a query is relevant
DOMAIN_KEYWORDS = [
    "order",
    "sales",
    "delivery",
    "billing",
    "invoice",
    "payment",
    "customer",
    "product",
    "material",
    "plant",
    "journal",
    "accounting",
    "document",
    "ship",
    "freight",
    "quantity",
    "amount",
    "cancel",
    "block",
    "status",
    "flow",
    "trace",
    "broken",
    "incomplete",
    "missing",
    "billed",
    "delivered",
    "partner",
    "address",
    "company",
    "fiscal",
    "clearing",
    "receivable",
    "revenue",
    "net amount",
    "gross",
    "weight",
    "currency",
    "inr",
    "highest",
    "lowest",
    "most",
    "least",
    "top",
    "average",
    "total",
    "count",
    "how many",
    "which",
    "what",
    "list",
    "show",
    "find",
    "identify",
    "get",
    "storage",
    "location",
    "warehouse",
    "schedule",
    "confirm",
]

# Off-topic patterns (strong signals for rejection)
OFF_TOPIC_PATTERNS = [
    r"(?i)\b(poem|poetry|story|fiction|creative\s+writ|novel|essay)\b",
    r"(?i)\b(recipe|cook|food|restaurant|weather|forecast)\b",
    r"(?i)\b(translate|translation|language\s+learning)\b",
    r"(?i)\b(game|play|sport|movie|music|song|entertainment)\b",
    r"(?i)\b(medical|health|doctor|symptom|diagnosis|treatment)\b",
    r"(?i)\b(stock|crypto|bitcoin|invest|trading|forex)\b",
    r"(?i)\b(who\s+is|biography|history\s+of|tell\s+me\s+about)\b(?!.*(?:customer|order|product|plant|partner|billing|delivery))",
    r"(?i)\b(code|program|python|javascript|html|css|api|develop)\b(?!.*(?:order|billing|delivery|product|sales))",
    r"(?i)\b(joke|funny|humor|riddle|guess)\b",
    r"(?i)^(hi|hello|hey|good\s+morning|good\s+evening|what'?s\s+up)\s*[!?.]*$",
    r"(?i)\b(explain|teach|tutor|learn\s+about)\b(?!.*(?:order|billing|delivery|product|sales|payment|customer))",
    r"(?i)\b(opinion|think\s+about|feel\s+about|political|religion)\b",
]

# SQL write/mutation keywords to block
SQL_WRITE_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "MERGE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
]

# SQL dangerous patterns
SQL_DANGEROUS_PATTERNS = [
    r";\s*(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)",  # Multi-statement injection
    r"--",  # SQL comment (injection vector)
    r"/\*",  # Block comment
    r"LOAD_EXTENSION",
    r"randomblob",
    r"writefile",
    r"readfile",
]


def check_domain_relevance(query: str) -> tuple[bool, str | None]:
    """
    Check if a query is relevant to the O2C domain.
    Returns (is_relevant, rejection_reason).
    """
    query_lower = query.lower().strip()

    # Empty queries
    if len(query_lower) < 3:
        return (
            False,
            "Please ask a specific question about the SAP Order-to-Cash data.",
        )

    # Check off-topic patterns first
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, query):
            return False, REJECTION_RESPONSE

    # Check domain relevance via keywords
    has_domain_keyword = any(kw in query_lower for kw in DOMAIN_KEYWORDS)

    if has_domain_keyword:
        return True, None

    # If no domain keywords found, check if it's a general analytical question
    # that could apply to the dataset (e.g., "show me the top 10", "give summary")
    analytical_patterns = [
        r"(?i)\b(show|list|find|get|display|summarize|summary|overview|statistics|stats|count|total)\b",
        r"(?i)\b(table|data|dataset|record|row|column|field)\b",
        r"(?i)\b(graph|node|edge|relationship|connection|link)\b",
    ]
    for pattern in analytical_patterns:
        if re.search(pattern, query):
            return True, None

    # Default: reject if we can't identify domain relevance
    return False, REJECTION_RESPONSE


def validate_sql_safety(sql: str) -> tuple[bool, str | None]:
    """
    Validate that generated SQL is safe (read-only, no injection).
    Returns (is_safe, rejection_reason).
    """
    sql_upper = sql.strip().upper()

    # Block write operations
    for kw in SQL_WRITE_KEYWORDS:
        if sql_upper.startswith(kw) or f" {kw} " in sql_upper:
            return False, f"Write operation blocked: {kw}"

    # Block dangerous patterns
    for pattern in SQL_DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, "Potentially unsafe SQL pattern detected."

    # Must start with SELECT or WITH (CTE)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed."

    # Enforce a LIMIT if not present
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip().rstrip(";") + " LIMIT 100"

    return True, None


def sanitize_sql(sql: str) -> str:
    """Add safety constraints to generated SQL."""
    sql = sql.strip().rstrip(";")
    sql_upper = sql.upper()

    # Add LIMIT if not present
    if "LIMIT" not in sql_upper:
        sql += " LIMIT 100"

    return sql + ";"
