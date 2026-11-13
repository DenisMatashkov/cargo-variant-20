"""Построение графа зависимостей обходом в ширину."""

import re
from collections import deque

from src.cargo_index import find_release, read_index
from src.cargo_versions import newest_version


def build_graph(root, requirements, resolve, max_depth, fragment):
    """Возвращает списки смежности в порядке BFS."""
    if fragment and fragment in root[0]:
        return {}
    graph = {root: []}
    queue = deque([(root, 0)])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue

        children = []
        for name, constraint in requirements(node):
            if fragment and fragment in name:
                continue
            child = (name, resolve(name, constraint))
            children.append(child)
            if child not in graph:
                graph[child] = []
                queue.append((child, depth + 1))

        graph[node] = list(dict.fromkeys(children))

    return graph


class CargoSource:
    """Читает пакеты из одного индекса и кеширует их записи."""

    def __init__(self, repository):
        """Сохраняет адрес индекса и создаёт кеш."""
        self.repository = repository
        self.cache = {}

    def records(self, name):
        """Загружает индекс конкретного пакета только при первом запросе."""
        if name not in self.cache:
            self.cache[name] = read_index(self.repository, name)
        return self.cache[name]

    def release(self, node):
        """Находит запись для пары (имя, версия)."""
        name, version = node
        return find_release(self.records(name), name, version)

    def requirements(self, node):
        """Даёт объявленные обычные и сборочные зависимости пакета."""
        for dependency in self.release(node)["deps"]:
            if dependency.get("kind") != "dev":
                name = dependency.get("package") or dependency["name"]
                yield name, dependency

    def resolve(self, name, dependency):
        """Подбирает версию для конкретного ребра графа."""
        registry = dependency.get("registry")
        if registry:
            raise ValueError(f"{name}: другой индекс Cargo ({registry})")
        try:
            return newest_version(self.records(name), dependency["req"])
        except ValueError as error:
            raise ValueError(f"{name}: {error}") from error


class TestSource:
    """Читает локальный граф со строками вида A: B C."""

    def __init__(self, path):
        """Читает список смежности и проверяет ссылки."""
        self.adjacency = {}
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for number, line in enumerate(lines, start=1):
            if line.strip():
                self.add_line(number, line)
        self.validate_references()

    def add_line(self, number, line):
        """Проверяет одну строку и добавляет вершину."""
        name, separator, names = line.partition(":")
        name = name.strip()
        children = names.split()
        if not separator or any(
            not re.fullmatch(r"[A-Z]+", part) for part in [name, *children]
        ):
            raise ValueError(f"Строка {number}: ожидается формат A: B C")
        if name in self.adjacency:
            raise ValueError(f"Строка {number}: пакет {name} повторяется")
        self.adjacency[name] = children

    def validate_references(self):
        """Проверяет, что у каждого пакета есть собственная строка."""
        for children in self.adjacency.values():
            for child in children:
                self.check_package(child)

    def check_package(self, name):
        """Проверяет наличие вершины в тестовом файле."""
        if name not in self.adjacency:
            raise ValueError(f"Пакет {name} не описан в тестовом файле")

    def requirements(self, node):
        """Возвращает непосредственных соседей тестовой вершины."""
        return ((name, "") for name in self.adjacency[node[0]])

    @staticmethod
    def resolve(_name, _constraint):
        """Возвращает пустую версию для тестового пакета."""
        return ""
