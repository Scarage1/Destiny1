from __future__ import annotations

import backend.db_adapter as db_adapter


def test_default_db_adapter_is_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("DB_BACKEND", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    db_adapter.clear_db_adapter_cache()

    adapter = db_adapter.get_db_adapter()
    assert adapter.name == "sqlite"


def test_postgres_adapter_requires_dsn(monkeypatch) -> None:
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    db_adapter.clear_db_adapter_cache()

    adapter = db_adapter.get_db_adapter()
    assert adapter.name == "postgres"

    try:
        adapter.execute_readonly_query("SELECT 1")
        raise AssertionError("Expected RuntimeError when POSTGRES_DSN is missing")
    except RuntimeError as e:
        assert "POSTGRES_DSN" in str(e)
