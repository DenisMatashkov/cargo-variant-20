"""Проверки параметров XML-конфигурации."""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.main import DEFAULT_CONFIG, load_config


class ConfigTests(unittest.TestCase):
    """Проверяет оба режима и ошибочные значения."""

    def load(self, *, fixture_name=None, **changes):
        """Создаёт временный XML, задаёт значения и проверяет настройки."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.xml"
            if fixture_name is not None:
                (path.parent / fixture_name).touch()

            tree = ElementTree.parse(DEFAULT_CONFIG)
            for name, value in changes.items():
                tree.find(name).text = value
            tree.write(path, encoding="utf-8")
            return load_config(path)

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
        fixture_name = "graph.txt"
        values = self.load(
            fixture_name=fixture_name,
            package="A",
            test_mode="true",
            repository=fixture_name,
        )
        self.assertEqual(values["repository"], fixture_name)

    def test_missing_local_repository(self):
        """Несуществующий тестовый файл вызывает ошибку."""
        with self.assertRaisesRegex(ValueError, "repository"):
            self.load(package="A", test_mode="true", repository="missing.txt")