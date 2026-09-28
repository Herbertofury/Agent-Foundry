#!/usr/bin/env python3
"""Stage image/GIF references into deterministic reconstruction evidence.

The tool never invents pixels. It extracts frames, foreground masks, edges, palette
samples, timing, hashes, bounding boxes, and centroids from the supplied media.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image

EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_inputs(items: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for p in items:
        if p.is_dir():
            out.extend(x for x in sorted(p.rglob("*")) if x.is_file() and x.suffix.lower() in EXTS)
        elif p.is_file() and p.suffix.lower() in EXTS:
            out.append(p)
    # keep first occurrence of each resolved path
    seen = set()
    unique = []
    for p in out:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def alpha_foreground(rgba: np.ndarray, threshold: int) -> np.ndarray | None:
    a = rgba[:, :, 3]
    if int(a.min()) >= 250:
        return None
    mask = (a > threshold).astype(np.uint8) * 255
    frac = float(np.mean(mask > 0))
    return mask if 0.001 < frac < 0.999 else None


def border_background_mask(rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    """Infer foreground from a mostly-consistent image border.

    This intentionally stays conservative. If the inferred mask is implausible, a
    center-seeded GrabCut fallback is attempted and the method is recorded.
    """
    h, w = rgb.shape[:2]
    b = max(1, min(h, w) // 40)
    border = np.concatenate(
        [rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3), rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)],
        axis=0,
    )
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    border_lab = cv2.cvtColor(border.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    center = np.median(border_lab, axis=0)
    border_dist = np.linalg.norm(border_lab - center, axis=1)
    dist = np.linalg.norm(lab - center.reshape(1, 1, 3), axis=2)
    threshold = float(max(12.0, np.percentile(border_dist, 97) + 10.0))
    raw_fg = (dist > threshold).astype(np.uint8) * 255

    # Keep only foreground components that do not primarily live on the image border.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw_fg, 8)
    mask = np.zeros_like(raw_fg)
    min_area = max(4, int(h * w * 0.0002))
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        touches = x <= 0 or y <= 0 or x + cw >= w or y + ch >= h
        if area >= min_area and not (touches and area < h * w * 0.03):
            mask[labels == i] = 255
    frac = float(np.mean(mask > 0))
    meta = {"method": "border-lab", "lab_distance_threshold": round(threshold, 4)}
    if 0.01 <= frac <= 0.92:
        return mask, meta

    # Conservative fallback: center rectangle as probable foreground.
    gc = np.full((h, w), cv2.GC_BGD, np.uint8)
    margin_x, margin_y = max(1, w // 10), max(1, h // 10)
    rect = (margin_x, margin_y, max(1, w - 2 * margin_x), max(1, h - 2 * margin_y))
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), gc, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        gmask = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        gfrac = float(np.mean(gmask > 0))
        if 0.01 <= gfrac <= 0.95:
            return gmask, {"method": "grabcut-center", "fallback_from": meta}
    except cv2.error:
        pass
    # Fail visibly instead of pretending background removal succeeded.
    return np.ones((h, w), np.uint8) * 255, {"method": "unsegmented", "fallback_from": meta}


def clean_mask(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    k = max(1, int(round(min(h, w) / 256)))
    kernel = np.ones((2 * k + 1, 2 * k + 1), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned


def mask_stats(mask: np.ndarray) -> dict:
    ys, xs = np.nonzero(mask > 0)
    if len(xs) == 0:
        return {"bbox": None, "centroid": None, "area_fraction": 0.0}
    return {
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
        "centroid": [round(float(xs.mean()), 4), round(float(ys.mean()), 4)],
        "area_fraction": round(float(len(xs) / mask.size), 6),
    }


def palette(rgb: np.ndarray, mask: np.ndarray, count: int) -> list[dict]:
    pix = rgb[mask > 0]
    if pix.size == 0:
        pix = rgb.reshape(-1, 3)
    # Deterministic subsample for large renders.
    if len(pix) > 200_000:
        idx = np.linspace(0, len(pix) - 1, 200_000, dtype=np.int64)
        pix = pix[idx]
    img = Image.fromarray(pix.reshape(1, -1, 3).astype(np.uint8), "RGB")
    q = img.quantize(colors=max(2, count), method=Image.Quantize.MEDIANCUT).convert("RGB")
    colors = q.getcolors(q.width * q.height) or []
    colors.sort(reverse=True)
    total = max(1, q.width * q.height)
    return [{"rgb": list(c), "fraction": round(n / total, 6)} for n, c in colors[:count]]


def frame_to_arrays(frame: Image.Image, alpha_threshold: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    rgba = np.asarray(frame.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[:, :, :3]
    mask = alpha_foreground(rgba, alpha_threshold)
    if mask is not None:
        method = {"method": "alpha", "alpha_threshold": alpha_threshold}
    else:
        mask, method = border_background_mask(rgb)
    mask = clean_mask(mask)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    edges = cv2.bitwise_and(edges, mask)
    return rgb, mask, edges, method


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--palette", type=int, default=12)
    ap.add_argument("--alpha-threshold", type=int, default=8)
    ap.add_argument("--max-frames", type=int, default=0, help="0 keeps all frames")
    args = ap.parse_args()

    files = expand_inputs(args.inputs)
    if not files:
        print("No supported reference media found")
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for file_index, path in enumerate(files):
        stem = f"{file_index:03d}_{path.stem}"
        item_dir = args.out / stem
        frame_dir = item_dir / "frames"
        mask_dir = item_dir / "masks"
        edge_dir = item_dir / "edges"
        frame_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)
        edge_dir.mkdir(parents=True, exist_ok=True)
        im = Image.open(path)
        total_frames = int(getattr(im, "n_frames", 1))
        keep = total_frames if args.max_frames <= 0 else min(total_frames, args.max_frames)
        frame_records = []
        elapsed = 0
        for i in range(keep):
            im.seek(i)
            fr = im.convert("RGBA").copy()
            duration = int(im.info.get("duration", 0) or 0)
            rgb, mask, edges, method = frame_to_arrays(fr, args.alpha_threshold)
            fpath = frame_dir / f"frame_{i:04d}.png"
            mpath = mask_dir / f"mask_{i:04d}.png"
            epath = edge_dir / f"edge_{i:04d}.png"
            Image.fromarray(np.dstack([rgb, np.full(mask.shape, 255, dtype=np.uint8)]), "RGBA").save(fpath)
            Image.fromarray(mask, "L").save(mpath)
            Image.fromarray(edges, "L").save(epath)
            stats = mask_stats(mask)
            frame_records.append(
                {
                    "index": i,
                    "time_ms": elapsed,
                    "duration_ms": duration,
                    "frame": str(fpath.relative_to(args.out)),
                    "mask": str(mpath.relative_to(args.out)),
                    "edges": str(epath.relative_to(args.out)),
                    "mask_method": method,
                    **stats,
                    "palette": palette(rgb, mask, args.palette),
                    "frame_sha256": sha256_file(fpath),
                }
            )
            elapsed += duration
        item = {
            "source": str(path),
            "source_sha256": sha256_file(path),
            "format": im.format,
            "size": [int(im.size[0]), int(im.size[1])],
            "frame_count_source": total_frames,
            "frame_count_staged": keep,
            "total_duration_ms_staged": elapsed,
            "frames": frame_records,
        }
        (item_dir / "manifest.json").write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
        records.append({**item, "manifest": str((item_dir / "manifest.json").relative_to(args.out))})

    master = {
        "schema_version": 1,
        "output_root": str(args.out.resolve()),
        "items": records,
        "note": "Foreground extraction is evidence, not truth. Verify masks visually when a baked/complex background is present.",
    }
    out_path = args.out / "REFERENCE-MEDIA-MANIFEST.json"
    out_path.write_text(json.dumps(master, indent=2) + "\n", encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
