from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_research.cleaning import run_cleaning
from movie_research.network import run_network
from movie_research.reconciliation import run_reconciliation
from movie_research.sensitivity import refresh_sensitivity_report, run_sensitivity


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the reproducible movie-network analysis.")
    parser.add_argument(
        "--stage",
        choices=("all", "reconcile", "clean", "network", "sensitivity", "sensitivity-report"),
        default="all",
        help="Run the full pipeline or one stage; later stages require prior outputs.",
    )
    stage = parser.parse_args().stage
    actions = {
        "reconcile": run_reconciliation,
        "clean": run_cleaning,
        "network": run_network,
        "sensitivity": run_sensitivity,
        "sensitivity-report": refresh_sensitivity_report,
    }
    stages = ("reconcile", "clean", "network", "sensitivity") if stage == "all" else (stage,)
    for current in stages:
        print(f"Running stage: {current}")
        result = actions[current]()
        if current == "sensitivity":
            print(f"Completed {result['seed_count']} sensitivity runs.")
    print("Analysis complete. Inspect the outputs/ directory.")


if __name__ == "__main__":
    main()
