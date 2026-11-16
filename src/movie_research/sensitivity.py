from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

from movie_research.common import OUTPUT_DIR, load_config, markdown_table, write_csv, write_json
from movie_research.network import build_graph, largest_component


def _compute_seed_scores(
    graph: nx.Graph,
    seed: int,
    k: int,
    normalized: bool,
) -> tuple[int, dict[tuple[str, str], float]]:
    scores = nx.betweenness_centrality(
        graph,
        k=k,
        normalized=normalized,
        weight=None,
        seed=seed,
    )
    return seed, scores


def _correlation_rows(scores: pd.DataFrame, seeds: list[int], baseline: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    pair_rows = []
    roles = ["all"] + sorted(scores["role"].unique().tolist())

    for seed in seeds:
        for role in roles:
            subset = scores if role == "all" else scores.loc[scores["role"] == role]
            current = subset.loc[subset["seed"] == seed, "betweenness"].to_numpy()
            reference = subset.loc[subset["seed"] == baseline, "betweenness"].to_numpy()
            rows.append(
                {
                    "seed": seed,
                    "reference_seed": baseline,
                    "scope": role,
                    "node_count": int(len(current)),
                    "spearman_rho": float(spearmanr(reference, current).statistic),
                    "kendall_tau_b": float(kendalltau(reference, current, variant="b").statistic),
                }
            )

    for seed_a, seed_b in combinations(seeds, 2):
        for role in roles:
            subset = scores if role == "all" else scores.loc[scores["role"] == role]
            a = subset.loc[subset["seed"] == seed_a, "betweenness"].to_numpy()
            b = subset.loc[subset["seed"] == seed_b, "betweenness"].to_numpy()
            pair_rows.append(
                {
                    "seed_a": seed_a,
                    "seed_b": seed_b,
                    "scope": role,
                    "spearman_rho": float(spearmanr(a, b).statistic),
                    "kendall_tau_b": float(kendalltau(a, b, variant="b").statistic),
                }
            )

    baseline_correlations = pd.DataFrame(rows)
    pairwise = pd.DataFrame(pair_rows)
    pairwise_summary = (
        pairwise.groupby("scope")
        .agg(
            seed_pairs=("spearman_rho", "size"),
            spearman_mean=("spearman_rho", "mean"),
            spearman_min=("spearman_rho", "min"),
            spearman_max=("spearman_rho", "max"),
            kendall_mean=("kendall_tau_b", "mean"),
            kendall_min=("kendall_tau_b", "min"),
            kendall_max=("kendall_tau_b", "max"),
        )
        .reset_index()
    )
    return baseline_correlations, pairwise_summary


def _baseline_correlation_summary(correlations: pd.DataFrame, baseline: int) -> pd.DataFrame:
    comparisons = correlations.loc[correlations["seed"] != baseline]
    return (
        comparisons.groupby("scope")
        .agg(
            compared_seeds=("seed", "nunique"),
            spearman_mean=("spearman_rho", "mean"),
            spearman_min=("spearman_rho", "min"),
            spearman_max=("spearman_rho", "max"),
            kendall_mean=("kendall_tau_b", "mean"),
            kendall_min=("kendall_tau_b", "min"),
            kendall_max=("kendall_tau_b", "max"),
        )
        .reset_index()
    )


def _top10_overlap_summary(scores: pd.DataFrame, seeds: list[int], baseline: int) -> pd.DataFrame:
    rows = []
    roles = sorted(scores["role"].unique().tolist())
    for role in roles:
        top_sets = {}
        subset = scores.loc[scores["role"] == role]
        for seed in seeds:
            top_sets[seed] = set(
                subset.loc[subset["seed"] == seed]
                .sort_values(["rank_within_role", "node_key"])
                .head(10)["node_key"]
            )
        reference = top_sets[baseline]
        for seed in seeds:
            if seed == baseline:
                continue
            overlap = len(reference & top_sets[seed])
            rows.append(
                {
                    "seed": seed,
                    "reference_seed": baseline,
                    "scope": role,
                    "top10_shared_nodes": overlap,
                    "top10_overlap_fraction": overlap / 10,
                }
            )
    return (
        pd.DataFrame(rows)
        .groupby("scope")
        .agg(
            compared_seeds=("seed", "nunique"),
            mean_shared_nodes=("top10_shared_nodes", "mean"),
            min_shared_nodes=("top10_shared_nodes", "min"),
            max_shared_nodes=("top10_shared_nodes", "max"),
            mean_overlap_fraction=("top10_overlap_fraction", "mean"),
            min_overlap_fraction=("top10_overlap_fraction", "min"),
            max_overlap_fraction=("top10_overlap_fraction", "max"),
        )
        .reset_index()
    )


def _summarize_sensitivity(
    scores: pd.DataFrame,
    seeds: list[int],
    baseline: int,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    grouped = scores.groupby(["node_key", "role", "name"], as_index=False).agg(
        mean_betweenness=("betweenness", "mean"),
        std_betweenness=("betweenness", "std"),
        min_betweenness=("betweenness", "min"),
        max_betweenness=("betweenness", "max"),
        mean_rank_within_role=("rank_within_role", "mean"),
        std_rank_within_role=("rank_within_role", "std"),
        min_rank_within_role=("rank_within_role", "min"),
        max_rank_within_role=("rank_within_role", "max"),
    )
    top10 = (
        scores.sort_values(["seed", "role", "rank_within_role", "node_key"])
        .groupby(["seed", "role"], group_keys=False)
        .head(10)
        .groupby(["node_key", "role", "name"])
        .size()
        .rename("top10_seed_count")
        .reset_index()
    )
    summary = grouped.merge(top10, on=["node_key", "role", "name"], how="left")
    summary["top10_seed_count"] = summary["top10_seed_count"].fillna(0).astype(int)
    summary["top10_seed_frequency"] = summary["top10_seed_count"] / len(seeds)
    summary["rank_range_within_role"] = (
        summary["max_rank_within_role"] - summary["min_rank_within_role"]
    )
    baseline_corr, pairwise_summary = _correlation_rows(scores, seeds, baseline)
    baseline_summary = _baseline_correlation_summary(baseline_corr, baseline)
    top10_summary = _top10_overlap_summary(scores, seeds, baseline)
    stable = summary.sort_values(
        ["role", "std_rank_within_role", "rank_range_within_role", "mean_rank_within_role"],
        ascending=[True, True, True, True],
    ).groupby("role", group_keys=False).head(1)
    variable = summary.sort_values(
        ["role", "std_rank_within_role", "rank_range_within_role", "mean_rank_within_role"],
        ascending=[True, False, False, False],
    ).groupby("role", group_keys=False).head(1)
    return summary, baseline_corr, pairwise_summary, baseline_summary, top10_summary, stable, variable


def _plot_variation(summary: pd.DataFrame, long: pd.DataFrame, output_dir: Path) -> None:
    selected = (
        summary.sort_values(["role", "mean_betweenness"], ascending=[True, False])
        .groupby("role", group_keys=False)
        .head(10)
        .copy()
    )
    roles = selected["role"].drop_duplicates().tolist()
    colors = plt.get_cmap("tab10")

    fig, axes = plt.subplots(1, len(roles), figsize=(14, max(6, len(selected) * 0.27)), squeeze=False)
    for axis, role in zip(axes[0], roles):
        group = selected.loc[selected["role"] == role].sort_values("mean_betweenness")
        positions = np.arange(len(group))
        for position, row in zip(positions, group.itertuples()):
            values = long.loc[
                (long["role"] == role) & (long["node_key"] == row.node_key), "betweenness"
            ].to_numpy()
            axis.scatter(values, np.full(len(values), position), s=11, alpha=0.45, color=colors(0))
        axis.errorbar(
            group["mean_betweenness"],
            positions,
            xerr=group["std_betweenness"].fillna(0),
            fmt="D",
            color="black",
            ecolor="black",
            capsize=2,
            markersize=4,
            label="Mean ± SD",
        )
        axis.set_yticks(positions)
        axis.set_yticklabels(group["name"].astype(str).tolist())
        axis.tick_params(axis="y", labelleft=True)
        axis.set_title(role.replace("_", " ").title())
        axis.set_xlabel("Normalized betweenness")
        axis.grid(axis="x", linestyle=":", alpha=0.5)
    fig.suptitle("Betweenness score variation across 30 seeds (top 10 per role)")
    fig.tight_layout()
    fig.savefig(output_dir / "betweenness_score_variation.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, len(roles), figsize=(14, max(6, len(selected) * 0.27)), squeeze=False)
    for axis, role in zip(axes[0], roles):
        group = selected.loc[selected["role"] == role].sort_values("mean_rank_within_role", ascending=False)
        positions = np.arange(len(group))
        for position, row in zip(positions, group.itertuples()):
            node_ranks = long.loc[
                (long["role"] == role) & (long["node_key"] == row.node_key), "rank_within_role"
            ].to_numpy()
            axis.scatter(node_ranks, np.full(len(node_ranks), position), s=11, alpha=0.45, color=colors(0))
        axis.errorbar(
            group["mean_rank_within_role"],
            positions,
            xerr=np.vstack(
                [
                    group["mean_rank_within_role"] - group["min_rank_within_role"],
                    group["max_rank_within_role"] - group["mean_rank_within_role"],
                ]
            ),
            fmt="D",
            color="black",
            ecolor="black",
            capsize=2,
            markersize=4,
        )
        axis.set_yticks(positions)
        axis.set_yticklabels(group["name"].astype(str).tolist())
        axis.tick_params(axis="y", labelleft=True)
        axis.set_title(role.replace("_", " ").title())
        axis.set_xlabel("Rank within role (1 = highest)")
        axis.invert_xaxis()
        axis.grid(axis="x", linestyle=":", alpha=0.5)
    fig.suptitle("Rank variation across 30 seeds (top 10 per role)")
    fig.tight_layout()
    fig.savefig(output_dir / "betweenness_rank_variation.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_sensitivity() -> dict[str, Any]:
    config = load_config()
    input_file = OUTPUT_DIR / "analysis_records.csv"
    if not input_file.is_file():
        raise FileNotFoundError("Run the cleaning stage first; analysis_records.csv is missing.")
    frame = pd.read_csv(input_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    graph = build_graph(frame, config)
    component = largest_component(graph)
    settings = config["network"]
    seeds = [int(seed) for seed in settings["sensitivity_seeds"]]
    baseline = int(settings["baseline_seed"])
    if len(seeds) < 3 or len(seeds) != len(set(seeds)):
        raise ValueError("Sensitivity seeds must contain at least three unique values.")
    if baseline not in seeds:
        raise ValueError("The baseline seed must be included among sensitivity seeds.")

    k = min(int(settings["betweenness_k"]), component.number_of_nodes())
    long_rows: list[dict[str, Any]] = []
    workers = min(8, len(seeds), os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _compute_seed_scores,
                component,
                seed,
                k,
                bool(settings["betweenness_normalized"]),
            ): seed
            for seed in seeds
        }
        for future in as_completed(futures):
            seed, values = future.result()
            print(f"Completed sensitivity seed {seed}.", flush=True)
            role_values: dict[str, list[tuple[str, float]]] = {}
            for node, value in values.items():
                role_values.setdefault(node[0], []).append((f"{node[0]}::{node[1]}", float(value)))
            ranks: dict[str, float] = {}
            for items in role_values.values():
                rank_series = pd.Series({node_key: score for node_key, score in items}).rank(
                    ascending=False, method="average"
                )
                ranks.update(rank_series.to_dict())
            for node, score in values.items():
                node_key = f"{node[0]}::{node[1]}"
                long_rows.append(
                    {
                        "seed": seed,
                        "node_key": node_key,
                        "role": node[0],
                        "name": node[1],
                        "betweenness": float(score),
                        "rank_within_role": float(ranks[node_key]),
                    }
                )
    long = pd.DataFrame(long_rows).sort_values(["seed", "node_key"]).reset_index(drop=True)
    (
        summary,
        baseline_corr,
        pairwise_summary,
        baseline_summary,
        top10_summary,
        stable,
        variable,
    ) = _summarize_sensitivity(long, seeds, baseline)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(long, OUTPUT_DIR / "sensitivity_scores_and_ranks.csv")
    write_csv(summary.sort_values(["role", "std_rank_within_role"]), OUTPUT_DIR / "sensitivity_summary.csv")
    write_csv(baseline_corr, OUTPUT_DIR / "sensitivity_correlations_vs_seed42.csv")
    write_csv(pairwise_summary, OUTPUT_DIR / "sensitivity_pairwise_correlation_summary.csv")
    _plot_variation(summary, long, OUTPUT_DIR)
    result = {
        "seed_count": len(seeds),
        "seeds": seeds,
        "baseline_seed": baseline,
        "k_requested": int(settings["betweenness_k"]),
        "k_used": k,
        "process_workers": workers,
        "nodes_in_largest_component": int(component.number_of_nodes()),
        "graph_edges_in_largest_component": int(component.number_of_edges()),
        "rank_definition": "Descending betweenness, average ranks for ties, calculated separately within each role.",
        "correlation_reference": f"Each sensitivity result is compared to seed {baseline}; pairwise summaries use all seed pairs.",
        "stable_nodes_by_role": stable[["role", "name", "std_rank_within_role", "rank_range_within_role"]].to_dict(orient="records"),
        "most_variable_nodes_by_role": variable[["role", "name", "std_rank_within_role", "rank_range_within_role"]].to_dict(orient="records"),
        "correlation_vs_baseline_summary": baseline_summary.to_dict(orient="records"),
        "top10_overlap_vs_baseline": top10_summary.to_dict(orient="records"),
        "pairwise_correlations": pairwise_summary.to_dict(orient="records"),
        "interpretation_caution": "High rank correlation or a high top-10 frequency is not by itself proof of score stability. Interpret these alongside per-node score standard deviations, rank standard deviations/ranges, and the sampled-source approximation used by NetworkX.",
    }
    write_json(OUTPUT_DIR / "sensitivity_report.json", result)
    _write_sensitivity_markdown(result, summary, baseline_corr, OUTPUT_DIR / "sensitivity_report.md")
    return result


def refresh_sensitivity_report() -> dict[str, Any]:
    long_path = OUTPUT_DIR / "sensitivity_scores_and_ranks.csv"
    summary_path = OUTPUT_DIR / "sensitivity_summary.csv"
    correlation_path = OUTPUT_DIR / "sensitivity_correlations_vs_seed42.csv"
    report_path = OUTPUT_DIR / "sensitivity_report.json"
    required = (long_path, summary_path, correlation_path, report_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Existing sensitivity outputs are required: {', '.join(missing)}")

    result = json.loads(report_path.read_text(encoding="utf-8"))
    long = pd.read_csv(long_path, encoding="utf-8-sig")
    baseline = int(result["baseline_seed"])
    seeds = [int(seed) for seed in result["seeds"]]
    (
        summary,
        correlations,
        pairwise_summary,
        baseline_summary,
        top10_summary,
        stable,
        variable,
    ) = _summarize_sensitivity(long, seeds, baseline)
    write_csv(summary.sort_values(["role", "std_rank_within_role"]), summary_path)
    write_csv(correlations, correlation_path)
    write_csv(pairwise_summary, OUTPUT_DIR / "sensitivity_pairwise_correlation_summary.csv")
    result["stable_nodes_by_role"] = stable[
        ["role", "name", "std_rank_within_role", "rank_range_within_role"]
    ].to_dict(orient="records")
    result["most_variable_nodes_by_role"] = variable[
        ["role", "name", "std_rank_within_role", "rank_range_within_role"]
    ].to_dict(orient="records")
    result["correlation_vs_baseline_summary"] = baseline_summary.to_dict(orient="records")
    result["top10_overlap_vs_baseline"] = top10_summary.to_dict(orient="records")
    result["pairwise_correlations"] = pairwise_summary.to_dict(orient="records")
    write_json(report_path, result)
    _plot_variation(summary, long, OUTPUT_DIR)
    _write_sensitivity_markdown(result, summary, correlations, OUTPUT_DIR / "sensitivity_report.md")
    return result


def _write_sensitivity_markdown(
    result: dict[str, Any],
    summary: pd.DataFrame,
    correlations: pd.DataFrame,
    path: Path,
) -> None:
    pair_table = markdown_table(pd.DataFrame(result["pairwise_correlations"]))
    stable_table = markdown_table(pd.DataFrame(result["stable_nodes_by_role"]))
    variable_table = markdown_table(pd.DataFrame(result["most_variable_nodes_by_role"]))
    score_sd_median = summary.groupby("role")["std_betweenness"].median().to_dict()
    score_sd_table = pd.DataFrame(
        [{"role": role, "median_score_sd_across_nodes": value} for role, value in score_sd_median.items()]
    )
    score_sd_table = markdown_table(score_sd_table)
    baseline_rows = correlations.loc[correlations["seed"] == 2026]
    seed_2026_table = markdown_table(
        baseline_rows[["scope", "spearman_rho", "kendall_tau_b"]].assign(comparison="seed 2026 vs seed 42")
        [["comparison", "scope", "spearman_rho", "kendall_tau_b"]]
    )
    baseline_table = markdown_table(
        pd.DataFrame(result["correlation_vs_baseline_summary"])
    )
    overlap_table = markdown_table(pd.DataFrame(result["top10_overlap_vs_baseline"]))
    content = f"""# Betweenness sensitivity analysis

## Design

The same retained rows, undirected role-specific bipartite graph, largest connected component, normalized unweighted betweenness, and `k={result['k_used']}` were used for each of {result['seed_count']} unique seeds: `{', '.join(map(str, result['seeds']))}`. Seed {result['baseline_seed']} is the reference and seed 2026 is retained for comparison with the manuscript. The seed set broadens the two-run comparison to a reproducible empirical assessment; it does not create a formal error bound or test data/identity uncertainty.

Betweenness was estimated by NetworkX {nx.__version__}'s sampled-source approximation. Every node has a score in each run within the same largest component ({result['nodes_in_largest_component']:,} nodes; {result['graph_edges_in_largest_component']:,} edges). Ranks are descending and calculated separately within each role, with average ranks for ties.

## Agreement with baseline seed {result['baseline_seed']}

Mean, minimum, and maximum rank correlation across the {len(result['seeds']) - 1} non-baseline runs:

{baseline_table}

Seed 2026 comparison retained from the manuscript:

{seed_2026_table}

## All-pairs seed agreement

{pair_table}

## Top-10 overlap with baseline

The top 10 are selected within each role; equal ranks at the cutoff are deterministically ordered by node key. The table summarizes the number of shared nodes between the baseline top 10 and each non-baseline seed.

{overlap_table}

## Score variation

Median per-node score standard deviation by role:

{score_sd_table}

Per-node means, standard deviations, minima, and maxima are in `sensitivity_summary.csv`. Stability is not inferred from means alone: score variation, rank standard deviation/range, top-10 frequency, and rank correlations should be considered together. Per-seed scores and ranks are available in `sensitivity_scores_and_ranks.csv`.

## Most stable and most variable rank by role

The following summaries identify the minimum and maximum across role-specific rank standard deviations (ties broken by rank range); these are descriptive extrema, not claims that a node's true industry position is stable or unstable.

Most stable:

{stable_table}

Most variable:

{variable_table}

The figures `betweenness_score_variation.png` and `betweenness_rank_variation.png` show score and rank variation for the top 10 nodes per role. Score and rank outputs are both necessary: a similar mean score can coexist with variable ranks, and high correlation across the full node set can coexist with movement among top-ranked nodes.

## Limitations

This sensitivity analysis varies only the random source sample used to approximate betweenness. It holds the graph and all parameters fixed, so it does not test sensitivity to missing records, duplicate title-year pairs, source revisions, alias/homonym resolution, or graph-definition choices. The dataset contains only one recorded `star` field per row, and scores apply only to the largest connected component.
"""
    path.write_text(content, encoding="utf-8", newline="\n")
