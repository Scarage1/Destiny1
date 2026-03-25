from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

IntentType = Literal["trace_flow", "detect_anomaly", "status_lookup", "analyze"]
EntityType = Literal["invoice", "sales_order", "delivery", "payment", "customer", "product", "plant"]
MetricType = Literal[
    "net_amount",
    "count",
    "quantity",
    "revenue",
    "billing_documents",
    "billing_document_count",
    "delivery_count",
]
OperationType = Literal["max", "min", "avg", "sum", "median", "list", "trace", "detect"]
GroupByType = Literal["product", "customer", "sales_order"]


class FilterClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    op: Literal["=", "!=", ">", ">=", "<", "<=", "in", "contains"] = "="
    value: str | int | float | bool


class IntentPlanV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: IntentType
    entity_type: EntityType | None = None
    entity_id: str | None = None
    metric: MetricType | None = None
    operation: OperationType | None = None
    filters: list[FilterClause] = Field(default_factory=list)
    group_by: GroupByType | None = None
    limit: int = Field(default=20, ge=1, le=100)
    time_range: str | None = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    clarification: str | None = None
    follow_up: bool = False
    verification: Literal["required"] = "required"
    anomaly_sub_type: str | None = None


def validate_and_normalize_plan(raw_plan: dict[str, Any]) -> dict[str, Any]:
    """Validate planner output against strict schema and return normalized dict."""
    try:
        model = IntentPlanV1.model_validate(raw_plan)
    except ValidationError as e:
        raise ValueError(f"Invalid intent plan: {str(e)}") from e
    return model.model_dump()
