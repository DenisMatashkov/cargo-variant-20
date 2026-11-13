"""CLI для анализа зависимостей Cargo."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.xml"

NUMBER = r"(?:0|[1-9][0-9]*)"
PRERELEASE = rf"(?:{NUMBER}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
VERSION = (
    rf"{NUMBER}\.{NUMBER}\.{NUMBER}"
    rf"(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)

WINDOWS_DEVICE = re.compile(
    r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³]"
)

RULES = {
    "package": (r"[A-Za-z][A-Za-z0-9_-]*", "некорректное имя пакета"),
    "repository": (r".+", "укажите URL или путь к файлу"),
    "test_mode": (r"true|false", "ожидается true или false"),
    "version": (VERSION, "ожидается версия вида 1.2.3"),
    "output": (
        r'[^<>:"/\\|?*\x00-\x1f]+(?i:\.svg)',
        "укажите имя файла с расширением .svg",
    ),
    "ascii_tree": (r"true|false", "ожидается true или false"),
    "max_depth": (r"[0-9]+", "ожидается целое число от 0"),
    "filter_substring": (r"[A-Za-z0-9_-]*", "недопустимые символы"),
}


def validate_repository(values, folder):
    """Проверяет HTTP(S)-адрес или путь к тестовому файлу."""
    value = values["repository"]
    if values["test_mode"] == "true":
        if not re.fullmatch(r"[A-Z]+", values["package"]):
            raise ValueError("package: используйте заглавные буквы A–Z")
        if not (folder / value).is_file():
            raise ValueError(f"repository: файл не найден: {value}")
        return

    try:
        url = urlsplit(value)
        url.port
    except ValueError as error:
        raise ValueError("repository: некорректный URL") from error

    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or any(char.isspace() for char in value)
    ):
        raise ValueError("repository: ожидается URL вида https://example.com")


def validate_output_name(name):
    """Отклоняет зарезервированные имена файлов Windows."""
    base_name = name.partition(".")[0].rstrip().upper()
    if WINDOWS_DEVICE.fullmatch(base_name):
        raise ValueError(f"output: имя {name} зарезервировано в Windows")


def load_config(path):
    """Загружает и проверяет все восемь параметров XML."""
    root = ElementTree.parse(path).getroot()
    if root.tag != "config":
        raise ValueError("корневой элемент должен называться config")

    values = {}
    for item in root:
        if item.tag not in RULES:
            raise ValueError(f"{item.tag}: неизвестный параметр")
        if item.tag in values:
            raise ValueError(f"{item.tag}: параметр повторяется")
        if len(item):
            raise ValueError(f"{item.tag}: ожидается текстовое значение")
        values[item.tag] = (item.text or "").strip()

    for name, (pattern, message) in RULES.items():
        if name not in values:
            raise ValueError(f"{name}: параметр отсутствует в XML")
        if not re.fullmatch(pattern, values[name]):
            raise ValueError(f"{name}: {message}")

    validate_output_name(values["output"])
    validate_repository(values, path.parent)
    return values


def main():
    """Принимает путь к XML и выводит параметры первого этапа."""
    parser = argparse.ArgumentParser(description="Конфигурация варианта 20")
    parser.add_argument("config", nargs="?", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    try:
        values = load_config(args.config)
    except (OSError, ElementTree.ParseError, ValueError) as error:
        parser.exit(1, f"Ошибка: {error}\n")

    for name in RULES:
        print(f"{name} = {values[name]}")


if __name__ == "__main__":
    main()
