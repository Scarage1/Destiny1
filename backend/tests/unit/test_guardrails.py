from __future__ import annotations

from backend.guardrails import (
    REJECTION_RESPONSE,
    check_domain_relevance,
    sanitize_sql,
    validate_sql_safety,
)


def test_off_topic_query_is_rejected() -> None:
    ok, reason = check_domain_relevance("Write me a poem about the moon")
    assert ok is False
    assert reason == REJECTION_RESPONSE


def test_domain_query_is_accepted() -> None:
    ok, reason = check_domain_relevance("Show sales orders delivered but not billed")
    assert ok is True
    assert reason is None


def test_sql_write_operation_is_blocked() -> None:
    ok, reason = validate_sql_safety("DELETE FROM sales_order_headers")
    assert ok is False
    assert "Write operation blocked" in (reason or "")


def test_sql_must_be_select_or_with() -> None:
    ok, reason = validate_sql_safety("PRAGMA table_info(sales_order_headers)")
    assert ok is False
    assert reason in {"Only SELECT queries are allowed.", "Write operation blocked: PRAGMA"}


def test_sql_injection_pattern_is_blocked() -> None:
    ok, reason = validate_sql_safety("SELECT * FROM sales_order_headers; DROP TABLE products")
    assert ok is False
    assert reason in {"Potentially unsafe SQL pattern detected.", "Write operation blocked: DROP"}


def test_sanitize_sql_adds_limit_and_semicolon() -> None:
    out = sanitize_sql("SELECT * FROM sales_order_headers")
    assert out.upper().startswith("SELECT")
    assert "LIMIT 100" in out.upper()
    assert out.endswith(";")
