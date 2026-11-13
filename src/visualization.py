"""Представление графа в Mermaid, SVG и ASCII."""

from collections import defaultdict
from xml.sax.saxutils import escape

MARGIN = 32
BOX_HEIGHT = 36
COLUMN_GAP = 24
ROW_STEP = 104
RAIL_GAP = 14
BRANCH_PADDING = {"": "", "|-- ": "|   ", "`-- ": "    "}


def package_label(node):
    """Формирует подпись вершины."""
    name, version = node
    return f"{name}@{version}" if version else name


def mermaid_text(graph):
    """Создаёт Mermaid-диаграмму со всеми вершинами и рёбрами."""
    ids = {node: f"n{i}" for i, node in enumerate(graph)}
    lines = ["flowchart TD"]
    for node, identifier in ids.items():
        lines.append(f'    {identifier}["{package_label(node)}"]')
    for node, children in graph.items():
        for child in children:
            lines.append(f"    {ids[node]} --> {ids[child]}")
    return "\n".join(lines) + "\n"


def ascii_tree(graph):
    """Возвращает ASCII-дерево с отметками повторных вершин."""
    if not graph:
        return "Граф пуст."

    stack = [(next(iter(graph)), "", "")]
    seen = set()
    lines = []
    while stack:
        node, prefix, branch = stack.pop()
        label = package_label(node)
        if node in seen:
            lines.append(f"{prefix}{branch}{label} [repeat]")
            continue

        seen.add(node)
        lines.append(f"{prefix}{branch}{label}")
        child_prefix = prefix + BRANCH_PADDING[branch]
        children = graph[node]
        for index in reversed(range(len(children))):
            link = "`-- " if index == len(children) - 1 else "|-- "
            stack.append((children[index], child_prefix, link))
    return "\n".join(lines)


def layout(graph):
    """Группирует вершины по уровням BFS и вычисляет координаты."""
    root = next(iter(graph))
    depths = {root: 0}
    rows = defaultdict(list)
    for node, children in graph.items():
        depth = depths[node]
        rows[depth].append(node)
        for child in children:
            depths.setdefault(child, depth + 1)

    longest = max(len(package_label(node)) for node in graph)
    box_width = max(96, 8 * longest + 28)
    slot = box_width + COLUMN_GAP
    columns = max(map(len, rows.values()))
    width = columns * slot - COLUMN_GAP + 2 * MARGIN
    height = (len(rows) - 1) * ROW_STEP + BOX_HEIGHT + 2 * MARGIN

    positions = {}
    for depth, nodes in rows.items():
        left = (width - len(nodes) * slot + COLUMN_GAP) // 2
        for index, node in enumerate(nodes):
            x = left + index * slot + box_width // 2
            positions[node] = (x, MARGIN + depth * ROW_STEP)
    return positions, box_width, width, height


def svg_edges(graph, positions, width):
    """Рисует стрелки между вершинами, в том числе обратные рёбра."""
    paths = []
    sides = []
    for node, children in graph.items():
        x1, y1 = positions[node]
        bottom = y1 + BOX_HEIGHT
        for child in children:
            x2, y2 = positions[child]
            if y2 - y1 == ROW_STEP:
                middle = (bottom + y2) // 2
                path = f"M{x1},{bottom} C{x1},{middle} {x2},{middle} {x2},{y2}"
                paths.append(f'<path d="{path}"/>')
            else:
                sides.append((x1, bottom, x2, y2))

    for index, (x1, bottom, x2, y2) in enumerate(sides, start=1):
        rail = width + index * RAIL_GAP
        gap = 8 + 20 * index / (len(sides) + 1)
        path = (
            f"M{x1},{bottom} V{bottom + gap:.2f} H{rail} "
            f"V{y2 - gap:.2f} H{x2} V{y2}"
        )
        paths.append(f'<path d="{path}" stroke-dasharray="5 3"/>')

    return paths, len(sides) * RAIL_GAP


def svg_nodes(positions, box_width):
    """Создаёт прямоугольники и подписи для вершин."""
    root = next(iter(positions), None)
    for node, (x, y) in positions.items():
        fill = "#dceafe" if node == root else "#fff"
        left = x - box_width // 2
        label = escape(package_label(node))
        yield (
            f'<rect x="{left}" y="{y}" width="{box_width}" '
            f'height="{BOX_HEIGHT}" rx="8" fill="{fill}" stroke="#64748b"/>'
        )
        yield f'<text x="{x}" y="{y + 23}">{label}</text>'


def svg_text(graph):
    """Генерирует SVG из того же списка смежности, что и Mermaid."""
    width, height = 300, 80
    paths = []
    nodes = ['<text x="150" y="45">Граф пуст</text>']
    if graph:
        positions, box_width, width, height = layout(graph)
        paths, extra_width = svg_edges(graph, positions, width)
        if extra_width:
            width += extra_width + MARGIN
        nodes = list(svg_nodes(positions, box_width))

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
        'refX="8" refY="4" orient="auto" viewBox="0 0 8 8">',
        '<path d="M0,0 L8,4 L0,8 Z" fill="#475569"/></marker></defs>',
        '<g fill="none" stroke="#475569" stroke-width="1.4" '
        'marker-end="url(#arrow)">',
        *paths,
        '</g>',
        '<g fill="#172033" font-family="monospace" font-size="13" '
        'text-anchor="middle">',
        *nodes,
        '</g>',
        '</svg>',
    ]
    return "\n".join(lines) + "\n"


def save_visualization(graph, svg_path):
    """Сохраняет Mermaid рядом с SVG и возвращает путь к нему."""
    mermaid_path = svg_path.with_suffix(".mmd")
    mermaid_path.write_text(mermaid_text(graph), encoding="utf-8")
    svg_path.write_text(svg_text(graph), encoding="utf-8")
    return mermaid_path
