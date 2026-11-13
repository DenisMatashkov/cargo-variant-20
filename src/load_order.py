"""Расчёт порядка, в котором зависимости предшествуют своим пакетам."""

from collections import deque


def reverse_edges(graph):
    """Для каждой зависимости находит пакеты, которые её используют."""
    dependents = {node: [] for node in graph}
    for node, children in graph.items():
        for child in children:
            dependents[child].append(node)
    return dependents


def calculate_load_order(graph):
    """Возвращает готовый порядок и пакеты, заблокированные циклом."""
    pending = {node: len(children) for node, children in graph.items()}
    dependents = reverse_edges(graph)

    ready = deque(node for node, count in pending.items() if not count)
    order = []

    while ready:
        node = ready.popleft()
        order.append(node)
        for dependent in dependents[node]:
            pending[dependent] -= 1
            if not pending[dependent]:
                ready.append(dependent)

    blocked = [node for node, count in pending.items() if count]
    return order, blocked
