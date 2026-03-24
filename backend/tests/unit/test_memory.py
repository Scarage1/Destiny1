from __future__ import annotations

import backend.agents.memory as memory


def test_memory_enforces_capacity(monkeypatch) -> None:
    memory.clear_context()
    monkeypatch.setattr(memory, "_MEMORY_MAX_CONVERSATIONS", 2)

    memory.update_context("c1", {"intent": "order_status", "entity_type": "order", "entity_id": "1001"}, "t1")
    memory.update_context("c2", {"intent": "order_status", "entity_type": "order", "entity_id": "1002"}, "t2")
    memory.update_context("c3", {"intent": "order_status", "entity_type": "order", "entity_id": "1003"}, "t3")

    assert memory.get_context("c1") == {}
    assert memory.get_context("c2")["last_trace_id"] == "t2"
    assert memory.get_context("c3")["last_trace_id"] == "t3"


def test_memory_update_moves_conversation_to_recent(monkeypatch) -> None:
    memory.clear_context()
    monkeypatch.setattr(memory, "_MEMORY_MAX_CONVERSATIONS", 2)

    memory.update_context("c1", {"intent": "order_status"}, "t1")
    memory.update_context("c2", {"intent": "order_status"}, "t2")
    memory.update_context("c1", {"intent": "order_lines"}, "t3")
    memory.update_context("c3", {"intent": "order_status"}, "t4")

    assert memory.get_context("c2") == {}
    assert memory.get_context("c1")["last_trace_id"] == "t3"
    assert memory.get_context("c3")["last_trace_id"] == "t4"


def test_memory_stats_reports_limits(monkeypatch) -> None:
    memory.clear_context()
    monkeypatch.setattr(memory, "_MEMORY_MAX_CONVERSATIONS", 5)

    memory.update_context("c1", {"intent": "order_status"}, "t1")
    stats = memory.get_memory_stats()

    assert stats["conversation_count"] == 1
    assert stats["max_conversations"] == 5
