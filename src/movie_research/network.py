from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from movie_research.common import (
    OUTPUT_DIR,
    load_config,
    markdown_table,
    write_csv,
    write_json,
)


def build_graph(frame: pd.DataFrame, config: dict[str, Any] | None = None) -> nx.Graph:
    config = config or load_config()
    director_field = config["cleaning"]["director_field"]
    actor_field = config["cleaning"]["lead_actor_field"]
    director_role = config["network"]["director_role"]
    actor_role = config["network"]["lead_actor_role"]
    graph = nx.Graph()

    for row in frame.to_dict(orient="records"):
        director = str(row[director_field]).strip()
        actor = str(row[actor_field]).strip()
        if not director or not actor:
            raise ValueError("Network input contains an empty director or star label.")
        director_node = (director_role, director)
        actor_node = (actor_role, actor)
        graph.add_node(director_node, bipartite=0, role=director_role, label=director)
        graph.add_node(actor_node, bipartite=1, role=actor_role, label=actor)
        if graph.has_edge(director_node, actor_node):
            graph[director_node][actor_node]["weight"] += 1
        else:
            graph.add_edge(director_node, actor_node, weight=1)
    return graph


def largest_component(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0:
        raise ValueError("Cannot analyze an empty graph.")
    component_nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(component_nodes).copy()


def _node_table(graph: nx.Graph, component: nx.Graph, betweenness: dict[tuple[str, str], float]) -> pd.DataFrame:
    rows = []
    for node, attributes in graph.nodes(data=True):
        role, label = node
        rows.append(
            {
                "node_key": f"{role}::{label}",
                "role": role,
                "name": label,
                "degree": int(graph.degree(node)),
                "strength": int(graph.degree(node, weight="weight")),
                "in_largest_component": node in component,
                "betweenness_lcc": betweenness.get(node),
            }
        )
    table = pd.DataFrame(rows)
    for metric in ("degree", "strength", "betweenness_lcc"):
        table[f"{metric}_rank_within_role"] = table.groupby("role")[metric].rank(
            ascending=False, method="min", na_option="bottom"
        )
    return table.sort_values(["role", "betweenness_lcc", "degree"], ascending=[True, False, False])


def run_network() -> dict[str, Any]:
    config = load_config()
    frame_path = OUTPUT_DIR / "analysis_records.csv"
    if not frame_path.is_file():
        raise FileNotFoundError("Run the cleaning stage first; analysis_records.csv is missing.")
    frame = pd.read_csv(frame_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    graph = build_graph(frame, config)
    component = largest_component(graph)
    settings = config["network"]
    k = min(int(settings["betweenness_k"]), component.number_of_nodes())
    betweenness = nx.betweenness_centrality(
        component,
        k=k,
        normalized=bool(settings["betweenness_normalized"]),
        weight=None,
        seed=int(settings["baseline_seed"]),
    )
    nodes = _node_table(graph, component, betweenness)
    directors = sum(1 for node in graph.nodes if node[0] == settings["director_role"])
    actors = graph.number_of_nodes() - directors
    density = graph.number_of_edges() / (directors * actors) if directors and actors else 0.0
    summary = {
        "analysis_rows": int(len(frame)),
        "director_nodes": int(directors),
        "lead_actor_nodes": int(actors),
        "total_nodes": int(graph.number_of_nodes()),
        "distinct_edges": int(graph.number_of_edges()),
        "edge_weight_sum": int(sum(data["weight"] for _, _, data in graph.edges(data=True))),
        "edges_weight_gt_1": int(sum(data["weight"] > 1 for _, _, data in graph.edges(data=True))),
        "connected_components": int(nx.number_connected_components(graph)),
        "largest_component_nodes": int(component.number_of_nodes()),
        "largest_component_edges": int(component.number_of_edges()),
        "largest_component_node_share": float(component.number_of_nodes() / graph.number_of_nodes()),
        "bipartite_density": float(density),
        "betweenness": {
            "component": "largest_connected_component",
            "normalized": bool(settings["betweenness_normalized"]),
            "k_requested": int(settings["betweenness_k"]),
            "k_used": k,
            "seed": int(settings["baseline_seed"]),
            "edge_weight_used_as_distance": False,
            "software_networkx": nx.__version__,
        },
        "node_class_degree": {
            role: {
                "median": float(nodes.loc[nodes["role"] == role, "degree"].median()),
                "mean": float(nodes.loc[nodes["role"] == role, "degree"].mean()),
                "degree_one_count": int((nodes.loc[nodes["role"] == role, "degree"] == 1).sum()),
            }
            for role in (settings["director_role"], settings["lead_actor_role"])
        },
    }
    edge_rows = [
        {
            "director": left[1] if left[0] == settings["director_role"] else right[1],
            "lead_actor": right[1] if right[0] == settings["lead_actor_role"] else left[1],
            "weight_rows": data["weight"],
        }
        for left, right, data in graph.edges(data=True)
    ]
    write_csv(nodes, OUTPUT_DIR / "network_nodes_baseline.csv")
    write_csv(pd.DataFrame(edge_rows, columns=["director", "lead_actor", "weight_rows"]), OUTPUT_DIR / "network_edges.csv")
    write_json(OUTPUT_DIR / "network_summary.json", summary)
    _write_network_markdown(nodes, summary, OUTPUT_DIR / "network_summary.md")
    return summary


def _write_network_markdown(nodes: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    top = nodes.loc[nodes["in_largest_component"]].sort_values(
        "betweenness_lcc", ascending=False
    ).groupby("role", group_keys=False).head(5)
    top_table = markdown_table(top[["role", "name", "degree", "strength", "betweenness_lcc"]])
    content = f"""# Network analysis summary

## Graph construction

The graph is an undirected, role-specific bipartite graph. Each retained row adds one director-role to lead-actor-role tie; repeated rows increase `weight_rows` on the same pair. Same display names in the two roles remain separate nodes. Edge weights are counts, not distances, and are not passed as shortest-path lengths.

## Network structure

| Measure | Value |
|---|---:|
| Analysis rows | {summary['analysis_rows']:,} |
| Director-role nodes | {summary['director_nodes']:,} |
| Lead-actor-role nodes | {summary['lead_actor_nodes']:,} |
| Total role-specific nodes | {summary['total_nodes']:,} |
| Distinct edges | {summary['distinct_edges']:,} |
| Sum of edge weights | {summary['edge_weight_sum']:,} |
| Edges with weight > 1 | {summary['edges_weight_gt_1']:,} |
| Connected components | {summary['connected_components']:,} |
| Largest component | {summary['largest_component_nodes']:,} nodes; {summary['largest_component_edges']:,} edges |
| Largest-component node share | {summary['largest_component_node_share']:.4%} |
| Bipartite density | {summary['bipartite_density']:.6f} |

## Baseline betweenness

Approximate normalized betweenness was calculated on the largest connected component using NetworkX {summary['betweenness']['software_networkx']}, `k={summary['betweenness']['k_used']}`, seed {summary['betweenness']['seed']}, and unweighted shortest paths. Nodes outside that component have no reported betweenness score in this analysis.

### Highest baseline betweenness by role

{top_table}

This is a single sampled-source estimate, not a stability conclusion. See the multi-seed sensitivity report and rank correlations before interpreting rankings. The measure describes shortest-path position in this observed graph; it does not establish real-world brokerage, influence, or causal impact.
"""
    path.write_text(content, encoding="utf-8", newline="\n")
