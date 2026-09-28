#!/usr/bin/env python3
"""Project fitted reference views back into a creature-spec box-UV texture atlas.

Run only after geometry/camera alignment is credible. The baker recovers *visible* texels
from supplied reference pixels and writes a coverage mask. Unobserved texels stay
transparent (or come from --base); they are never hallucinated.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from reference_cuboid_fit import rot_xyz, world_cube_points

# Outward winding for face visibility / depth ordering.
FACE_OUT = {
    "left": [0, 1, 3, 2],
    "right": [4, 6, 7, 5],
    "down": [0, 4, 5, 1],
    "up": [2, 3, 7, 6],
    "front": [0, 2, 6, 4],
    "back": [1, 5, 7, 3],
}
# Vertex order mapped to UV rectangle TL,TR,BR,BL.
FACE_UV = {
    "front": [2, 6, 4, 0],
    "back": [7, 3, 1, 5],
    "left": [3, 2, 0, 1],
    "right": [6, 7, 5, 4],
    "up": [3, 7, 6, 2],
    "down": [0, 4, 5, 1],
}


def box_faces(uv: list[float], size: list[float]) -> dict[str, tuple[int, int, int, int]]:
    u, v = (int(round(x)) for x in uv); x, y, z = (max(1, int(round(abs(float(q))))) for q in size)
    return {
        "up": (u + z, v, x, z), "down": (u + z + x, v, x, z),
        "left": (u, v + z, z, y), "front": (u + z, v + z, x, y),
        "right": (u + z + x, v + z, z, y), "back": (u + 2 * z + x, v + z, x, y),
    }


def view_space(points: np.ndarray, camera: dict[str, Any]) -> np.ndarray:
    target = np.asarray(camera.get("target", [0, 0, 0]), dtype=np.float64)
    r = rot_xyz([-float(camera.get("pitch", 0.0)), -float(camera.get("yaw", 0.0)), -float(camera.get("roll", 0.0))])
    return (points - target) @ r.T


def project_view(p: np.ndarray, camera: dict[str, Any], width: int, height: int) -> np.ndarray:
    ox, oy = float(camera.get("offset_x", 0.0)), float(camera.get("offset_y", 0.0))
    if str(camera.get("projection", "orthographic")).lower() == "perspective":
        dist = float(camera.get("distance", 64.0)); fov = math.radians(float(camera.get("fov", 35.0)))
        z = np.maximum(1e-6, dist - p[:, 2]); focal = 0.5 * width / math.tan(max(1e-4, fov / 2.0))
        x = p[:, 0] * focal / z + width / 2.0 + ox; y = -p[:, 1] * focal / z + height / 2.0 + oy
    else:
        scale = max(1e-6, float(camera.get("ortho_scale", 32.0)))
        x = p[:, 0] * (width / scale) + width / 2.0 + ox; y = -p[:, 1] * (width / scale) + height / 2.0 + oy
    return np.stack([x, y], axis=1)


def face_records(spec: dict[str, Any], camera: dict[str, Any], width: int, height: int) -> list[dict]:
    recs = []
    for cube in spec.get("cubes", []):
        if not isinstance(cube, dict) or not isinstance(cube.get("uv"), list): continue
        pts_world = world_cube_points(spec, cube); pts_view = view_space(pts_world, camera); pts_screen = project_view(pts_view, camera, width, height)
        rects = box_faces(cube["uv"], cube["size"])
        for face, out_idx in FACE_OUT.items():
            q = pts_view[out_idx]
            normal = np.cross(q[1] - q[0], q[2] - q[0])
            if normal[2] <= 1e-7: continue
            ui = FACE_UV[face]; screen = pts_screen[ui].astype(np.float32)
            if abs(cv2.contourArea(screen)) < 0.5: continue
            u, v, fw, fh = rects[face]
            uvq = np.array([[u, v], [u + fw - 1, v], [u + fw - 1, v + fh - 1], [u, v + fh - 1]], dtype=np.float32)
            recs.append({"cube": str(cube.get("id")), "face": face, "screen": screen, "uv": uvq, "depth": float(np.mean(q[:, 2]))})
    return recs


def visible_id_map(records: list[dict], width: int, height: int) -> np.ndarray:
    ids = np.full((height, width), -1, dtype=np.int32)
    # In this camera convention larger view-space z is nearer the viewer.
    for idx in sorted(range(len(records)), key=lambda i: records[i]["depth"]):
        poly = np.round(records[idx]["screen"]).astype(np.int32)
        cv2.fillConvexPoly(ids, poly, idx)
    return ids


def render_textured(spec: dict[str, Any], texture: np.ndarray, camera: dict[str, Any], size: tuple[int, int]) -> np.ndarray:
    width, height = size; recs = face_records(spec, camera, width, height); ids = visible_id_map(recs, width, height)
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    tex_h, tex_w = texture.shape[:2]
    for idx, rec in enumerate(recs):
        src = rec["uv"].copy(); src[:, 0] = np.clip(src[:, 0], 0, tex_w - 1); src[:, 1] = np.clip(src[:, 1], 0, tex_h - 1)
        dst = rec["screen"].astype(np.float32)
        hmat = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(texture, hmat, (width, height), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
        m = ids == idx
        if warped.shape[2] == 3:
            canvas[m, :3] = warped[m]; canvas[m, 3] = 255
        else:
            canvas[m] = warped[m]
            canvas[m, 3] = np.maximum(canvas[m, 3], 255)
    return canvas


def bake(spec: dict[str, Any], observations: list[dict], root: Path, base: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    tex_w = int(spec.get("texture", {}).get("width", 64)); tex_h = int(spec.get("texture", {}).get("height", 64))
    sums = np.zeros((tex_h, tex_w, 3), dtype=np.float64); sumsq = np.zeros((tex_h, tex_w, 3), dtype=np.float64); weights = np.zeros((tex_h, tex_w), dtype=np.float64); samples = np.zeros((tex_h, tex_w), dtype=np.int32)
    per_obs = []
    for oi, obs in enumerate(observations):
        ip = Path(str(obs["image"])); ip = ip if ip.is_absolute() else root / ip
        rgba = np.asarray(Image.open(ip).convert("RGBA"), dtype=np.uint8); h, w = rgba.shape[:2]
        camera = obs.get("camera", {}); recs = face_records(spec, camera, w, h); ids = visible_id_map(recs, w, h); ow = float(obs.get("weight", 1.0)); used = 0
        for idx, rec in enumerate(recs):
            src = rec["screen"].astype(np.float32); dst = rec["uv"].astype(np.float32)
            hmat = cv2.getPerspectiveTransform(src, dst)
            face_mask = (ids == idx).astype(np.uint8) * 255
            warped_rgb = cv2.warpPerspective(rgba[:, :, :3], hmat, (tex_w, tex_h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
            warped_m = cv2.warpPerspective(face_mask, hmat, (tex_w, tex_h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT) > 127
            if np.any(warped_m):
                vals = warped_rgb[warped_m].astype(np.float64)
                sums[warped_m] += vals * ow; sumsq[warped_m] += (vals ** 2) * ow; weights[warped_m] += ow; samples[warped_m] += 1; used += int(warped_m.sum())
        per_obs.append({"image": str(ip), "visible_faces": len(recs), "texel_samples": used})
    out = np.zeros((tex_h, tex_w, 4), dtype=np.uint8)
    covered = weights > 0
    if np.any(covered): out[covered, :3] = np.clip(sums[covered] / weights[covered, None], 0, 255).astype(np.uint8); out[covered, 3] = 255
    if base is not None:
        if base.shape[:2] != (tex_h, tex_w): base = cv2.resize(base, (tex_w, tex_h), interpolation=cv2.INTER_NEAREST)
        missing = ~covered; out[missing] = base[missing]
    coverage = (covered.astype(np.uint8) * 255)
    variance = np.zeros((tex_h, tex_w, 3), dtype=np.float64)
    if np.any(covered):
        mean = np.zeros_like(sums); mean[covered] = sums[covered] / weights[covered, None]
        variance[covered] = np.maximum(0.0, sumsq[covered] / weights[covered, None] - mean[covered] ** 2)
    color_std = np.sqrt(np.mean(variance, axis=2))
    # Confidence rewards repeated observations but penalizes cross-view color disagreement.
    repeat = np.minimum(1.0, samples.astype(np.float64) / 2.0)
    conf = np.where(covered, repeat * (1.0 / (1.0 + color_std / 16.0)), 0.0)
    confidence = np.clip(np.rint(conf * 255.0), 0, 255).astype(np.uint8)
    stats = color_std[covered]
    return out, coverage, confidence, {"coverage_fraction": float(covered.mean()), "multi_observed_fraction": float(np.mean(samples[covered] >= 2)) if np.any(covered) else 0.0, "mean_cross_view_color_std": float(np.mean(stats)) if len(stats) else 0.0, "p95_cross_view_color_std": float(np.percentile(stats, 95)) if len(stats) else 0.0, "observations": per_obs}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("spec", type=Path); ap.add_argument("observations", type=Path); ap.add_argument("--output", type=Path, required=True); ap.add_argument("--coverage", type=Path, required=True); ap.add_argument("--confidence", type=Path); ap.add_argument("--base", type=Path); ap.add_argument("--report", type=Path)
    args = ap.parse_args(); spec = json.loads(args.spec.read_text(encoding="utf-8")); cfg = json.loads(args.observations.read_text(encoding="utf-8")); obs = cfg.get("observations", [])
    if not isinstance(obs, list) or not obs: print("observations must be non-empty"); return 2
    base = np.asarray(Image.open(args.base).convert("RGBA"), dtype=np.uint8) if args.base else None
    out, cov, conf, report = bake(spec, obs, args.observations.parent, base)
    args.output.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(out, "RGBA").save(args.output); Image.fromarray(cov, "L").save(args.coverage)
    if args.confidence: Image.fromarray(conf, "L").save(args.confidence)
    report.update({"result": "pass" if report["coverage_fraction"] > 0 else "fail", "texture": str(args.output), "coverage": str(args.coverage), "confidence": str(args.confidence) if args.confidence else None, "note": "Only observed texels are recovered. Low confidence or high cross-view color variance usually means lighting/occlusion/calibration disagreement; verify before calling albedo exact."})
    if args.report: args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2)); return 0 if report["result"] == "pass" else 2


if __name__ == "__main__": raise SystemExit(main())
