#!/usr/bin/env python3
"""One-command premium mob-pack static QA orchestration."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return 124, f"Timed out after {timeout}s: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--strict", action="store_true", help="Treat any JSON-reported warning finding as a release failure")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("01-premium-gate", [sys.executable, str(script_dir / "premium_mob_pack_gate.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "01-premium-gate.md"), "--json", str(out / "01-premium-gate.json")]),
        ("02-animation-audit", [sys.executable, str(script_dir / "mob_animation_state_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "02-animation-audit.md"), "--json", str(out / "02-animation-audit.json")]),
        ("03-model-complexity", [sys.executable, str(script_dir / "mob_model_complexity_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "03-model-complexity.md"), "--json", str(out / "03-model-complexity.json")]),
        ("04-creature-spec-compile", [sys.executable, str(script_dir / "mob_pack_spec_compile.py"), str(args.manifest), "--root", str(args.root), "--out", str(out / "04-compiled-specs"), "--markdown", str(out / "04-creature-spec-compile.md"), "--json", str(out / "04-creature-spec-compile.json")]),
        ("05-geometry-rig-quality", [sys.executable, str(script_dir / "mob_geometry_quality_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "05-geometry-rig-quality.md"), "--json", str(out / "05-geometry-rig-quality.json")]),
        ("05b-silhouette-diversity", [sys.executable, str(script_dir / "mob_silhouette_diversity_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "05b-silhouette-diversity.md"), "--json", str(out / "05b-silhouette-diversity.json")]),
        ("06-texture-material", [sys.executable, str(script_dir / "creature_texture_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "06-texture-material.md"), "--json", str(out / "06-texture-material.json")]),
        ("07-variant-quality", [sys.executable, str(script_dir / "mob_variant_quality_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "07-variant-quality.md"), "--json", str(out / "07-variant-quality.json")]),
        ("08-vfx-contract", [sys.executable, str(script_dir / "mob_vfx_contract_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "08-vfx-contract.md"), "--json", str(out / "08-vfx-contract.json")]),
        ("09-sfx-contract", [sys.executable, str(script_dir / "mob_sfx_contract_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "09-sfx-contract.md"), "--json", str(out / "09-sfx-contract.json")]),
        ("10-event-marker-audit", [sys.executable, str(script_dir / "mob_event_marker_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "10-event-marker-audit.md"), "--json", str(out / "10-event-marker-audit.json")]),
        ("11-animation-curves", [sys.executable, str(script_dir / "mob_animation_curve_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "11-animation-curves.md"), "--json", str(out / "11-animation-curves.json")]),
        ("12-encounter-graphs", [sys.executable, str(script_dir / "mob_encounter_graph_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "12-encounter-graphs.md"), "--json", str(out / "12-encounter-graphs.json")]),
        ("13-combat-design", [sys.executable, str(script_dir / "mob_combat_design_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "13-combat-design.md"), "--json", str(out / "13-combat-design.json")]),
        ("14-runtime-contract", [sys.executable, str(script_dir / "mob_runtime_contract_audit.py"), str(args.manifest), "--root", str(args.root), "--markdown", str(out / "14-runtime-contract.md"), "--json", str(out / "14-runtime-contract.json")]),
        ("15-runtime-plan", [sys.executable, str(script_dir / "premium_mob_runtime_plan.py"), str(args.manifest), "--output", str(out / "15-runtime-plan.md"), "--json", str(out / "15-runtime-plan.json")]),
        ("16-shotlist", [sys.executable, str(script_dir / "mob_pack_shotlist.py"), str(args.manifest), "--output", str(out / "16-shotlist.md")]),
    ]
    results = []
    overall = 0
    for name, cmd in jobs:
        rc, output = run(cmd, args.timeout)
        results.append({"name": name, "returncode": rc, "output_tail": output[-4000:]})
        if rc != 0:
            overall = 2
    strict_warnings = []
    if args.strict:
        for report in sorted(out.glob("*.json")):
            if report.name == "PIPELINE-RECEIPT.json":
                continue
            try:
                payload = json.loads(report.read_text(encoding="utf-8"))
            except Exception:
                continue
            for finding in payload.get("findings", []) if isinstance(payload, dict) else []:
                if isinstance(finding, dict) and finding.get("level") == "warning":
                    strict_warnings.append({"report": report.name, **finding})
        if strict_warnings:
            overall = 2

    receipt = {
        "manifest": str(args.manifest),
        "manifest_sha256": sha256(args.manifest),
        "root": str(args.root.resolve()),
        "result": "pass" if overall == 0 else "fail",
        "jobs": results,
        "strict": args.strict,
        "strict_warning_failures": strict_warnings,
        "note": "Static premium QA only. Native Minecraft visual/gameplay/performance proof remains required.",
    }
    (out / "PIPELINE-RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    index = [
        "# Premium Mob Pack Pipeline",
        "",
        f"- Result: **{receipt['result'].upper()}**",
        f"- Strict release mode: **{args.strict}**",
        f"- Strict warning blockers: **{len(strict_warnings)}**",
        f"- Manifest SHA-256: `{receipt['manifest_sha256']}`",
        "",
        "## Reports",
        "",
        "- `01-premium-gate.md`",
        "- `02-animation-audit.md`",
        "- `03-model-complexity.md`",
        "- `04-creature-spec-compile.md`",
        "- `05-geometry-rig-quality.md`",
        "- `05b-silhouette-diversity.md`",
        "- `06-texture-material.md`",
        "- `07-variant-quality.md`",
        "- `08-vfx-contract.md`",
        "- `09-sfx-contract.md`",
        "- `10-event-marker-audit.md`",
        "- `11-animation-curves.md`",
        "- `12-encounter-graphs.md`",
        "- `13-combat-design.md`",
        "- `14-runtime-contract.md`",
        "- `15-runtime-plan.md`",
        "- `16-shotlist.md`",
        "- `PIPELINE-RECEIPT.json`",
        "",
        "A static pass is only the handoff into Project Visual QA + native Minecraft client/server proof.",
    ]
    (out / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(out / "README.md")
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
