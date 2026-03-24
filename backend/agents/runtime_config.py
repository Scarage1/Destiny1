from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(minimum, value)


@dataclass(frozen=True)
class RuntimeConfig:
    gemini_api_key: str
    groq_api_key: str
    groq_model: str

    llm_timeout_seconds: float
    pipeline_timeout_ms: int
    stage_budget_ms: dict[str, int]
    strict_deterministic: bool

    sql_cache_ttl_seconds: int
    sql_cache_max_entries: int
    sql_exec_retries: int
    exec_cb_failure_threshold: int
    exec_cb_open_seconds: int
    memory_max_conversations: int
    observability_recent_traces: int = 500
    observability_events_per_trace: int = 50
    observability_metrics_max_events_scan: int = 10000


def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
        llm_timeout_seconds=_env_float("O2C_LLM_TIMEOUT_SECONDS", 20.0, minimum=0.1),
        pipeline_timeout_ms=_env_int("O2C_PIPELINE_TIMEOUT_MS", 8000, minimum=1000),
        stage_budget_ms={
            "planner": _env_int("O2C_STAGE_BUDGET_PLANNER_MS", 700, minimum=50),
            "guard": _env_int("O2C_STAGE_BUDGET_GUARD_MS", 120, minimum=20),
            "validator": _env_int("O2C_STAGE_BUDGET_VALIDATOR_MS", 120, minimum=20),
            "query_agent": _env_int("O2C_STAGE_BUDGET_QUERY_AGENT_MS", 300, minimum=20),
            "execution": _env_int("O2C_STAGE_BUDGET_EXECUTION_MS", 2500, minimum=100),
            "verification": _env_int("O2C_STAGE_BUDGET_VERIFICATION_MS", 300, minimum=20),
            "response": _env_int("O2C_STAGE_BUDGET_RESPONSE_MS", 2200, minimum=100),
        },
        strict_deterministic=_env_bool("O2C_STRICT_DETERMINISTIC", default=False),
        sql_cache_ttl_seconds=_env_int("O2C_SQL_CACHE_TTL_SECONDS", 30, minimum=0),
        sql_cache_max_entries=_env_int("O2C_SQL_CACHE_MAX_ENTRIES", 256, minimum=1),
        sql_exec_retries=_env_int("O2C_SQL_EXEC_RETRIES", 1, minimum=0),
        exec_cb_failure_threshold=_env_int("O2C_EXEC_CB_FAILURE_THRESHOLD", 3, minimum=1),
        exec_cb_open_seconds=_env_int("O2C_EXEC_CB_OPEN_SECONDS", 20, minimum=1),
        memory_max_conversations=_env_int("O2C_MEMORY_MAX_CONVERSATIONS", 2000, minimum=1),
        observability_recent_traces=_env_int("O2C_OBS_RECENT_TRACES", 500, minimum=10),
        observability_events_per_trace=_env_int("O2C_OBS_EVENTS_PER_TRACE", 50, minimum=5),
        observability_metrics_max_events_scan=_env_int("O2C_OBS_METRICS_MAX_EVENTS_SCAN", 10000, minimum=100),
    )
