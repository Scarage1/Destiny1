from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

from .observability import log_event
from .runtime_config import get_runtime_config

try:
    from ..db_adapter import get_db_adapter
except ImportError:
    from db_adapter import get_db_adapter

try:
    from ..guardrails import sanitize_sql, validate_sql_safety
except ImportError:
    from guardrails import sanitize_sql, validate_sql_safety


_SQL_RESULT_CACHE: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
_EXEC_CB_STATE: dict[str, int | float] = {"failures": 0, "opened_until": 0.0}


def _clone_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def _canonicalize_sql_for_cache(sql: str) -> str:
    canonical = (sql or "").strip().rstrip(";")
    canonical = " ".join(canonical.split())
    return canonical.lower()


def _cache_get(cache_key: str, ttl: int) -> tuple[bool, list[dict[str, Any]]]:
    if ttl <= 0:
        return False, []
    entry = _SQL_RESULT_CACHE.get(cache_key)
    if entry is None:
        return False, []
    ts, payload = entry
    if (time.time() - ts) > ttl:
        _SQL_RESULT_CACHE.pop(cache_key, None)
        return False, []
    _SQL_RESULT_CACHE.move_to_end(cache_key)
    return True, _clone_rows(payload)


def _cache_set(cache_key: str, results: list[dict[str, Any]], ttl: int, max_entries: int) -> None:
    if ttl <= 0:
        return
    _SQL_RESULT_CACHE[cache_key] = (time.time(), _clone_rows(results))
    _SQL_RESULT_CACHE.move_to_end(cache_key)
    while len(_SQL_RESULT_CACHE) > max_entries:
        _SQL_RESULT_CACHE.popitem(last=False)


def _is_transient_db_error(error: Exception) -> bool:
    msg = str(error).lower()
    transient_tokens = [
        "database is locked",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "connection refused",
        "too many connections",
        "could not connect",
        "server closed the connection",
    ]
    return any(token in msg for token in transient_tokens)


def _is_circuit_open(now: float) -> bool:
    return now < float(_EXEC_CB_STATE.get("opened_until", 0.0))


def _mark_execution_failure(now: float, trace_id: str, reason: str, threshold: int, open_seconds: int) -> None:
    failures = int(_EXEC_CB_STATE.get("failures", 0)) + 1
    _EXEC_CB_STATE["failures"] = failures
    if failures >= threshold:
        opened_until = now + open_seconds
        _EXEC_CB_STATE["opened_until"] = opened_until
        log_event(
            trace_id,
            "execution_circuit_open",
            {
                "failures": failures,
                "open_seconds": open_seconds,
                "reason": reason,
            },
        )


def _reset_execution_circuit() -> None:
    _EXEC_CB_STATE["failures"] = 0
    _EXEC_CB_STATE["opened_until"] = 0.0


def execute_sql(sql: str, trace_id: str, semantic_cache_key: str | None = None) -> dict[str, Any]:
    """Execute validated SQL through a strict deterministic boundary."""
    cfg = get_runtime_config()

    validation = validate_sql_safety(sql)

    is_safe = False
    reason = "Invalid SQL validator result"
    sanitized = ""
    if isinstance(validation, tuple) and len(validation) == 3:
        is_safe, reason, sanitized = validation
    elif isinstance(validation, tuple) and len(validation) == 2:
        is_safe, reason = validation

    if not is_safe:
        log_event(trace_id, "guard_block_sql", {"reason": reason, "sql": sql})
        return {
            "ok": False,
            "status": "blocked",
            "reason": reason,
            "sql": sql,
            "results": None,
        }

    safe_sql = sanitized if sanitized else sanitize_sql(sql)
    adapter = get_db_adapter()
    sql_key = _canonicalize_sql_for_cache(safe_sql)
    cache_key = f"{adapter.name}:{semantic_cache_key or sql_key}"

    now = time.time()
    if _is_circuit_open(now):
        reason = "Execution subsystem is temporarily unavailable. Please retry shortly."
        log_event(
            trace_id,
            "execution_circuit_short_circuit",
            {"reason": reason, "db_backend": adapter.name},
        )
        return {
            "ok": False,
            "status": "error",
            "reason": reason,
            "sql": safe_sql,
            "results": None,
        }

    cache_hit, cached_rows = _cache_get(cache_key, cfg.sql_cache_ttl_seconds)
    if cache_hit:
        log_event(
            trace_id,
            "execution_cache_hit",
            {
                "row_count": len(cached_rows),
                "db_backend": adapter.name,
                "semantic_cache_key": semantic_cache_key,
            },
        )
        return {
            "ok": True,
            "status": "success",
            "reason": None,
            "sql": safe_sql,
            "results": cached_rows,
        }

    attempts = cfg.sql_exec_retries + 1
    last_error: Exception | None = None
    results: list[dict[str, Any]] | None = None

    for attempt in range(1, attempts + 1):
        try:
            results = adapter.execute_readonly_query(safe_sql)
            break
        except Exception as e:
            last_error = e
            transient = _is_transient_db_error(e)
            log_event(
                trace_id,
                "execution_retry",
                {
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "transient": transient,
                    "error": str(e),
                    "db_backend": adapter.name,
                },
            )
            if not transient or attempt >= attempts:
                break
            time.sleep(min(0.2, 0.05 * attempt))

    if results is None:
        err = last_error or RuntimeError("Unknown execution error")
        _mark_execution_failure(
            time.time(), trace_id, str(err),
            cfg.exec_cb_failure_threshold, cfg.exec_cb_open_seconds,
        )
        log_event(
            trace_id,
            "execution_error",
            {"error": str(err), "sql": safe_sql, "db_backend": adapter.name},
        )
        return {
            "ok": False,
            "status": "error",
            "reason": f"Query execution failed: {str(err)}",
            "sql": safe_sql,
            "results": None,
        }

    _reset_execution_circuit()

    _cache_set(cache_key, results, cfg.sql_cache_ttl_seconds, cfg.sql_cache_max_entries)

    log_event(trace_id, "execution", {"row_count": len(results)})
    return {
        "ok": True,
        "status": "success",
        "reason": None,
        "sql": safe_sql,
        "results": results,
    }
