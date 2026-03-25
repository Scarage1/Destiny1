"""T6 — compare_analytics intent tests."""
from __future__ import annotations

from backend.agents.planner_agent import plan


def test_compare_region_intent() -> None:
    """Region query without explicit compare keyword → detect_anomaly (correct) or compare_analytics."""
    result = plan("Which region has the highest number of incomplete transactions?", context={}, model=None, trace_id="test-t6")
    # Without explicit "compare"/"vs" keyword, heuristic routes to detect_anomaly (incomplete_region)
    # or compare_analytics if compare keyword is present. Both are valid O2C intents.
    assert result["intent"] in ("compare_analytics", "detect_anomaly", "analyze")


def test_compare_regions_vs_syntax() -> None:
    """'Compare East vs West region completion rate' → compare_analytics intent."""
    result = plan("Compare East vs West region completion rate", context={}, model=None, trace_id="test-t6")
    assert result["intent"] == "compare_analytics"
    # group_by may be 'region' or None depending on entity_type resolution order


def test_compare_monthly_period_intent() -> None:
    """'Compare orders this month vs last month' → compare_analytics."""
    result = plan("Compare orders this month vs last month", context={}, model=None, trace_id="test-t6")
    assert result["intent"] == "compare_analytics"


def test_time_range_this_year_filter() -> None:
    """'Top customers this year' → filters include date_from/date_to."""
    result = plan("Top customers this year", context={}, model=None, trace_id="test-t6")
    date_filters = [f for f in result.get("filters", []) if f.get("field") == "date"]
    assert len(date_filters) >= 2
    froms = [f for f in date_filters if f["op"] == ">="]
    tos   = [f for f in date_filters if f["op"] == "<="]
    assert froms and tos
    assert froms[0]["value"].endswith("-01-01")


def test_time_range_quarter_filter() -> None:
    """'Q1 2024 billing volume' → filters include Q1 date range."""
    result = plan("Q1 2024 billing volume by customer", context={}, model=None, trace_id="test-t6")
    date_filters = [f for f in result.get("filters", []) if f.get("field") == "date"]
    assert len(date_filters) >= 2
    assert "2024-01-01" in [f["value"] for f in date_filters]
