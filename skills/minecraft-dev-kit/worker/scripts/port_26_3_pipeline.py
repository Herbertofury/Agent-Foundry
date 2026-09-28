#!/usr/bin/env python3
"""Chain 26.3 intake -> target scaffold -> evidence/ledger initialization for a new port workspace."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from port_intake import inspect, render_md as render_intake_md
from mixin_surface_audit import render_md as render_mixin_md
from port_semantic_planner import plan as semantic_plan, render_md as render_semantic_md
from content_identity_inventory import inventory as content_inventory
from registration_identity_inventory import inventory as registration_inventory

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("--loader", required=True, choices=["fabric", "neoforge"])
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--mod-id", required=True)
    ap.add_argument("--mod-name")
    ap.add_argument("--group", default="com.example")
    ap.add_argument("--mod-version", default="1.0.0")
    args = ap.parse_args()

    source = args.source.resolve()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output must be empty/new for pipeline safety: {out}")

    intake = inspect(source, args.loader)
    semantics = semantic_plan(source, args.loader)
    source_content = content_inventory(source)
    source_registrations = registration_inventory(source)
    cmd = [
        sys.executable, str(SCRIPT_DIR / "port_scaffold_26_3.py"),
        "--loader", args.loader, "--output", str(out), "--mod-id", args.mod_id,
        "--group", args.group, "--mod-version", args.mod_version,
    ]
    if args.mod_name:
        cmd += ["--mod-name", args.mod_name]
    subprocess.run(cmd, check=True)

    evidence = out / "devkit-evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "port-intake.json").write_text(json.dumps(intake, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "port-intake.md").write_text(render_intake_md(intake), encoding="utf-8")
    (evidence / "mapping-plan.json").write_text(json.dumps(intake.get("mapping_plan"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "mixin-audit.json").write_text(json.dumps(intake.get("mixin_audit"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "mixin-audit.md").write_text(render_mixin_md(intake["mixin_audit"]), encoding="utf-8")
    (evidence / "semantic-port-plan.json").write_text(json.dumps(semantics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "semantic-port-plan.md").write_text(render_semantic_md(semantics), encoding="utf-8")
    (evidence / "source-content-inventory.json").write_text(json.dumps(source_content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "source-registration-inventory.json").write_text(json.dumps(source_registrations, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ledger_path = out / "porting-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["source_manifest"] = {
        "identity": intake["input"],
        "detected_loaders": intake["detected"]["loaders"],
        "source_minecraft_version": intake.get("source_minecraft_version"),
        "inventory": intake["inventory"],
        "mapping_hints": intake.get("mapping_hints"),
        "intake_evidence": "devkit-evidence/port-intake.json",
        "mapping_plan_evidence": "devkit-evidence/mapping-plan.json",
        "mixin_audit_evidence": "devkit-evidence/mixin-audit.json",
        "semantic_port_plan_evidence": "devkit-evidence/semantic-port-plan.json",
        "content_identity_evidence": "devkit-evidence/source-content-inventory.json",
        "content_identity_count": source_content.get("entry_count", 0),
        "registration_identity_evidence": "devkit-evidence/source-registration-inventory.json",
        "registration_identity_count": source_registrations.get("entry_count", 0),
    }
    # Initialize coarse surfaces so the guard keeps the workspace honest until each source-owned surface is classified.
    items = []
    ignored = {"files", "mixins", "access_wideners", "access_transformers", "services", "datagen_markers"}
    for key, value in intake["inventory"].items():
        if key in ignored:
            continue
        count = value if isinstance(value, int) else len(value or [])
        if count:
            items.append({"id": f"surface:{key}", "source_count": count, "status": "missing", "target_evidence": None, "notes": "classify after porting this source surface"})
    for key in ["mixins", "access_wideners", "access_transformers", "services", "datagen_markers"]:
        value = intake["inventory"].get(key) or []
        if value:
            items.append({"id": f"surface:{key}", "source_count": len(value), "status": "missing", "target_evidence": None, "notes": "classify after porting this source surface"})
    for task in semantics.get("tasks") or []:
        items.append({
            "id": f"semantic:{task['id']}",
            "source_count": len(task.get("evidence") or []) or 1,
            "status": "missing",
            "target_evidence": None,
            "notes": task.get("replacement"),
            "required_qa": task.get("qa") or [],
        })
    # Content parity is mechanically checked by port_guard against the exact source identity inventory.
    # Keep exclusions explicit and evidence-backed rather than generating thousands of hand-maintained ledger rows.
    ledger.setdefault("content_exclusions", [])
    ledger.setdefault("registration_exclusions", [])
    ledger["items"] = items
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    result = {
        "status": "workspace-created",
        "source": intake["input"],
        "target": {"minecraft": "26.3", "loader": args.loader, "java": 25},
        "output": str(out),
        "initial_missing_surfaces": len(items),
        "source_content_identities": source_content.get("entry_count", 0),
        "source_registration_identities": source_registrations.get("entry_count", 0),
        "next": f"Port source behavior, classify porting-ledger.json, then run port_guard.py {out} --loader {args.loader}",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
