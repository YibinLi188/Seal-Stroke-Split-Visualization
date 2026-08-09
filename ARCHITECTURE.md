# Architecture

## Data flow

```text
内置 data/*.png ─┐
                 ├─ split_character_image(...) ─┬─ binary.png
上传 image file ─┘                               ├─ overlay.png
                                                 ├─ strokes_individual/stroke_*.png
                                                 └─ result.json
                                                        │
已有结果目录 ── load_demo_index() ──────────────────────┤
上传结果目录 ── RUNTIME_INDEX ──────────────────────────┤
                                                        ▼
                                           JSON API + /media resources
                                                        ▼
                                      app.js colored stroke replay layers
```

## Boundaries

| Area | Entry point | Responsibility |
| --- | --- | --- |
| Algorithm | `src/seal_stroke_split/pipeline.py` | Image preparation, skeleton segmentation, pixel reassignment and artifact generation |
| CLI experiment | `scripts/run_experiment.py` | Run the algorithm over local files and save artifacts |
| Local HTTP layer | `网站/server.py` | Index curated demos, validate uploads, run the pipeline, serve JSON and images |
| Browser state | `网站/app.js` | Load API records, replay layers, manage controls and upload state |
| Browser layout | `网站/index.html`, `网站/styles.css` | Visual hierarchy and responsive presentation |

## Result contract

`save_result_artifacts(...)` emits the data consumed by the website:

- `binary.png`: cropped binary foreground image.
- `overlay.png`: algorithm output overlay.
- `strokes_gallery.png`: grid overview of all individual strokes.
- `strokes_individual/stroke_XX.png`: grayscale bitmap for one stroke.
- `result.json`: segment count, per-segment point/pixel counts and artifact paths.

The web service turns each grayscale individual-stroke image into a cached transparent PNG with a deterministic palette.
The browser overlays those transparent PNGs in sequence, so the animation represents the exact raster output rather than a redrawn approximation. Since masks are derived from the final single-label `stroke_map`, a foreground pixel can appear in only one layer.

## Curated examples vs. uploads

- `修改后的程序的结果/` contains reusable result folders. On a fresh clone, `ensure_demo_results()` generates missing folders from the curated source PNGs before indexing. `server.py` only indexes folders whose name begins with a numeric sample ID and whose matching source PNG exists under `data/`.
- Uploads are allocated a random job ID beneath `网站/runtime_results/` and kept in the in-memory `RUNTIME_INDEX` until the service stops.
- `.cache/` and `runtime_results/` are generated data and excluded from Git.

## Change guide

| Intended change | Start here |
| --- | --- |
| Split or merge behavior | `src/seal_stroke_split/` and matching tests under `tests/` |
| Website upload restrictions or output paths | `网站/server.py` |
| Playback state and controls | `网站/app.js` |
| Layout, colors and responsive behavior | `网站/styles.css` |
| Copy and semantic page structure | `网站/index.html` |

Keep `result.json` and the `stroke_files` paths compatible when changing artifact generation: both the website and existing result directories depend on them.
