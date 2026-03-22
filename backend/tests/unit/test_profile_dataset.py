from pathlib import Path
from backend.ingestion.profile_dataset import (
    profile_raw_dataset,
    ColumnStats,
    EntityStats,
    infer_candidate_keys,
    build_data_dictionary_md,
    build_quality_report_md,
)


def test_column_stats():
    stats = ColumnStats()
    stats.observe("foo")
    stats.observe("bar")
    stats.observe("foo")
    stats.observe("")
    stats.observe(None)
    assert stats.non_null == 3
    assert stats.nulls == 2
    assert stats.unique_values == {"foo", "bar"}


def test_entity_stats():
    stats = EntityStats()
    stats.observe_row({"id": "1", "val": "A"})
    stats.observe_row({"id": "2", "val": None})
    summary = stats.to_summary()
    assert summary["rows"] == 2
    assert summary["columns"]["id"]["non_null"] == 2
    assert summary["columns"]["val"]["nulls"] == 1


def test_infer_candidate_keys():
    columns = {
        "id": {"non_null": 5, "unique_count": 5},
        "status": {"non_null": 5, "unique_count": 2},
        "empty": {"non_null": 0, "unique_count": 0},
    }
    keys = infer_candidate_keys(columns)
    assert keys == ["id"]


def test_markdown_builders():
    summary = {
        "entity_count": 1,
        "total_rows": 10,
        "entities": {
            "test_entity": {
                "files": 1,
                "rows": 10,
                "parse_errors": 0,
                "columns": {
                    "id": {
                        "non_null": 10,
                        "nulls": 0,
                        "null_pct": 0.0,
                        "unique_count": 10,
                        "unique_pct_of_non_null": 100.0,
                    },
                    "val": {
                        "non_null": 5,
                        "nulls": 5,
                        "null_pct": 50.0,
                        "unique_count": 2,
                        "unique_pct_of_non_null": 40.0,
                    },
                },
                "candidate_keys": ["id"],
            }
        },
        "join_hints": [
            {
                "source_table": "test_entity",
                "source_column": "id",
                "target_table": "other",
                "target_column": "fk",
                "relation": "1:N",
            }
        ],
    }
    dict_md = build_data_dictionary_md(summary)
    assert "test_entity" in dict_md

    qual_md = build_quality_report_md(summary)
    assert "High-null Columns" in qual_md
    assert "50.0" in qual_md


def test_profile_raw_dataset_returns_expected_shape():
    root = Path(__file__).resolve().parents[3]
    raw_root = root / "data" / "raw" / "sap-o2c-data"

    summary = profile_raw_dataset(raw_root)

    assert summary["entity_count"] >= 15
    assert summary["total_rows"] > 0
    assert "sales_order_headers" in summary["entities"]
    assert "billing_document_headers" in summary["entities"]
    assert len(summary["join_hints"]) > 5
