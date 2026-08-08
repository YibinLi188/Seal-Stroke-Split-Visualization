from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from seal_stroke_split import SplitConfig, split_character_image
from seal_stroke_split.pipeline import save_result_artifacts


def _default_input_dir() -> Path:
    data_dir = ROOT / "data"
    subdirs = sorted(path for path in data_dir.iterdir() if path.is_dir())
    return subdirs[0] if subdirs else data_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run seal-script stroke splitting experiments.")
    parser.add_argument("--input-dir", type=Path, default=_default_input_dir())
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "experiment_v1")
    parser.add_argument("--threshold", type=int, default=0)
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument("--min-component-area", type=int, default=8)
    parser.add_argument("--direction-window", type=int, default=2)
    parser.add_argument("--split-angle-deg", type=float, default=55.0)
    parser.add_argument("--min-segment-points", type=int, default=5)
    parser.add_argument("--merge-angle-deg", type=float, default=28.0)
    parser.add_argument("--through-angle-deg", type=float, default=32.0)
    parser.add_argument("--tiny-segment-points", type=int, default=6)
    parser.add_argument("--min-region-area", type=int, default=10)
    parser.add_argument("--overlap-margin", type=float, default=1.35)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SplitConfig(
        threshold=args.threshold,
        padding=args.padding,
        min_component_area=args.min_component_area,
        direction_window=args.direction_window,
        split_angle_deg=args.split_angle_deg,
        min_segment_points=args.min_segment_points,
        merge_angle_deg=args.merge_angle_deg,
        through_angle_deg=args.through_angle_deg,
        tiny_segment_points=args.tiny_segment_points,
        min_region_area=args.min_region_area,
        overlap_margin=args.overlap_margin,
    )
    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[str] = []
    records: list[dict] = []
    for image_path in sorted(input_dir.glob("*.png")):
        result = split_character_image(str(image_path), config)
        stem = image_path.stem
        sample_dir = output_dir / stem
        save_result_artifacts(result, sample_dir)
        rows.append(
            f"{image_path.name}\t{result.debug['segment_count']}\t{result.debug['overlap_pixel_count']}\t{result.debug['segment_lengths']}"
        )
        records.append(
            {
                "image": image_path.name,
                "segment_count": result.debug["segment_count"],
                "overlap_pixel_count": result.debug["overlap_pixel_count"],
                "segment_lengths": result.debug["segment_lengths"],
            }
        )

    summary_path = output_dir / "summary.tsv"
    summary_path.write_text(
        "image\tsegment_count\toverlap_pixel_count\tsegment_lengths\n" + "\n".join(rows),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "config": config.to_dict(),
                "results": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"done: {summary_path}")


if __name__ == "__main__":
    main()
