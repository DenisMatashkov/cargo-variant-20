"""Проверки чтения индекса Cargo без обращения к сети."""

import unittest
from io import BytesIO
from unittest.mock import patch

from src.cargo_index import get_release, index_path

REPOSITORY = "https://index.example/"


class CargoIndexTests(unittest.TestCase):
    """Проверяет построение пути и выбор точной версии."""

    def test_index_paths(self):
        """Имена разной длины получают нужный префикс."""
        paths = {
            "A": "1/a",
            "cc": "2/cc",
            "syn": "3/s/syn",
            "regex": "re/ge/regex",
        }
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(index_path(name), path)

    @patch("src.cargo_index.urlopen")
    def test_exact_version(self, request):
        """Для выбранной версии возвращаются именно её зависимости."""
        request.return_value = BytesIO(
            b'{"vers": "1.0.0", "deps": []}\n'
            b'{"vers": "1.1.0", "deps": [{"name": "dep", "req": "^2"}]}\n'
        )
        release = get_release(REPOSITORY, "regex", "1.1.0")
        self.assertEqual(release["deps"], [{"name": "dep", "req": "^2"}])
        self.assertEqual(request.call_args.args[0], REPOSITORY + "re/ge/regex")

    @patch("src.cargo_index.urlopen")
    def test_missing_version(self, request):
        """Отсутствующая версия приводит к понятной ошибке."""
        request.return_value = BytesIO(b'{"vers": "1.0.0", "deps": []}\n')
        with self.assertRaisesRegex(ValueError, r"Версия 2\.0\.0"):
            get_release(REPOSITORY, "regex", "2.0.0")
