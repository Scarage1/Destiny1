"""
Domain guardrails: validates user queries before LLM/DB processing.
- Rejects off-topic/out-of-domain prompts
- Validates generated SQL for safety (read-only)
- Enforces schema whitelist
"""

import re

MAX_SQL_LENGTH = 12000
MAX_SQL_JOINS = 12


def normalize_user_query(query: str) -> str:
    """Normalize user input for deterministic downstream processing."""
    if query is None:
        return ""
    # Remove control characters and collapse whitespace.
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", str(query))
    # Recover a few common contractions and omitted apostrophes in fast typing.
    cleaned = re.sub(r"\bhasn'?t\b", "has not", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bhaven'?t\b", "have not", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bwon'?t\b", "will not", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdon'?t\b", "do not", cleaned, flags=re.IGNORECASE)
    # Recover a few common fused question words from fast typing, e.g. "whichnhas" -> "which has".
    cleaned = re.sub(r"\b(which|what|who)n+(has|is|are|was|were)\b", r"\1 \2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(which|what|who)(has|is|are|was|were)\b", r"\1 \2", cleaned, flags=re.IGNORECASE)
    # Light typo recovery for common business-chat misspellings.
    typo_replacements = {
        r"\btellme\b": "tell me",
        r"\babot\b": "about",
        r"\babt\b": "about",
        r"\bselled\b": "sold",
    }
    for pattern, replacement in typo_replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

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
    "orders",
    "sales",
    "delivery",
    "deliveries",
    "billing",
    "invoice",
    "payment",
    "paid",
    "unpaid",
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
    "price",
    "cost",
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
    "goods movement",
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

# Prompt-injection / model-manipulation patterns (reject early)
PROMPT_INJECTION_PATTERNS = [
    r"(?i)\b(ignore|disregard|override)\b.{0,40}\b(previous|prior|above|all)\b.{0,40}\b(instruction|instructions|rules|policy|policies)\b",
    r"(?i)\b(system\s+prompt|developer\s+prompt|hidden\s+prompt|internal\s+instruction)\b",
    r"(?i)\b(jailbreak|bypass\s+guard|disable\s+guard|turn\s+off\s+safety)\b",
    r"(?i)\b(exfiltrate|leak|reveal|dump)\b.{0,30}\b(prompt|key|secret|token|credentials?)\b",
]

SECURITY_REJECTION_RESPONSE = (
    "This request was blocked by safety policy. "
    "Please ask a business question about the SAP Order-to-Cash dataset."
)


ENTITY_ID_PATTERNS: dict[str, str] = {
    # IDs are intentionally conservative to prevent malformed/potentially injected values.
    "invoice": r"^[A-Za-z0-9_-]{3,40}$",
    "sales_order": r"^[A-Za-z0-9_-]{3,40}$",
    "delivery": r"^[A-Za-z0-9_-]{3,40}$",
    "payment": r"^[A-Za-z0-9_-]{3,40}$",
    "customer": r"^[A-Za-z0-9_-]{2,40}$",
    "product": r"^[A-Za-z0-9_-]{2,40}$",
    "plant": r"^[A-Za-z0-9_-]{2,20}$",
}


def validate_entity_id(entity_type: str | None, entity_id: str | None) -> tuple[bool, str | None]:
    """Validate entity identifier format for deterministic lookup/trace queries."""
    if not entity_id:
        return True, None

    normalized_id = normalize_user_query(entity_id)
    if len(normalized_id) > 64:
        return False, "Entity ID is too long."

    if entity_type is None:
        # Without explicit type, allow conservative alphanumeric IDs only.
        if not re.fullmatch(r"^[A-Za-z0-9_-]{2,40}$", normalized_id):
            return False, "Entity ID format is invalid."
        return True, None

    pattern = ENTITY_ID_PATTERNS.get(entity_type)
    if not pattern:
        return False, f"Unsupported entity type '{entity_type}'."

    if not re.fullmatch(pattern, normalized_id):
        return False, f"Entity ID format is invalid for entity type '{entity_type}'."

    return True, None

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
    normalized_query = normalize_user_query(query)
    query_lower = normalized_query.lower()

    # Empty queries
    if len(query_lower) < 3:
        return (
            False,
            "Please ask a specific question about the SAP Order-to-Cash data.",
        )

    # Check off-topic patterns first
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, normalized_query):
            return False, SECURITY_REJECTION_RESPONSE

    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, normalized_query):
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
        if re.search(pattern, normalized_query):
            return True, None

    # Default: reject if we can't identify domain relevance
    return False, REJECTION_RESPONSE


def validate_sql_safety(sql: str) -> tuple[bool, str | None, str]:
    """
    Validate that generated SQL is safe (read-only, no injection).
    Returns (is_safe, rejection_reason, sanitized_sql).
    The third element is the (possibly modified) SQL with safety constraints applied.
    """
    sql = (sql or "").strip()
    sql_upper = sql.upper()

    if len(sql) > MAX_SQL_LENGTH:
        return False, "SQL exceeds maximum allowed length.", sql

    join_count = len(re.findall(r"(?i)\bJOIN\b", sql))
    if join_count > MAX_SQL_JOINS:
        return False, "SQL complexity exceeds maximum allowed JOIN count.", sql

    # Enforce single statement execution only.
    body = sql[:-1] if sql.endswith(";") else sql
    if ";" in body:
        return False, "Only single-statement SQL is allowed.", sql

    # Block write operations
    for kw in SQL_WRITE_KEYWORDS:
        if sql_upper.startswith(kw) or f" {kw} " in sql_upper:
            return False, f"Write operation blocked: {kw}", sql

    # Block dangerous patterns
    for pattern in SQL_DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, "Potentially unsafe SQL pattern detected.", sql

    # Must start with SELECT or WITH (CTE)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed.", sql

    # Enforce table whitelist
    table_ok, table_reason = validate_table_whitelist(sql)
    if not table_ok:
        return False, table_reason, sql

    # Apply safety constraints (add LIMIT if missing)
    sql = sanitize_sql(sql)

    return True, None, sql


def sanitize_sql(sql: str) -> str:
    """Add safety constraints to generated SQL."""
    sql = sql.strip().rstrip(";")
    sql_upper = sql.upper()

    # Add LIMIT if not present
    if "LIMIT" not in sql_upper:
        sql += " LIMIT 100"

    return sql + ";"


def _extract_cte_names(sql: str) -> set[str]:
    """Extract CTE names from WITH clause so they are not mistaken as physical tables."""
    ctes: set[str] = set()
    # Supports: WITH cte AS (...), another_cte AS (...)
    for match in re.finditer(r"(?i)(?:WITH|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(", sql):
        ctes.add(match.group(1).lower())
    return ctes


def _extract_referenced_tables(sql: str) -> set[str]:
    """Extract table tokens used after FROM/JOIN clauses."""
    matches = re.findall(
        r"(?i)\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_\.]*)",
        sql,
    )
    return {m.split(".")[-1].lower() for m in matches}


def validate_table_whitelist(sql: str) -> tuple[bool, str | None]:
    """Validate that SQL only references known allowed tables."""
    referenced = _extract_referenced_tables(sql)
    if not referenced:
        return True, None

    cte_names = _extract_cte_names(sql)
    disallowed = sorted(
        table for table in referenced
        if table not in ALLOWED_TABLES and table not in cte_names
    )
    if disallowed:
        return False, f"Disallowed table(s) referenced: {', '.join(disallowed)}"
    return True, None


def validate_response_grounding(answer: str, results: list[dict]) -> bool:
    """Ensure synthesized answer includes at least one concrete value from results."""
    if not results:
        return "No matching records found in the dataset." in answer

    answer_lower = answer.lower()
    for row in results[:10]:
        for value in row.values():
            if value is None:
                continue
            token = str(value).strip()
            if len(token) < 3:
                continue
            if token.lower() in answer_lower:
                return True
    return False
