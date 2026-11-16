# Betweenness sensitivity analysis

## Design

The same retained rows, undirected role-specific bipartite graph, largest connected component, normalized unweighted betweenness, and `k=1000` were used for each of 30 unique seeds: `42, 2026, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27`. Seed 42 is the reference and seed 2026 is retained for comparison with the manuscript. The seed set broadens the two-run comparison to a reproducible empirical assessment; it does not create a formal error bound or test data/identity uncertainty.

Betweenness was estimated by NetworkX 3.7's sampled-source approximation. Every node has a score in each run within the same largest component (3,898 nodes; 5,944 edges). Ranks are descending and calculated separately within each role, with average ranks for ties.

## Agreement with baseline seed 42

Mean, minimum, and maximum rank correlation across the 29 non-baseline runs:

| scope | compared_seeds | spearman_mean | spearman_min | spearman_max | kendall_mean | kendall_min | kendall_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 29 | 0.9809186268326043 | 0.9796783855170013 | 0.9827039310654363 | 0.9069425581867864 | 0.9034259225584451 | 0.911751467060852 |
| director | 29 | 0.9751040249911391 | 0.9723881390162084 | 0.9778553600925002 | 0.8928968474306013 | 0.8865168009737183 | 0.9000426193693183 |
| lead_actor | 29 | 0.9861469530334177 | 0.9844699026007548 | 0.9876575056603137 | 0.9214443199444113 | 0.9167452458187222 | 0.9267290870989496 |

Seed 2026 comparison retained from the manuscript:

| comparison | scope | spearman_rho | kendall_tau_b |
| --- | --- | --- | --- |
| seed 2026 vs seed 42 | all | 0.9813117536824187 | 0.9087155533646392 |
| seed 2026 vs seed 42 | director | 0.9759692704951753 | 0.8962460797255021 |
| seed 2026 vs seed 42 | lead_actor | 0.9862003347921547 | 0.9216114285054687 |

## All-pairs seed agreement

| scope | seed_pairs | spearman_mean | spearman_min | spearman_max | kendall_mean | kendall_min | kendall_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | 435 | 0.9801033467158554 | 0.9770359934147342 | 0.9829063452142905 | 0.904480856257902 | 0.8966394569731452 | 0.9121460037199516 |
| director | 435 | 0.9744056429386442 | 0.9704903150661331 | 0.9784624747143997 | 0.8908126960709378 | 0.880631205385072 | 0.901188157162339 |
| lead_actor | 435 | 0.9853461612422656 | 0.9817981350108678 | 0.9884808260893081 | 0.9188509279218899 | 0.9089511198015022 | 0.929502747681473 |

## Top-10 overlap with baseline

The top 10 are selected within each role; equal ranks at the cutoff are deterministically ordered by node key. The table summarizes the number of shared nodes between the baseline top 10 and each non-baseline seed.

| scope | compared_seeds | mean_shared_nodes | min_shared_nodes | max_shared_nodes | mean_overlap_fraction | min_overlap_fraction | max_overlap_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| director | 29 | 9.068965517241379 | 8 | 10 | 0.9068965517241377 | 0.8 | 1.0 |
| lead_actor | 29 | 7.793103448275862 | 6 | 10 | 0.7793103448275861 | 0.6 | 1.0 |

## Score variation

Median per-node score standard deviation by role:

| role | median_score_sd_across_nodes |
| --- | --- |
| director | 0.00010769536486541736 |
| lead_actor | 4.9905116417636825e-06 |

Per-node means, standard deviations, minima, and maxima are in `sensitivity_summary.csv`. Stability is not inferred from means alone: score variation, rank standard deviation/range, top-10 frequency, and rank correlations should be considered together. Per-seed scores and ranks are available in `sensitivity_scores_and_ranks.csv`.

## Most stable and most variable rank by role

The following summaries identify the minimum and maximum across role-specific rank standard deviations (ties broken by rank range); these are descriptive extrema, not claims that a node's true industry position is stable or unstable.

Most stable:

| role | name | std_rank_within_role | rank_range_within_role |
| --- | --- | --- | --- |
| director | Ridley Scott | 0.0 | 0.0 |
| lead_actor | 50 Cent | 0.0 | 0.0 |

Most variable:

| role | name | std_rank_within_role | rank_range_within_role |
| --- | --- | --- | --- |
| director | Philippe Mora | 225.4199943451661 | 479.5 |
| lead_actor | Shameik Moore | 154.01567318363058 | 334.5 |

The figures `betweenness_score_variation.png` and `betweenness_rank_variation.png` show score and rank variation for the top 10 nodes per role. Score and rank outputs are both necessary: a similar mean score can coexist with variable ranks, and high correlation across the full node set can coexist with movement among top-ranked nodes.

## Limitations

This sensitivity analysis varies only the random source sample used to approximate betweenness. It holds the graph and all parameters fixed, so it does not test sensitivity to missing records, duplicate title-year pairs, source revisions, alias/homonym resolution, or graph-definition choices. The dataset contains only one recorded `star` field per row, and scores apply only to the largest connected component.
