import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from movie_research.common import normalize_text
from movie_research.network import build_graph, largest_component


class AnalysisHelpersTest(unittest.TestCase):
    def test_text_normalization_ignores_case_spacing_and_punctuation(self) -> None:
        self.assertEqual(normalize_text("  THE-Film!!  "), "the film")

    def test_graph_aggregates_repeated_pairs_and_keeps_roles_distinct(self) -> None:
        frame = pd.DataFrame(
            [
                {"director": "Same Name", "star": "Same Name"},
                {"director": "Same Name", "star": "Same Name"},
                {"director": "Other Director", "star": "Same Name"},
            ]
        )
        config = {
            "cleaning": {"director_field": "director", "lead_actor_field": "star"},
            "network": {"director_role": "director", "lead_actor_role": "lead_actor"},
        }

        graph = build_graph(frame, config)

        self.assertEqual(graph.number_of_nodes(), 3)
        self.assertEqual(graph.number_of_edges(), 2)
        self.assertEqual(graph[("director", "Same Name")][("lead_actor", "Same Name")]["weight"], 2)
        self.assertIn(("director", "Same Name"), graph)
        self.assertIn(("lead_actor", "Same Name"), graph)
        self.assertEqual(largest_component(graph).number_of_nodes(), 3)


if __name__ == "__main__":
    unittest.main()
