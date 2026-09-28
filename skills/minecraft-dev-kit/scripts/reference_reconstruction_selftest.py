#!/usr/bin/env python3
"""Regression-test inverse reference reconstruction end to end.

Exercises: multi-view geometry fitting, camera fitting, media ingest/temporal probe,
animated parity positive/negative gates, GIF-to-bone pose fitting, and visible box-UV
texture inversion. Synthetic fixtures make the expected answer knowable; real projects
still require visual + native Minecraft proof.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from reference_cuboid_fit import render_mask
from reference_texture_bake import render_textured


def run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(cmd, 124, exc.stdout or "", (exc.stderr or "") + "\nTIMEOUT\n")


def must(cp: subprocess.CompletedProcess[str], label: str) -> None:
    if cp.returncode != 0:
        raise RuntimeError(f"{label} failed rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}")


def base_spec() -> dict:
    return {
        "schema_version": 1,
        "id": "reference-selftest",
        "texture": {"width": 64, "height": 64},
        "visible_bounds": {"width": 2.0, "height": 2.5, "offset": [0, 1, 0]},
        "bones": [
            {"id": "root", "pivot": [0, 0, 0]},
            {"id": "body", "parent": "root", "pivot": [0, 10, 0]},
            {"id": "head", "parent": "body", "pivot": [0, 18, 0]},
        ],
        "cubes": [
            {"id": "body", "bone": "body", "origin": [-4, 4, -3], "size": [8, 12, 6], "uv": [0, 0]},
            {"id": "head", "bone": "head", "origin": [-3, 16, -3], "size": [6, 6, 6], "uv": [28, 0]},
            # Intentional asymmetric/depth cues keep camera inverse-fitting observable.
            {"id": "snout", "bone": "head", "origin": [-2, 17, -6], "size": [4, 3, 3], "uv": [0, 26]},
            {"id": "crest", "bone": "head", "origin": [2, 20, -1], "size": [2, 5, 2], "uv": [20, 26]},
        ],
        "animations": [],
    }


def pose_spec() -> dict:
    return {
        "schema_version": 1,
        "id": "pose-selftest",
        "texture": {"width": 32, "height": 32},
        "bones": [
            {"id": "root", "pivot": [0, 0, 0]},
            {"id": "body", "parent": "root", "pivot": [0, 10, 0]},
            {"id": "arm", "parent": "body", "pivot": [4, 14, 0], "rotation": [0, 0, 0]},
        ],
        "cubes": [
            {"id": "body", "bone": "body", "origin": [-4, 4, -3], "size": [8, 12, 6], "uv": [0, 0]},
            {"id": "arm", "bone": "arm", "origin": [4, 7, -2], "size": [3, 8, 4], "uv": [0, 18]},
        ],
        "animations": [],
    }


def save_mask_gif(path: Path, masks: list[np.ndarray], duration: int = 70) -> None:
    frames = []
    for mask in masks:
        rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        rgba[:, :, :3] = np.array([64, 110, 155], dtype=np.uint8)
        rgba[:, :, 3] = mask
        frames.append(Image.fromarray(rgba, "RGBA"))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=2)


def texture_roundtrip(root: Path, tools: Path) -> tuple[float, float]:
    spec = {
        "schema_version": 1, "id": "texture-selftest", "texture": {"width": 32, "height": 32},
        "bones": [{"id": "root", "pivot": [0, 0, 0]}],
        "cubes": [{"id": "cube", "bone": "root", "origin": [-4, -4, -4], "size": [8, 8, 8], "uv": [0, 0]}],
        "animations": [],
    }
    specp = root / "texture-spec.json"; specp.write_text(json.dumps(spec, indent=2) + "\n")
    yy, xx = np.indices((32, 32)); truth = np.zeros((32, 32, 4), dtype=np.uint8)
    truth[:, :, 0] = (xx * 7 + yy * 3) % 256; truth[:, :, 1] = (xx * 5 + yy * 11) % 256; truth[:, :, 2] = (xx * 13 + yy * 2) % 256; truth[:, :, 3] = 255
    Image.fromarray(truth, "RGBA").save(root / "truth-texture.png")
    obsdir = root / "texture-obs"; obsdir.mkdir()
    cams = [
        {"id": "front", "projection": "orthographic", "yaw": 0, "pitch": 0, "ortho_scale": 18, "target": [0, 0, 0]},
        {"id": "right", "projection": "orthographic", "yaw": 90, "pitch": 0, "ortho_scale": 18, "target": [0, 0, 0]},
        {"id": "back", "projection": "orthographic", "yaw": 180, "pitch": 0, "ortho_scale": 18, "target": [0, 0, 0]},
        {"id": "left", "projection": "orthographic", "yaw": 270, "pitch": 0, "ortho_scale": 18, "target": [0, 0, 0]},
        {"id": "top", "projection": "orthographic", "yaw": 0, "pitch": 90, "ortho_scale": 18, "target": [0, 0, 0]},
        {"id": "bottom", "projection": "orthographic", "yaw": 0, "pitch": -90, "ortho_scale": 18, "target": [0, 0, 0]},
    ]
    observations = []
    for cam in cams:
        rgba = render_textured(spec, truth, cam, (96, 96)); p = obsdir / f"{cam['id']}.png"; Image.fromarray(rgba, "RGBA").save(p)
        observations.append({"image": str(p.relative_to(root)), "camera": cam})
    obsp = root / "texture-observations.json"; obsp.write_text(json.dumps({"observations": observations}, indent=2) + "\n")
    cp = run([sys.executable, str(tools / "reference_texture_bake.py"), str(specp), str(obsp), "--output", str(root / "recovered-texture.png"), "--coverage", str(root / "texture-coverage.png"), "--confidence", str(root / "texture-confidence.png"), "--report", str(root / "texture-report.json")])
    must(cp, "texture bake")
    recovered = np.asarray(Image.open(root / "recovered-texture.png").convert("RGBA"), dtype=np.int16); cov = np.asarray(Image.open(root / "texture-coverage.png").convert("L")) > 0
    mae = float(np.abs(recovered[:, :, :3] - truth[:, :, :3])[cov].mean()) if np.any(cov) else 999.0
    report = json.loads((root / "texture-report.json").read_text())
    if mae > 0.01:
        raise RuntimeError(f"texture inverse roundtrip MAE {mae}")
    return float(report["coverage_fraction"]), mae


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--keep", type=Path); args = ap.parse_args()
    root = Path(tempfile.mkdtemp(prefix="reference-recon-selftest-")); tools = Path(__file__).resolve().parent
    try:
        refs = root / "refs"; refs.mkdir(); truth = base_spec()
        cameras = [
            {"id": "front", "projection": "orthographic", "yaw": 0, "pitch": 0, "ortho_scale": 32, "target": [0, 12, 0]},
            {"id": "side", "projection": "orthographic", "yaw": 90, "pitch": 0, "ortho_scale": 32, "target": [0, 12, 0]},
        ]
        for cam in cameras: cv2.imwrite(str(refs / f"{cam['id']}.png"), render_mask(truth, cam, (160, 160)))

        start = copy.deepcopy(truth); start["cubes"][0]["size"][0] = 5.5; start["cubes"][0]["size"][2] = 8.5; start["cubes"][1]["size"][0] = 8.0; start["cubes"][1]["size"][1] = 4.0
        specp = root / "start.creature.json"; specp.write_text(json.dumps(start, indent=2) + "\n")
        cfg = {"references": [{"id": "front", "mask": "refs/front.png", "camera": cameras[0]}, {"id": "side", "mask": "refs/side.png", "camera": cameras[1]}], "parameters": [
            {"target": "cube/body/size/0", "min": 5, "max": 11}, {"target": "cube/body/size/2", "min": 4, "max": 10}, {"target": "cube/head/size/0", "min": 4, "max": 9}, {"target": "cube/head/size/1", "min": 4, "max": 9}]}
        cfgp = root / "fit.json"; cfgp.write_text(json.dumps(cfg, indent=2) + "\n")
        fitp = run([sys.executable, str(tools / "reference_cuboid_fit.py"), str(specp), str(cfgp), "--out-spec", str(root / "fitted.json"), "--report", str(root / "fit-report.json"), "--render-dir", str(root / "fitted-renders"), "--maxiter", "45", "--popsize", "8", "--min-iou", "0.96"])
        must(fitp, "geometry fit"); fit_report = json.loads((root / "fit-report.json").read_text())

        # Camera-only inverse fixture. Geometry is fixed and asymmetric, so camera parameters are observable.
        cam_truth = {"id": "camfit", "projection": "orthographic", "yaw": 17, "pitch": -6, "ortho_scale": 30, "target": [0, 12, 0], "offset_x": 5, "offset_y": -4}
        cv2.imwrite(str(refs / "camera.png"), render_mask(truth, cam_truth, (160, 160)))
        cam_start = {**cam_truth, "yaw": -3, "pitch": 2, "ortho_scale": 36, "offset_x": 0, "offset_y": 0}
        cam_cfg = {"references": [{"id": "camera", "mask": "refs/camera.png", "camera": cam_start}], "parameters": [
            {"target": "camera/camfit/yaw", "min": -15, "max": 30}, {"target": "camera/camfit/pitch", "min": -15, "max": 12},
            {"target": "camera/camfit/ortho_scale", "min": 25, "max": 40}, {"target": "camera/camfit/offset_x", "min": -12, "max": 12}, {"target": "camera/camfit/offset_y", "min": -12, "max": 12}]}
        camcfgp = root / "camera-fit.json"; camcfgp.write_text(json.dumps(cam_cfg, indent=2) + "\n")
        camfit = run([sys.executable, str(tools / "reference_cuboid_fit.py"), str(root / "fitted.json"), str(camcfgp), "--out-spec", str(root / "camera-fitted-spec.json"), "--report", str(root / "camera-fit-report.json"), "--render-dir", str(root / "camera-fit-render"), "--maxiter", "45", "--popsize", "8", "--min-iou", "0.97"])
        must(camfit, "camera fit"); cam_report = json.loads((root / "camera-fit-report.json").read_text())

        # General animated reference + temporal diagnostic + parity positive/negative.
        gif = root / "motion.gif"; frames = []
        for i in list(range(8)) + list(range(6, -1, -1)):
            im = Image.new("RGBA", (96, 96), (255, 255, 255, 255)); d = ImageDraw.Draw(im); x = 18 + i * 5; d.rectangle((x, 34, x + 20, 54), fill=(42, 90, 130, 255)); frames.append(im)
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=60, loop=0, disposal=2)
        ingest_dir = root / "ingest"; ing = run([sys.executable, str(tools / "reference_media_ingest.py"), str(gif), "--out", str(ingest_dir)]); must(ing, "media ingest")
        item_manifest = next(ingest_dir.glob("*/manifest.json")); seq = run([sys.executable, str(tools / "reference_sequence_probe.py"), str(item_manifest), "--output", str(root / "sequence.json")]); must(seq, "sequence probe")
        good = run([sys.executable, str(tools / "reference_parity_gate.py"), str(gif), str(gif), "--min-score", "0.99", "--min-silhouette", "0.99"]); must(good, "positive parity")
        badgif = root / "bad.gif"; badframes = []
        for _ in frames:
            im = Image.new("RGBA", (96, 96), (255, 255, 255, 255)); d = ImageDraw.Draw(im); d.rectangle((8, 8, 38, 38), fill=(180, 20, 20, 255)); badframes.append(im)
        badframes[0].save(badgif, save_all=True, append_images=badframes[1:], duration=60, loop=0, disposal=2)
        bad = run([sys.executable, str(tools / "reference_parity_gate.py"), str(gif), str(badgif), "--min-score", "0.90", "--min-silhouette", "0.90"])
        if bad.returncode == 0: raise RuntimeError("negative parity fixture false-passed")

        # GIF -> bone-rotation sequence inverse fit.
        pspec = pose_spec(); psp = root / "pose-spec.json"; psp.write_text(json.dumps(pspec, indent=2) + "\n")
        pcamera = {"id": "ref", "projection": "orthographic", "yaw": 0, "pitch": 0, "ortho_scale": 32, "target": [0, 10, 0]}
        rotations = [-45, -25, 0, 30, 55, 30, 0, -25, -45]; pmasks = []
        for angle in rotations:
            ss = copy.deepcopy(pspec); ss["bones"][2]["rotation"][2] = angle; pmasks.append(render_mask(ss, pcamera, (128, 128)))
        pgif = root / "pose.gif"; save_mask_gif(pgif, pmasks, 70)
        pingest = root / "pose-ingest"; cp = run([sys.executable, str(tools / "reference_media_ingest.py"), str(pgif), "--out", str(pingest)]); must(cp, "pose media ingest")
        pmanifest = next(pingest.glob("*/manifest.json")); posecfg = {"camera": pcamera, "animation_name": "arm_swing", "selected_frames": list(range(9)), "parameters": [{"target": "bone/arm/rotation/2", "min": -70, "max": 70}], "temporal_regularization": 0.003, "min_frame_iou": 0.94, "loop": True}
        posecfgp = root / "pose-fit-config.json"; posecfgp.write_text(json.dumps(posecfg, indent=2) + "\n")
        posecp = run([sys.executable, str(tools / "reference_pose_sequence_fit.py"), str(psp), str(pmanifest), str(posecfgp), "--output", str(root / "pose-animation.json"), "--report", str(root / "pose-report.json"), "--render-dir", str(root / "pose-renders"), "--maxiter", "50", "--popsize", "8"], timeout=240); must(posecp, "pose inverse fit")
        pose_report = json.loads((root / "pose-report.json").read_text())

        texture_coverage, texture_mae = texture_roundtrip(root, tools)
        sequence = json.loads((root / "sequence.json").read_text())
        result = {"result": "pass", "geometry_mean_iou": fit_report["mean_iou"], "geometry_evaluations": fit_report["optimizer"]["evaluations"], "camera_mean_iou": cam_report["mean_iou"], "pose_mean_iou": pose_report["mean_iou"], "texture_atlas_coverage_fraction": round(texture_coverage, 6), "texture_visible_mae": round(texture_mae, 6), "sequence_frames": sequence["frames"], "selected_frames": sequence["selected_frames"], "positive_parity_rc": good.returncode, "negative_parity_rc": bad.returncode}
        print(json.dumps(result, indent=2))
        if args.keep:
            if args.keep.exists(): shutil.rmtree(args.keep)
            shutil.copytree(root, args.keep)
        return 0
    except Exception as exc:
        print(f"REFERENCE RECONSTRUCTION SELFTEST FAILED: {exc}", file=sys.stderr)
        if args.keep:
            if args.keep.exists(): shutil.rmtree(args.keep)
            shutil.copytree(root, args.keep)
        return 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
