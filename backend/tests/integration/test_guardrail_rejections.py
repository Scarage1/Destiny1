from __future__ import annotations

from backend.llm_service import process_query
from backend.guardrails import REJECTION_RESPONSE


def test_process_query_rejects_off_domain_before_llm_call() -> None:
    result = process_query("Tell me a joke about football")

    assert result["status"] == "rejected"
    assert result["query"] is None
    assert result["results"] is None
    assert result["result_columns"] is None
    assert result["total_results"] is None
    assert isinstance(result["trace_id"], str)
    assert len(result["trace_id"]) >= 8
    assert result["answer"] == REJECTION_RESPONSE
