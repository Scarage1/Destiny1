from __future__ import annotations

import json
from pathlib import Path

from backend.ingest import run_ingestion


def test_ingestion_writes_summary_and_reject_reports() -> None:
    summary = run_ingestion()

    root = Path(__file__).resolve().parents[3]
    processed = root / "data" / "processed"
    summary_path = processed / "ingestion_summary.json"
    rejects_path = processed / "normalization_rejects.json"

    assert summary_path.exists()
    assert rejects_path.exists()

    disk_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert disk_summary["total_loaded"] == summary["total_loaded"]
    assert "business_partners" in disk_summary["entities"]
    assert "sales_order_headers" in disk_summary["entities"]
    assert len(disk_summary["normalized_entities"]) >= 5


def test_ingestion_summary_has_non_negative_quality_counts() -> None:
    summary = run_ingestion()

    assert summary["total_loaded"] > 0
    assert summary["total_errors"] >= 0
    assert summary["total_rejected"] >= 0

    for entity, stats in summary["entities"].items():
        assert stats["loaded"] >= 0, entity
        assert stats["errors"] >= 0, entity
        assert stats["rejected"] >= 0, entity
