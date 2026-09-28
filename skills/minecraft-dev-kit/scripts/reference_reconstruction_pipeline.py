#!/usr/bin/env python3
"""Run a rights-gated, evidence-preserving image/GIF -> Minecraft reconstruction workflow.

The contract is intentionally explicit. It can stage media, probe motion, inverse-fit cuboid
geometry/cameras, inverse-fit bone rotations from GIF frames, back-project visible texels,
and run parity gates. It never claims unseen geometry or unobserved texels were recovered.

Example contract keys:
{
  "schema_version": 1,
  "project_id": "authorized-creature",
  "rights": {"authorized": true, "basis": "owned or permission"},
  "inputs": [{"path":"refs/front.png","role":"front"}, "refs/attack.gif"],
  "geometry_fit": {
    "spec":"start.creature.json",
    "references":[{"source":"refs/front.png","frame":0,"camera":{...}}],
    "parameters":[{"target":"cube/body/size/0","min":4,"max":12}],
    "min_iou":0.94
  },
  "pose_fits":[{"source":"refs/attack.gif","config":"attack-fit.json","spec":"$geometry"}],
  "texture_bake": {
    "spec":"$geometry",
    "observations":[{"source":"refs/front.png","frame":0,"camera":{...}}]
  },
  "parity":[{"reference":"refs/attack.gif","candidate":"renders/attack.gif","min_score":0.92,"min_silhouette":0.94}]
}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(root: Path, value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (root / p).resolve()


def run_step(name: str, cmd: list[str], steps: list[dict], timeout: int = 900, required: bool = True) -> bool:
    start = time.monotonic()
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        rc, stdout, stderr = cp.returncode, cp.stdout, cp.stderr
    except subprocess.TimeoutExpired as exc:
        rc, stdout, stderr = 124, exc.stdout or "", (exc.stderr or "") + "\nTIMEOUT\n"
    elapsed = round(time.monotonic() - start, 3)
    steps.append({"name": name, "command": cmd, "returncode": rc, "elapsed_seconds": elapsed, "stdout_tail": stdout[-4000:], "stderr_tail": stderr[-4000:], "required": required})
    if rc != 0 and required:
        raise RuntimeError(f"{name} failed rc={rc}: {(stderr or stdout)[-1200:]}")
    return rc == 0


def input_records(contract: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    out = []
    for raw in contract.get("inputs", []):
        if isinstance(raw, str):
            p, role = resolve(root, raw), None
        elif isinstance(raw, dict) and raw.get("path"):
            p, role = resolve(root, str(raw["path"])), raw.get("role")
        else:
            raise ValueError(f"invalid input entry: {raw!r}")
        if not p.exists():
            raise FileNotFoundError(p)
        out.append({"path": p, "role": role})
    if not out:
        raise ValueError("contract.inputs must contain at least one image/GIF reference")
    return out


def load_master(path: Path) -> tuple[dict, dict[str, dict]]:
    master = json.loads(path.read_text(encoding="utf-8")); root = path.parent; mapping = {}
    for item in master.get("items", []):
        src = Path(str(item.get("source", ""))).resolve()
        rec = dict(item); rec["item_manifest_abs"] = str((root / str(item["manifest"])).resolve()); mapping[str(src)] = rec
    return master, mapping


def source_item(mapping: dict[str, dict], root: Path, source: str) -> dict:
    p = resolve(root, source).resolve(); key = str(p)
    if key not in mapping:
        raise KeyError(f"source {p} was not staged; include it in contract.inputs")
    return mapping[key]


def staged_frame(item: dict, frame: int, field: str, media_root: Path) -> Path:
    frames = item.get("frames", [])
    if frame < 0 or frame >= len(frames):
        raise IndexError(f"frame {frame} outside 0..{len(frames)-1} for {item.get('source')}")
    return (media_root / str(frames[frame][field])).resolve()


def write_readme(out: Path, receipt: dict) -> None:
    lines = [
        "# Reference Reconstruction Receipt", "",
        f"- Result: **{receipt['result'].upper()}**",
        f"- Project: `{receipt.get('project_id','')}`",
        f"- Contract SHA-256: `{receipt['contract_sha256']}`",
        f"- Required steps passed: **{sum(1 for x in receipt['steps'] if x['required'] and x['returncode']==0)} / {sum(1 for x in receipt['steps'] if x['required'])}**",
        "",
        "## Evidence boundary", "",
        "This workflow measures observable reference agreement. Hidden/occluded geometry and unobserved texture texels remain inferred until additional evidence observes them. Native Minecraft rendering/gameplay proof is still required before release.", "",
        "## Steps", "",
    ]
    for s in receipt["steps"]:
        status = "PASS" if s["returncode"] == 0 else "FAIL"
        lines.append(f"- **{status}** `{s['name']}` — rc={s['returncode']}, {s['elapsed_seconds']}s")
    lines += ["", "## Outputs", ""]
    for r in receipt.get("outputs", []): lines.append(f"- `{r['path']}` — `{r['sha256']}`")
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("contract", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=900, help="per child step; capped at 900 seconds")
    args = ap.parse_args(); timeout = max(30, min(900, int(args.timeout)))
    contract_path = args.contract.resolve(); root = contract_path.parent
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    rights = contract.get("rights", {})
    if not isinstance(rights, dict) or rights.get("authorized") is not True:
        print("REFUSED: contract.rights.authorized must be true for exact reconstruction work", file=sys.stderr); return 3
    if int(contract.get("schema_version", 0)) != 1:
        print("Unsupported contract schema_version", file=sys.stderr); return 2
    try:
        inputs = input_records(contract, root)
    except Exception as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr); return 2

    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True); tools = Path(__file__).resolve().parent; steps: list[dict] = []
    shutil.copy2(contract_path, out / "RECONSTRUCTION-CONTRACT.json")
    receipt: dict[str, Any] = {"schema_version": 1, "project_id": str(contract.get("project_id", contract_path.stem)), "rights": rights, "contract_sha256": sha256(contract_path), "steps": steps, "outputs": [], "result": "fail"}
    try:
        # 01 media
        media_dir = out / "01-media"; media_cfg = contract.get("media", {}) if isinstance(contract.get("media"), dict) else {}
        cmd = [sys.executable, str(tools / "reference_media_ingest.py"), *[str(x["path"]) for x in inputs], "--out", str(media_dir), "--palette", str(int(media_cfg.get("palette", 12))), "--alpha-threshold", str(int(media_cfg.get("alpha_threshold", 8)))]
        if int(media_cfg.get("max_frames", 0)) > 0: cmd += ["--max-frames", str(int(media_cfg["max_frames"]))]
        run_step("media-ingest", cmd, steps, timeout)
        master_path = media_dir / "REFERENCE-MEDIA-MANIFEST.json"; master, mapping = load_master(master_path)

        # 02 temporal probes for all animations unless disabled.
        if contract.get("sequence_probe", True):
            seqdir = out / "02-sequence"; seqdir.mkdir(exist_ok=True)
            for idx, item in enumerate(master.get("items", [])):
                if int(item.get("frame_count_staged", 1)) <= 1: continue
                im = (media_dir / str(item["manifest"])).resolve(); op = seqdir / f"{idx:03d}-sequence.json"
                run_step(f"sequence-probe:{Path(str(item['source'])).name}", [sys.executable, str(tools / "reference_sequence_probe.py"), str(im), "--output", str(op), "--count", str(int(contract.get("sequence_frame_count", 12)))], steps, timeout)

        # 02b flat sprite/icon extraction for authorized sheets (skills, UI, item icon families).
        sprites = contract.get("sprite_extracts", [])
        if isinstance(sprites, list):
            for idx, sp in enumerate(sprites):
                if not isinstance(sp, dict): raise ValueError("sprite_extracts entries must be objects")
                source = resolve(root, str(sp["source"])); sdir = out / "02b-sprites" / f"{idx:03d}-{sp.get('name','sprites')}"
                cmd = [sys.executable, str(tools / "reference_sprite_extract.py"), str(source), "--out", str(sdir), "--mode", str(sp.get("mode", "auto")), "--target-size", str(int(sp.get("target_size", 0))), "--padding", str(int(sp.get("padding", 0))), "--min-area", str(int(sp.get("min_area", 16))), "--prefix", str(sp.get("prefix", "icon"))]
                if int(sp.get("rows", 0)) > 0: cmd += ["--rows", str(int(sp["rows"]))]
                if int(sp.get("cols", 0)) > 0: cmd += ["--cols", str(int(sp["cols"]))]
                run_step(f"sprite-extract:{sp.get('name',idx)}", cmd, steps, timeout, bool(sp.get("required", True)))

        current_spec: Path | None = None
        # 03a semantic zero-start scaffold for single/few-view weapons, armor, cosmetics or props.
        sc = contract.get("asset_scaffold")
        if isinstance(sc, dict):
            sdir = out / "03a-asset-scaffold"; sdir.mkdir(exist_ok=True); current_spec = sdir / "scaffold.creature.json"
            scmd = [sys.executable, str(tools / "reference_asset_scaffold.py"), "--id", str(sc.get("id", receipt["project_id"] + "-scaffold")), "--class", str(sc["class"]), "--out", str(current_spec), "--texture", str(int(sc.get("texture", 64))), "--uv-padding", str(int(sc.get("uv_padding", 1))), "--scale", str(float(sc.get("scale", 1.0)))]
            run_step("asset-scaffold", scmd, steps, timeout)

        # 03a turntable GIF -> inferred camera yaw set -> visual hull.
        tt = contract.get("turntable_hull")
        if isinstance(tt, dict):
            if current_spec is not None: raise ValueError("use asset_scaffold or turntable_hull as the zero-start source, not both")
            tdir = out / "03a-turntable-hull"; tdir.mkdir(exist_ok=True)
            item = source_item(mapping, root, str(tt["source"])); item_manifest = Path(item["item_manifest_abs"])
            bounds = tt.get("bounds") if isinstance(tt.get("bounds"), dict) else {}
            bmin, bmax = bounds.get("min"), bounds.get("max")
            if not (isinstance(bmin, list) and len(bmin) == 3 and isinstance(bmax, list) and len(bmax) == 3): raise ValueError("turntable_hull.bounds min/max are required")
            calibration = tdir / "turntable-calibration.json"
            projection = str(tt.get("projection", "orthographic"))
            ccmd = [sys.executable, str(tools / "reference_turntable_calibrate.py"), str(item_manifest), "--output", str(calibration), "--bounds-min", *[str(x) for x in bmin], "--bounds-max", *[str(x) for x in bmax], "--count", str(int(tt.get("count", 8))), "--start-yaw", str(float(tt.get("start_yaw", 0.0))), "--direction", str(tt.get("direction", "cw")), "--pitch", str(float(tt.get("pitch", 0.0))), "--roll", str(float(tt.get("roll", 0.0))), "--projection", projection]
            if float(tt.get("ortho_scale", 0.0)) > 0: ccmd += ["--ortho-scale", str(float(tt["ortho_scale"]))]
            if projection == "perspective":
                ccmd += ["--fov", str(float(tt.get("fov", 35.0)))]
                if float(tt.get("distance", 0.0)) > 0: ccmd += ["--distance", str(float(tt["distance"]))]
            if float(tt.get("subject_height", 0.0)) > 0: ccmd += ["--subject-height", str(float(tt["subject_height"]))]
            if isinstance(tt.get("target"), list) and len(tt["target"]) == 3: ccmd += ["--target", *[str(x) for x in tt["target"]]]
            run_step("turntable-calibrate", ccmd, steps, timeout)
            cal = json.loads(calibration.read_text(encoding="utf-8")); hp = tdir / "hull-manifest.json"
            hcfg = {"id": str(tt.get("id", receipt["project_id"] + "-turntable-hull")), "bounds": cal["bounds"], "voxel": float(tt.get("voxel", 1.0)), "references": [{"id": r["id"], "mask": r["mask"], "camera": r["camera"]} for r in cal.get("references", [])], "texture": int(tt.get("texture", 64)), "uv_padding": int(tt.get("uv_padding", 1)), "max_voxels": int(tt.get("max_voxels", 2_000_000))}
            hp.write_text(json.dumps(hcfg, indent=2) + "\n", encoding="utf-8")
            current_spec = tdir / "hull.creature.json"
            run_step("turntable-visual-hull", [sys.executable, str(tools / "reference_visual_hull.py"), str(hp), "--output", str(current_spec), "--report", str(tdir / "report.json"), "--render-dir", str(tdir / "renders"), "--min-iou", str(float(tt.get("min_iou", 0.90)))], steps, timeout)

        # 03a calibrated still-view zero-start visual hull.
        vh = contract.get("visual_hull")
        if isinstance(vh, dict):
            if current_spec is not None: raise ValueError("use either turntable_hull or visual_hull as the zero-start source, not both")
            hdir = out / "03a-visual-hull"; hdir.mkdir(exist_ok=True); hp = hdir / "hull-manifest.json"
            refs = []
            for j, r in enumerate(vh.get("references", [])):
                if not isinstance(r, dict) or not r.get("source") or not isinstance(r.get("camera"), dict):
                    raise ValueError("visual_hull.references need source + camera")
                item = source_item(mapping, root, str(r["source"])); mask = staged_frame(item, int(r.get("frame", 0)), "mask", media_dir)
                refs.append({"id": str(r.get("id", f"view_{j}")), "mask": str(mask), "camera": r["camera"]})
            hcfg = {"id": str(vh.get("id", receipt["project_id"] + "-hull")), "bounds": vh.get("bounds"), "voxel": float(vh.get("voxel", 1.0)), "references": refs, "texture": int(vh.get("texture", 64)), "uv_padding": int(vh.get("uv_padding", 1)), "max_voxels": int(vh.get("max_voxels", 2_000_000))}
            hp.write_text(json.dumps(hcfg, indent=2) + "\n", encoding="utf-8")
            current_spec = hdir / "hull.creature.json"
            run_step("visual-hull", [sys.executable, str(tools / "reference_visual_hull.py"), str(hp), "--output", str(current_spec), "--report", str(hdir / "report.json"), "--render-dir", str(hdir / "renders"), "--min-iou", str(float(vh.get("min_iou", 0.90)))], steps, timeout)

        # 03b automatic evidence-constrained scaffold/hull refinement (no manual parameter list).
        ar = contract.get("auto_refine")
        if isinstance(ar, dict):
            specv = ar.get("spec", "$current")
            spec = current_spec if specv in {"$current", "$hull", "$scaffold"} else resolve(root, str(specv))
            if spec is None: raise ValueError("auto_refine requires an asset_scaffold/visual_hull/turntable_hull or explicit spec")
            adir = out / "03b-auto-refine"; adir.mkdir(exist_ok=True); rp = adir / "references.json"; refs=[]
            for j, r in enumerate(ar.get("references", [])):
                if not isinstance(r, dict) or not r.get("source") or not isinstance(r.get("camera"), dict): raise ValueError("auto_refine.references need source + camera")
                item=source_item(mapping, root, str(r["source"])); fi=int(r.get("frame",0)); rec={"id":str(r.get("id",f"view_{j}")),"mask":str(staged_frame(item,fi,"mask",media_dir)),"camera":r["camera"],"weight":float(r.get("weight",1.0))}
                if float(r.get("edge_weight",0.0))>0: rec.update({"edges":str(staged_frame(item,fi,"edges",media_dir)),"edge_weight":float(r.get("edge_weight",0.0)),"edge_tolerance":int(r.get("edge_tolerance",2))})
                refs.append(rec)
            if not refs: raise ValueError("auto_refine.references must be non-empty")
            rp.write_text(json.dumps({"references":refs},indent=2)+"\n",encoding="utf-8"); refined=adir/"refined.creature.json"
            acmd=[sys.executable,str(tools/"reference_auto_refine.py"),str(spec),str(rp),"--output",str(refined),"--report",str(adir/"report.json"),"--passes",str(int(ar.get("passes",2))),"--maxiter",str(int(ar.get("maxiter",14))),"--popsize",str(int(ar.get("popsize",6))),"--size-factor",str(float(ar.get("size_factor",1.65))),"--origin-fraction",str(float(ar.get("origin_fraction",.55))),"--min-iou",str(float(ar.get("min_iou",.90)))]
            if bool(ar.get("auto_camera",False)): acmd.append("--auto-camera")
            if isinstance(ar.get("include"),list) and ar["include"]: acmd += ["--include", *[str(x) for x in ar["include"]]]
            run_step("auto-refine",acmd,steps,timeout); current_spec=refined

        # 03c explicit geometry + camera inverse fit for constrained/hand-selected parameters.
        gf = contract.get("geometry_fit")
        if isinstance(gf, dict):
            specv = gf.get("spec", "$hull" if current_spec is not None else None)
            if specv is None: raise ValueError("geometry_fit.spec is required when visual_hull is absent")
            spec = current_spec if specv in {"$hull", "$current", "$scaffold"} else resolve(root, str(specv))
            if spec is None: raise ValueError("geometry_fit requested the current zero-start spec but no scaffold/hull is available")
            fitdir = out / "03c-geometry"; fitdir.mkdir(exist_ok=True); fit_manifest = fitdir / "fit-manifest.json"
            if gf.get("fit_manifest"):
                shutil.copy2(resolve(root, str(gf["fit_manifest"])), fit_manifest)
            else:
                refs = []
                for j, r in enumerate(gf.get("references", [])):
                    if not isinstance(r, dict) or not r.get("source") or not isinstance(r.get("camera"), dict): raise ValueError("geometry_fit.references need source + camera")
                    item = source_item(mapping, root, str(r["source"])); frame_i = int(r.get("frame", 0)); mask = staged_frame(item, frame_i, "mask", media_dir)
                    rec = {"id": str(r.get("id", f"view_{j}")), "mask": str(mask), "camera": r["camera"], "weight": float(r.get("weight", 1.0))}
                    if float(r.get("edge_weight", 0.0)) > 0:
                        rec["edges"] = str(staged_frame(item, frame_i, "edges", media_dir)); rec["edge_weight"] = float(r.get("edge_weight", 0.0)); rec["edge_tolerance"] = int(r.get("edge_tolerance", 2))
                    refs.append(rec)
                fit_manifest.write_text(json.dumps({"references": refs, "parameters": gf.get("parameters", [])}, indent=2) + "\n", encoding="utf-8")
            current_spec = fitdir / "fitted.creature.json"
            cmd = [sys.executable, str(tools / "reference_cuboid_fit.py"), str(spec), str(fit_manifest), "--out-spec", str(current_spec), "--report", str(fitdir / "report.json"), "--render-dir", str(fitdir / "renders"), "--maxiter", str(int(gf.get("maxiter", 80))), "--popsize", str(int(gf.get("popsize", 10))), "--seed", str(int(gf.get("seed", 1337))), "--min-iou", str(float(gf.get("min_iou", 0.90)))]
            run_step("geometry-camera-fit", cmd, steps, timeout)

        # 03d attachment/context transform fits: held items, armor/cosmetics, furniture anchors.
        afs = contract.get("attachment_fits", [])
        if isinstance(afs, list):
            for idx, af in enumerate(afs):
                if not isinstance(af, dict): raise ValueError("attachment_fits entries must be objects")
                fdir = out / "03d-attachment" / f"{idx:03d}-{af.get('name','attachment')}"; fdir.mkdir(parents=True, exist_ok=True)
                specv = af.get("spec", "$current"); spec = current_spec if specv in {"$current", "$hull", "$scaffold"} else resolve(root, str(specv))
                if spec is None: raise ValueError("attachment fit requested current spec but no current scaffold/hull/refined spec exists")
                manifest = resolve(root, str(af["config"]))
                cmd = [sys.executable, str(tools / "reference_attachment_fit.py"), str(spec), str(manifest), "--output", str(fdir / "runtime-transform.json"), "--report", str(fdir / "report.json"), "--min-screen-rmse", str(float(af.get("min_screen_rmse", 1.5))), "--min-world-rmse", str(float(af.get("min_world_rmse", 0.20)))]
                run_step(f"attachment-fit:{af.get('name',idx)}", cmd, steps, timeout, bool(af.get("required", True)))

        # 04 pose fits.
        pfs = contract.get("pose_fits", [])
        if isinstance(pfs, list):
            for idx, pf in enumerate(pfs):
                if not isinstance(pf, dict): raise ValueError("pose_fits entries must be objects")
                pdir = out / "04-pose" / f"{idx:03d}-{pf.get('name','pose')}"; pdir.mkdir(parents=True, exist_ok=True)
                specv = pf.get("spec", "$geometry")
                spec = current_spec if specv == "$geometry" else resolve(root, str(specv))
                if spec is None: raise ValueError("pose fit requested $geometry but geometry_fit is absent")
                item = source_item(mapping, root, str(pf["source"])); item_manifest = Path(item["item_manifest_abs"])
                if bool(pf.get("motion_partition", False)):
                    run_step(f"motion-partition:{pf.get('name',idx)}", [sys.executable, str(tools / "reference_motion_partition.py"), str(item_manifest), "--output", str(pdir / "motion-partition.json"), "--labels", str(pdir / "motion-labels.png"), "--clusters", str(int(pf.get("motion_clusters", 4))), "--min-motion", str(float(pf.get("min_motion", 0.35)))], steps, timeout, False)
                cfg = resolve(root, str(pf["config"])); cmd = [sys.executable, str(tools / "reference_pose_sequence_fit.py"), str(spec), str(item_manifest), str(cfg), "--output", str(pdir / "animation.json"), "--report", str(pdir / "report.json"), "--render-dir", str(pdir / "renders"), "--maxiter", str(int(pf.get("maxiter", 50))), "--popsize", str(int(pf.get("popsize", 8))), "--seed", str(int(pf.get("seed", 4242)))]
                run_step(f"pose-fit:{pf.get('name',idx)}", cmd, steps, timeout)

        # 05 visible texture inverse bake.
        tb = contract.get("texture_bake")
        if isinstance(tb, dict):
            tdir = out / "05-texture"; tdir.mkdir(exist_ok=True); specv = tb.get("spec", "$geometry"); spec = current_spec if specv == "$geometry" else resolve(root, str(specv))
            if spec is None: raise ValueError("texture bake requested $geometry but geometry_fit is absent")
            obs = []
            if tb.get("observations_file"):
                shutil.copy2(resolve(root, str(tb["observations_file"])), tdir / "observations.json")
            else:
                for r in tb.get("observations", []):
                    item = source_item(mapping, root, str(r["source"])); image = staged_frame(item, int(r.get("frame", 0)), "frame", media_dir)
                    obs.append({"image": str(image), "camera": r["camera"], "weight": float(r.get("weight", 1.0))})
                (tdir / "observations.json").write_text(json.dumps({"observations": obs}, indent=2) + "\n", encoding="utf-8")
            cmd = [sys.executable, str(tools / "reference_texture_bake.py"), str(spec), str(tdir / "observations.json"), "--output", str(tdir / "recovered.png"), "--coverage", str(tdir / "coverage.png"), "--confidence", str(tdir / "confidence.png"), "--report", str(tdir / "report.json")]
            if tb.get("base"): cmd += ["--base", str(resolve(root, str(tb["base"])))]
            run_step("visible-texture-bake", cmd, steps, timeout)
            delight = tb.get("delight")
            if delight is True or isinstance(delight, dict):
                dc = delight if isinstance(delight, dict) else {}
                dcmd = [sys.executable, str(tools / "reference_texture_delight.py"), str(tdir / "recovered.png"), "--coverage", str(tdir / "coverage.png"), "--output", str(tdir / "draft-albedo.png"), "--emissive", str(tdir / "emissive-candidates.png"), "--report", str(tdir / "delight-report.json"), "--palette", str(int(dc.get("palette", 24))), "--sigma", str(float(dc.get("sigma", 3.0)))]
                run_step("texture-delight-draft", dcmd, steps, timeout, False)

        # 06 explicit parity gates against candidate rendered evidence.
        parity = contract.get("parity", [])
        if isinstance(parity, list):
            pdir = out / "06-parity"; pdir.mkdir(exist_ok=True)
            for idx, p in enumerate(parity):
                ref = resolve(root, str(p["reference"])); cand = resolve(root, str(p["candidate"])); rep = pdir / f"{idx:03d}.json"
                cmd = [sys.executable, str(tools / "reference_parity_gate.py"), str(ref), str(cand), "--output", str(rep), "--min-score", str(float(p.get("min_score", 0.90))), "--min-silhouette", str(float(p.get("min_silhouette", 0.92))), "--max-frames", str(int(p.get("max_frames", 48)))]
                if p.get("no_align"): cmd.append("--no-align")
                parity_ok = run_step(f"parity:{idx}", cmd, steps, timeout, bool(p.get("required", True)))
                if bool(p.get("residual", False)) and ref.suffix.lower() not in {".gif", ".webp"} and cand.suffix.lower() not in {".gif", ".webp"}:
                    run_step(f"residual:{idx}", [sys.executable, str(tools / "reference_residual_map.py"), str(ref), str(cand), "--out", str(pdir / f"{idx:03d}-residual.png"), "--report", str(pdir / f"{idx:03d}-residual.json")], steps, timeout, False)

        # 07 optional family-level consistency audit over reconstructed/original asset catalog.
        pc = contract.get("pack_consistency")
        if isinstance(pc, dict):
            cpath = resolve(root, str(pc["catalog"])); cdir = out / "07-pack-consistency"; cdir.mkdir(exist_ok=True)
            cmd = [sys.executable, str(tools / "reference_pack_consistency_audit.py"), str(cpath), "--output", str(cdir / "report.json"), "--markdown", str(cdir / "report.md")]
            if bool(pc.get("strict", False)): cmd.append("--strict")
            run_step("pack-consistency", cmd, steps, timeout, bool(pc.get("required", True)))

        # Hash material outputs, but skip staged duplicate frame noise.
        for p in sorted(out.rglob("*")):
            if not p.is_file() or "01-media" in p.parts or p.name in {"RECONSTRUCTION-RECEIPT.json", "README.md"}: continue
            receipt["outputs"].append({"path": str(p.relative_to(out)), "size": p.stat().st_size, "sha256": sha256(p)})
        receipt["result"] = "pass"
    except Exception as exc:
        receipt["error"] = str(exc); receipt["result"] = "fail"
    finally:
        (out / "RECONSTRUCTION-RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8"); write_readme(out, receipt)
    print(json.dumps({"result": receipt["result"], "receipt": str(out / "RECONSTRUCTION-RECEIPT.json"), "steps": len(steps)}, indent=2))
    return 0 if receipt["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
