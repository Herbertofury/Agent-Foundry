#!/usr/bin/env python3
"""Convert an animated GIF into a Minecraft vertical texture strip plus .png.mcmeta.

Preserves frame timing to the nearest Minecraft tick (50 ms) and writes explicit
per-frame time entries when timing is non-uniform.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

TICK_MS = 50


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Source animated GIF")
    ap.add_argument("output", type=Path, help="Output PNG texture strip")
    ap.add_argument("--interpolate", action="store_true")
    ap.add_argument("--default-ms", type=int, default=100, help="Fallback duration for GIF frames with no duration")
    ap.add_argument("--allow-nonsquare", action="store_true")
    args = ap.parse_args()

    if args.default_ms < 1:
        raise SystemExit("--default-ms must be positive")

    src = Image.open(args.input)
    n = getattr(src, "n_frames", 1)
    if n < 2:
        raise SystemExit("input is not animated")

    frames = []
    durations_ms = []
    for i in range(n):
        src.seek(i)
        frames.append(src.convert("RGBA").copy())
        durations_ms.append(int(src.info.get("duration", 0) or args.default_ms))

    size = frames[0].size
    if any(f.size != size for f in frames):
        raise SystemExit("GIF frames do not share one canvas size")
    w, h = size
    if w != h and not args.allow_nonsquare:
        raise SystemExit("frames are non-square; use --allow-nonsquare only when the target texture supports explicit dimensions")

    ticks = [max(1, round(ms / TICK_MS)) for ms in durations_ms]
    strip = Image.new("RGBA", (w, h * n), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        strip.alpha_composite(frame, (0, i * h))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    strip.save(args.output)

    animation: dict[str, object] = {"interpolate": bool(args.interpolate)}
    if w != h:
        animation["width"] = w
        animation["height"] = h

    if len(set(ticks)) == 1:
        animation["frametime"] = ticks[0]
    else:
        animation["frames"] = [{"index": i, "time": t} for i, t in enumerate(ticks)]

    meta = {"animation": animation}
    meta_path = Path(str(args.output) + ".mcmeta")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    report = {
        "input": str(args.input),
        "texture": str(args.output),
        "mcmeta": str(meta_path),
        "frame_count": n,
        "frame_size": [w, h],
        "source_durations_ms": durations_ms,
        "minecraft_ticks": ticks,
        "timing_quantization_error_ms": [ticks[i] * TICK_MS - durations_ms[i] for i in range(n)],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
