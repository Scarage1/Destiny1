from __future__ import annotations

from typing import Any

from backend.agents.runtime_config import get_runtime_config

CONVERSATION_MEMORY: dict[str, dict[str, Any]] = {}
_MEMORY_MAX_CONVERSATIONS = get_runtime_config().memory_max_conversations


def _enforce_capacity() -> None:
    while len(CONVERSATION_MEMORY) > _MEMORY_MAX_CONVERSATIONS:
        oldest_key = next(iter(CONVERSATION_MEMORY), None)
        if oldest_key is None:
            break
        CONVERSATION_MEMORY.pop(oldest_key, None)


def get_context(conversation_id: str | None) -> dict[str, Any]:
    if not conversation_id:
        return {}
    return CONVERSATION_MEMORY.get(conversation_id, {})


def update_context(
    conversation_id: str | None,
    plan: dict[str, Any],
    trace_id: str,
    *,
    pending_clarification: bool = False,
) -> None:
    if not conversation_id:
        return

    memory = CONVERSATION_MEMORY.get(conversation_id, {}).copy()
    entity_type = plan.get("entity_type")
    entity_id = plan.get("entity_id")

    memory["last_intent"] = plan.get("intent")
    memory["last_trace_id"] = trace_id
    memory["last_plan"] = plan

    if entity_type and entity_id:
        memory["last_entity"] = {"type": entity_type, "id": entity_id}

    if pending_clarification:
        memory["pending_plan"] = plan
    else:
        memory.pop("pending_plan", None)

    if conversation_id in CONVERSATION_MEMORY:
        CONVERSATION_MEMORY.pop(conversation_id, None)
    CONVERSATION_MEMORY[conversation_id] = memory
    _enforce_capacity()


def clear_context(conversation_id: str | None = None) -> None:
    if conversation_id is None:
        CONVERSATION_MEMORY.clear()
        return
    CONVERSATION_MEMORY.pop(conversation_id, None)


def get_memory_stats() -> dict[str, int]:
    return {
        "conversation_count": len(CONVERSATION_MEMORY),
        "max_conversations": _MEMORY_MAX_CONVERSATIONS,
    }
