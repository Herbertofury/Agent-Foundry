#!/usr/bin/env python3
"""Inspect a reference image/GIF for reconstruction-relevant evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat


def dominant_colors(img: Image.Image, count: int):
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    bg.alpha_composite(rgba)
    rgb = Image.new("RGB", rgba.size, (255, 255, 255))
    rgb.paste(rgba.convert("RGB"), mask=rgba.getchannel("A"))
    q = rgb.quantize(colors=max(2, count), method=Image.Quantize.MEDIANCUT).convert("RGB")
    colors = q.getcolors(q.width * q.height) or []
    colors.sort(reverse=True)
    total = q.width * q.height
    return [
        {"rgb": list(color), "fraction": round(n / total, 6)}
        for n, color in colors[:count]
    ]


def motion_score(a: Image.Image, b: Image.Image) -> float:
    a = a.convert("RGB").resize((128, 128))
    b = b.convert("RGB").resize((128, 128))
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    return round(sum(stat.mean) / (3 * 255), 6)


def alpha_bbox(img: Image.Image):
    if "A" not in img.getbands():
        return None
    box = img.convert("RGBA").getchannel("A").getbbox()
    return list(box) if box else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--colors", type=int, default=12)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    im = Image.open(args.input)
    frames = []
    durations = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        frames.append(im.convert("RGBA").copy())
        durations.append(int(im.info.get("duration", 0) or 0))

    motion = [0.0]
    for i in range(1, len(frames)):
        motion.append(motion_score(frames[i - 1], frames[i]))

    informative = sorted(range(len(frames)), key=lambda i: motion[i], reverse=True)[: min(8, len(frames))]
    informative.sort()

    first = frames[0]
    report = {
        "file": str(args.input),
        "format": im.format,
        "size": list(first.size),
        "mode": first.mode,
        "frame_count": len(frames),
        "durations_ms": durations,
        "total_duration_ms": sum(durations),
        "alpha_bbox_first_frame": alpha_bbox(first),
        "dominant_colors_first_frame": dominant_colors(first, args.colors),
        "frame_motion_scores": motion,
        "informative_frame_indexes": informative,
    }
    text = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
