# Data quality and cleaning report

## Before/after summary

| Stage | Rows |
|---|---:|
| Local source before processing | 7,668 |
| Excluded from network input by documented rules | 32 |
| Network input after documented filters | 7,636 |
| Full-row duplicate rows flagged | 0 |
| Normalized title-year candidate rows | 0 |
| Entity-resolution candidate pairs | 7 |

## Missing values

| metric | value | notes |
| --- | --- | --- |
| missing:name | 0 | Blank or whitespace-only cell count before cleaning. |
| missing:rating | 77 | Blank or whitespace-only cell count before cleaning. |
| missing:genre | 0 | Blank or whitespace-only cell count before cleaning. |
| missing:year | 0 | Blank or whitespace-only cell count before cleaning. |
| missing:released | 2 | Blank or whitespace-only cell count before cleaning. |
| missing:score | 3 | Blank or whitespace-only cell count before cleaning. |
| missing:votes | 3 | Blank or whitespace-only cell count before cleaning. |
| missing:director | 0 | Blank or whitespace-only cell count before cleaning. |
| missing:writer | 3 | Blank or whitespace-only cell count before cleaning. |
| missing:star | 1 | Blank or whitespace-only cell count before cleaning. |
| missing:country | 3 | Blank or whitespace-only cell count before cleaning. |
| missing:budget | 2171 | Blank or whitespace-only cell count before cleaning. |
| missing:gross | 189 | Blank or whitespace-only cell count before cleaning. |
| missing:company | 17 | Blank or whitespace-only cell count before cleaning. |
| missing:runtime | 4 | Blank or whitespace-only cell count before cleaning. |

## Entity resolution and retention policy

The source file remains unchanged. `cleaned_movies.csv` retains every source record, adding a source-row index and trimming leading/trailing whitespace only from the `director` and `star` fields. `analysis_records.csv` applies the paper's stated network filters: missing `star` and generic `director`/`directors` labels. Excluded records and reasons are preserved in `excluded_rows.csv`; row-level edits and exclusions are recorded in `cleaning_change_log.csv`.

Title-year and person-name candidates are screening results only. They are never automatically removed or merged. String similarity is not proof of identity. The available fields contain no stable person identifiers or authority data, so aliases and homonyms cannot be adjudicated reliably from this file alone.

The title-year normalization applies Unicode compatibility normalization, case folding, and punctuation/whitespace normalization. The near-spelling screen uses a similarity threshold of 0.92 and is limited to labels sharing an initial character; this is a candidate-generation heuristic, not exhaustive entity resolution. Review `duplicate_title_year_candidates.csv` and `entity_resolution_candidates.csv` before making any identity decisions.
