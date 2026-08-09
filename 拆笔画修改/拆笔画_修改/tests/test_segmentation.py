from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from seal_stroke_split.config import SplitConfig
from seal_stroke_split.segmentation import assign_foreground_to_strokes, order_segments_for_drawing, segment_skeleton
from seal_stroke_split.types import StrokeSegment


class SegmentationTests(unittest.TestCase):
    def test_cross_shape_splits_into_two_segments(self) -> None:
        skeleton = np.zeros((9, 9), dtype=bool)
        skeleton[4, 1:8] = True
        skeleton[1:8, 4] = True
        segments = segment_skeleton(skeleton, SplitConfig(split_angle_deg=45.0))
        self.assertGreaterEqual(len(segments), 2)

    def test_two_diagonal_strokes_are_not_merged(self) -> None:
        skeleton = np.zeros((9, 9), dtype=bool)
        for i in range(1, 8):
            skeleton[i, i] = True
            skeleton[i, 8 - i] = True
        segments = segment_skeleton(skeleton, SplitConfig(split_angle_deg=35.0, merge_angle_deg=20.0))
        self.assertGreaterEqual(len(segments), 2)

    def test_vertical_stem_survives_side_branches(self) -> None:
        skeleton = np.zeros((11, 11), dtype=bool)
        skeleton[1:10, 5] = True
        skeleton[4, 3:8] = True
        segments = segment_skeleton(
            skeleton,
            SplitConfig(
                split_angle_deg=45.0,
                merge_angle_deg=20.0,
                through_angle_deg=25.0,
                tiny_segment_points=3,
            ),
        )
        vertical_like = [
            seg for seg in segments
            if max(y for y, _ in seg.points) - min(y for y, _ in seg.points) >= 7
        ]
        self.assertTrue(vertical_like)

    def test_stroke_order_is_top_to_bottom_and_horizontal_first(self) -> None:
        segments = [
            StrokeSegment(1, [(1, 5), (4, 5)]),
            StrokeSegment(2, [(1, 1), (1, 8)]),
            StrokeSegment(3, [(4, 1), (7, 4)]),
        ]
        ordered = order_segments_for_drawing(segments)
        self.assertEqual(ordered[0].points, [(1, 1), (1, 8)])
        self.assertEqual(ordered[1].points, [(1, 5), (4, 5)])

    def test_foreground_pixels_are_assigned_to_one_stroke_only(self) -> None:
        mask = np.zeros((9, 9), dtype=bool)
        mask[4, 1:8] = True
        mask[1:8, 4] = True
        segments = order_segments_for_drawing([
            StrokeSegment(1, [(4, 1), (4, 7)]),
            StrokeSegment(2, [(1, 4), (7, 4)]),
        ])
        stroke_map, stroke_masks = assign_foreground_to_strokes(mask, segments, SplitConfig())
        counts = np.sum(np.stack(stroke_masks, axis=0), axis=0)
        self.assertTrue(np.all(counts[mask] == 1))
        self.assertTrue(np.all(stroke_map[mask] > 0))
        self.assertEqual(int(counts.max()), 1)

if __name__ == "__main__":
    unittest.main()
