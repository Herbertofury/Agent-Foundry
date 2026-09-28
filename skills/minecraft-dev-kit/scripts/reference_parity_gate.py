#!/usr/bin/env python3
"""High-signal static/animated reference parity gate.

Compares actual candidate renders to reference media using alignment-aware silhouette,
edge, SSIM, and color metrics. GIFs/sequences use dynamic-time-warped frame matching.
This is diagnostic evidence; it does not make unobserved 3D surfaces knowable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageSequence
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import structural_similarity


def frames(path: Path, max_frames: int) -> tuple[list[np.ndarray], list[int]]:
    im = Image.open(path)
    out, dur = [], []
    n = int(getattr(im, "n_frames", 1))
    idxs = list(range(n))
    if max_frames > 0 and n > max_frames:
        idxs = sorted(set(round(i * (n - 1) / max(1, max_frames - 1)) for i in range(max_frames)))
    for i in idxs:
        im.seek(i)
        out.append(np.asarray(im.convert("RGBA"), dtype=np.uint8))
        dur.append(int(im.info.get("duration", 0) or 0))
    return out, dur


def foreground(rgba: np.ndarray) -> np.ndarray:
    a = rgba[:, :, 3]
    if int(a.min()) < 250:
        m = a > 8
        if 0.001 < float(m.mean()) < 0.999:
            return m
    rgb = rgba[:, :, :3]
    h, w = rgb.shape[:2]
    b = max(1, min(h, w) // 50)
    border = np.concatenate([rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3), rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)])
    bg = np.median(border.astype(np.float32), axis=0)
    d = np.linalg.norm(rgb.astype(np.float32) - bg.reshape(1, 1, 3), axis=2)
    t = max(18.0, float(np.percentile(np.linalg.norm(border.astype(np.float32) - bg, axis=1), 98)) + 12.0)
    m = d > t
    if not (0.005 < float(m.mean()) < 0.98):
        m = np.ones((h, w), bool)
    return m


def resize_like(arr: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    return cv2.resize(arr, (w, h), interpolation=cv2.INTER_NEAREST if arr.ndim == 2 else cv2.INTER_NEAREST)


def align_translation(ref_gray: np.ndarray, cand_gray: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    shift, _ = cv2.phaseCorrelate(ref_gray.astype(np.float32), cand_gray.astype(np.float32))
    # phaseCorrelate returns shift to map src1 -> src2; invert to bring candidate onto reference.
    dx, dy = -float(shift[0]), -float(shift[1])
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    aligned = cv2.warpAffine(cand_gray, m, (cand_gray.shape[1], cand_gray.shape[0]), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    return aligned, (dx, dy)


def shift_rgba(arr: np.ndarray, dx: float, dy: float) -> np.ndarray:
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(arr, m, (arr.shape[1], arr.shape[0]), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255, 0))


def edge_f1(ref_mask: np.ndarray, cand_mask: np.ndarray, tolerance: int = 2) -> float:
    rm = (ref_mask.astype(np.uint8) * 255)
    cm = (cand_mask.astype(np.uint8) * 255)
    re = cv2.Canny(rm, 50, 150) > 0
    ce = cv2.Canny(cm, 50, 150) > 0
    if not np.any(re) and not np.any(ce):
        return 1.0
    if not np.any(re) or not np.any(ce):
        return 0.0
    rd = cv2.distanceTransform((~re).astype(np.uint8), cv2.DIST_L2, 3)
    cd = cv2.distanceTransform((~ce).astype(np.uint8), cv2.DIST_L2, 3)
    precision = float(np.mean(rd[ce] <= tolerance))
    recall = float(np.mean(cd[re] <= tolerance))
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def internal_edge_f1(ref: np.ndarray, cand: np.ndarray, ref_mask: np.ndarray, cand_mask: np.ndarray, tolerance: int = 2) -> float:
    """Compare internal rendered/image features without double-counting the outer silhouette."""
    rg = cv2.cvtColor(ref[:, :, :3], cv2.COLOR_RGB2GRAY)
    cg = cv2.cvtColor(cand[:, :, :3], cv2.COLOR_RGB2GRAY)
    kernel = np.ones((3, 3), np.uint8)
    ri = cv2.erode(ref_mask.astype(np.uint8), kernel, iterations=2) > 0
    ci = cv2.erode(cand_mask.astype(np.uint8), kernel, iterations=2) > 0
    re = (cv2.Canny(rg, 35, 110) > 0) & ri
    ce = (cv2.Canny(cg, 35, 110) > 0) & ci
    if not np.any(re) and not np.any(ce):
        return 1.0
    if not np.any(re) or not np.any(ce):
        return 0.0
    rd = cv2.distanceTransform((~re).astype(np.uint8), cv2.DIST_L2, 3)
    cd = cv2.distanceTransform((~ce).astype(np.uint8), cv2.DIST_L2, 3)
    precision = float(np.mean(rd[ce] <= tolerance))
    recall = float(np.mean(cd[re] <= tolerance))
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def single_score(ref: np.ndarray, cand: np.ndarray, auto_align: bool) -> dict:
    h, w = ref.shape[:2]
    if cand.shape[:2] != (h, w):
        cand = cv2.resize(cand, (w, h), interpolation=cv2.INTER_NEAREST)
    ref_gray = cv2.cvtColor(ref[:, :, :3], cv2.COLOR_RGB2GRAY)
    cand_gray = cv2.cvtColor(cand[:, :, :3], cv2.COLOR_RGB2GRAY)
    rm0, cm0 = foreground(ref), foreground(cand)
    shift = (0.0, 0.0)
    if auto_align:
        # Align on the outer subject mask, not internal texture/lighting features.
        # Otherwise a wrong stripe/seam can incorrectly move an already aligned model.
        _, shift = align_translation((rm0.astype(np.uint8) * 255), (cm0.astype(np.uint8) * 255))
        cand = shift_rgba(cand, *shift)
        cand_gray = cv2.cvtColor(cand[:, :, :3], cv2.COLOR_RGB2GRAY)
    rm, cm = foreground(ref), foreground(cand)
    inter = int(np.logical_and(rm, cm).sum())
    union = int(np.logical_or(rm, cm).sum())
    iou = 1.0 if union == 0 else inter / union
    ef1 = edge_f1(rm, cm)
    internal_f1 = internal_edge_f1(ref, cand, rm, cm)
    ssim = float(structural_similarity(ref_gray, cand_gray, data_range=255))
    common = rm & cm
    if np.any(common):
        rlab = rgb2lab(ref[:, :, :3].astype(np.float32) / 255.0)
        clab = rgb2lab(cand[:, :, :3].astype(np.float32) / 255.0)
        de = deltaE_ciede2000(rlab[common], clab[common])
        mean_de = float(np.mean(de))
        color = max(0.0, 1.0 - mean_de / 50.0)
    else:
        mean_de, color = 100.0, 0.0
    score = 0.38 * iou + 0.18 * ef1 + 0.16 * internal_f1 + 0.18 * max(0.0, ssim) + 0.10 * color
    return {
        "silhouette_iou": round(float(iou), 6),
        "silhouette_edge_f1": round(float(ef1), 6),
        "internal_edge_f1": round(float(internal_f1), 6),
        "ssim": round(float(ssim), 6),
        "mean_delta_e": round(float(mean_de), 6),
        "color_score": round(float(color), 6),
        "weighted_score": round(float(score), 6),
        "alignment_shift_px": [round(float(shift[0]), 4), round(float(shift[1]), 4)],
    }


def dtw(cost: np.ndarray) -> tuple[float, list[tuple[int, int]]]:
    n, m = cost.shape
    dp = np.full((n + 1, m + 1), np.inf, dtype=np.float64)
    dp[0, 0] = 0.0
    back = np.zeros((n + 1, m + 1, 2), dtype=np.int32)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            choices = [(dp[i - 1, j], i - 1, j), (dp[i, j - 1], i, j - 1), (dp[i - 1, j - 1], i - 1, j - 1)]
            best = min(choices, key=lambda x: x[0])
            dp[i, j] = cost[i - 1, j - 1] + best[0]
            back[i, j] = [best[1], best[2]]
    path = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        i, j = map(int, back[i, j])
    path.reverse()
    return float(dp[n, m] / max(1, len(path))), path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reference", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--min-score", type=float, default=0.90)
    ap.add_argument("--min-silhouette", type=float, default=0.92)
    ap.add_argument("--max-frames", type=int, default=48)
    ap.add_argument("--no-align", action="store_true")
    args = ap.parse_args()

    rf, rd = frames(args.reference, args.max_frames)
    cf, cd = frames(args.candidate, args.max_frames)
    auto_align = not args.no_align
    if len(rf) == 1 and len(cf) == 1:
        details = single_score(rf[0], cf[0], auto_align)
        score = details["weighted_score"]
        silhouette = details["silhouette_iou"]
        seq = None
    else:
        cost = np.zeros((len(rf), len(cf)), dtype=np.float64)
        cache: dict[tuple[int, int], dict] = {}
        for i, r in enumerate(rf):
            for j, c in enumerate(cf):
                s = single_score(r, c, auto_align)
                cache[(i, j)] = s
                cost[i, j] = 1.0 - s["weighted_score"]
        mean_cost, path = dtw(cost)
        matched = [cache[p] for p in path]
        score = 1.0 - mean_cost
        silhouette = float(np.mean([x["silhouette_iou"] for x in matched])) if matched else 0.0
        duration_ref, duration_cand = sum(rd), sum(cd)
        duration_ratio = 1.0 if duration_ref == duration_cand == 0 else min(duration_ref, duration_cand) / max(1, max(duration_ref, duration_cand))
        score = 0.9 * score + 0.1 * duration_ratio
        details = {
            "mean_matched_silhouette_iou": round(float(silhouette), 6),
            "duration_ref_ms": duration_ref,
            "duration_candidate_ms": duration_cand,
            "duration_ratio": round(float(duration_ratio), 6),
            "dtw_pairs": path,
            "matched_scores": matched,
        }
        seq = True
    passed = score >= args.min_score and silhouette >= args.min_silhouette
    report = {
        "result": "pass" if passed else "fail",
        "reference": str(args.reference),
        "candidate": str(args.candidate),
        "reference_frames": len(rf),
        "candidate_frames": len(cf),
        "sequence": bool(seq),
        "thresholds": {"weighted_score": args.min_score, "silhouette_iou": args.min_silhouette},
        "weighted_score": round(float(score), 6),
        "silhouette_iou": round(float(silhouette), 6),
        "details": details,
        "note": "Visible-view parity only. Hidden geometry and native Minecraft behavior still require separate proof.",
    }
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
