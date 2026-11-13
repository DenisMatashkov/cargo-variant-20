"""CLI для анализа зависимостей Cargo."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from src.dependency_graph import CargoSource, TestSource, build_graph
from src.load_order import calculate_load_order

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


def collect_graph(values, config_path):
    """Подключает нужный источник и запускает BFS."""
    package = values["package"]
    if values["test_mode"] == "true":
        source = TestSource(config_path.parent / values["repository"])
        source.check_package(package)
        root = (package, "")
    else:
        source = CargoSource(values["repository"])
        root = (package, values["version"])
        root = (source.release(root)["name"], root[1])

    return build_graph(
        root,
        source.requirements,
        source.resolve,
        int(values["max_depth"]),
        values["filter_substring"],
    )


def package_label(node):
    """Подписывает вершину именем и версией, если она есть."""
    name, version = node
    return f"{name}@{version}" if version else name


def print_graph(graph):
    """Печатает списки смежности в порядке обхода."""
    if not graph:
        print("Граф пуст: начальный пакет исключён фильтром.")
        return

    print("Граф зависимостей (BFS)")
    for node, children in graph.items():
        labels = ", ".join(map(package_label, children))
        print(f"{package_label(node)} -> {labels or '—'}")


def print_load_order(graph):
    """Печатает порядок загрузки и сообщает, удалось ли его построить."""
    if not graph:
        print("Граф пуст: начальный пакет исключён фильтром.")
        return True

    root = next(iter(graph))
    order, blocked = calculate_load_order(graph)
    dependencies = [node for node in order if node != root]

    print(f"Порядок загрузки зависимостей {package_label(root)}")
    for number, node in enumerate(dependencies, start=1):
        print(f"{number}. {package_label(node)}")

    if blocked:
        labels = ", ".join(map(package_label, blocked))
        print(f"Из-за цикла порядок не определён для: {labels}")
        return False

    if not dependencies:
        print("Зависимостей для загрузки нет.")
    return True


def main():
    """Читает XML и выводит граф или порядок загрузки."""
    parser = argparse.ArgumentParser(description="Граф зависимостей Cargo")
    parser.add_argument("config", nargs="?", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--load-order",
        action="store_true",
        help="вывести порядок загрузки зависимостей",
    )
    args = parser.parse_args()

    try:
        graph = collect_graph(load_config(args.config), args.config)
    except (OSError, ElementTree.ParseError, ValueError) as error:
        parser.exit(1, f"Ошибка: {error}\n")

    if not args.load_order:
        print_graph(graph)
        return

    if not print_load_order(graph):
        parser.exit(1)


if __name__ == "__main__":
    main()
