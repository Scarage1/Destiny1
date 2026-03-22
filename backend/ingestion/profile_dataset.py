"""Dataset profiling utility for raw SAP O2C JSONL files.

Generates:
- data/processed/profile_summary.json
- docs/data-dictionary.md
- docs/data-quality-report.md

Usage:
    python backend/ingestion/profile_dataset.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "sap-o2c-data"
PROCESSED_ROOT = ROOT / "data" / "processed"
SUMMARY_JSON = PROCESSED_ROOT / "profile_summary.json"
DATA_DICTIONARY_MD = ROOT / "docs" / "data-dictionary.md"
DATA_QUALITY_MD = ROOT / "docs" / "data-quality-report.md"

# High-confidence business join hints for downstream ingestion/graph mapping.
JOIN_HINTS: list[tuple[str, str, str, str, str]] = [
    (
        "sales_order_headers",
        "salesOrder",
        "sales_order_items",
        "salesOrder",
        "header-to-item",
    ),
    (
        "sales_order_items",
        "salesOrder",
        "outbound_delivery_items",
        "referenceSdDocument",
        "order-to-delivery",
    ),
    (
        "outbound_delivery_headers",
        "deliveryDocument",
        "outbound_delivery_items",
        "deliveryDocument",
        "header-to-item",
    ),
    (
        "outbound_delivery_headers",
        "deliveryDocument",
        "billing_document_items",
        "referenceSdDocument",
        "delivery-to-billing",
    ),
    (
        "billing_document_headers",
        "billingDocument",
        "billing_document_items",
        "billingDocument",
        "header-to-item",
    ),
    (
        "billing_document_headers",
        "accountingDocument",
        "journal_entry_items_accounts_receivable",
        "accountingDocument",
        "billing-to-journal",
    ),
    (
        "journal_entry_items_accounts_receivable",
        "clearingAccountingDocument",
        "payments_accounts_receivable",
        "accountingDocument",
        "journal-to-payment",
    ),
    (
        "billing_document_headers",
        "soldToParty",
        "business_partners",
        "businessPartner",
        "billing-to-customer",
    ),
    (
        "sales_order_headers",
        "soldToParty",
        "business_partners",
        "businessPartner",
        "sales-to-customer",
    ),
    (
        "sales_order_items",
        "material",
        "products",
        "product",
        "item-to-product",
    ),
    (
        "billing_document_items",
        "material",
        "products",
        "product",
        "billing-item-to-product",
    ),
    (
        "sales_order_items",
        "productionPlant",
        "plants",
        "plant",
        "item-to-plant",
    ),
    (
        "outbound_delivery_items",
        "plant",
        "plants",
        "plant",
        "delivery-item-to-plant",
    ),
]


@dataclass
class ColumnStats:
    non_null: int = 0
    nulls: int = 0
    unique_values: set[str] = field(default_factory=set)

    def observe(self, value: Any) -> None:
        if value is None or value == "":
            self.nulls += 1
            return
        self.non_null += 1
        self.unique_values.add(str(value))


@dataclass
class EntityStats:
    files: int = 0
    rows: int = 0
    parse_errors: int = 0
    columns: dict[str, ColumnStats] = field(default_factory=dict)

    def observe_row(self, row: dict[str, Any]) -> None:
        self.rows += 1
        keys = set(self.columns.keys()) | set(row.keys())
        for key in keys:
            self.columns.setdefault(key, ColumnStats())
            self.columns[key].observe(row.get(key))

    def to_summary(self) -> dict[str, Any]:
        summary_cols: dict[str, dict[str, Any]] = {}
        for name, stats in sorted(self.columns.items()):
            non_null = stats.non_null
            nulls = stats.nulls
            total = non_null + nulls
            unique = len(stats.unique_values)
            summary_cols[name] = {
                "non_null": non_null,
                "nulls": nulls,
                "total": total,
                "null_pct": round((nulls / total) * 100, 2) if total else 0.0,
                "unique_count": unique,
                "unique_pct_of_non_null": (
                    round((unique / non_null) * 100, 2) if non_null else 0.0
                ),
            }
        return {
            "files": self.files,
            "rows": self.rows,
            "parse_errors": self.parse_errors,
            "columns": summary_cols,
            "candidate_keys": infer_candidate_keys(summary_cols),
        }


def infer_candidate_keys(columns: dict[str, dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for col, stats in columns.items():
        nn = stats["non_null"]
        unique = stats["unique_count"]
        if nn > 0 and unique == nn:
            candidates.append(col)
    return sorted(candidates)


def profile_raw_dataset(raw_root: Path) -> dict[str, Any]:
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw data folder not found: {raw_root}")

    entities: dict[str, EntityStats] = {}

    for entity_dir in sorted(p for p in raw_root.iterdir() if p.is_dir()):
        stats = EntityStats()
        jsonl_files = sorted(entity_dir.glob("*.jsonl"))
        stats.files = len(jsonl_files)

        for path in jsonl_files:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            stats.observe_row(row)
                        else:
                            stats.parse_errors += 1
                    except json.JSONDecodeError:
                        stats.parse_errors += 1

        entities[entity_dir.name] = stats

    # Build referential hints summary.
    relationships: list[dict[str, Any]] = []
    for src_t, src_c, dst_t, dst_c, relation in JOIN_HINTS:
        src_rows = entities[src_t].rows if src_t in entities else 0
        dst_rows = entities[dst_t].rows if dst_t in entities else 0
        relationships.append(
            {
                "source_table": src_t,
                "source_column": src_c,
                "target_table": dst_t,
                "target_column": dst_c,
                "relation": relation,
                "source_rows": src_rows,
                "target_rows": dst_rows,
            }
        )

    return {
        "raw_root": str(raw_root),
        "entity_count": len(entities),
        "total_rows": sum(s.rows for s in entities.values()),
        "entities": {
            name: s.to_summary() for name, s in sorted(entities.items())
        },
        "join_hints": relationships,
    }


def _table_md_header() -> str:
    return "| Entity | Files | Rows | Parse Errors | Columns | Candidate Keys |\n|---|---:|---:|---:|---:|---|"


def build_data_dictionary_md(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Data Dictionary",
        "",
        "Generated from raw JSONL dataset profiling.",
        "",
        f"- Total entities: {summary['entity_count']}",
        f"- Total rows: {summary['total_rows']}",
        "",
        "## Entity Inventory",
        "",
        _table_md_header(),
    ]

    for entity, info in summary["entities"].items():
        keys = (
            ", ".join(info["candidate_keys"][:4])
            if info["candidate_keys"]
            else "-"
        )
        lines.append(
            f"| {entity} | {info['files']} | {info['rows']} | {info['parse_errors']} | {len(info['columns'])} | {keys} |"
        )

    lines.extend(
        [
            "",
            "## Join Key Candidates",
            "",
            "| Source | Target | Relationship |",
            "|---|---|---|",
        ]
    )
    for rel in summary["join_hints"]:
        src = f"{rel['source_table']}.{rel['source_column']}"
        dst = f"{rel['target_table']}.{rel['target_column']}"
        lines.append(f"| {src} | {dst} | {rel['relation']} |")

    lines.extend(["", "## Column-level Details", ""])
    for entity, info in summary["entities"].items():
        lines.append(f"### {entity}")
        lines.append("")
        lines.append(
            "| Column | Non-null | Nulls | Null % | Unique (non-null) |"
        )
        lines.append("|---|---:|---:|---:|---:|")
        for col, col_stats in info["columns"].items():
            lines.append(
                f"| {col} | {col_stats['non_null']} | {col_stats['nulls']} | {col_stats['null_pct']} | {col_stats['unique_count']} |"
            )
        lines.append("")

    return "\n".join(lines)


def build_quality_report_md(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Data Quality Report",
        "",
        "Profiling-based quality report for raw SAP O2C dataset.",
        "",
        "## Executive Summary",
        "",
        f"- Entities scanned: {summary['entity_count']}",
        f"- Records scanned: {summary['total_rows']}",
        "",
        "## Issues to Monitor",
        "",
    ]

    high_null_columns: list[tuple[str, str, float]] = []
    low_uniqueness_keys: list[tuple[str, str, float]] = []

    for entity, info in summary["entities"].items():
        for col, col_stats in info["columns"].items():
            if col_stats["null_pct"] >= 30.0:
                high_null_columns.append((entity, col, col_stats["null_pct"]))
            uniq = col_stats["unique_pct_of_non_null"]
            if col in info["candidate_keys"] and uniq < 100.0:
                low_uniqueness_keys.append((entity, col, uniq))

    if high_null_columns:
        lines.append("### High-null Columns (>=30%)")
        lines.append("")
        lines.append("| Entity | Column | Null % |")
        lines.append("|---|---|---:|")
        for entity, col, pct in sorted(
            high_null_columns, key=lambda x: x[2], reverse=True
        )[:40]:
            lines.append(f"| {entity} | {col} | {pct} |")
        lines.append("")
    else:
        lines.append("- No high-null columns above threshold.")
        lines.append("")

    if low_uniqueness_keys:
        lines.append("### Candidate Key Risks")
        lines.append("")
        lines.append("| Entity | Column | Unique % of Non-null |")
        lines.append("|---|---|---:|")
        for entity, col, pct in low_uniqueness_keys:
            lines.append(f"| {entity} | {col} | {pct} |")
        lines.append("")

    lines.append("## Ingestion Risk Notes")
    lines.append("")
    lines.append(
        "- Two entities are present in raw data but not yet mapped in current ingestion code: `product_plants`, `product_storage_locations`."
    )
    lines.append(
        "- Relationship integrity must be validated during graph load (missing source/target IDs should be reported)."
    )
    lines.append(
        "- Use deterministic canonical IDs and idempotent load semantics."
    )

    return "\n".join(lines)


def write_outputs(summary: dict[str, Any]) -> None:
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    DATA_DICTIONARY_MD.write_text(
        build_data_dictionary_md(summary), encoding="utf-8"
    )
    DATA_QUALITY_MD.write_text(
        build_quality_report_md(summary), encoding="utf-8"
    )


def main() -> None:
    summary = profile_raw_dataset(RAW_ROOT)
    write_outputs(summary)
    print(f"Profile JSON: {SUMMARY_JSON}")
    print(f"Data dictionary: {DATA_DICTIONARY_MD}")
    print(f"Data quality report: {DATA_QUALITY_MD}")


if __name__ == "__main__":
    main()
