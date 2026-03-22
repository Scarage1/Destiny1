from __future__ import annotations

from types import SimpleNamespace

import backend.llm_service as llm_service


class _FakeModel:
    def __init__(self, sql_text: str, answer_text: str = "Grounded answer"):
        self.sql_text = sql_text
        self.answer_text = answer_text
        self.calls = 0

    def generate_content(self, _prompt):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(text=self.sql_text)
        return SimpleNamespace(text=self.answer_text)


def test_pipeline_returns_blocked_contract_for_unsafe_sql(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "get_schema_description", lambda: "schema")
    monkeypatch.setattr(llm_service, "_get_model", lambda: _FakeModel("DELETE FROM sales_order_headers"))

    result = llm_service.process_query("show sales orders")

    assert result["status"] == "blocked"
    assert result["results"] is None
    assert result["result_columns"] is None
    assert result["total_results"] is None
    assert isinstance(result["trace_id"], str)


def test_pipeline_returns_no_data_grounded_answer(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "get_schema_description", lambda: "schema")
    monkeypatch.setattr(llm_service, "_get_model", lambda: _FakeModel("SELECT salesOrder FROM sales_order_headers"))
    monkeypatch.setattr(llm_service, "execute_readonly_query", lambda _sql: [])

    result = llm_service.process_query("show sales orders with impossible condition")

    assert result["status"] == "success"
    assert result["total_results"] == 0
    assert result["results"] == []
    assert result["result_columns"] == []
    assert result["answer"] == "No matching records found in the dataset."
    assert isinstance(result["trace_id"], str)


def test_pipeline_success_contract_contains_columns_and_trace(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "get_schema_description", lambda: "schema")
    monkeypatch.setattr(
        llm_service,
        "_get_model",
        lambda: _FakeModel(
            "SELECT salesOrder, soldToParty FROM sales_order_headers",
            "Top sales order is SO-1",
        ),
    )
    monkeypatch.setattr(
        llm_service,
        "execute_readonly_query",
        lambda _sql: [{"salesOrder": "SO-1", "soldToParty": "101000"}],
    )

    result = llm_service.process_query("show top sales order")

    assert result["status"] == "success"
    assert result["total_results"] == 1
    assert result["result_columns"] == ["salesOrder", "soldToParty"]
    assert result["results"][0]["salesOrder"] == "SO-1"
    assert "SalesOrder:SO-1" in result["referenced_nodes"]
    assert isinstance(result["trace_id"], str)
