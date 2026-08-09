import json
from pathlib import Path

from .config import SplitConfig
from .image_ops import crop_foreground, load_binary_image, remove_small_components
from .segmentation import assign_foreground_to_strokes, segment_skeleton
from .thinning import zhang_suen_thinning
from .thinning import recover_T_junctions
from .thinning import remove_redundant_cross_points
from .thinning import fix_cross_alignment
from .types import SplitResult
from .visualization import (
    render_binary,
    render_overlap_map,
    render_overlay,
    render_single_stroke,
    render_stroke_gallery,
    render_stroke_map,
)


def split_character_image(image_path: str, config: SplitConfig | None = None) -> SplitResult:
    config = config or SplitConfig()
    binary = load_binary_image(image_path, config.threshold)
    cropped = crop_foreground(binary, config.padding)
    cleaned = remove_small_components(cropped, config.min_component_area)
    skeleton = zhang_suen_thinning(cleaned)
    skeleton = recover_T_junctions(cleaned, skeleton)
    skeleton = fix_cross_alignment(skeleton)
    skeleton = remove_redundant_cross_points(skeleton)
    segments = segment_skeleton(skeleton, config)
    stroke_map, stroke_masks = assign_foreground_to_strokes(cleaned, segments, config)
    overlap_pixels = int(sum(mask.sum() for mask in stroke_masks) - cleaned.sum())
    debug = {
        "segment_count": len(segments),
        "segment_lengths": [len(seg.points) for seg in segments],
        "overlap_pixel_count": overlap_pixels,
        "pixel_assignment": "exclusive-nearest-v1",
        "stroke_order": "top-to-bottom-horizontal-first-v1",
    }
    return SplitResult(
        binary=binary,
        cropped_binary=cleaned,
        skeleton=skeleton,
        stroke_map=stroke_map,
        stroke_masks=stroke_masks,
        segments=segments,
        debug=debug,
    )


def save_result_artifacts(result: SplitResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stroke_dir = out_dir / "strokes_individual"
    stroke_dir.mkdir(parents=True, exist_ok=True)
    render_binary(result.cropped_binary).save(out_dir / "binary.png")
    render_binary(result.skeleton).save(out_dir / "skeleton.png")
    render_stroke_map(result.stroke_map).save(out_dir / "strokes.png")
    render_overlay(result).save(out_dir / "overlay.png")
    render_overlap_map(result).save(out_dir / "overlap.png")
    render_stroke_gallery(result).save(out_dir / "strokes_gallery.png")
    for idx, stroke_mask in enumerate(result.stroke_masks, start=1):
        render_single_stroke(stroke_mask).save(stroke_dir / f"stroke_{idx:02d}.png")
    payload = {
        "segment_count": result.debug["segment_count"],
        "segment_lengths": result.debug["segment_lengths"],
        "overlap_pixel_count": result.debug["overlap_pixel_count"],
        "pixel_assignment": result.debug.get("pixel_assignment", "exclusive-nearest-v1"),
        "stroke_order": result.debug.get("stroke_order", "top-to-bottom-horizontal-first-v1"),
        "stroke_gallery": "strokes_gallery.png",
        "stroke_files": [f"strokes_individual/stroke_{idx:02d}.png" for idx in range(1, len(result.stroke_masks) + 1)],
        "segments": [
            {
                "stroke_id": seg.stroke_id,
                "point_count": len(seg.points),
                "points": [[int(y), int(x)] for y, x in seg.points],
                "pixel_count": int(result.stroke_masks[seg.stroke_id - 1].sum()),
            }
            for seg in result.segments
        ],
    }
    (out_dir / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
