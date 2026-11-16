# Movie Industry Network Analysis

This project reproduces and extends the analysis of a director–lead-actor bipartite network using the local `movies.csv`. It keeps the original file unchanged, reports data-quality issues, preserves possible duplicate/entity candidates for review, reproduces the manuscript's graph definition, and evaluates betweenness-rank sensitivity across 30 deterministic seeds.

## Important source limitation

The local CSV contains 7,668 data rows, 15 columns, and `year` values from 1980 to 2020. The Kaggle page checked on 2026-11-16 identifies page version 2 (page metadata modified 2021-07-23) but its description states 6,820 movies from 1986 to 2016. The 15 field names match; row count and year range do not. The page's version-2 archive endpoint returned HTTP 404 when checked, so exact file identity is **inconclusive**. The local revision and its historical download date were not recorded. See `outputs/dataset_reconciliation.md`.

The reported page-check date is not a claim about when the local file was downloaded. Do not describe the local file as an exact Kaggle-version match unless an archived source file is independently verified.

## Project structure

```text
MOVIES ARTICLE/
├── movies.csv                         # Original local input; never overwritten
├── config/analysis_config.json        # Source evidence and analysis parameters
├── src/movie_research/
│   ├── common.py                      # Shared paths, input, and output helpers
│   ├── reconciliation.py              # Dataset/source comparison
│   ├── cleaning.py                    # Missingness, duplicate/entity candidates
│   ├── network.py                     # Graph construction and baseline metrics
│   └── sensitivity.py                 # Multi-seed scores, ranks, correlations, plots
├── scripts/run_analysis.py            # Ordered end-to-end entry point
├── .vscode/settings.json              # Project-local Pylance source path
├── pyrightconfig.json                 # Pylance/Pyright source-root configuration
├── docs/                              # Methods and publication notes
├── outputs/                           # Generated tables, reports, and figures
├── requirements.txt                   # Exact versions observed in the tested environment
└── tests/                             # Focused regression tests
```

## Requirements and installation

The analysis was run with Python 3.13.7. Exact dependency versions from the available project virtual environment are pinned in `requirements.txt`.

From this directory, create/activate an environment and install dependencies:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Keep the original `movies.csv` in this directory. The CSV is not downloaded or modified by the pipeline.

## Run

Open `MOVIES ARTICLE` as the workspace folder so the project-local Pylance settings and `pyrightconfig.json` apply. Run the entire pipeline in order:

```powershell
python scripts\run_analysis.py
```

Individual stages are available when their prerequisite outputs already exist:

```powershell
python scripts\run_analysis.py --stage reconcile
python scripts\run_analysis.py --stage clean
python scripts\run_analysis.py --stage network
python scripts\run_analysis.py --stage sensitivity
python scripts\run_analysis.py --stage sensitivity-report
```

Run focused tests:

```powershell
python -m unittest discover -s tests -v
```

## Analysis definition

- The graph is undirected and bipartite, with separate director-role and lead-actor-role nodes.
- The `star` field is one recorded lead actor per row; the graph is not a complete cast or actor–actor co-starring network.
- Every retained row contributes one to its director–lead-actor edge weight. Weights represent repeated rows and are not shortest-path distances.
- One missing-`star` row and 31 rows with generic `Director`/`Directors` labels are excluded from network input to reproduce the provided manuscript. Original rows and reasons are retained in outputs.
- Approximate normalized betweenness is computed on the largest connected component, with `k=1000`, unweighted paths, and baseline seed 42.
- Sensitivity runs use 30 unique fixed seeds, including 42 and 2026. All graph and betweenness parameters remain fixed. Spearman rho, Kendall tau-b, score variation, rank variation, and top-10 frequency are reported; means alone are not used to claim stability.
- Title/year and name-resolution candidates are flagged for manual review only. The pipeline does not automatically delete, merge, or infer identities.

See `docs/methods_and_reproducibility.md` for parameter rationale and interpretation limits.

## Main outputs

The `outputs/` directory is generated when the pipeline runs. It includes the source reconciliation, missing-value and duplicate reports, retained/excluded rows and change log, network tables, per-seed scores/ranks, rank-correlation summaries, sensitivity interpretation, and 300-dpi PNG figures.

## Publication/repository guidance

Publish this project directory as the repository root (or as a clearly scoped subdirectory in a larger repository). Include the analysis code, configuration, reports, and dependency pins. Disclose the local dataset's provenance limitations; only redistribute the CSV if its license and source terms have been checked for the exact copy.
