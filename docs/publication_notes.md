# Publication update notes

Before submission, update the manuscript using values generated in `outputs/` after a full run. Do not copy previous manuscript results without checking them against the local output.

1. **Data availability/reconciliation:** identify the source page, the page version and metadata date observed, the date the page was checked, and the local CSV SHA-256. State that the local file has 7,668 rows and 15 columns and that Kaggle's current page description reports 6,820 rows for 1986–2016. Exact file identity remains unverified because the public version-2 archive was unavailable during the check. Do not invent a local revision or historical download date.
2. **Data preprocessing:** report missing values, normalized title-year candidate checks, exact duplicate counts, the 1 missing-`star` exclusion, the 31 generic-director exclusions, and the no-auto-merge entity policy from the generated cleaning report.
3. **Network definition:** retain the role-specific director–lead-actor bipartite graph, edge weights as repeated retained rows, and unweighted shortest-path definition. Explain that `star` contains one recorded lead actor per row and does not represent a full cast.
4. **Betweenness sensitivity:** replace the two-seed-only stability claim with 30-seed results. Report score/rank variability and both Spearman and Kendall agreement, including the comparison baseline and scope (all largest-component nodes, directors, or lead actors). Avoid equating high correlation with invariant top ranks.
5. **Code availability:** publish the scoped project directory or archive its exact revision, and state the actual repository URL/identifier only after it exists. Include the environment and configuration.

The generated reports are descriptive results from this local file. Revisit conclusions if a verifiable source-version file, stable entity identifiers, or a different graph specification becomes available.
