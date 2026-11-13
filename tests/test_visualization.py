"""Проверки генерации Mermaid, SVG и ASCII."""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.main import collect_graph, load_config
from src.visualization import ascii_tree, save_visualization, svg_text

CONFIG = Path(__file__).with_name("config_graph.xml")
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}


class VisualizationTests(unittest.TestCase):
    """Проверяет визуализацию общего узла, цикла и пустого графа."""

    def setUp(self):
        """Загружает граф с общим пакетом D и циклом D -> A."""
        self.graph = collect_graph(load_config(CONFIG), CONFIG)

    def test_mermaid_and_svg(self):
        """Оба файла сохраняют пять вершин и шесть рёбер."""
        with tempfile.TemporaryDirectory() as folder:
            svg = Path(folder) / "graph.svg"
            mermaid = save_visualization(self.graph, svg)
            content = mermaid.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("flowchart TD\n"))
            self.assertEqual(content.count('["'), 5)
            self.assertEqual(content.count(" --> "), 6)
            self.assertIn("n3 --> n0", content)
            root = ElementTree.parse(svg).getroot()
            self.assertEqual(len(root.findall(".//svg:text", SVG_NAMESPACE)), 5)
            edges = root.findall("svg:g/svg:path", SVG_NAMESPACE)
            self.assertEqual(len(edges), 6)

    def test_ascii_tree(self):
        """Дерево показывает повторные A и D и завершает обход."""
        lines = ascii_tree(self.graph).splitlines()
        self.assertEqual(lines[0], "A")
        self.assertIn("A [repeat]", "\n".join(lines))
        self.assertIn("D [repeat]", "\n".join(lines))
        self.assertEqual(len(lines), 7)

    def test_empty_graph(self):
        """Пустой граф даёт корректный SVG и сообщение в терминале."""
        root = ElementTree.fromstring(svg_text({}))
        self.assertIn("Граф пуст", "".join(root.itertext()))
        self.assertEqual(ascii_tree({}), "Граф пуст.")
