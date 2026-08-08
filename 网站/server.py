from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import sys
import uuid
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, quote

from PIL import Image, ImageOps


WEBSITE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WEBSITE_ROOT.parent
CODE_ROOT = PROJECT_ROOT / "拆笔画修改" / "拆笔画_修改"
SOURCE_ROOT = CODE_ROOT / "src"
RESULT_ROOT = CODE_ROOT / "修改后的程序的结果"
DATA_ROOT = CODE_ROOT / "data"
CACHE_ROOT = WEBSITE_ROOT / ".cache"
RUNTIME_ROOT = WEBSITE_ROOT / "runtime_results"
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
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

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from seal_stroke_split import SplitConfig, split_character_image  # noqa: E402
from seal_stroke_split.pipeline import save_result_artifacts  # noqa: E402


# The documentation records 180 degrees as the modified path split setting.
WEB_CONFIG = SplitConfig(split_angle_deg=180.0)
DEMO_INDEX: dict[str, dict] = {}
RUNTIME_INDEX: dict[str, dict] = {}


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler: BaseHTTPRequestHandler, message: str, status: int = 400) -> None:
    json_response(handler, {"error": message}, status)


def safe_public_id(value: str) -> str:
    return quote(value, safe="")


def character_from_id(value: str) -> str:
    parts = value.split("_")
    return parts[1] if len(parts) > 1 and parts[1] else value


def find_source_image(stem: str) -> Path | None:
    matches = list(DATA_ROOT.rglob(f"{stem}.png"))
    return matches[0] if matches else None


def load_result_payload(result_dir: Path) -> dict:
    return json.loads((result_dir / "result.json").read_text(encoding="utf-8"))


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.width, image.height


def make_colored_stroke(source: Path, destination: Path, color: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_mtime >= source.stat().st_mtime:
        return
    with Image.open(source).convert("L") as gray:
        alpha = ImageOps.invert(gray)
        rgba = Image.new("RGBA", gray.size, color)
        rgba.putalpha(alpha)
        rgba.save(destination, "PNG")


def cache_strokes(cache_key: str, result_dir: Path, payload: dict) -> list[dict]:
    cache_dir = CACHE_ROOT / cache_key
    strokes: list[dict] = []
    for index, relative_path in enumerate(payload.get("stroke_files", []), start=1):
        source = result_dir / relative_path
        target = cache_dir / f"stroke_{index:02d}.png"
        make_colored_stroke(source, target, PALETTE[(index - 1) % len(PALETTE)])
        strokes.append(
            {
                "id": index,
                "point_count": payload.get("segments", [])[index - 1].get("point_count", 0)
                if index <= len(payload.get("segments", []))
                else 0,
                "pixel_count": payload.get("segments", [])[index - 1].get("pixel_count", 0)
                if index <= len(payload.get("segments", []))
                else 0,
                "color": PALETTE[(index - 1) % len(PALETTE)],
                "file": f"stroke_{index:02d}.png",
            }
        )
    return strokes


def build_record(
    kind: str,
    record_id: str,
    result_dir: Path,
    input_path: Path | None,
    payload: dict,
) -> dict:
    binary_path = result_dir / "binary.png"
    width, height = image_size(binary_path)
    strokes = cache_strokes(f"{kind}_{record_id}", result_dir, payload)
    encoded_id = safe_public_id(record_id)
    base_url = f"/media/{kind}/{encoded_id}"
    return {
        "id": record_id,
        "character": character_from_id(record_id) if kind == "demo" else "上传图片",
        "source_name": input_path.name if input_path else record_id,
        "segment_count": int(payload.get("segment_count", len(strokes))),
        "overlap_pixel_count": int(payload.get("overlap_pixel_count", 0)),
        "width": width,
        "height": height,
        "input_url": f"{base_url}/input",
        "binary_url": f"{base_url}/binary.png",
        "overlay_url": f"{base_url}/overlay.png",
        "gallery_url": f"{base_url}/strokes_gallery.png",
        "strokes": [
            {
                **stroke,
                "url": f"{base_url}/{stroke['file']}",
            }
            for stroke in strokes
        ],
    }


def ensure_demo_results() -> None:
    """Generate missing curated demo artifacts on a fresh clone."""
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for input_path in sorted(DATA_ROOT.rglob("*.png"), key=lambda path: path.name):
        sample_id = input_path.stem
        if sample_id in seen or not re.match(r"^\d+_", sample_id):
            continue
        seen.add(sample_id)
        result_dir = RESULT_ROOT / sample_id
        if (result_dir / "result.json").exists() and (result_dir / "binary.png").exists():
            continue
        try:
            result = split_character_image(str(input_path), WEB_CONFIG)
            save_result_artifacts(result, result_dir)
        except Exception as exc:
            print(f"示例 {sample_id} 自动生成失败：{exc}")


def load_demo_index() -> None:
    ensure_demo_results()
    for result_dir in sorted(RESULT_ROOT.iterdir(), key=lambda path: path.name):
        result_file = result_dir / "result.json"
        binary_file = result_dir / "binary.png"
        if not result_dir.is_dir() or not result_file.exists() or not binary_file.exists():
            continue
        if not re.match(r"^\d+_", result_dir.name):
            continue
        try:
            payload = load_result_payload(result_dir)
        except (OSError, json.JSONDecodeError):
            continue
        input_path = find_source_image(result_dir.name)
        # The demo list is intentionally limited to the project's curated
        # examples. This also keeps leftover result folders from appearing as
        # anonymous hash strings in the interface.
        if input_path is None:
            continue
        DEMO_INDEX[result_dir.name] = {
            "id": result_dir.name,
            "character": character_from_id(result_dir.name),
            "source_name": result_dir.name,
            "segment_count": int(payload.get("segment_count", 0)),
            "overlap_pixel_count": int(payload.get("overlap_pixel_count", 0)),
            "result_dir": result_dir,
            "input_path": input_path,
            "payload": payload,
        }


def demo_summary(info: dict) -> dict:
    return {
        "id": info["id"],
        "character": info["character"],
        "source_name": info["source_name"],
        "segment_count": info["segment_count"],
        "overlap_pixel_count": info["overlap_pixel_count"],
    }


def serve_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    if not path.is_file():
        error_response(handler, "文件不存在", 404)
        return
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(data)


def media_path(kind: str, record_id: str, asset: str) -> Path | None:
    index = DEMO_INDEX if kind == "demo" else RUNTIME_INDEX
    info = index.get(record_id)
    if info is None:
        return None
    if asset == "input":
        return info.get("input_path")
    if not re.fullmatch(r"(?:binary|overlay|strokes_gallery)\.png|stroke_\d{2}\.png", asset):
        return None
    if asset.startswith("stroke_"):
        return CACHE_ROOT / f"{kind}_{record_id}" / asset
    return info["result_dir"] / asset


class StrokeHandler(BaseHTTPRequestHandler):
    server_version = "SealStrokeWeb/1.0"

    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def do_GET(self) -> None:
        request = urlparse(self.path)
        path = request.path
        if path == "/api/health":
            json_response(self, {"ok": True, "examples": len(DEMO_INDEX)})
            return
        if path == "/api/examples":
            json_response(self, {"examples": [demo_summary(info) for info in DEMO_INDEX.values()]})
            return
        if path.startswith("/api/examples/"):
            record_id = unquote(path.removeprefix("/api/examples/"))
            info = DEMO_INDEX.get(record_id)
            if info is None:
                error_response(self, "找不到这个示例", 404)
                return
            record = build_record("demo", record_id, info["result_dir"], info["input_path"], info["payload"])
            json_response(self, record)
            return
        if path.startswith("/media/"):
            parts = path.split("/")
            if len(parts) != 5:
                error_response(self, "资源路径无效", 404)
                return
            kind, record_id, asset = parts[2], unquote(parts[3]), unquote(parts[4])
            resolved = media_path(kind, record_id, asset)
            if resolved is None:
                error_response(self, "找不到资源", 404)
                return
            serve_file(self, resolved)
            return
        if path == "/" or path == "/index.html":
            serve_file(self, WEBSITE_ROOT / "index.html")
            return
        relative = unquote(path.lstrip("/"))
        if relative.startswith(".") or ".." in Path(relative).parts:
            error_response(self, "路径无效", 400)
            return
        serve_file(self, WEBSITE_ROOT / relative)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/analyze":
            error_response(self, "接口不存在", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            error_response(self, "图片大小需在 1 到 16 MB 之间", 413)
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            error_response(self, "请以图片文件上传", 415)
            return
        body = self.rfile.read(length)
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        file_part = next((part for part in message.walk() if part.get_filename()), None)
        if file_part is None:
            error_response(self, "没有读取到图片文件", 400)
            return
        filename = Path(file_part.get_filename()).name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            error_response(self, "仅支持 PNG、JPG、JPEG 或 WebP 图片", 415)
            return
        job_id = uuid.uuid4().hex[:12]
        job_dir = RUNTIME_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        input_path = job_dir / f"input{suffix}"
        input_path.write_bytes(file_part.get_payload(decode=True) or b"")
        try:
            result = split_character_image(str(input_path), WEB_CONFIG)
            save_result_artifacts(result, job_dir)
            payload = load_result_payload(job_dir)
            RUNTIME_INDEX[job_id] = {
                "id": job_id,
                "result_dir": job_dir,
                "input_path": input_path,
                "payload": payload,
            }
            record = build_record("upload", job_id, job_dir, input_path, payload)
            record["original_filename"] = filename
            json_response(self, record, 201)
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            error_response(self, f"分析失败：{exc}", 500)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local visual frontend for seal-script stroke splitting.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    load_demo_index()
    server = ThreadingHTTPServer((args.host, args.port), StrokeHandler)
    print(f"拆笔画网站已启动：http://{args.host}:{args.port}")
    print(f"已加载示例：{len(DEMO_INDEX)} 个")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
