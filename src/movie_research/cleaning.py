from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from movie_research.common import (
    OUTPUT_DIR,
    load_config,
    markdown_table,
    normalize_text,
    read_source,
    write_csv,
    write_json,
)


def _normalized_year(value: str) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.notna(number):
        return str(int(number))
    return normalize_text(value)


def _title_year_candidates(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    title_field = config["cleaning"]["title_field"]
    year_field = config["cleaning"]["year_field"]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in frame.to_dict(orient="records"):
        title_key = normalize_text(row.get(title_field, ""))
        year_key = _normalized_year(row.get(year_field, ""))
        if title_key and year_key:
            groups[(title_key, year_key)].append(row)

    output: list[dict[str, Any]] = []
    for (title_key, year_key), records in groups.items():
        if len(records) < 2:
            continue
        for record in records:
            output.append(
                {
                    "normalized_title": title_key,
                    "normalized_year": year_key,
                    "source_row": record["_source_row"],
                    "original_title": record.get(title_field, ""),
                    "original_year": record.get(year_field, ""),
                    "candidate_group_size": len(records),
                    "action": "manual_review_only",
                }
            )
    return pd.DataFrame(
        output,
        columns=[
            "normalized_title",
            "normalized_year",
            "source_row",
            "original_title",
            "original_year",
            "candidate_group_size",
            "action",
        ],
    )


def _entity_candidates(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    threshold = float(config["cleaning"]["entity_fuzzy_similarity_threshold"])
    generic_labels = {
        normalize_text(value)
        for value in config["cleaning"]["generic_director_labels"]
    }
    fields = [
        (config["cleaning"]["director_field"], "director"),
        (config["cleaning"]["lead_actor_field"], "lead_actor"),
    ]
    candidates: list[dict[str, Any]] = []
    for field, role in fields:
        raw_names = sorted(
            {
                value.strip()
                for value in frame[field]
                if value.strip()
                and not (role == "director" and normalize_text(value) in generic_labels)
            }
        )
        normalized_to_raw: dict[str, set[str]] = defaultdict(set)
        for raw_name in raw_names:
            normalized_to_raw[normalize_text(raw_name)].add(raw_name)

        for normalized_name, variants in normalized_to_raw.items():
            if len(variants) > 1:
                for name_a, name_b in combinations(sorted(variants), 2):
                    candidates.append(
                        {
                            "role": role,
                            "name_a": name_a,
                            "name_b": name_b,
                            "similarity": 1.0,
                            "candidate_type": "same_after_case_space_punctuation_normalization",
                            "normalized_a": normalized_name,
                            "normalized_b": normalized_name,
                            "action": "manual_review_only",
                        }
                    )

        distinct_normalized = sorted(normalized_to_raw)
        by_initial: dict[str, list[str]] = defaultdict(list)
        for normalized_name in distinct_normalized:
            if normalized_name:
                by_initial[normalized_name[0]].append(normalized_name)
        for group in by_initial.values():
            for norm_a, norm_b in combinations(group, 2):
                if abs(len(norm_a) - len(norm_b)) > 2:
                    continue
                score = SequenceMatcher(None, norm_a, norm_b).ratio()
                if score < threshold:
                    continue
                for name_a in sorted(normalized_to_raw[norm_a]):
                    for name_b in sorted(normalized_to_raw[norm_b]):
                        candidates.append(
                            {
                                "role": role,
                                "name_a": name_a,
                                "name_b": name_b,
                                "similarity": round(score, 4),
                                "candidate_type": "near_spelling_screen",
                                "normalized_a": norm_a,
                                "normalized_b": norm_b,
                                "action": "manual_review_only",
                            }
                        )

    return pd.DataFrame(
        candidates,
        columns=[
            "role",
            "name_a",
            "name_b",
            "similarity",
            "candidate_type",
            "normalized_a",
            "normalized_b",
            "action",
        ],
    ).drop_duplicates()


def run_cleaning() -> dict[str, Any]:
    config = load_config()
    source = read_source(config)
    source.insert(0, "_source_row", range(2, len(source) + 2))
    original = source.copy()
    cleaned = source.copy()
    director_field = config["cleaning"]["director_field"]
    actor_field = config["cleaning"]["lead_actor_field"]
    generic_labels = {value.casefold() for value in config["cleaning"]["generic_director_labels"]}

    for field in (director_field, actor_field):
        cleaned[field] = cleaned[field].astype(str).str.strip()

    missing = {
        column: int(source[column].astype(str).str.strip().eq("").sum())
        for column in source.columns
        if column != "_source_row"
    }
    exact_duplicate_rows = int(source.drop(columns="_source_row").duplicated(keep=False).sum())
    title_candidates = _title_year_candidates(source, config)
    entity_candidates = _entity_candidates(source, config)

    missing_actor = cleaned[actor_field].eq("")
    generic_director = cleaned[director_field].str.casefold().isin(generic_labels)
    reasons = []
    for no_actor, generic in zip(missing_actor, generic_director):
        row_reasons = []
        if no_actor:
            row_reasons.append("missing_star")
        if generic:
            row_reasons.append("generic_director_label")
        reasons.append(";".join(row_reasons))
    cleaned["_cleaning_action"] = [
        f"excluded:{reason}" if reason else "retained_for_graph"
        for reason in reasons
    ]

    excluded_mask = missing_actor | generic_director
    analysis_records = cleaned.loc[~excluded_mask].copy()
    excluded = original.loc[excluded_mask].copy()
    excluded["exclusion_reason"] = [reasons[index] for index in range(len(reasons)) if excluded_mask.iloc[index]]

    changes: list[dict[str, Any]] = []
    for field in (director_field, actor_field):
        changed_mask = original[field].astype(str) != cleaned[field].astype(str)
        for index in original.index[changed_mask]:
            changes.append(
                {
                    "source_row": int(original.at[index, "_source_row"]),
                    "field": field,
                    "original_value": original.at[index, field],
                    "cleaned_value": cleaned.at[index, field],
                    "action": "trim_leading_trailing_whitespace",
                    "reason": "Matches the preprocessing described in the manuscript.",
                }
            )
    for index in range(len(reasons)):
        if reasons[index]:
            changes.append(
                {
                    "source_row": int(original.iloc[index]["_source_row"]),
                    "field": "row",
                    "original_value": "",
                    "cleaned_value": "",
                    "action": "excluded_from_network_input",
                    "reason": reasons[index],
                }
            )

    quality_rows = [
        {"metric": "source_rows_before", "value": len(source), "notes": "Raw rows; header excluded."},
        {"metric": "source_columns", "value": len(source.columns) - 1, "notes": "Excludes internal _source_row field."},
        {"metric": "exact_duplicate_rows", "value": exact_duplicate_rows, "notes": "Full-row comparison; not automatically removed."},
        {"metric": "normalized_title_year_candidate_rows", "value": len(title_candidates), "notes": "Normalization is used only to flag candidates."},
        {"metric": "entity_resolution_candidate_pairs", "value": len(entity_candidates), "notes": "Exact-normalized variants and high-similarity spellings; manual review only."},
        {"metric": "rows_missing_star", "value": int(missing_actor.sum()), "notes": "Excluded from the network input, consistent with the manuscript."},
        {"metric": "rows_with_generic_director_label", "value": int(generic_director.sum()), "notes": "Excluded from the network input, consistent with the manuscript."},
        {"metric": "rows_after_documented_filters", "value": len(analysis_records), "notes": "No title-year candidates, aliases, or homonyms are merged or deleted."},
    ]
    quality_rows.extend(
        {"metric": f"missing:{column}", "value": count, "notes": "Blank or whitespace-only cell count before cleaning."}
        for column, count in missing.items()
    )
    quality = pd.DataFrame(quality_rows)
    result = {
        "rows_before": int(len(source)),
        "rows_after_documented_filters": int(len(analysis_records)),
        "rows_excluded": int(excluded_mask.sum()),
        "rows_missing_star": int(missing_actor.sum()),
        "rows_generic_director_label": int(generic_director.sum()),
        "exact_duplicate_rows": exact_duplicate_rows,
        "normalized_title_year_candidate_rows": int(len(title_candidates)),
        "entity_resolution_candidate_pairs": int(len(entity_candidates)),
        "missing_values_by_column": missing,
        "entity_resolution_limits": "The dataset has no stable person identifiers or external authority file. String similarity can suggest manual-review candidates but cannot establish aliases or distinguish homonyms.",
        "changes": "Only leading/trailing whitespace was trimmed from director and star fields. The 1 row with missing star and 31 rows with generic director labels are excluded from network input to reproduce the manuscript. No duplicate or entity candidate was deleted or merged.",
    }

    write_csv(cleaned, OUTPUT_DIR / "cleaned_movies.csv")
    write_csv(analysis_records, OUTPUT_DIR / "analysis_records.csv")
    write_csv(excluded, OUTPUT_DIR / "excluded_rows.csv")
    write_csv(pd.DataFrame(changes, columns=["source_row", "field", "original_value", "cleaned_value", "action", "reason"]), OUTPUT_DIR / "cleaning_change_log.csv")
    write_csv(quality, OUTPUT_DIR / "data_quality_summary.csv")
    write_csv(title_candidates, OUTPUT_DIR / "duplicate_title_year_candidates.csv")
    write_csv(entity_candidates, OUTPUT_DIR / "entity_resolution_candidates.csv")
    write_json(OUTPUT_DIR / "cleaning_report.json", result)
    _write_cleaning_markdown(result, quality, OUTPUT_DIR / "data_cleaning_report.md")
    return result


def _write_cleaning_markdown(result: dict[str, Any], quality: pd.DataFrame, path: Path) -> None:
    content = f"""# Data quality and cleaning report

## Before/after summary

| Stage | Rows |
|---|---:|
| Local source before processing | {result['rows_before']:,} |
| Excluded from network input by documented rules | {result['rows_excluded']:,} |
| Network input after documented filters | {result['rows_after_documented_filters']:,} |
| Full-row duplicate rows flagged | {result['exact_duplicate_rows']:,} |
| Normalized title-year candidate rows | {result['normalized_title_year_candidate_rows']:,} |
| Entity-resolution candidate pairs | {result['entity_resolution_candidate_pairs']:,} |

## Missing values

{markdown_table(quality.loc[quality['metric'].str.startswith('missing:')])}

## Entity resolution and retention policy

The source file remains unchanged. `cleaned_movies.csv` retains every source record, adding a source-row index and trimming leading/trailing whitespace only from the `director` and `star` fields. `analysis_records.csv` applies the paper's stated network filters: missing `star` and generic `director`/`directors` labels. Excluded records and reasons are preserved in `excluded_rows.csv`; row-level edits and exclusions are recorded in `cleaning_change_log.csv`.

Title-year and person-name candidates are screening results only. They are never automatically removed or merged. String similarity is not proof of identity. The available fields contain no stable person identifiers or authority data, so aliases and homonyms cannot be adjudicated reliably from this file alone.

The title-year normalization applies Unicode compatibility normalization, case folding, and punctuation/whitespace normalization. The near-spelling screen uses a similarity threshold of {0.92:.2f} and is limited to labels sharing an initial character; this is a candidate-generation heuristic, not exhaustive entity resolution. Review `duplicate_title_year_candidates.csv` and `entity_resolution_candidates.csv` before making any identity decisions.
"""
    path.write_text(content, encoding="utf-8", newline="\n")
