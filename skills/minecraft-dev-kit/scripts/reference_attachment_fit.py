#!/usr/bin/env python3
"""Fit an asset attachment/display transform from authorized context evidence.

The geometry stays unchanged. The solver fits scale + Euler rotation + translation around
one semantic asset anchor, using any combination of 2D projected landmarks and 3D world
constraints. Regularization prevents unconstrained hidden-axis drift.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from reference_cuboid_fit import project, rot_xyz


def vec3(value: Any, name: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in value):
        raise ValueError(f"{name} must be three finite numbers")
    return np.asarray(value, dtype=np.float64)


def load_oracles(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def oracle_point(oracles: dict[str, Any], profile: str, name: str) -> np.ndarray:
    try:
        return vec3(oracles["profiles"][profile]["points"][name], f"oracle {profile}/{name}")
    except KeyError as exc:
        raise KeyError(f"unknown player oracle point {profile}/{name}") from exc


def collect_locators(spec: dict[str, Any]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for bone in spec.get("bones", []):
        if not isinstance(bone, dict):
            continue
        locs = bone.get("locators")
        if not isinstance(locs, dict):
            continue
        for name, value in locs.items():
            if isinstance(value, list) and len(value) == 3:
                out[str(name)] = vec3(value, f"locator {name}")
    return out


def collect_points(spec: dict[str, Any]) -> dict[str, np.ndarray]:
    out = collect_locators(spec)
    for bone in spec.get("bones", []):
        if isinstance(bone, dict) and bone.get("id") and isinstance(bone.get("pivot"), list):
            out[f"bone:{bone['id']}"] = vec3(bone["pivot"], f"bone {bone['id']} pivot")
    for cube in spec.get("cubes", []):
        if not isinstance(cube, dict) or not cube.get("id"):
            continue
        try:
            o, s = vec3(cube["origin"], "cube origin"), vec3(cube["size"], "cube size")
        except Exception:
            continue
        center = o + s / 2.0
        out[f"cube:{cube['id']}:center"] = center
        for label, delta in {
            "min": np.zeros(3),
            "max": s,
            "top": np.array([s[0] / 2, s[1], s[2] / 2]),
            "bottom": np.array([s[0] / 2, 0, s[2] / 2]),
        }.items():
            out[f"cube:{cube['id']}:{label}"] = o + delta
    return out


def resolve_local(points: dict[str, np.ndarray], item: dict[str, Any]) -> np.ndarray:
    if isinstance(item.get("local"), list):
        return vec3(item["local"], "constraint local")
    ref = item.get("point") or item.get("locator")
    if not isinstance(ref, str) or ref not in points:
        raise KeyError(f"constraint requires local or known point/locator; got {ref!r}")
    return points[ref].copy()


def transform_point(local: np.ndarray, anchor_local: np.ndarray, anchor_world: np.ndarray, scale: float, rotation: np.ndarray, offset: np.ndarray) -> np.ndarray:
    r = rot_xyz(rotation.tolist())
    return anchor_world + offset + (r @ ((local - anchor_local) * scale))


def parameter_vector(initial: dict[str, Any]) -> np.ndarray:
    return np.asarray([
        float(initial.get("scale", 1.0)),
        *vec3(initial.get("rotation", [0, 0, 0]), "initial.rotation"),
        *vec3(initial.get("offset", [0, 0, 0]), "initial.offset"),
    ], dtype=np.float64)


def bounds_vector(cfg: dict[str, Any], x0: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = cfg.get("bounds", {}) if isinstance(cfg.get("bounds"), dict) else {}
    scale = b.get("scale", [max(0.05, x0[0] * 0.35), max(0.1, x0[0] * 2.8)])
    rot_span = vec3(b.get("rotation_span", [180, 180, 180]), "bounds.rotation_span")
    off_span = vec3(b.get("offset_span", [16, 16, 16]), "bounds.offset_span")
    lo = np.asarray([float(scale[0]), *(x0[1:4] - rot_span), *(x0[4:7] - off_span)], dtype=np.float64)
    hi = np.asarray([float(scale[1]), *(x0[1:4] + rot_span), *(x0[4:7] + off_span)], dtype=np.float64)
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, default=Path(__file__).resolve().parent.parent / "references" / "player-rig-oracles.json")
    ap.add_argument("--min-screen-rmse", type=float, default=1.5)
    ap.add_argument("--min-world-rmse", type=float, default=0.20)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    cfg = json.loads(args.manifest.read_text(encoding="utf-8"))
    oracles = load_oracles(args.oracle)
    points = collect_points(spec)
    anchor = cfg.get("anchor", {}) if isinstance(cfg.get("anchor"), dict) else {}
    anchor_name = anchor.get("asset_point") or anchor.get("locator")
    if not isinstance(anchor_name, str) or anchor_name not in points:
        print(f"Unknown asset anchor {anchor_name!r}")
        return 2
    anchor_local = points[anchor_name]
    if isinstance(anchor.get("world"), list):
        anchor_world = vec3(anchor["world"], "anchor.world")
        oracle_meta = None
    elif isinstance(anchor.get("player"), dict):
        p = anchor["player"]
        profile, name = str(p.get("profile", "default")), str(p["point"])
        anchor_world = oracle_point(oracles, profile, name)
        oracle_meta = {"profile": profile, "point": name}
    else:
        print("anchor requires world or player {profile,point}")
        return 2

    camera = cfg.get("camera") if isinstance(cfg.get("camera"), dict) else None
    screen_raw = cfg.get("screen_constraints", [])
    world_raw = cfg.get("world_constraints", [])
    if not screen_raw and not world_raw:
        print("At least one screen_constraints or world_constraints entry is required")
        return 2
    if screen_raw and camera is None:
        print("camera is required for screen constraints")
        return 2

    screen = []
    for row in screen_raw:
        local = resolve_local(points, row)
        target = row.get("target_px")
        if not isinstance(target, list) or len(target) != 2:
            print("screen constraint target_px must be [x,y]")
            return 2
        screen.append((str(row.get("id", row.get("point", "screen"))), local, np.asarray(target, dtype=np.float64), float(row.get("weight", 1.0))))
    world = []
    for row in world_raw:
        local = resolve_local(points, row)
        target = vec3(row["target_world"], "world constraint target_world")
        world.append((str(row.get("id", row.get("point", "world"))), local, target, float(row.get("weight", 1.0))))

    initial = cfg.get("initial", {}) if isinstance(cfg.get("initial"), dict) else {}
    x0 = parameter_vector(initial)
    lo, hi = bounds_vector(cfg, x0)
    reg = cfg.get("regularization", {}) if isinstance(cfg.get("regularization"), dict) else {}
    reg_scale = float(reg.get("scale", 0.025))
    reg_rotation = float(reg.get("rotation", 0.0025))
    reg_offset = float(reg.get("offset", 0.025))
    screen_norm = float(cfg.get("screen_normalization_px", 16.0))
    world_norm = float(cfg.get("world_normalization", 4.0))

    def unpack(x: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        return float(x[0]), x[1:4], x[4:7]

    def residuals(x: np.ndarray) -> np.ndarray:
        scale, rotation, offset = unpack(x)
        out: list[float] = []
        for _, local, target, weight in screen:
            wp = transform_point(local, anchor_local, anchor_world, scale, rotation, offset)
            pp = project(wp.reshape(1, 3), camera or {}, int(cfg.get("image_width", 256)), int(cfg.get("image_height", 256)))[0]
            out.extend(((pp - target) / max(1.0, screen_norm) * math.sqrt(max(0.0, weight))).tolist())
        for _, local, target, weight in world:
            wp = transform_point(local, anchor_local, anchor_world, scale, rotation, offset)
            out.extend(((wp - target) / max(1e-6, world_norm) * math.sqrt(max(0.0, weight))).tolist())
        out.append((scale - x0[0]) * reg_scale)
        out.extend(((rotation - x0[1:4]) * reg_rotation).tolist())
        out.extend(((offset - x0[4:7]) * reg_offset).tolist())
        return np.asarray(out, dtype=np.float64)

    opt = least_squares(residuals, x0, bounds=(lo, hi), method="trf", xtol=1e-11, ftol=1e-11, gtol=1e-11, max_nfev=int(cfg.get("max_evaluations", 4000)))
    scale, rotation, offset = unpack(opt.x)
    screen_rows, world_rows = [], []
    screen_errors, world_errors = [], []
    for name, local, target, weight in screen:
        wp = transform_point(local, anchor_local, anchor_world, scale, rotation, offset)
        pp = project(wp.reshape(1, 3), camera or {}, int(cfg.get("image_width", 256)), int(cfg.get("image_height", 256)))[0]
        err = float(np.linalg.norm(pp - target)); screen_errors.append(err)
        screen_rows.append({"id": name, "target_px": target.tolist(), "fitted_px": [round(float(v), 5) for v in pp], "error_px": round(err, 6), "weight": weight})
    for name, local, target, weight in world:
        wp = transform_point(local, anchor_local, anchor_world, scale, rotation, offset)
        err = float(np.linalg.norm(wp - target)); world_errors.append(err)
        world_rows.append({"id": name, "target_world": target.tolist(), "fitted_world": [round(float(v), 5) for v in wp], "error": round(err, 6), "weight": weight})
    screen_rmse = math.sqrt(float(np.mean(np.square(screen_errors)))) if screen_errors else 0.0
    world_rmse = math.sqrt(float(np.mean(np.square(world_errors)))) if world_errors else 0.0
    passed = (not screen_errors or screen_rmse <= args.min_screen_rmse) and (not world_errors or world_rmse <= args.min_world_rmse)

    result = {
        "schema_version": 1,
        "result": "pass" if passed else "fail",
        "asset": spec.get("id"),
        "asset_class": spec.get("asset_class"),
        "context": cfg.get("context", "attachment"),
        "anchor": {"asset_point": anchor_name, "asset_local": anchor_local.tolist(), "world": anchor_world.tolist(), "player_oracle": oracle_meta},
        "transform": {"scale": round(scale, 8), "rotation": [round(float(v), 8) for v in rotation], "translation": [round(float(v), 8) for v in offset]},
        "screen_rmse_px": round(screen_rmse, 6),
        "world_rmse": round(world_rmse, 6),
        "screen_constraints": screen_rows,
        "world_constraints": world_rows,
        "optimizer": {"success": bool(opt.success), "status": int(opt.status), "message": str(opt.message), "evaluations": int(opt.nfev), "cost": float(opt.cost)},
        "runtime_contract": {
            "anchor_world": [round(float(v), 8) for v in anchor_world],
            "pivot_local": [round(float(v), 8) for v in anchor_local],
            "scale": round(scale, 8),
            "rotation_degrees_xyz": [round(float(v), 8) for v in rotation],
            "offset_model_units": [round(float(v), 8) for v in offset],
            "note": "Map this similarity transform explicitly into the target renderer/display convention; do not assume Java item-display axis/order parity without native validation."
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result["runtime_contract"], indent=2) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "screen_rmse_px": result["screen_rmse_px"], "world_rmse": result["world_rmse"], "transform": result["transform"], "report": str(args.report)}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
