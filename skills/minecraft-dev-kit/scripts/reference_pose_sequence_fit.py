#!/usr/bin/env python3
"""Fit creature-spec bone rotations to selected frames from an image/GIF reference.

The result is a sparse animation blockout whose keyframes are solved against visible
silhouette evidence. It is intended to accelerate animation reconstruction; final arc,
contact, secondary motion, and native-runtime QA remain mandatory.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.optimize import differential_evolution, minimize

from reference_cuboid_fit import find_bone, metrics, render_mask, render_wireframe, set_target, tolerant_edge_f1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("media_manifest", type=Path, help="Per-item manifest.json from reference_media_ingest.py")
    ap.add_argument("config", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--render-dir", type=Path)
    ap.add_argument("--maxiter", type=int, default=50)
    ap.add_argument("--popsize", type=int, default=8)
    ap.add_argument("--seed", type=int, default=4242)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    media = json.loads(args.media_manifest.read_text(encoding="utf-8"))
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    frames = media.get("frames", [])
    if not isinstance(frames, list) or not frames:
        print("media manifest contains no frames"); return 2
    root = args.media_manifest.parent.parent
    selected = cfg.get("selected_frames")
    if not isinstance(selected, list) or not selected:
        count = min(int(cfg.get("count", 10)), len(frames))
        selected = sorted(set(round(i * (len(frames) - 1) / max(1, count - 1)) for i in range(count)))
    selected = [int(i) for i in selected if 0 <= int(i) < len(frames)]
    if not selected:
        print("no valid selected frames"); return 2

    params = cfg.get("parameters", [])
    if not isinstance(params, list) or not params:
        print("config.parameters must define bone rotation and/or position targets"); return 2
    targets, setter_targets, bounds, channels = [], [], [], []
    for p in params:
        t = str(p.get("target", "")); bits = t.split("/")
        if len(bits) != 4 or bits[0] != "bone" or bits[2] not in {"rotation", "position"} or bits[3] not in {"0", "1", "2"}:
            print(f"pose parameter must be bone/<id>/rotation|position/<axis>: {t}"); return 2
        bone = find_bone(spec, bits[1]); channel = bits[2]
        if channel == "rotation":
            bone.setdefault("rotation", [0.0, 0.0, 0.0]); setter = t
        else:
            bone.setdefault("_fit_translation", [0.0, 0.0, 0.0]); setter = f"bone/{bits[1]}/_fit_translation/{bits[3]}"
        targets.append(t); setter_targets.append(setter); channels.append(channel); bounds.append((float(p["min"]), float(p["max"])))

    camera = copy.deepcopy(cfg.get("camera", {}))
    camera.setdefault("projection", "orthographic")
    temporal = float(cfg.get("temporal_regularization", 0.015))
    min_frame_iou = float(cfg.get("min_frame_iou", 0.90))
    previous = np.asarray([float(find_bone(spec, st.split("/")[1]).get(st.split("/")[2], [0, 0, 0])[int(st.split("/")[3])]) for st in setter_targets], dtype=np.float64)
    solved = []
    if args.render_dir: args.render_dir.mkdir(parents=True, exist_ok=True)

    for order, idx in enumerate(selected):
        fr = frames[idx]
        target = cv2.imread(str(root / str(fr["mask"])), cv2.IMREAD_GRAYSCALE)
        if target is None:
            print(f"could not read mask for frame {idx}"); return 2
        target = (target > 127).astype(np.uint8) * 255
        edge_weight = max(0.0, float(cfg.get("edge_weight", 0.0)))
        edge_target = None
        if edge_weight > 0 and fr.get("edges"):
            edge_target = cv2.imread(str(root / str(fr["edges"])), cv2.IMREAD_GRAYSCALE)
            if edge_target is None: print(f"could not read edge evidence for frame {idx}"); return 2
            if edge_target.shape != target.shape: edge_target = cv2.resize(edge_target, (target.shape[1], target.shape[0]), interpolation=cv2.INTER_NEAREST)
            edge_target = (edge_target > 0).astype(np.uint8) * 255

        def evaluate(x: np.ndarray) -> tuple[float, float, float | None, np.ndarray]:
            ss = copy.deepcopy(spec)
            cams = {"ref": camera}
            for t, v in zip(setter_targets, x): set_target(ss, cams, t, float(v))
            cand = render_mask(ss, camera, (target.shape[1], target.shape[0]))
            m = metrics(target, cand)
            edge_f1 = None
            base = 0.88 * (1.0 - m["iou"]) + 0.12 * m["normalized_chamfer"]
            if edge_weight > 0 and edge_target is not None:
                wire = render_wireframe(ss, camera, (target.shape[1], target.shape[0]))
                edge_f1 = tolerant_edge_f1(edge_target, wire, int(cfg.get("edge_tolerance", 2)))
                base = (base + edge_weight * (1.0 - edge_f1)) / (1.0 + edge_weight)
            smooth = float(np.mean(((x - previous) / np.maximum(1.0, np.asarray([b[1] - b[0] for b in bounds]))) ** 2)) if order > 0 else 0.0
            cost = base + temporal * smooth
            return float(cost), float(m["iou"]), (float(edge_f1) if edge_f1 is not None else None), cand

        local = minimize(lambda x: evaluate(np.asarray(x))[0], previous, method="Powell", bounds=bounds, options={"maxiter": args.maxiter, "xtol": 0.02, "ftol": 1e-5})
        best = np.asarray(local.x, dtype=np.float64)
        cost, iou, edge_f1, cand = evaluate(best)
        global_used = False
        if iou < min_frame_iou:
            de = differential_evolution(lambda x: evaluate(np.asarray(x))[0], bounds=bounds, seed=args.seed + idx, maxiter=max(12, args.maxiter // 2), popsize=args.popsize, polish=True, workers=1, updating="immediate")
            gx = np.asarray(de.x, dtype=np.float64); gcost, giou, gedge, gcand = evaluate(gx)
            if gcost < cost:
                best, cost, iou, edge_f1, cand = gx, gcost, giou, gedge, gcand
            global_used = True
        previous = best.copy()
        solved.append({"frame": idx, "time_ms": int(fr.get("time_ms", 0)), "values": [round(float(x), 5) for x in best], "iou": round(iou, 6), **({"geometry_edge_f1": round(edge_f1, 6)} if edge_f1 is not None else {}), "cost": round(cost, 6), "global_fallback": global_used})
        if args.render_dir: cv2.imwrite(str(args.render_dir / f"frame_{idx:04d}.png"), cand)

    # Convert solved scalar targets into vector rotation/position tracks per bone.
    tracks: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in solved:
        per: dict[tuple[str, str], list[float]] = {}
        for target_name, value in zip(targets, row["values"]):
            bits = target_name.split("/"); bid, channel, axis = bits[1], bits[2], int(bits[3])
            per.setdefault((bid, channel), [0.0, 0.0, 0.0])[axis] = float(value)
        for (bid, channel), value in per.items():
            tracks.setdefault(bid, {}).setdefault(channel, []).append({"time": round(row["time_ms"] / 1000.0, 6), "value": [round(v, 5) for v in value], "lerp": str(cfg.get("lerp", "catmullrom"))})
    animation = {
        "name": str(cfg.get("animation_name", "reconstructed")),
        "length": round(max(row["time_ms"] for row in solved) / 1000.0, 6),
        "loop": bool(cfg.get("loop", False)),
        "bones": tracks,
        "reference_frames": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
    mean_iou = float(np.mean([x["iou"] for x in solved]))
    edge_vals = [float(x["geometry_edge_f1"]) for x in solved if "geometry_edge_f1" in x]
    mean_edge = float(np.mean(edge_vals)) if edge_vals else None
    min_edge = float(cfg.get("min_edge_f1", 0.0))
    passed = mean_iou >= min_frame_iou and (mean_edge is None or mean_edge >= min_edge)
    report = {"result": "pass" if passed else "fail", "mean_iou": round(mean_iou, 6), "min_frame_iou": min_frame_iou, **({"mean_geometry_edge_f1": round(mean_edge, 6), "min_edge_f1": min_edge} if mean_edge is not None else {}), "selected_frames": selected, "solved": solved, "animation": str(args.output), "note": "Silhouette/internal-edge-fit rotation/position keyframes are a blockout. Refine arcs/contacts/overlap and prove against the animated reference + native runtime."}
    args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "mean_iou": report["mean_iou"], "animation": str(args.output)}, indent=2))
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
