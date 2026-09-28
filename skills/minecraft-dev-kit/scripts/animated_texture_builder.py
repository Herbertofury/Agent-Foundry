#!/usr/bin/env python3
"""Build a Minecraft vertical animated texture strip and .png.mcmeta."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=Path, help="Output PNG path")
    ap.add_argument("frames", nargs="+", type=Path)
    ap.add_argument("--frametime", type=int, default=2)
    ap.add_argument("--interpolate", action="store_true")
    ap.add_argument("--allow-nonsquare", action="store_true")
    args = ap.parse_args()
    if args.frametime < 1:
        raise SystemExit("frametime must be >= 1 Minecraft tick")

    images = [Image.open(p).convert("RGBA") for p in args.frames]
    size = images[0].size
    if any(im.size != size for im in images):
        raise SystemExit("all frames must have identical dimensions")
    w, h = size
    if w != h and not args.allow_nonsquare:
        raise SystemExit("frames are non-square; pass --allow-nonsquare only when the target runtime supports explicit frame dimensions")

    out = Image.new("RGBA", (w, h * len(images)), (0,0,0,0))
    for i, im in enumerate(images):
        out.alpha_composite(im, (0, i*h))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)

    anim = {"frametime": args.frametime, "interpolate": bool(args.interpolate)}
    if w != h:
        anim["width"] = w
        anim["height"] = h
    meta = {"animation": anim}
    meta_path = Path(str(args.output) + ".mcmeta")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"texture": str(args.output), "mcmeta": str(meta_path), "frames": len(images), "frame_size": [w,h]}, indent=2))

if __name__ == "__main__":
    main()
