"""Проверки параметров XML-конфигурации."""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.main import DEFAULT_CONFIG, load_config


class ConfigTests(unittest.TestCase):
    """Проверяет оба режима и ошибочные значения."""

    def setUp(self):
        """Создаёт временный каталог для конфигураций."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "config.xml"

    def load(self, **changes):
        """Подставляет тестовые значения и читает полученный XML."""
        tree = ElementTree.parse(DEFAULT_CONFIG)
        for name, value in changes.items():
            tree.find(name).text = value
        tree.write(self.path, encoding="utf-8")
        return load_config(self.path)

    def test_default_config(self):
        """Все восемь полей корректно читаются."""
        values = self.load()
        self.assertEqual(len(values), 8)
        self.assertEqual(values["package"], "regex")
        self.assertEqual(values["filter_substring"], "")

    def test_invalid_parameters(self):
        """Ошибки для каждого поля содержат его имя."""
        cases = {
            "package": "bad/name",
            "repository": "ftp://example.com",
            "test_mode": "yes",
            "version": "1.11",
            "output": "graph.png",
            "ascii_tree": "maybe",
            "max_depth": "-1",
            "filter_substring": "re*",
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, name):
                    self.load(**{name: value})

        with self.assertRaisesRegex(ValueError, "output"):
            self.load(output="NUL.svg")

    def test_local_repository(self):
        """Путь к тестовому файлу читается относительно XML."""
        fixture = self.path.parent / "graph.txt"
        fixture.touch()
        values = self.load(
            package="A", test_mode="true", repository=fixture.name
        )
        self.assertEqual(values["repository"], fixture.name)

    def test_missing_local_repository(self):
        """Несуществующий тестовый файл вызывает ошибку."""
        with self.assertRaisesRegex(ValueError, "repository"):
            self.load(package="A", test_mode="true", repository="missing.txt")
