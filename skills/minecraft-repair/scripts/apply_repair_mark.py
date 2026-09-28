#!/usr/bin/env python3
"""Apply the deterministic Minecraft Repair Mark v2 to official project artwork.

This script performs ordinary image compositing. It does not fetch artwork and does
not use generative image tools. Resolve/download the exact official artwork first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc

RED = (232, 24, 35, 255)
CHECK_BG = (0, 0, 0, 150)


def _stroke(draw: ImageDraw.ImageDraw, points, width: int, fill=RED):
    draw.line(points, fill=fill, width=max(1, width), joint="curve")


def apply_mark(src: Image.Image) -> Image.Image:
    img = src.convert("RGBA")
    w, h = img.size
    if w < 24 or h < 24:
        raise ValueError("Artwork is too small for a legible repair mark (minimum 24x24).")

    draw = ImageDraw.Draw(img, "RGBA")
    base = min(w, h)
    outer = max(2, round(base * 0.026))
    inner = max(1, round(base * 0.012))
    inset = max(3, round(base * 0.055))
    corner = max(8, round(base * 0.23))

    # Double red frame.
    half_outer = outer // 2
    draw.rectangle(
        [half_outer, half_outer, w - 1 - half_outer, h - 1 - half_outer],
        outline=RED,
        width=outer,
    )
    draw.rectangle(
        [inset, inset, w - 1 - inset, h - 1 - inset],
        outline=RED,
        width=inner,
    )

    # Corner brackets strengthen recognition at small launcher-icon sizes.
    bw = max(2, round(base * 0.02))
    c0 = inset
    c1x = min(w - inset, inset + corner)
    c1y = min(h - inset, inset + corner)
    rx = w - 1 - inset
    by = h - 1 - inset
    _stroke(draw, [(c0, c1y), (c0, c0), (c1x, c0)], bw)
    _stroke(draw, [(rx - corner, c0), (rx, c0), (rx, c0 + corner)], bw)
    _stroke(draw, [(c0, by - corner), (c0, by), (c0 + corner, by)], bw)
    _stroke(draw, [(rx - corner, by), (rx, by), (rx, by - corner)], bw)

    # Verified repair check in the lower-right, intentionally compact.
    badge_r = max(7, round(base * 0.12))
    margin = max(4, round(base * 0.055))
    cx = w - margin - badge_r
    cy = h - margin - badge_r
    draw.ellipse([cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r], fill=CHECK_BG, outline=RED, width=max(2, bw))
    p1 = (cx - round(badge_r * 0.52), cy + round(badge_r * 0.02))
    p2 = (cx - round(badge_r * 0.12), cy + round(badge_r * 0.42))
    p3 = (cx + round(badge_r * 0.58), cy - round(badge_r * 0.42))
    _stroke(draw, [p1, p2, p3], max(2, round(badge_r * 0.28)))

    return img


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Minecraft Repair Mark v2 to official project artwork.")
    parser.add_argument("input", type=Path, help="Official unmarked project artwork")
    parser.add_argument("output", type=Path, help="Output PNG path")
    args = parser.parse_args()

    with Image.open(args.input) as source:
        marked = apply_mark(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    marked.save(args.output, format="PNG", optimize=True)
    print(f"wrote {args.output} ({marked.width}x{marked.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
