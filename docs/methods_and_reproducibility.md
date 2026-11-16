# Methods and reproducibility record

## Input and provenance

The analysis input is the local file `movies.csv`; it is not overwritten. The Kaggle page at <https://www.kaggle.com/datasets/danielgrijalvas/movies> was checked on 2026-11-16. The page exposed version 2 and a metadata-modified timestamp of 2021-07-23T19:48:26.173Z. Its description reports 6,820 movies and years 1986–2016, while the local file has 7,668 rows and year values 1980–2020. The local and page field-name sets match. The public version-2 download endpoint returned HTTP 404 during the check, so the exact local file revision and historical download date remain unknown and exact correspondence is inconclusive.

The SHA-256, byte size, column names, local filesystem modification timestamp, and observed data profile are recorded in `outputs/dataset_reconciliation.json`. Filesystem modification time is not treated as a download or creation date.

## Cleaning and inclusion

The source file is read as text so identifiers and labels are not silently coerced. Blank or whitespace-only cells are counted as missing. Name keys used for screening are normalized with Unicode NFKC, case folding, and punctuation/whitespace normalization. Year values are normalized numerically where possible.

The graph input reproduces the manuscript's documented filters: trim leading/trailing whitespace from director and star names; exclude rows with missing `star`; exclude rows whose director is the generic label `Director` or `Directors`. No title/year duplicates, aliases, or homonyms are automatically removed or merged. Every excluded row and every field trim is recorded. Fuzzy name candidates are heuristic and require external evidence or human review.

## Network construction

Each retained row creates or increments an undirected edge between a role-specific director node and a role-specific lead-actor node. Nodes are identified by `(role, displayed name)`, so identical names in different roles remain distinct. Edge weight is the number of retained rows for that pair. Degree counts distinct counterpart nodes; strength sums edge weights.

Betweenness is approximate, normalized, and computed only on the largest connected component. NetworkX's sampled-source algorithm is run with `k=1000`, seed 42 for the baseline, and `weight=None`; repeated-row weights are not distances. The 30-seed sensitivity run changes only the seed and retains the same graph, component, normalization, and `k`. The seed set includes 42 and 2026 for continuity with the manuscript and 28 additional fixed seeds for a broader empirical comparison.

Rank is descending betweenness, calculated within role with average ranks for ties. Spearman rank correlation and Kendall tau-b are compared with seed 42 and summarized over all seed pairs. Per-node score standard deviation/range, rank standard deviation/range, and top-10 frequency are also reported. These diagnostics measure sampling sensitivity of the approximation only; they do not test source revisions, missing records, entity resolution, or alternative graph definitions.

## Runtime and dependencies

The implementation was prepared and tested with Python 3.13.7 and the exact package versions pinned in `requirements.txt`. Random seeds are specified in `config/analysis_config.json`. Run the complete workflow with `python scripts\\run_analysis.py`.

## Interpretation

Results describe relationships represented by the local file and its single `star` field, not complete cast/crew collaboration. Betweenness describes shortest-path position in this defined graph; it does not establish practical brokerage, influence, causal effects, or artistic/commercial quality. Nodes outside the largest component do not receive betweenness values in the reported sensitivity analysis.
