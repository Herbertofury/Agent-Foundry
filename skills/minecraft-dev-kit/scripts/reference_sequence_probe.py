#!/usr/bin/env python3
"""Analyze GIF/reference frame sequences for motion, cycle, and high-information poses."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from skimage.metrics import structural_similarity


def read_gray(path: Path) -> np.ndarray:
    arr = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if arr is None:
        raise ValueError(f"Could not read {path}")
    return arr


def read_mask(path: Path) -> np.ndarray:
    arr = read_gray(path)
    return (arr > 127).astype(np.uint8)


def motion_pair(a: np.ndarray, b: np.ndarray, ma: np.ndarray, mb: np.ndarray) -> dict:
    # Phase correlation estimates camera/global translation separately from deformation.
    shift, response = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32))
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag = np.linalg.norm(flow, axis=2)
    union = (ma | mb) > 0
    flow_mean = float(mag[union].mean()) if np.any(union) else float(mag.mean())
    flow_p95 = float(np.percentile(mag[union], 95)) if np.any(union) else float(np.percentile(mag, 95))
    inter = int(np.logical_and(ma, mb).sum())
    uni = int(np.logical_or(ma, mb).sum())
    iou = 1.0 if uni == 0 else inter / uni
    return {
        "translation": [round(float(shift[0]), 4), round(float(shift[1]), 4)],
        "phase_response": round(float(response), 6),
        "flow_mean": round(flow_mean, 6),
        "flow_p95": round(flow_p95, 6),
        "mask_change": round(1.0 - iou, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path, help="Per-item manifest.json from reference_media_ingest.py")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--count", type=int, default=12)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.manifest.parent.parent
    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        print("No frames in manifest")
        return 2
    grays = [read_gray(root / str(f["frame"])) for f in frames]
    masks = [read_mask(root / str(f["mask"])) for f in frames]
    pairs = []
    energies = [0.0]
    for i in range(1, len(frames)):
        m = motion_pair(grays[i - 1], grays[i], masks[i - 1], masks[i])
        pairs.append({"from": i - 1, "to": i, **m})
        energies.append(m["flow_mean"] + 10.0 * m["mask_change"])

    # Seam/cycle evidence; duration is metadata truth, seam score is only a diagnostic.
    if len(grays) > 1:
        seam_ssim = float(structural_similarity(grays[0], grays[-1], data_range=255))
        seam_inter = int(np.logical_and(masks[0], masks[-1]).sum())
        seam_union = int(np.logical_or(masks[0], masks[-1]).sum())
        seam_iou = 1.0 if seam_union == 0 else seam_inter / seam_union
    else:
        seam_ssim, seam_iou = 1.0, 1.0

    n = len(frames)
    k = max(1, min(args.count, n))
    even = {round(i * (n - 1) / max(1, k - 1)) for i in range(k)}
    peaks = set(sorted(range(n), key=lambda i: energies[i], reverse=True)[: max(1, k // 2)])
    selected = sorted(even | peaks)
    if len(selected) > k:
        selected = sorted(selected, key=lambda i: (i not in peaks, -energies[i]))[:k]
        selected.sort()

    centroids = np.asarray([f.get("centroid") or [0.0, 0.0] for f in frames], dtype=np.float64)
    bboxes = [f.get("bbox") for f in frames]
    centroid_span = [float(np.ptp(centroids[:, 0])), float(np.ptp(centroids[:, 1]))] if len(centroids) else [0.0, 0.0]
    diag = (grays[0].shape[0] ** 2 + grays[0].shape[1] ** 2) ** 0.5
    trans_mag = [float(np.hypot(*p["translation"])) for p in pairs]
    shape_change = [float(p["mask_change"]) for p in pairs]
    # Stable centroid + non-trivial silhouette change is common in turntable/reference spin GIFs.
    turntable_score = 0.0
    if n >= 6:
        center_stability = max(0.0, 1.0 - (sum(centroid_span) / max(1.0, diag * 0.25)))
        shape = min(1.0, (float(np.mean(shape_change)) if shape_change else 0.0) * 8.0)
        low_translation = max(0.0, 1.0 - (float(np.mean(trans_mag)) if trans_mag else 0.0) / max(1.0, diag * 0.03))
        turntable_score = center_stability * shape * low_translation

    report = {
        "schema_version": 1,
        "source": data.get("source"),
        "frames": n,
        "duration_ms": data.get("total_duration_ms_staged", 0),
        "pair_motion": pairs,
        "motion_energy": [round(float(x), 6) for x in energies],
        "selected_frames": selected,
        "selected_time_ms": [frames[i].get("time_ms", 0) for i in selected],
        "cycle_seam": {"ssim": round(seam_ssim, 6), "mask_iou": round(float(seam_iou), 6)},
        "centroid_span_px": [round(x, 4) for x in centroid_span],
        "turntable_or_rotation_score": round(float(turntable_score), 6),
        "interpretation": "turntable/rotation likely" if turntable_score >= 0.45 else "deformation/translation or uncertain",
        "note": "Motion classification is diagnostic; confirm semantic poses against the actual reference.",
    }
    out = args.output or args.manifest.with_name("sequence-probe.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
