from __future__ import annotations

import importlib
import os
from typing import Any, Protocol


class DatabaseAdapter(Protocol):
    name: str

    def execute_readonly_query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        ...

    def db_exists(self) -> bool:
        ...


class SQLiteAdapter:
    name = "sqlite"

    def execute_readonly_query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        try:
            from .database import execute_readonly_query
        except ImportError:
            from database import execute_readonly_query
        return execute_readonly_query(sql, params)

    def db_exists(self) -> bool:
        try:
            from .database import DB_PATH
        except ImportError:
            from database import DB_PATH
        return DB_PATH.exists()


class PostgresAdapter:
    name = "postgres"

    def __init__(self, dsn: str | None) -> None:
        self.dsn = dsn

    def execute_readonly_query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if not self.dsn:
            raise RuntimeError("POSTGRES_DSN is required when DB_BACKEND=postgres")

        try:
            psycopg = importlib.import_module("psycopg")
        except Exception as e:
            raise RuntimeError(
                "psycopg is required for Postgres backend but is not installed"
            ) from e

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description is None:
                    return []
                columns = [desc.name for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row, strict=False)) for row in rows]

    def db_exists(self) -> bool:
        return bool(self.dsn)


def get_db_adapter() -> DatabaseAdapter:
    backend = os.environ.get("DB_BACKEND", "sqlite").strip().lower()

    if backend == "postgres":
        return PostgresAdapter(os.environ.get("POSTGRES_DSN"))

    return SQLiteAdapter()


def clear_db_adapter_cache() -> None:
    # Backward-compatible no-op; adapter lookup is environment-driven per call.
    return None
