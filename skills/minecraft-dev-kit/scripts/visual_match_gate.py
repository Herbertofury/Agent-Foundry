#!/usr/bin/env python3
"""Compare a candidate render to a reference using simple deterministic visual metrics."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageStat, ImageOps


def fit(img, size):
    return ImageOps.fit(img.convert("RGBA"), size, method=Image.Resampling.NEAREST, centering=(0.5, 0.5))


def mask(img, threshold):
    if "A" in img.getbands() and img.getchannel("A").getextrema()[0] < 255:
        return img.getchannel("A").point(lambda p: 255 if p > threshold else 0)
    gray = img.convert("L")
    return gray.point(lambda p: 255 if p < 250 else 0)


def _pixels(img):
    getter = getattr(img, "get_flattened_data", None)
    return getter() if getter else img.getdata()

def iou(a, b):
    aa = set(i for i,p in enumerate(_pixels(a)) if p)
    bb = set(i for i,p in enumerate(_pixels(b)) if p)
    union = len(aa | bb)
    return 1.0 if not union else len(aa & bb) / union


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--threshold", type=int, default=8)
    ap.add_argument("--heatmap", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    ref = Image.open(args.reference).convert("RGBA")
    cand = fit(Image.open(args.candidate), ref.size)

    diff = ImageChops.difference(ref.convert("RGB"), cand.convert("RGB"))
    mean = ImageStat.Stat(diff).mean
    mae = sum(mean) / (3*255)
    color_score = max(0.0, 1.0 - mae)

    ref_edge = ref.convert("L").filter(ImageFilter.FIND_EDGES)
    cand_edge = cand.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_diff = ImageStat.Stat(ImageChops.difference(ref_edge, cand_edge)).mean[0] / 255
    edge_score = max(0.0, 1.0 - edge_diff)

    silhouette_iou = iou(mask(ref, args.threshold), mask(cand, args.threshold))
    score = 0.50*silhouette_iou + 0.30*edge_score + 0.20*color_score
    report = {
        "reference": str(args.reference),
        "candidate": str(args.candidate),
        "size": list(ref.size),
        "silhouette_iou": round(silhouette_iou, 6),
        "edge_score": round(edge_score, 6),
        "color_score": round(color_score, 6),
        "weighted_score": round(score, 6),
        "note": "Diagnostic only: judge camera, geometry, material, and animation fidelity visually as well."
    }
    if args.heatmap:
        diff.save(args.heatmap)
    text = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.write_text(text+"\n", encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
