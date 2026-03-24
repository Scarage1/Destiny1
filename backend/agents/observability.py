from __future__ import annotations

import json
from collections import OrderedDict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_config import get_runtime_config

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "agent_events.log"
_RUNTIME_CONFIG = get_runtime_config()
_RECENT_TRACES_MAX = _RUNTIME_CONFIG.observability_recent_traces
_EVENTS_PER_TRACE_MAX = _RUNTIME_CONFIG.observability_events_per_trace
_METRICS_MAX_EVENTS_SCAN = _RUNTIME_CONFIG.observability_metrics_max_events_scan

_RECENT_EVENTS_BY_TRACE: "OrderedDict[str, deque[dict[str, Any]]]" = OrderedDict()


def _remember_recent_event(record: dict[str, Any]) -> None:
    trace_id = str(record.get("trace_id") or "").strip()
    if not trace_id:
        return

    bucket = _RECENT_EVENTS_BY_TRACE.get(trace_id)
    if bucket is None:
        bucket = deque(maxlen=_EVENTS_PER_TRACE_MAX)
        _RECENT_EVENTS_BY_TRACE[trace_id] = bucket
    else:
        _RECENT_EVENTS_BY_TRACE.move_to_end(trace_id)
    bucket.append(record)

    while len(_RECENT_EVENTS_BY_TRACE) > _RECENT_TRACES_MAX:
        _RECENT_EVENTS_BY_TRACE.popitem(last=False)


def log_event(trace_id: str, stage: str, payload: dict[str, Any]) -> None:
    """Write structured agent events for traceability and audit."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "stage": stage,
        "payload": payload,
    }
    _remember_recent_event(record)

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        # Logging must never break query execution.
        pass


def get_trace(trace_id: str) -> list[dict[str, Any]]:
    """Return all events for a specific trace id."""
    cached = _RECENT_EVENTS_BY_TRACE.get(trace_id)
    if cached:
        _RECENT_EVENTS_BY_TRACE.move_to_end(trace_id)
        return list(cached)

    return _read_trace_events_from_file(trace_id, max_events=_EVENTS_PER_TRACE_MAX)


def _read_trace_events_from_file(trace_id: str, *, max_events: int | None = None) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []

    maxlen = max_events if isinstance(max_events, int) and max_events > 0 else None
    bucket: deque[dict[str, Any]] | list[dict[str, Any]]
    bucket = deque(maxlen=maxlen) if maxlen else []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("trace_id") != trace_id:
                continue
            bucket.append(row)

    return list(bucket)


def _read_all_events(max_events: int | None = None) -> list[dict[str, Any]]:
    """Read all structured events from log file."""
    if not LOG_PATH.exists():
        return []

    maxlen = max_events if isinstance(max_events, int) and max_events > 0 else None
    events: deque[dict[str, Any]] | list[dict[str, Any]]
    events = deque(maxlen=maxlen) if maxlen else []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            events.append(row)
    return list(events)


def build_agent_trace_summary(
    trace_id: str,
    intent_plan: dict[str, Any] | None = None,
    sql: str | None = None,
    verification: dict[str, Any] | None = None,
    clarification: str | None = None,
    row_count: int | None = None,
    llm_used: bool = False,
    llm_provider: str | None = None,
    stage_latencies_ms: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build normalized inline trace payload for API responses."""
    events = get_trace(trace_id)
    latency_ms: int | None = None

    if events:
        try:
            start = datetime.fromisoformat(events[0]["ts"])
            end = datetime.fromisoformat(events[-1]["ts"])
            latency_ms = int((end - start).total_seconds() * 1000)
        except Exception:
            latency_ms = None

    return {
        "trace_id": trace_id,
        "intent": intent_plan,
        "clarification": {
            "required": bool(clarification),
            "question": clarification,
        },
        "sql": sql,
        "params": {},
        "execution": {
            "rows": row_count,
            "latency_ms": latency_ms,
        },
        "verification": verification,
        "summary": {
            "total_ms": latency_ms,
            "stage_count": len(events),
            "llm_used": llm_used,
            "llm_provider": llm_provider,
        },
        "stage_latencies_ms": stage_latencies_ms or {},
        "events": events,
    }


def get_metrics_summary() -> dict[str, Any]:
    """Compute lightweight API metrics from trace event logs."""
    events = _read_all_events(max_events=_METRICS_MAX_EVENTS_SCAN)
    if not events:
        return {
            "request_count": 0,
            "success_rate": 0.0,
            "guard_rejection_rate": 0.0,
            "clarification_rate": 0.0,
            "deterministic_hit_rate": 0.0,
            "llm_fallback_rate": 0.0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "stage_latency_p95_ms": {},
            "stage_latency_p99_ms": {},
        }

    traces: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        tid = ev.get("trace_id")
        if not tid:
            continue
        traces.setdefault(tid, []).append(ev)

    request_count = 0
    success_count = 0
    guard_reject_count = 0
    clarification_count = 0
    deterministic_count = 0
    fallback_count = 0
    latencies: list[int] = []
    stage_latencies: dict[str, list[int]] = {}

    terminal_stages = {
        "response",
        "guard_reject",
        "query_agent_error",
        "execution_error",
        "llm_unavailable",
        "clarification",
    }

    for trace_events in traces.values():
        request = next((e for e in trace_events if e.get("stage") == "request"), None)
        if request is None:
            continue
        request_count += 1

        if any(e.get("stage") == "response" for e in trace_events):
            success_count += 1
        if any(e.get("stage") == "guard_reject" for e in trace_events):
            guard_reject_count += 1
        if any(e.get("stage") == "clarification" for e in trace_events):
            clarification_count += 1
        if any(
            e.get("stage") == "query_agent" and str((e.get("payload") or {}).get("mode", "")).startswith("deterministic")
            for e in trace_events
        ):
            deterministic_count += 1
        if any(e.get("stage") in {"llm_fallback_switch", "llm_fallback_selected"} for e in trace_events):
            fallback_count += 1

        terminal = next((e for e in reversed(trace_events) if e.get("stage") in terminal_stages), None)
        if terminal is not None:
            try:
                start = datetime.fromisoformat(request["ts"])
                end = datetime.fromisoformat(terminal["ts"])
                latencies.append(int((end - start).total_seconds() * 1000))
            except Exception:
                pass

        for ev in trace_events:
            if ev.get("stage") != "stage_latency":
                continue
            payload = ev.get("payload") or {}
            stage = payload.get("stage")
            elapsed = payload.get("elapsed_ms")
            if not isinstance(stage, str):
                continue
            if not isinstance(elapsed, int):
                continue
            stage_latencies.setdefault(stage, []).append(elapsed)

    def _rate(n: int) -> float:
        return round((n / request_count), 4) if request_count else 0.0

    def _percentile(values: list[int], p: float) -> int:
        if not values:
            return 0
        ordered = sorted(values)
        idx = int(max(0, round(p * (len(ordered) - 1))))
        return ordered[idx]

    p95_latency = _percentile(latencies, 0.95)
    p99_latency = _percentile(latencies, 0.99)
    stage_p95 = {k: _percentile(v, 0.95) for k, v in stage_latencies.items()}
    stage_p99 = {k: _percentile(v, 0.99) for k, v in stage_latencies.items()}

    return {
        "request_count": request_count,
        "success_rate": _rate(success_count),
        "guard_rejection_rate": _rate(guard_reject_count),
        "clarification_rate": _rate(clarification_count),
        "deterministic_hit_rate": _rate(deterministic_count),
        "llm_fallback_rate": _rate(fallback_count),
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "stage_latency_p95_ms": stage_p95,
        "stage_latency_p99_ms": stage_p99,
    }
