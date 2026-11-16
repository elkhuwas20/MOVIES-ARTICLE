# Network analysis summary

## Graph construction

The graph is an undirected, role-specific bipartite graph. Each retained row adds one director-role to lead-actor-role tie; repeated rows increase `weight_rows` on the same pair. Same display names in the two roles remain separate nodes. Edge weights are counts, not distances, and are not passed as shortest-path lengths.

## Network structure

| Measure | Value |
|---|---:|
| Analysis rows | 7,636 |
| Director-role nodes | 2,946 |
| Lead-actor-role nodes | 2,797 |
| Total role-specific nodes | 5,743 |
| Distinct edges | 6,994 |
| Sum of edge weights | 7,636 |
| Edges with weight > 1 | 449 |
| Connected components | 796 |
| Largest component | 3,898 nodes; 5,944 edges |
| Largest-component node share | 67.8739% |
| Bipartite density | 0.000849 |

## Baseline betweenness

Approximate normalized betweenness was calculated on the largest connected component using NetworkX 3.7, `k=1000`, seed 42, and unweighted shortest paths. Nodes outside that component have no reported betweenness score in this analysis.

### Highest baseline betweenness by role

| role | name | degree | strength | betweenness_lcc |
| --- | --- | --- | --- | --- |
| lead_actor | Bruce Willis | 32 | 34 | 0.053142532040065936 |
| lead_actor | Nicolas Cage | 38 | 43 | 0.04487804802587934 |
| lead_actor | Robert De Niro | 31 | 41 | 0.039598842518705 |
| director | Ridley Scott | 20 | 23 | 0.03612979479395919 |
| lead_actor | Tom Cruise | 27 | 34 | 0.033862294038470395 |
| lead_actor | Robin Williams | 25 | 27 | 0.02673989265827859 |
| director | Steven Spielberg | 21 | 27 | 0.02438983861743438 |
| director | Walter Hill | 16 | 17 | 0.02370674566538215 |
| director | Joel Schumacher | 20 | 22 | 0.02359219704508352 |
| director | Lasse Hallström | 15 | 15 | 0.022878439961068073 |

This is a single sampled-source estimate, not a stability conclusion. See the multi-seed sensitivity report and rank correlations before interpreting rankings. The measure describes shortest-path position in this observed graph; it does not establish real-world brokerage, influence, or causal impact.
