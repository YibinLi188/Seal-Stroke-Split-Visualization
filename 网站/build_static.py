from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps


WEBSITE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WEBSITE_ROOT.parent
CODE_ROOT = PROJECT_ROOT / "拆笔画修改" / "拆笔画_修改"
RESULT_ROOT = CODE_ROOT / "修改后的程序的结果"
DATA_ROOT = CODE_ROOT / "data"
ASSET_ROOT = WEBSITE_ROOT / "assets"
OUTPUT_PATH = WEBSITE_ROOT / "static-data.json"
PALETTE = [
    "#d64b3f",
    "#287c88",
    "#d49a35",
    "#7657a8",
    "#43895e",
    "#c2638f",
    "#3f6da8",
    "#b26935",
]


def character_from_id(value: str) -> str:
    parts = value.split("_")
    return parts[1] if len(parts) > 1 and parts[1] else value


def find_input_image(sample_id: str) -> Path | None:
    matches = sorted(DATA_ROOT.rglob(f"{sample_id}.png"))
    return matches[0] if matches else None


def make_colored_stroke(source: Path, destination: Path, color: str) -> None:
    with Image.open(source).convert("L") as gray:
        alpha = ImageOps.invert(gray)
        rgba = Image.new("RGBA", gray.size, color)
        rgba.putalpha(alpha)
        rgba.save(destination, "PNG")


def copy_asset(source: Path, destination: Path) -> None:
    if source.is_file():
        shutil.copy2(source, destination)


def build_record(result_dir: Path) -> dict | None:
    sample_id = result_dir.name
    result_path = result_dir / "result.json"
    binary_path = result_dir / "binary.png"
    input_path = find_input_image(sample_id)
    if not result_path.is_file() or not binary_path.is_file() or input_path is None:
        return None
    if not re.match(r"^\d+_", sample_id):
        return None

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    asset_id = f"sample_{sample_id.split('_', 1)[0]}"
    asset_dir = ASSET_ROOT / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    copy_asset(input_path, asset_dir / "input.png")
    for filename in ("binary.png", "overlay.png", "strokes_gallery.png"):
        copy_asset(result_dir / filename, asset_dir / filename)

    with Image.open(binary_path) as image:
        width, height = image.width, image.height

    strokes = []
    segments = payload.get("segments", [])
    for index, relative_path in enumerate(payload.get("stroke_files", []), start=1):
        source = result_dir / relative_path
        filename = f"stroke_{index:02d}.png"
        destination = asset_dir / filename
        if source.is_file():
            make_colored_stroke(source, destination, PALETTE[(index - 1) % len(PALETTE)])
        segment = segments[index - 1] if index <= len(segments) else {}
        strokes.append(
            {
                "id": index,
                "point_count": int(segment.get("point_count", 0)),
                "pixel_count": int(segment.get("pixel_count", 0)),
                "points": segment.get("points", []),
                "color": PALETTE[(index - 1) % len(PALETTE)],
                "url": f"assets/{asset_id}/{filename}",
            }
        )

    return {
        "id": sample_id,
        "character": character_from_id(sample_id),
        "source_name": sample_id,
        "segment_count": int(payload.get("segment_count", len(strokes))),
        "overlap_pixel_count": int(payload.get("overlap_pixel_count", 0)),
        "pixel_assignment": payload.get("pixel_assignment", "legacy-overlap"),
        "stroke_order": payload.get("stroke_order", "legacy-order"),
        "render_mode": "path-reveal-v2",
        "width": width,
        "height": height,
        "input_url": f"assets/{asset_id}/input.png",
        "binary_url": f"assets/{asset_id}/binary.png",
        "overlay_url": f"assets/{asset_id}/overlay.png",
        "gallery_url": f"assets/{asset_id}/strokes_gallery.png",
        "strokes": strokes,
    }


def main() -> None:
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    records = {}
    examples = []
    for result_dir in sorted(RESULT_ROOT.iterdir(), key=lambda path: path.name):
        if not result_dir.is_dir():
            continue
        record = build_record(result_dir)
        if record is None:
            continue
        records[record["id"]] = record
        examples.append(
            {
                key: record[key]
                for key in ("id", "character", "source_name", "segment_count", "overlap_pixel_count")
            }
        )
    payload = {"static_mode": True, "examples": examples, "records": records}
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Built {len(examples)} static examples in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
