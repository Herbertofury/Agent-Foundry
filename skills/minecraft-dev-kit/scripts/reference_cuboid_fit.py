#!/usr/bin/env python3
"""Fit a Dev Kit creature-spec cuboid blockout to one or more reference silhouettes.

This is a deterministic inverse-fitting aid, not a claim that unseen 3D geometry can be
recovered uniquely. Multi-view/GIF evidence reduces ambiguity; hidden surfaces remain
explicit inference until observed.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.optimize import differential_evolution


FACE_OUT = {
    "left": [0, 1, 3, 2], "right": [4, 6, 7, 5],
    "down": [0, 4, 5, 1], "up": [2, 3, 7, 6],
    "front": [0, 2, 6, 4], "back": [1, 5, 7, 3],
}


def rot_xyz(deg: list[float]) -> np.ndarray:
    x, y, z = [math.radians(float(v)) for v in (deg + [0, 0, 0])[:3]]
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float64)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float64)
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float64)
    return rz @ ry @ rx


def cube_corners(origin: list[float], size: list[float], inflate: float = 0.0) -> np.ndarray:
    o = np.asarray(origin, dtype=np.float64) - float(inflate)
    s = np.asarray(size, dtype=np.float64) + 2.0 * float(inflate)
    pts = []
    for xi in (0, 1):
        for yi in (0, 1):
            for zi in (0, 1):
                pts.append(o + s * np.array([xi, yi, zi], dtype=np.float64))
    return np.asarray(pts)


def transform_about(points: np.ndarray, pivot: list[float], rotation: list[float] | None) -> np.ndarray:
    if not rotation or not any(abs(float(v)) > 1e-12 for v in rotation):
        return points
    p = np.asarray(pivot, dtype=np.float64)
    r = rot_xyz([float(v) for v in rotation])
    return (points - p) @ r.T + p


def bone_chain(bones: dict[str, dict[str, Any]], bid: str) -> list[dict[str, Any]]:
    out = []
    seen = set()
    cur = bid
    while cur in bones and cur not in seen:
        seen.add(cur)
        out.append(bones[cur])
        parent = bones[cur].get("parent")
        if not isinstance(parent, str):
            break
        cur = parent
    return out


def world_cube_points(spec: dict[str, Any], cube: dict[str, Any]) -> np.ndarray:
    points = cube_corners(cube["origin"], cube["size"], float(cube.get("inflate", 0.0)))
    cp = cube.get("pivot")
    if not isinstance(cp, list):
        o, s = np.asarray(cube["origin"], dtype=float), np.asarray(cube["size"], dtype=float)
        cp = (o + s / 2.0).tolist()
    points = transform_about(points, cp, cube.get("rotation"))
    bones = {str(b["id"]): b for b in spec.get("bones", []) if isinstance(b, dict) and b.get("id")}
    for bone in bone_chain(bones, str(cube.get("bone", ""))):
        points = transform_about(points, bone.get("pivot", [0, 0, 0]), bone.get("rotation"))
        # Private inverse-fit translation used by reference_pose_sequence_fit.py to
        # evaluate animated bone position channels without changing the static spec schema.
        if isinstance(bone.get("_fit_translation"), list) and len(bone["_fit_translation"]) == 3:
            points = points + np.asarray(bone["_fit_translation"], dtype=np.float64)
    return points


def project(points: np.ndarray, camera: dict[str, Any], width: int, height: int) -> np.ndarray:
    target = np.asarray(camera.get("target", [0, 0, 0]), dtype=np.float64)
    yaw = float(camera.get("yaw", 0.0))
    pitch = float(camera.get("pitch", 0.0))
    roll = float(camera.get("roll", 0.0))
    # Rotate model opposite camera orientation into view space.
    r = rot_xyz([-pitch, -yaw, -roll])
    p = (points - target) @ r.T
    ox = float(camera.get("offset_x", 0.0))
    oy = float(camera.get("offset_y", 0.0))
    projection = str(camera.get("projection", "orthographic")).lower()
    if projection == "perspective":
        dist = float(camera.get("distance", 64.0))
        fov = math.radians(float(camera.get("fov", 35.0)))
        z = dist - p[:, 2]
        z = np.where(np.abs(z) < 1e-6, 1e-6, z)
        focal = 0.5 * width / math.tan(max(1e-4, fov / 2.0))
        x = p[:, 0] * focal / z + width / 2.0 + ox
        y = -p[:, 1] * focal / z + height / 2.0 + oy
    else:
        scale = max(1e-6, float(camera.get("ortho_scale", 32.0)))
        x = p[:, 0] * (width / scale) + width / 2.0 + ox
        y = -p[:, 1] * (width / scale) + height / 2.0 + oy
    return np.stack([x, y], axis=1)


def view_points(points: np.ndarray, camera: dict[str, Any]) -> np.ndarray:
    target = np.asarray(camera.get("target", [0, 0, 0]), dtype=np.float64)
    r = rot_xyz([-float(camera.get("pitch", 0.0)), -float(camera.get("yaw", 0.0)), -float(camera.get("roll", 0.0))])
    return (points - target) @ r.T


def render_wireframe(spec: dict[str, Any], camera: dict[str, Any], size: tuple[int, int], thickness: int = 1) -> np.ndarray:
    """Render projected edges of front-facing cuboid faces as geometry-feature evidence."""
    width, height = int(size[0]), int(size[1]); image = np.zeros((height, width), dtype=np.uint8)
    for cube in spec.get("cubes", []):
        if not isinstance(cube, dict) or not all(k in cube for k in ("origin", "size", "bone")): continue
        world = world_cube_points(spec, cube); view = view_points(world, camera); screen = project(world, camera, width, height)
        edges:set[tuple[int,int]] = set()
        for ids in FACE_OUT.values():
            q=view[ids]; normal=np.cross(q[1]-q[0],q[2]-q[0])
            if normal[2] <= 1e-7: continue
            for a,b in zip(ids, ids[1:]+ids[:1]): edges.add(tuple(sorted((a,b))))
        for a,b in edges:
            pa=tuple(np.rint(screen[a]).astype(int)); pb=tuple(np.rint(screen[b]).astype(int)); cv2.line(image,pa,pb,255,max(1,int(thickness)),cv2.LINE_8)
    return image


def tolerant_edge_f1(target: np.ndarray, candidate: np.ndarray, tolerance: int = 2) -> float:
    te=target>0; ce=candidate>0
    if not np.any(te) and not np.any(ce): return 1.0
    if not np.any(te) or not np.any(ce): return 0.0
    td=cv2.distanceTransform((~te).astype(np.uint8),cv2.DIST_L2,3); cd=cv2.distanceTransform((~ce).astype(np.uint8),cv2.DIST_L2,3)
    precision=float(np.mean(td[ce] <= tolerance)); recall=float(np.mean(cd[te] <= tolerance))
    return 0.0 if precision+recall==0 else 2*precision*recall/(precision+recall)


def render_mask(spec: dict[str, Any], camera: dict[str, Any], size: tuple[int, int]) -> np.ndarray:
    width, height = int(size[0]), int(size[1])
    mask = np.zeros((height, width), dtype=np.uint8)
    for cube in spec.get("cubes", []):
        if not isinstance(cube, dict) or not all(k in cube for k in ("origin", "size", "bone")):
            continue
        pts = project(world_cube_points(spec, cube), camera, width, height)
        hull = cv2.convexHull(np.round(pts).astype(np.int32))
        if len(hull) >= 3:
            cv2.fillConvexPoly(mask, hull, 255)
    return mask


def read_target(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read target mask {path}")
    return (img > 127).astype(np.uint8) * 255


def metrics(target: np.ndarray, cand: np.ndarray) -> dict[str, float]:
    t = target > 0
    c = cand > 0
    inter = int(np.logical_and(t, c).sum())
    union = int(np.logical_or(t, c).sum())
    iou = 1.0 if union == 0 else inter / union
    te = cv2.Canny(target, 50, 150) > 0
    ce = cv2.Canny(cand, 50, 150) > 0
    if np.any(te) and np.any(ce):
        td = cv2.distanceTransform((~te).astype(np.uint8), cv2.DIST_L2, 3)
        cd = cv2.distanceTransform((~ce).astype(np.uint8), cv2.DIST_L2, 3)
        chamfer = 0.5 * (float(np.mean(td[ce])) + float(np.mean(cd[te])))
    elif not np.any(te) and not np.any(ce):
        chamfer = 0.0
    else:
        chamfer = float(max(target.shape))
    norm_chamfer = chamfer / max(1.0, float(np.hypot(*target.shape)))
    return {"iou": float(iou), "chamfer_px": chamfer, "normalized_chamfer": norm_chamfer}


def find_cube(spec: dict[str, Any], cid: str) -> dict[str, Any]:
    for c in spec.get("cubes", []):
        if isinstance(c, dict) and str(c.get("id")) == cid:
            return c
    raise KeyError(f"cube {cid!r} not found")


def find_bone(spec: dict[str, Any], bid: str) -> dict[str, Any]:
    for b in spec.get("bones", []):
        if isinstance(b, dict) and str(b.get("id")) == bid:
            return b
    raise KeyError(f"bone {bid!r} not found")


def get_target(spec: dict[str, Any], cameras: dict[str, dict[str, Any]], target: str) -> float:
    p = target.split("/")
    if len(p) == 4 and p[0] == "cube":
        obj = find_cube(spec, p[1]); return float(obj[p[2]][int(p[3])])
    if len(p) == 4 and p[0] == "bone":
        obj = find_bone(spec, p[1]); return float(obj[p[2]][int(p[3])])
    if len(p) == 3 and p[0] == "camera":
        return float(cameras[p[1]].get(p[2], 0.0))
    raise KeyError(f"unsupported parameter target {target!r}")


def set_target(spec: dict[str, Any], cameras: dict[str, dict[str, Any]], target: str, value: float) -> None:
    p = target.split("/")
    if len(p) == 4 and p[0] == "cube":
        obj = find_cube(spec, p[1]); obj[p[2]][int(p[3])] = float(value); return
    if len(p) == 4 and p[0] == "bone":
        obj = find_bone(spec, p[1]); obj[p[2]][int(p[3])] = float(value); return
    if len(p) == 3 and p[0] == "camera":
        cameras[p[1]][p[2]] = float(value); return
    raise KeyError(f"unsupported parameter target {target!r}")


def fit(spec: dict[str, Any], cfg: dict[str, Any], cfg_root: Path, maxiter: int, popsize: int, seed: int) -> tuple[dict, dict, list[dict]]:
    refs = []
    cameras: dict[str, dict[str, Any]] = {}
    for idx, r in enumerate(cfg.get("references", [])):
        cam = copy.deepcopy(r.get("camera", {}))
        cid = str(cam.get("id", f"view_{idx}")); cam["id"] = cid; cameras[cid] = cam
        target_path = (cfg_root / str(r["mask"])).resolve() if not Path(str(r["mask"])).is_absolute() else Path(str(r["mask"]))
        target = read_target(target_path)
        edge = None; edge_path = None
        if r.get("edges"):
            edge_path = (cfg_root / str(r["edges"])).resolve() if not Path(str(r["edges"])).is_absolute() else Path(str(r["edges"]))
            edge = cv2.imread(str(edge_path), cv2.IMREAD_GRAYSCALE)
            if edge is None: raise ValueError(f"Could not read edge target {edge_path}")
            if edge.shape != target.shape: edge = cv2.resize(edge, (target.shape[1], target.shape[0]), interpolation=cv2.INTER_NEAREST)
            edge = (edge > 0).astype(np.uint8) * 255
        refs.append({"id": str(r.get("id", cid)), "camera_id": cid, "target": target, "edge": edge, "edge_weight": float(r.get("edge_weight", 0.0)), "weight": float(r.get("weight", 1.0)), "mask_path": str(target_path), "edge_path": str(edge_path) if edge_path else None})
    if not refs:
        raise ValueError("fit manifest requires references")
    params = cfg.get("parameters", [])
    bounds = []
    targets = []
    for p in params:
        targets.append(str(p["target"]))
        bounds.append((float(p["min"]), float(p["max"])))

    base_spec = copy.deepcopy(spec)
    base_cameras = copy.deepcopy(cameras)

    def evaluate(x: np.ndarray) -> tuple[float, dict, dict]:
        ss = copy.deepcopy(base_spec); cc = copy.deepcopy(base_cameras)
        for target, value in zip(targets, x):
            set_target(ss, cc, target, float(value))
        per = []
        weighted = 0.0; totalw = 0.0
        for r in refs:
            target = r["target"]; cand = render_mask(ss, cc[r["camera_id"]], (target.shape[1], target.shape[0]))
            m = metrics(target, cand)
            base_cost = 0.82 * (1.0 - m["iou"]) + 0.18 * m["normalized_chamfer"]
            edge_f1 = None; ew = max(0.0, float(r.get("edge_weight", 0.0)))
            if ew > 0 and r.get("edge") is not None:
                wire = render_wireframe(ss, cc[r["camera_id"]], (target.shape[1], target.shape[0]))
                edge_f1 = tolerant_edge_f1(r["edge"], wire, int(r.get("edge_tolerance", 2)))
            cost = (base_cost + ew * (1.0 - edge_f1)) / (1.0 + ew) if edge_f1 is not None else base_cost
            weighted += r["weight"] * cost; totalw += r["weight"]
            per.append({"id": r["id"], **m, **({"geometry_edge_f1": float(edge_f1)} if edge_f1 is not None else {})})
        return weighted / max(totalw, 1e-9), ss, {"cameras": cc, "views": per}

    if bounds:
        result = differential_evolution(lambda x: evaluate(x)[0], bounds=bounds, seed=seed, maxiter=maxiter, popsize=popsize, polish=True, updating="immediate", workers=1)
        best_x = np.asarray(result.x, dtype=np.float64)
        score, fitted_spec, aux = evaluate(best_x)
        opt = {"success": bool(result.success), "message": str(result.message), "iterations": int(result.nit), "evaluations": int(result.nfev), "cost": float(score)}
    else:
        best_x = np.asarray([], dtype=np.float64)
        score, fitted_spec, aux = evaluate(best_x)
        opt = {"success": True, "message": "evaluation only", "iterations": 0, "evaluations": 1, "cost": float(score)}
    fitted_params = [{"target": t, "value": float(v), "start": get_target(base_spec, base_cameras, t)} for t, v in zip(targets, best_x)]
    return fitted_spec, {"optimizer": opt, "parameters": fitted_params, **aux}, refs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("fit_manifest", type=Path)
    ap.add_argument("--out-spec", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--render-dir", type=Path)
    ap.add_argument("--maxiter", type=int, default=80)
    ap.add_argument("--popsize", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--min-iou", type=float, default=0.90)
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    cfg = json.loads(args.fit_manifest.read_text(encoding="utf-8"))
    fitted, report, refs = fit(spec, cfg, args.fit_manifest.parent, args.maxiter, args.popsize, args.seed)
    args.out_spec.parent.mkdir(parents=True, exist_ok=True)
    args.out_spec.write_text(json.dumps(fitted, indent=2) + "\n", encoding="utf-8")

    if args.render_dir:
        args.render_dir.mkdir(parents=True, exist_ok=True)
        for r in refs:
            cam = report["cameras"][r["camera_id"]]
            t = r["target"]
            cand = render_mask(fitted, cam, (t.shape[1], t.shape[0]))
            cv2.imwrite(str(args.render_dir / f"{r['id']}.png"), cand)
    mean_iou = float(np.mean([v["iou"] for v in report["views"]])) if report["views"] else 0.0
    passed = mean_iou >= args.min_iou
    report.update({"result": "pass" if passed else "fail", "mean_iou": mean_iou, "min_iou": args.min_iou, "out_spec": str(args.out_spec)})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "mean_iou": round(mean_iou, 6), "out_spec": str(args.out_spec), "report": str(args.report)}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
