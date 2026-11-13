"""Проверка обхода в ширину на локальном графе."""

import unittest
from pathlib import Path

from src.main import collect_graph, load_config

CONFIG = Path(__file__).with_name("config_graph.xml")


class GraphTests(unittest.TestCase):
    """Проверяет циклы, общие вершины, глубину и фильтр."""

    def graph(self, depth="3", fragment=""):
        """Строит тестовый граф с указанными ограничениями."""
        values = load_config(CONFIG)
        values.update(max_depth=depth, filter_substring=fragment)
        graph = collect_graph(values, CONFIG)
        return {
            name: [child[0] for child in children]
            for (name, _), children in graph.items()
        }

    def test_cycle_and_shared_node(self):
        """D посещается один раз, а ребро из D в A сохраняется."""
        graph = self.graph()
        self.assertEqual(list(graph), ["A", "B", "C", "D", "E"])
        self.assertEqual(graph["B"], ["D"])
        self.assertEqual(graph["C"], ["D", "E"])
        self.assertEqual(graph["D"], ["A"])

    def test_max_depth(self):
        """У вершин на предельной глубине соседи не запрашиваются."""
        self.assertEqual(self.graph("1"), {"A": ["B", "C"], "B": [], "C": []})
        self.assertEqual(self.graph("0"), {"A": []})

    def test_filter(self):
        """Фильтр исключает D из обеих веток."""
        graph = self.graph(fragment="D")
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": ["E"], "E": []})
