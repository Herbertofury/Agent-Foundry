#!/usr/bin/env python3
"""Validate a stable Dev Kit creature spec and compile GeckoLib4-style runtime JSON.

The input spec intentionally avoids Blockbench's internal .bbmodel schema. It emits the
Bedrock-style geometry/animation JSON consumed by GeckoLib 4, while .bbmodel remains an
artist-authoring project that can be validated separately.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9_.-]+$")
CHANNELS = {"rotation", "position", "scale"}
LERP = {"linear", "catmullrom", "step"}

def box_uv_footprint(size: list[float]) -> tuple[int, int]:
    x, y, z = (abs(float(v)) for v in size)
    return max(1, math.ceil(2 * (x + z))), max(1, math.ceil(y + z))


@dataclass
class Issue:
    level: str
    code: str
    message: str


def vec(value: Any, n: int, where: str, issues: list[Issue], *, positive: bool = False) -> list[float] | None:
    if not isinstance(value, list) or len(value) != n or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value):
        issues.append(Issue("error", "vector", f"{where} must be {n} finite numbers"))
        return None
    out = [float(v) for v in value]
    if positive and any(v <= 0 for v in out):
        issues.append(Issue("error", "positive-vector", f"{where} values must be > 0"))
    return out


def validate_spec(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if spec.get("schema_version") != 1:
        issues.append(Issue("error", "schema", "schema_version must be 1"))
    sid = spec.get("id")
    if not isinstance(sid, str) or not ID_RE.fullmatch(sid):
        issues.append(Issue("error", "id", "id must match [a-z0-9_.-]+"))

    tex = spec.get("texture")
    if not isinstance(tex, dict):
        issues.append(Issue("error", "texture", "texture object is required"))
    else:
        for key in ("width", "height"):
            if not isinstance(tex.get(key), int) or tex[key] <= 0:
                issues.append(Issue("error", "texture-size", f"texture.{key} must be a positive integer"))

    bounds = spec.get("visible_bounds", {})
    if bounds:
        for k in ("width", "height"):
            if not isinstance(bounds.get(k), (int, float)) or bounds[k] <= 0:
                issues.append(Issue("error", "visible-bounds", f"visible_bounds.{k} must be > 0"))
        if "offset" in bounds:
            vec(bounds["offset"], 3, "visible_bounds.offset", issues)

    bones = spec.get("bones")
    if not isinstance(bones, list) or not bones:
        issues.append(Issue("error", "bones", "bones must be a non-empty list"))
        bones = []
    bone_ids: set[str] = set()
    parent_of: dict[str, str] = {}
    for i, bone in enumerate(bones):
        where = f"bones[{i}]"
        if not isinstance(bone, dict):
            issues.append(Issue("error", "bone", f"{where} must be an object"))
            continue
        bid = bone.get("id")
        if not isinstance(bid, str) or not ID_RE.fullmatch(bid):
            issues.append(Issue("error", "bone-id", f"{where}.id invalid"))
            continue
        if bid in bone_ids:
            issues.append(Issue("error", "bone-duplicate", f"duplicate bone id {bid}"))
        bone_ids.add(bid)
        vec(bone.get("pivot", [0, 0, 0]), 3, f"{where}.pivot", issues)
        if "rotation" in bone:
            vec(bone["rotation"], 3, f"{where}.rotation", issues)
        locators = bone.get("locators", {})
        if locators is not None and not isinstance(locators, dict):
            issues.append(Issue("error", "bone-locators", f"{where}.locators must be an object"))
        elif isinstance(locators, dict):
            for lid, lval in locators.items():
                if not isinstance(lid, str) or not ID_RE.fullmatch(lid):
                    issues.append(Issue("error", "locator-id", f"{where} locator id {lid!r} invalid"))
                vec(lval, 3, f"{where}.locators.{lid}", issues)
        parent = bone.get("parent")
        if parent is not None:
            if not isinstance(parent, str):
                issues.append(Issue("error", "bone-parent", f"{where}.parent must be a string"))
            else:
                parent_of[bid] = parent
    for child, parent in parent_of.items():
        if parent not in bone_ids:
            issues.append(Issue("error", "bone-parent-missing", f"bone {child} references missing parent {parent}"))
    roots = [b for b in bone_ids if b not in parent_of]
    if len(roots) != 1:
        issues.append(Issue("warning", "bone-roots", f"expected one semantic root bone, found {len(roots)}: {sorted(roots)}"))
    for start in bone_ids:
        seen = {start}
        cur = start
        while cur in parent_of:
            cur = parent_of[cur]
            if cur in seen:
                issues.append(Issue("error", "bone-cycle", f"bone hierarchy cycle reaches {cur}"))
                break
            seen.add(cur)

    cube_ids: set[str] = set()
    tex_w = tex.get("width") if isinstance(tex, dict) and isinstance(tex.get("width"), int) else None
    tex_h = tex.get("height") if isinstance(tex, dict) and isinstance(tex.get("height"), int) else None
    cubes = spec.get("cubes", [])
    uv_rects: list[tuple[str, float, float, float, float, bool]] = []
    if not isinstance(cubes, list):
        issues.append(Issue("error", "cubes", "cubes must be a list"))
        cubes = []
    if not cubes:
        issues.append(Issue("warning", "cubes-empty", "spec has no cubes"))
    for i, cube in enumerate(cubes):
        where = f"cubes[{i}]"
        if not isinstance(cube, dict):
            issues.append(Issue("error", "cube", f"{where} must be an object"))
            continue
        cid = cube.get("id")
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
            issues.append(Issue("error", "cube-id", f"{where}.id invalid"))
        elif cid in cube_ids:
            issues.append(Issue("error", "cube-duplicate", f"duplicate cube id {cid}"))
        else:
            cube_ids.add(cid)
        if cube.get("bone") not in bone_ids:
            issues.append(Issue("error", "cube-bone", f"{where}.bone references missing bone {cube.get('bone')!r}"))
        vec(cube.get("origin"), 3, f"{where}.origin", issues)
        vec(cube.get("size"), 3, f"{where}.size", issues, positive=True)
        if "pivot" in cube:
            vec(cube["pivot"], 3, f"{where}.pivot", issues)
        if "rotation" in cube:
            vec(cube["rotation"], 3, f"{where}.rotation", issues)
        uv = cube.get("uv")
        if uv is None:
            issues.append(Issue("error", "cube-uv", f"{where}.uv is required for box UV"))
        else:
            parsed = vec(uv, 2, f"{where}.uv", issues)
            sizev = cube.get("size") if isinstance(cube.get("size"), list) and len(cube.get("size")) == 3 else None
            if parsed and sizev and all(isinstance(v, (int, float)) for v in sizev):
                fw, fh = box_uv_footprint([float(v) for v in sizev])
                if tex_w and tex_h and (parsed[0] < 0 or parsed[1] < 0 or parsed[0] + fw > tex_w or parsed[1] + fh > tex_h):
                    issues.append(Issue("error", "cube-uv-range", f"{where} box-UV footprint {fw}x{fh} at {parsed} exceeds texture {tex_w}x{tex_h}"))
                uv_rects.append((str(cid), parsed[0], parsed[1], parsed[0] + fw, parsed[1] + fh, bool(cube.get("uv_overlap_ok"))))
        inflate = cube.get("inflate", 0)
        if not isinstance(inflate, (int, float)) or not math.isfinite(inflate):
            issues.append(Issue("error", "cube-inflate", f"{where}.inflate must be finite"))

    for i in range(len(uv_rects)):
        a = uv_rects[i]
        for j in range(i + 1, len(uv_rects)):
            b = uv_rects[j]
            overlap = not (a[3] <= b[1] or a[1] >= b[3] or a[4] <= b[2] or a[2] >= b[4])
            if overlap and not (a[5] or b[5]):
                issues.append(Issue("warning", "cube-uv-overlap", f"UV footprints overlap for cubes {a[0]} and {b[0]}; mark uv_overlap_ok only when deliberate"))

    anim_names: set[str] = set()
    animations = spec.get("animations", [])
    if not isinstance(animations, list):
        issues.append(Issue("error", "animations", "animations must be a list"))
        animations = []
    for ai, anim in enumerate(animations):
        where = f"animations[{ai}]"
        if not isinstance(anim, dict):
            issues.append(Issue("error", "animation", f"{where} must be an object"))
            continue
        name = anim.get("name")
        if not isinstance(name, str) or not ID_RE.fullmatch(name):
            issues.append(Issue("error", "animation-name", f"{where}.name invalid"))
            continue
        if name in anim_names:
            issues.append(Issue("error", "animation-duplicate", f"duplicate animation name {name}"))
        anim_names.add(name)
        length = anim.get("length")
        if not isinstance(length, (int, float)) or length <= 0 or not math.isfinite(length):
            issues.append(Issue("error", "animation-length", f"{where}.length must be > 0"))
            length = 0
        tracks = anim.get("bones", {})
        if not isinstance(tracks, dict):
            issues.append(Issue("error", "animation-bones", f"{where}.bones must be an object"))
            continue
        if not tracks:
            issues.append(Issue("warning", "animation-empty", f"{where} has no authored bone tracks"))
        marker_ids: set[str] = set()
        markers = anim.get("markers", [])
        if markers is not None and not isinstance(markers, list):
            issues.append(Issue("error", "animation-markers", f"{where}.markers must be a list"))
            markers = []
        for mi, marker in enumerate(markers or []):
            mw = f"{where}.markers[{mi}]"
            if not isinstance(marker, dict):
                issues.append(Issue("error", "marker", f"{mw} must be an object"))
                continue
            mid = marker.get("id")
            if not isinstance(mid, str) or not ID_RE.fullmatch(mid):
                issues.append(Issue("error", "marker-id", f"{mw}.id invalid"))
            elif mid in marker_ids:
                issues.append(Issue("error", "marker-duplicate", f"duplicate marker {mid} in animation {name}"))
            else:
                marker_ids.add(mid)
            mt = marker.get("time")
            if not isinstance(mt, (int, float)) or not math.isfinite(mt) or mt < 0 or (length and mt > length + 1e-9):
                issues.append(Issue("error", "marker-time", f"{mw}.time must be within animation length"))
            if marker.get("kind") not in {"damage", "vfx", "sfx", "gameplay", "footstep", "projectile", "custom"}:
                issues.append(Issue("warning", "marker-kind", f"{mw}.kind is uncommon/unspecified"))
        for bid, channels in tracks.items():
            if bid not in bone_ids:
                issues.append(Issue("error", "animation-bone-missing", f"{where} targets missing bone {bid}"))
            if not isinstance(channels, dict):
                issues.append(Issue("error", "animation-channel", f"{where}.bones.{bid} must be an object"))
                continue
            for channel, keys in channels.items():
                if channel not in CHANNELS:
                    issues.append(Issue("error", "animation-channel-name", f"unsupported channel {channel} on {name}/{bid}"))
                    continue
                if not isinstance(keys, list) or not keys:
                    issues.append(Issue("error", "animation-keys", f"{name}/{bid}/{channel} needs keyframes"))
                    continue
                last = -math.inf
                for ki, key in enumerate(keys):
                    kw = f"{name}/{bid}/{channel}[{ki}]"
                    if not isinstance(key, dict):
                        issues.append(Issue("error", "keyframe", f"{kw} must be an object"))
                        continue
                    t = key.get("time")
                    if not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0:
                        issues.append(Issue("error", "keyframe-time", f"{kw}.time must be finite and >= 0"))
                    else:
                        if t < last:
                            issues.append(Issue("error", "keyframe-order", f"{kw}.time is out of order"))
                        last = t
                        if length and t > length + 1e-9:
                            issues.append(Issue("error", "keyframe-range", f"{kw}.time {t} exceeds animation length {length}"))
                    vec(key.get("value"), 3, f"{kw}.value", issues)
                    lerp = key.get("lerp", "linear")
                    if lerp not in LERP:
                        issues.append(Issue("error", "keyframe-lerp", f"{kw}.lerp {lerp!r} unsupported; use {sorted(LERP)}"))

    return issues


def keyframes_to_gecko(keys: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in keys:
        t = float(key["time"])
        time_key = f"{t:g}"
        value = [float(v) for v in key["value"]]
        lerp = key.get("lerp", "linear")
        if lerp == "linear":
            result[time_key] = {"vector": value}
        else:
            result[time_key] = {"post": {"vector": value}, "lerp_mode": lerp}
    return result


def compile_geometry(spec: dict[str, Any]) -> dict[str, Any]:
    cubes_by_bone: dict[str, list[dict[str, Any]]] = {}
    for cube in spec.get("cubes", []):
        out = {
            "origin": [float(v) for v in cube["origin"]],
            "size": [float(v) for v in cube["size"]],
            "uv": [float(v) for v in cube["uv"]],
        }
        if cube.get("inflate", 0):
            out["inflate"] = float(cube["inflate"])
        if "pivot" in cube:
            out["pivot"] = [float(v) for v in cube["pivot"]]
        if "rotation" in cube:
            out["rotation"] = [float(v) for v in cube["rotation"]]
        if cube.get("mirror") is True:
            out["mirror"] = True
        cubes_by_bone.setdefault(cube["bone"], []).append(out)

    bones_out = []
    for bone in spec["bones"]:
        out: dict[str, Any] = {"name": bone["id"], "pivot": [float(v) for v in bone.get("pivot", [0, 0, 0])]}
        if bone.get("parent"):
            out["parent"] = bone["parent"]
        if "rotation" in bone:
            out["rotation"] = [float(v) for v in bone["rotation"]]
        if bone.get("mirror") is True:
            out["mirror"] = True
        if bone.get("never_render") is True:
            out["neverRender"] = True
        if isinstance(bone.get("locators"), dict) and bone["locators"]:
            out["locators"] = {name: [float(v) for v in value] for name, value in bone["locators"].items()}
        if bone["id"] in cubes_by_bone:
            out["cubes"] = cubes_by_bone[bone["id"]]
        bones_out.append(out)

    tex = spec["texture"]
    bounds = spec.get("visible_bounds", {})
    desc: dict[str, Any] = {
        "identifier": f"geometry.{spec['id']}",
        "texture_width": tex["width"],
        "texture_height": tex["height"],
        "visible_bounds_width": float(bounds.get("width", 2.5)),
        "visible_bounds_height": float(bounds.get("height", 3.0)),
        "visible_bounds_offset": [float(v) for v in bounds.get("offset", [0, 1.0, 0])],
    }
    return {"format_version": "1.12.0", "minecraft:geometry": [{"description": desc, "bones": bones_out}]}


def compile_animations(spec: dict[str, Any]) -> dict[str, Any]:
    anims: dict[str, Any] = {}
    for anim in spec.get("animations", []):
        out: dict[str, Any] = {"animation_length": float(anim["length"]), "bones": {}}
        loop = anim.get("loop", False)
        if loop:
            out["loop"] = True if loop is True else loop
        for bid, channels in anim.get("bones", {}).items():
            bone_out: dict[str, Any] = {}
            for channel, keys in channels.items():
                bone_out[channel] = keyframes_to_gecko(keys)
            out["bones"][bid] = bone_out
        timeline: dict[str, list[str]] = {}
        for marker in anim.get("markers", []) or []:
            t = f"{float(marker['time']):g}"
            token = f"devkit_event:{marker.get('kind', 'custom')}:{marker['id']}"
            timeline.setdefault(t, []).append(token)
        if timeline:
            out["timeline"] = {t: "||".join(tokens) for t, tokens in timeline.items()}
        anims[f"animation.{spec['id']}.{anim['name']}"] = out
    return {"format_version": "1.8.0", "animations": anims}


def compile_events(spec: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"schema_version": 1, "entity": spec["id"], "animations": {}}
    for anim in spec.get("animations", []):
        markers = anim.get("markers", []) or []
        if markers:
            result["animations"][anim["name"]] = [
                {"id": m["id"], "time": float(m["time"]), "kind": m.get("kind", "custom"), **({"payload": m["payload"]} if "payload" in m else {})}
                for m in markers
            ]
    return result


def markdown_report(spec_path: Path, issues: list[Issue], geo_path: Path | None, anim_path: Path | None, events_path: Path | None = None) -> str:
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    lines = ["# Creature Spec Compiler", "", f"- Spec: `{spec_path}`", f"- Result: **{'FAIL' if errors else 'PASS'}**", f"- Errors: {len(errors)}", f"- Warnings: {len(warnings)}"]
    if geo_path:
        lines.append(f"- Geometry: `{geo_path}`")
    if anim_path:
        lines.append(f"- Animations: `{anim_path}`")
    if events_path:
        lines.append(f"- Event markers: `{events_path}`")
    if issues:
        lines += ["", "## Issues", ""] + [f"- **{i.level.upper()}** `{i.code}`: {i.message}" for i in issues]
    else:
        lines += ["", "No structural issues found."]
    lines += ["", "This validates/compiles structure only. Artist inspection and native Minecraft runtime proof remain required."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--geo", type=Path)
    ap.add_argument("--animation", type=Path)
    ap.add_argument("--events", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read spec: {exc}", flush=True)
        return 2
    if not isinstance(spec, dict):
        print("ERROR: spec root must be an object", flush=True)
        return 2
    issues = validate_spec(spec)
    errors = [i for i in issues if i.level == "error"]
    geo_path = None
    anim_path = None
    events_path = None
    if not errors and not args.validate_only:
        geo_path = args.geo or args.spec.with_suffix(".geo.json")
        anim_path = args.animation or args.spec.with_suffix(".animation.json")
        geo_path.parent.mkdir(parents=True, exist_ok=True)
        anim_path.parent.mkdir(parents=True, exist_ok=True)
        geo_path.write_text(json.dumps(compile_geometry(spec), indent=2, sort_keys=False) + "\n", encoding="utf-8")
        anim_path.write_text(json.dumps(compile_animations(spec), indent=2, sort_keys=False) + "\n", encoding="utf-8")
        events_path = args.events or args.spec.with_suffix(".events.json")
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(json.dumps(compile_events(spec), indent=2, sort_keys=False) + "\n", encoding="utf-8")
    report = markdown_report(args.spec, issues, geo_path, anim_path, events_path)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
