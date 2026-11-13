"""Проверки порядка загрузки на локальном тестовом репозитории."""

import unittest
from pathlib import Path

from src.load_order import calculate_load_order
from src.main import collect_graph, load_config

CONFIG = Path(__file__).with_name("config_graph.xml")


class LoadOrderTests(unittest.TestCase):
    """Проверяет полный и частичный порядок."""

    def order(self, depth="3", fragment=""):
        """Строит граф и возвращает имена готовых и заблокированных узлов."""
        values = load_config(CONFIG)
        values.update(max_depth=depth, filter_substring=fragment)
        graph = collect_graph(values, CONFIG)
        order, blocked = calculate_load_order(graph)
        return [name for name, _ in order], [name for name, _ in blocked]

    def test_shared_dependency(self):
        """Общий пакет D стоит раньше B и C и встречается один раз."""
        self.assertEqual(self.order(depth="2"), (["D", "E", "B", "C", "A"], []))

    def test_cycle(self):
        """У цикла остаются заблокированные вершины, но E доступен."""
        self.assertEqual(self.order(), (["E"], ["A", "B", "C", "D"]))

    def test_filter(self):
        """После исключения D порядок определяется для всего графа."""
        self.assertEqual(self.order(fragment="D"), (["B", "E", "C", "A"], []))

    def test_only_root(self):
        """При глубине ноль остаётся только исходный пакет."""
        self.assertEqual(self.order(depth="0"), (["A"], []))
