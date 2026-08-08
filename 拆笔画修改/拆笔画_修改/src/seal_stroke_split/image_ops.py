from collections import deque

import numpy as np
from PIL import Image


def load_binary_image(path: str, threshold: int) -> np.ndarray:
    gray = Image.open(path).convert("L")
    arr = np.array(gray, dtype=np.uint8)
    return arr == threshold

def crop_foreground(mask: np.ndarray, padding: int) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return mask.copy()
    y0 = max(int(ys.min()) - padding, 0)
    y1 = min(int(ys.max()) + padding + 1, mask.shape[0])
    x0 = max(int(xs.min()) - padding, 0)
    x1 = min(int(xs.max()) + padding + 1, mask.shape[1])
    return mask[y0:y1, x0:x1]


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[list[tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            comp: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(y, x)])
            seen[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                comp.append((cy, cx))
                for ny in range(max(0, cy - 1), min(h, cy + 2)):
                    for nx in range(max(0, cx - 1), min(w, cx + 2)):
                        if (ny == cy and nx == cx) or seen[ny, nx] or not mask[ny, nx]:
                            continue
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            comps.append(comp)
    return comps


def remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    cleaned = np.zeros_like(mask, dtype=bool)
    for comp in connected_components(mask):
        if len(comp) < min_area:
            continue
        ys, xs = zip(*comp)
        cleaned[np.array(ys), np.array(xs)] = True
    return cleaned
