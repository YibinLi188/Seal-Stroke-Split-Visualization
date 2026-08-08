import math
from collections import defaultdict

import numpy as np

from .types import Point


NEIGHBOR_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def skeleton_neighbors(skeleton: np.ndarray, point: Point) -> list[Point]:
    h, w = skeleton.shape
    y, x = point
    out: list[Point] = []
    for dy, dx in NEIGHBOR_OFFSETS:
        ny, nx = y + dy, x + dx
        if not (0 <= ny < h and 0 <= nx < w and skeleton[ny, nx]):
            continue
        if dy != 0 and dx != 0:
            orth1 = (y, x + dx)
            orth2 = (y + dy, x)
            has_orth1 = 0 <= orth1[0] < h and 0 <= orth1[1] < w and skeleton[orth1]
            has_orth2 = 0 <= orth2[0] < h and 0 <= orth2[1] < w and skeleton[orth2]
            if has_orth1 or has_orth2:
                continue
        out.append((ny, nx))
    return out


def build_graph(skeleton: np.ndarray) -> dict[Point, list[Point]]:
    points = np.argwhere(skeleton)
    graph: dict[Point, list[Point]] = {}
    for y, x in points:
        point = (int(y), int(x))
        graph[point] = skeleton_neighbors(skeleton, point)
    return graph


def node_degrees(graph: dict[Point, list[Point]]) -> dict[Point, int]:
    return {point: len(neigh) for point, neigh in graph.items()}


def trace_paths(graph: dict[Point, list[Point]]) -> list[list[Point]]:
    degrees = node_degrees(graph)
    critical = {p for p, d in degrees.items() if d != 2}
    visited_edges: set[tuple[Point, Point]] = set()
    paths: list[list[Point]] = []

    def edge_key(a: Point, b: Point) -> tuple[Point, Point]:
        return tuple(sorted((a, b)))

    for start in critical:
        for nxt in graph[start]:
            key = edge_key(start, nxt)
            if key in visited_edges:
                continue
            path = [start, nxt]
            visited_edges.add(key)
            prev, cur = start, nxt
            while degrees[cur] == 2:
                neighbors = graph[cur]
                nxt_candidates = [p for p in neighbors if p != prev]
                if not nxt_candidates:
                    break
                nxt2 = nxt_candidates[0]
                key = edge_key(cur, nxt2)
                if key in visited_edges:
                    break
                path.append(nxt2)
                visited_edges.add(key)
                prev, cur = cur, nxt2
            paths.append(path)

    leftover = set()
    for point, neighs in graph.items():
        for neigh in neighs:
            key = tuple(sorted((point, neigh)))
            if key not in visited_edges:
                leftover.add(key)

    while leftover:
        a, b = leftover.pop()
        cycle = [a, b]
        prev, cur = a, b
        while True:
            neighbors = [p for p in graph[cur] if p != prev]
            if not neighbors:
                break
            nxt = neighbors[0]
            key = tuple(sorted((cur, nxt)))
            if key in leftover:
                leftover.remove(key)
            if nxt == cycle[0]:
                cycle.append(nxt)
                break
            cycle.append(nxt)
            prev, cur = cur, nxt
        paths.append(cycle)

    return [path for path in paths if len(path) >= 2]


def point_distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_angle(a: Point, b: Point) -> float:
    return math.atan2(b[0] - a[0], b[1] - a[1])


def angle_delta_deg(a1: float, a2: float) -> float:
    diff = abs(a1 - a2)
    diff = min(diff, 2 * math.pi - diff)
    return math.degrees(diff)


# 在 skeleton_graph.py 中

def group_by_endpoint(segments: list[list[Point]]) -> dict[Point, list[int]]:
    endpoint_map: dict[Point, list[int]] = defaultdict(list)
    for idx, seg in enumerate(segments):
        if not seg:
            continue
        endpoint_map[seg[0]].append(idx)
        endpoint_map[seg[-1]].append(idx)
    return endpoint_map
