#!/usr/bin/env python3
"""Create a contact sheet of evenly spaced + high-motion GIF frames."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from PIL import Image, ImageChops, ImageStat, ImageOps, ImageDraw


def diff_score(a, b):
    a = a.convert("RGB").resize((96, 96))
    b = b.convert("RGB").resize((96, 96))
    s = ImageStat.Stat(ImageChops.difference(a, b))
    return sum(s.mean) / (3 * 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--thumb", type=int, default=192)
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()

    im = Image.open(args.input)
    frames, durations = [], []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        frames.append(im.convert("RGBA").copy())
        durations.append(int(im.info.get("duration", 0) or 0))
    n = len(frames)
    k = max(1, min(args.count, n))
    even = {round(i * (n - 1) / max(1, k - 1)) for i in range(k)}
    motion = [0.0] + [diff_score(frames[i-1], frames[i]) for i in range(1, n)]
    peak_budget = max(0, k // 2)
    peaks = set(sorted(range(n), key=lambda i: motion[i], reverse=True)[:peak_budget])
    selected = sorted(even | peaks)
    if len(selected) > k:
        selected = sorted(selected, key=lambda i: (i not in peaks, -motion[i]))[:k]
        selected.sort()
    elif len(selected) < k:
        for i in sorted(range(n), key=lambda i: motion[i], reverse=True):
            if i not in selected:
                selected.append(i)
            if len(selected) == k:
                break
        selected.sort()

    cols = min(4, len(selected))
    rows = math.ceil(len(selected) / cols)
    label_h = 24
    sheet = Image.new("RGBA", (cols * args.thumb, rows * (args.thumb + label_h)), (32,32,32,255))
    draw = ImageDraw.Draw(sheet)
    elapsed = [0]
    for d in durations[:-1]:
        elapsed.append(elapsed[-1] + d)
    for slot, idx in enumerate(selected):
        r, c = divmod(slot, cols)
        thumb = ImageOps.contain(frames[idx], (args.thumb, args.thumb))
        x = c * args.thumb + (args.thumb - thumb.width)//2
        y = r * (args.thumb + label_h) + (args.thumb - thumb.height)//2
        sheet.alpha_composite(thumb, (x,y))
        draw.text((c*args.thumb+4, r*(args.thumb+label_h)+args.thumb+4), f"f{idx}  t={elapsed[idx]}ms", fill=(255,255,255,255))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)

    manifest = {
        "input": str(args.input),
        "frame_count": n,
        "selected": selected,
        "selected_time_ms": [elapsed[i] for i in selected],
        "motion_scores": [round(motion[i], 6) for i in selected],
        "contact_sheet": str(args.output),
    }
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
