"""Backward-compatible shim for the agentic query orchestrator."""

from typing import Any

try:
    from .agents.orchestrator import process_query as _process_query
except ImportError:
    from agents.orchestrator import process_query as _process_query


def process_query(user_query: str, conversation_id: str | None = None) -> dict[str, Any]:
    """Compatibility wrapper around the multi-agent orchestrator."""
    return _process_query(user_query=user_query, conversation_id=conversation_id)


__all__ = ["process_query"]
