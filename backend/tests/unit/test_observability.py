from __future__ import annotations

import json

import backend.agents.observability as obs


def test_get_trace_prefers_recent_in_memory_cache(tmp_path, monkeypatch) -> None:
    log_file = tmp_path / "agent_events.log"
    monkeypatch.setattr(obs, "LOG_PATH", log_file)
    obs._RECENT_EVENTS_BY_TRACE.clear()

    obs.log_event("t-cache", "request", {"query": "show one"})
    obs.log_event("t-cache", "response", {"status": "success"})

    trace_events = obs.get_trace("t-cache")
    assert len(trace_events) == 2
    assert trace_events[0]["stage"] == "request"
    assert trace_events[1]["stage"] == "response"


def test_read_all_events_honors_max_events_bound(tmp_path, monkeypatch) -> None:
    log_file = tmp_path / "agent_events.log"
    monkeypatch.setattr(obs, "LOG_PATH", log_file)

    rows = [
        {"ts": "2026-03-24T10:00:00+00:00", "trace_id": "t1", "stage": "request", "payload": {}},
        {"ts": "2026-03-24T10:00:01+00:00", "trace_id": "t2", "stage": "request", "payload": {}},
        {"ts": "2026-03-24T10:00:02+00:00", "trace_id": "t3", "stage": "request", "payload": {}},
    ]
    with log_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    events = obs._read_all_events(max_events=2)
    assert len(events) == 2
    assert [e["trace_id"] for e in events] == ["t2", "t3"]


def test_get_metrics_summary_from_events(tmp_path, monkeypatch) -> None:
    log_file = tmp_path / "agent_events.log"
    monkeypatch.setattr(obs, "LOG_PATH", log_file)

    rows = [
        {
            "ts": "2026-03-24T10:00:00+00:00",
            "trace_id": "t1",
            "stage": "request",
            "payload": {},
        },
        {
            "ts": "2026-03-24T10:00:00.030000+00:00",
            "trace_id": "t1",
            "stage": "query_agent",
            "payload": {"mode": "deterministic_nl"},
        },
        {
            "ts": "2026-03-24T10:00:00.060000+00:00",
            "trace_id": "t1",
            "stage": "response",
            "payload": {"status": "success"},
        },
        {
            "ts": "2026-03-24T10:00:00.020000+00:00",
            "trace_id": "t1",
            "stage": "stage_latency",
            "payload": {"stage": "planner", "elapsed_ms": 21},
        },
        {
            "ts": "2026-03-24T10:00:01+00:00",
            "trace_id": "t2",
            "stage": "request",
            "payload": {},
        },
        {
            "ts": "2026-03-24T10:00:01.010000+00:00",
            "trace_id": "t2",
            "stage": "guard_reject",
            "payload": {},
        },
        {
            "ts": "2026-03-24T10:00:01.005000+00:00",
            "trace_id": "t2",
            "stage": "stage_latency",
            "payload": {"stage": "planner", "elapsed_ms": 7},
        },
    ]

    with log_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    metrics = obs.get_metrics_summary()
    assert metrics["request_count"] == 2
    assert metrics["success_rate"] == 0.5
    assert metrics["guard_rejection_rate"] == 0.5
    assert metrics["deterministic_hit_rate"] == 0.5
    assert metrics["p95_latency_ms"] >= 10
    assert metrics["p99_latency_ms"] >= metrics["p95_latency_ms"]
    assert metrics["stage_latency_p95_ms"]["planner"] >= 7
    assert metrics["stage_latency_p99_ms"]["planner"] >= metrics["stage_latency_p95_ms"]["planner"]
