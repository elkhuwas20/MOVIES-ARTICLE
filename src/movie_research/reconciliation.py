from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from movie_research.common import (
    OUTPUT_DIR,
    input_path,
    load_config,
    markdown_table,
    read_source,
    write_csv,
    write_json,
)


def build_reconciliation() -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config()
    source = config["dataset"]
    path = input_path(config)
    frame = read_source(config)
    years = pd.to_numeric(frame.get("year", pd.Series(dtype=str)), errors="coerce").dropna()
    with path.open("rb") as file:
        file_hash = hashlib.sha256(file.read()).hexdigest()

    local = {
        "filename": path.name,
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": list(frame.columns),
        "year_min": int(years.min()) if not years.empty else None,
        "year_max": int(years.max()) if not years.empty else None,
        "file_size_bytes": path.stat().st_size,
        "filesystem_modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
        "sha256": file_hash,
        "revision": source["local_file_revision"],
        "historical_download_date": source["historical_download_date"],
    }
    kaggle_columns = source["kaggle_description_columns"]
    local_column_set = set(local["column_names"])
    kaggle_column_set = set(kaggle_columns)
    same_count = local["rows"] == source["kaggle_description_rows"]
    same_year_range = (
        local["year_min"] == source["kaggle_description_year_min"]
        and local["year_max"] == source["kaggle_description_year_max"]
    )
    same_columns = local_column_set == kaggle_column_set

    rows = [
        ("Nama file lokal", local["filename"], "movies.csv pada salinan lokal", "Diperiksa"),
        ("Revisi lokal", "Tidak tercatat", f"Kaggle versi {source['kaggle_page_version']}", "Identitas revisi lokal tidak diketahui"),
        ("Tanggal pemeriksaan halaman", source["kaggle_page_checked_on"], "Tanggal pemeriksaan halaman Kaggle saat audit", "Bukan tanggal unduh historis"),
        ("Tanggal modifikasi halaman", source["kaggle_page_modified_utc"], "Metadata halaman Kaggle", "Tersedia"),
        ("Baris data", local["rows"], source["kaggle_description_rows"], "Sesuai" if same_count else "Berbeda dari deskripsi halaman"),
        ("Kolom", local["columns"], len(kaggle_columns), "Jumlah sesuai" if local["columns"] == len(kaggle_columns) else "Berbeda"),
        ("Nama kolom", "; ".join(local["column_names"]), "; ".join(kaggle_columns), "Sama (urutan diabaikan)" if same_columns else "Berbeda"),
        ("Rentang tahun", f"{local['year_min']}–{local['year_max']}", f"{source['kaggle_description_year_min']}–{source['kaggle_description_year_max']}", "Sesuai" if same_year_range else "Berbeda dari deskripsi halaman"),
        ("Identitas file biner", local["sha256"], "Tidak tersedia untuk pembandingan arsip", "Belum terverifikasi"),
    ]
    report = pd.DataFrame(rows, columns=["item", "dataset_lokal", "metadata_kaggle", "penilaian"])
    details = {
        "kaggle_url": source["kaggle_url"],
        "kaggle_page_checked_on": source["kaggle_page_checked_on"],
        "kaggle_page_version": source["kaggle_page_version"],
        "kaggle_page_modified_utc": source["kaggle_page_modified_utc"],
        "kaggle_description_rows": source["kaggle_description_rows"],
        "kaggle_description_year_range": [
            source["kaggle_description_year_min"],
            source["kaggle_description_year_max"],
        ],
        "kaggle_description_columns": kaggle_columns,
        "local": local,
        "comparison": {
            "column_names_match": same_columns,
            "description_row_count_matches": same_count,
            "description_year_range_matches": same_year_range,
            "binary_identity_verified": source["local_file_identity_verified_against_kaggle"],
            "conclusion": "The local file has the same 15 field names as the page description, but its row count and year range differ. Since the version-2 archive could not be retrieved for byte/content comparison, exact correspondence remains inconclusive.",
        },
        "reconciliation_note": source["reconciliation_note"],
    }
    return report, details


def run_reconciliation() -> dict[str, Any]:
    report, details = build_reconciliation()
    write_csv(report, OUTPUT_DIR / "dataset_reconciliation.csv")
    write_json(OUTPUT_DIR / "dataset_reconciliation.json", details)
    _write_reconciliation_markdown(report, details, OUTPUT_DIR / "dataset_reconciliation.md")
    return details


def _write_reconciliation_markdown(report: pd.DataFrame, details: dict[str, Any], path: Path) -> None:
    table = markdown_table(report)
    content = f"""# Dataset reconciliation

Page checked: {details['kaggle_page_checked_on']}<br>
Source: <{details['kaggle_url']}><br>
Kaggle page version: {details['kaggle_page_version']}<br>
Page metadata modified: {details['kaggle_page_modified_utc']}

{table}

## Assessment

The local CSV contains {details['local']['rows']:,} data rows, {details['local']['columns']} columns, and year values from {details['local']['year_min']} to {details['local']['year_max']}. The Kaggle page description reports {details['kaggle_description_rows']:,} movies from {details['kaggle_description_year_range'][0]} to {details['kaggle_description_year_range'][1]}. The 15 field names match, but the row count and year range in the page description do not match the local file.

The Kaggle page identifies version {details['kaggle_page_version']}; it does not establish which version produced this local copy. The public version-2 download endpoint returned HTTP 404 during this check, so an exact content or binary comparison was not possible. The Kaggle description may be stale; the evidence is insufficient to distinguish stale metadata from a different local revision. The local SHA-256 is recorded in `dataset_reconciliation.json` to identify this exact file.

The page-check date above is the date of this metadata inspection, **not** a historical download date. The local file revision and historical download date were not supplied. The filesystem modification time is recorded as file-system metadata only and must not be interpreted as the dataset's creation or download date.
"""
    path.write_text(content, encoding="utf-8", newline="\n")
