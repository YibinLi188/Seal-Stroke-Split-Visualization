from collections import Counter
import math

import numpy as np

from .config import SplitConfig
from .image_ops import connected_components
from .skeleton_graph import angle_delta_deg, build_graph, group_by_endpoint, point_angle, trace_paths
from .types import Point, StrokeSegment
from .thinning import fix_cross_alignment


def _path_angles(path: list[Point], window: int) -> list[float]:
    angles: list[float] = []
    n = len(path)
    for i in range(n):
        left = path[max(0, i - window)]
        right = path[min(n - 1, i + window)]
        if left == right and i + 1 < n:
            right = path[i + 1]
        angles.append(point_angle(left, right))
    return angles

def split_path_by_angle(path: list[Point], config: SplitConfig) -> list[list[Point]]:
    if len(path) <= config.min_segment_points:
        return [path]
    angles = _path_angles(path, config.direction_window)
    split_indices = [0]
    last_split = 0
    for i in range(1, len(path) - 1):
        if i - last_split < config.min_segment_points:
            continue
        delta = angle_delta_deg(angles[i - 1], angles[i + 1])
        if delta >= config.split_angle_deg:
            split_indices.append(i)
            last_split = i
    split_indices.append(len(path) - 1)

    parts: list[list[Point]] = []
    for a, b in zip(split_indices[:-1], split_indices[1:]):
        segment = path[a:b + 1]
        if len(segment) >= 2:
            parts.append(segment)
    return parts or [path]



def _segment_endpoint_angle(segment: list[Point], at_start: bool, window: int) -> float:
    if len(segment) == 1:
        return 0.0
    if at_start:
        a = segment[0]
        b = segment[min(len(segment) - 1, window)]
    else:
        a = segment[-1]
        b = segment[max(0, len(segment) - 1 - window)]
    return point_angle(a, b)


def _combine_segments(
    seg_a: list[Point],
    seg_b: list[Point],
    a_at_start: bool,
    b_at_start: bool,
) -> list[Point]:
    if a_at_start:
        seg_a = list(reversed(seg_a))
    if not b_at_start:
        seg_b = list(reversed(seg_b))
    return seg_a + seg_b[1:]


def merge_segments_at_endpoints(segments: list[list[Point]], config: SplitConfig) -> list[list[Point]]:
    """
    合并共享端点的路径段。
    
    策略：
    1. 先遍历所有端点，收集所有可合并的路径对
    2. 记录每对路径的合并方式（方向、角度等）
    3. 所有判断完成后，统一执行合并
    4. 重复上述过程直到没有更多合并
    
    这样可以避免合并过程中端点被"占用"导致其他可能的合并被遗漏。
    """
    merged = [list(seg) for seg in segments]
    
    while True:
        # 获取当前所有端点分组
        endpoint_map = group_by_endpoint(merged)
        
        # 第一步：收集所有可合并的配对
        # 结构: [(ia, ib, a_at_start, b_at_start, merge_type, score), ...]
        # merge_type: 'same_direction' 或 'through_junction'
        candidates = []
        
        for point, idxs in endpoint_map.items():
            active = [idx for idx in idxs if merged[idx]]
            if len(active) < 2:
                continue
            
            # 检查这个端点上的所有路径对
            for i in range(len(active)):
                for j in range(i + 1, len(active)):
                    ia = active[i]
                    ib = active[j]
                    seg_a = merged[ia]
                    seg_b = merged[ib]
                    
                    # 确定两条路径在端点处的方向
                    a_at_start = seg_a[0] == point
                    b_at_start = seg_b[0] == point
                    ang_a = _segment_endpoint_angle(seg_a, a_at_start, config.direction_window)
                    ang_b = _segment_endpoint_angle(seg_b, b_at_start, config.direction_window)
                    delta = angle_delta_deg(ang_a, ang_b)
                    
                    # 判断合并类型
                    merge_type = None
                    score = None
                    
                    # 情况1：同方向合并（角度差小）
                    if delta <= config.merge_angle_deg:
                        merge_type = 'same_direction'
                        score = delta + abs(len(seg_a) - len(seg_b)) * 0.01
                    
                    # 情况2：穿过交叉点合并（角度差接近180°）
                    straightness = abs(delta - 180.0)
                    if len(active) >= 3 and straightness <= config.through_angle_deg:
                        # 如果同方向也满足，选择评分更优的
                        through_score = straightness - min(len(seg_a), len(seg_b)) * 0.01
                        if merge_type is None or through_score < score:
                            merge_type = 'through_junction'
                            score = through_score
                    
                    if merge_type is not None:
                        candidates.append({
                            'ia': ia,
                            'ib': ib,
                            'a_at_start': a_at_start,
                            'b_at_start': b_at_start,
                            'point': point,
                            'merge_type': merge_type,
                            'score': score,
                            'len_a': len(seg_a),
                            'len_b': len(seg_b),
                        })
        
        # 如果没有候选，退出循环
        if not candidates:
            break
        
        # 第二步：按评分排序（评分越低越好）
        candidates.sort(key=lambda x: x['score'])
        
        # 第三步：选择要执行的合并（避免路径冲突）
        used_indices = set()
        selected_merges = []
        
        for cand in candidates:
            ia = cand['ia']
            ib = cand['ib']
            
            # 如果某条路径已经被合并了，跳过
            if ia in used_indices or ib in used_indices:
                continue
            
            # 确保两条路径还存在
            if not merged[ia] or not merged[ib]:
                continue
            
            # 选择这个合并
            selected_merges.append(cand)
            used_indices.add(ia)
            used_indices.add(ib)
        
        # 第四步：统一执行所有合并
        for cand in selected_merges:
            ia = cand['ia']
            ib = cand['ib']
            a_at_start = cand['a_at_start']
            b_at_start = cand['b_at_start']
            
            merged[ia] = _combine_segments(merged[ia], merged[ib], a_at_start, b_at_start)
            merged[ib] = []
        
        # 如果本次没有实际合并，退出循环
        if not selected_merges:
            break
    
    # 返回非空路径
    return [seg for seg in merged if len(seg) >= 2]


def absorb_tiny_segments(segments: list[list[Point]], config: SplitConfig) -> list[list[Point]]:
    merged = [list(seg) for seg in segments]
    changed = True
    while changed:
        changed = False
        endpoint_map = group_by_endpoint(merged)
        for idx, seg in enumerate(merged):
            if not seg or len(seg) > config.tiny_segment_points:
                continue
            candidate = None
            best_score = None
            for endpoint in (seg[0], seg[-1]):
                neighbors = [other for other in endpoint_map.get(endpoint, []) if other != idx and merged[other]]
                at_start = seg[0] == endpoint
                tiny_angle = _segment_endpoint_angle(seg, at_start, config.direction_window)
                for other in neighbors:
                    other_seg = merged[other]
                    other_at_start = other_seg[0] == endpoint
                    other_angle = _segment_endpoint_angle(other_seg, other_at_start, config.direction_window)
                    delta = min(angle_delta_deg(tiny_angle, other_angle), abs(angle_delta_deg(tiny_angle, other_angle) - 180.0))
                    score = delta + len(seg) * 0.5 - len(other_seg) * 0.02
                    if best_score is None or score < best_score:
                        best_score = score
                        candidate = (idx, other, at_start, other_at_start, endpoint)
            if candidate is None:
                continue
            tiny_idx, other_idx, tiny_at_start, other_at_start, endpoint = candidate
            tiny_seg = merged[tiny_idx]
            other_seg = merged[other_idx]
            tiny_forward = tiny_seg if tiny_seg[0] == endpoint else list(reversed(tiny_seg))
            if other_at_start:
                combined = tiny_forward + other_seg[1:]
            else:
                combined = other_seg + tiny_forward[1:]
            merged[other_idx] = combined
            merged[tiny_idx] = []
            changed = True
            break
    return [seg for seg in merged if len(seg) >= 2]


def segment_skeleton(skeleton: np.ndarray, config: SplitConfig) -> list[StrokeSegment]:
    # ========== 新增：骨架预处理 ==========
    aligned = fix_cross_alignment(skeleton)  # ← 新增，修正错位的竖线
    
    # ========== 使用预处理后的骨架 ==========
    graph = build_graph(aligned)             # ← 改了：用 aligned 而不是 skeleton
    base_paths = trace_paths(graph)
    
    split_paths: list[list[Point]] = []
    for path in base_paths:
        split_paths.extend(split_path_by_angle(path, config))
    
    # ========== 合并函数替换 ==========
    merged = merge_segments_at_endpoints(split_paths, config)  # ← 新函数，替代原来的两个
    
    cleaned = absorb_tiny_segments(merged, config)             # ← 改了：用 merged 而不是 through
    
    return order_segments_for_drawing(
        [StrokeSegment(stroke_id=i + 1, points=path) for i, path in enumerate(cleaned)]
    )


def _stroke_order_key(segment: StrokeSegment) -> tuple[float, int, float, float, float, int]:
    """Approximate a readable character writing order from segment geometry."""
    points = np.asarray(segment.points, dtype=np.float32)
    ys = points[:, 0]
    xs = points[:, 1]
    height = float(ys.max() - ys.min())
    width = float(xs.max() - xs.min())
    if width >= height * 1.4:
        direction_rank = 0  # horizontal first
    elif height >= width * 1.4:
        direction_rank = 1  # then vertical
    else:
        direction_rank = 2  # diagonals and curves
    return (
        float(ys.min()),
        direction_rank,
        float(xs.min()),
        float(ys.mean()),
        float(xs.mean()),
        -len(segment.points),
    )


def order_segments_for_drawing(segments: list[StrokeSegment]) -> list[StrokeSegment]:
    ordered = sorted(segments, key=_stroke_order_key)
    return [StrokeSegment(stroke_id=index, points=list(segment.points)) for index, segment in enumerate(ordered, start=1)]


def _distance_maps(mask: np.ndarray, segments: list[StrokeSegment]) -> tuple[np.ndarray, np.ndarray]:
    fg_points = np.argwhere(mask)
    if len(fg_points) == 0:
        return np.zeros((0, 0)), fg_points
    distances = np.empty((len(segments), len(fg_points)), dtype=np.float32)
    for idx, seg in enumerate(segments):
        seg_points = np.array(seg.points, dtype=np.float32)
        diff = fg_points[:, None, :].astype(np.float32) - seg_points[None, :, :]
        sq_dist = np.sum(diff * diff, axis=2)
        distances[idx] = np.sqrt(np.min(sq_dist, axis=1))
    return distances, fg_points


def _reassign_tiny_regions(stroke_map: np.ndarray, mask: np.ndarray, config: SplitConfig) -> np.ndarray:
    refined = stroke_map.copy()
    max_id = int(refined.max())
    for stroke_id in range(1, max_id + 1):
        label_mask = refined == stroke_id
        for comp in connected_components(label_mask):
            if len(comp) >= config.min_region_area:
                continue
            neighbor_votes: Counter[int] = Counter()
            for y, x in comp:
                for ny in range(max(0, y - 1), min(refined.shape[0], y + 2)):
                    for nx in range(max(0, x - 1), min(refined.shape[1], x + 2)):
                        other = int(refined[ny, nx])
                        if other != 0 and other != stroke_id:
                            neighbor_votes[other] += 1
            replacement = neighbor_votes.most_common(1)[0][0] if neighbor_votes else 0
            if replacement == 0:
                continue
            ys, xs = zip(*comp)
            refined[np.array(ys), np.array(xs)] = replacement
    refined[~mask] = 0
    return refined


def assign_foreground_to_strokes(
    mask: np.ndarray,
    segments: list[StrokeSegment],
    config: SplitConfig,
) -> tuple[np.ndarray, list[np.ndarray]]:
    if not segments:
        empty = np.zeros(mask.shape, dtype=np.int32)
        return empty, []

    distances, fg_points = _distance_maps(mask, segments)
    stroke_map = np.zeros(mask.shape, dtype=np.int32)
    nearest = np.argmin(distances, axis=0) + 1
    ys = fg_points[:, 0]
    xs = fg_points[:, 1]
    stroke_map[ys, xs] = nearest
    stroke_map = _reassign_tiny_regions(stroke_map, mask, config)

    # Every foreground pixel belongs to exactly one stroke. The previous
    # margin-based inclusion duplicated pixels near crossings.
    stroke_masks = [stroke_map == (idx + 1) for idx in range(len(segments))]

    return stroke_map, stroke_masks
