#!/usr/bin/env python3
"""Prewarm authoritative historical mapping evidence used to migrate mods into unobfuscated Minecraft 26.3.

The cache is checksum-addressed evidence, not a target mapping layer. Minecraft 26.3 itself uses
official/unobfuscated names. Legacy MCP named mappings are never guessed; pass an exact source
mapping hint for those projects when available.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mapping_lineage import harvest, source_plan

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ROOT / "references" / "minecraft-mapping-prewarm-profiles.json"


def parse_profile(value: str) -> dict:
    parts = value.split(":", 2)
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("profile must be <minecraft>:<loader>[:<mapping-hint>]")
    result = {"minecraft": parts[0], "loader": parts[1]}
    if len(parts) == 3 and parts[2]:
        result["mapping_hint"] = parts[2]
    return result


def load_defaults(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["profiles"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, default=DEFAULTS, help="JSON profile catalog")
    ap.add_argument("--profile", action="append", type=parse_profile, default=[], help="extra <mc>:<loader>[:mapping-hint]")
    ap.add_argument("--only-explicit", action="store_true", help="do not include the default common-lineage profiles")
    ap.add_argument("--plan-only", action="store_true", help="write plans without network downloads")
    ap.add_argument("--manifest", type=Path, help="output manifest; defaults under cache")
    args = ap.parse_args()

    profiles = ([] if args.only_explicit else load_defaults(args.profiles)) + args.profile
    args.cache.mkdir(parents=True, exist_ok=True)
    results = []
    failed = False
    for profile in profiles:
        mc = str(profile["minecraft"])
        loader = str(profile["loader"])
        hint = profile.get("mapping_hint")
        plan = source_plan(mc, loader, hint)
        row = {"profile": profile, "plan": plan}
        if args.plan_only or plan["source"]["unobfuscated"]:
            row["status"] = "IDENTITY" if plan["source"]["unobfuscated"] else "PLANNED"
        else:
            try:
                fetched = harvest(mc, loader, args.cache, hint)
                row["harvest"] = fetched
                row["status"] = "CACHED" if fetched.get("complete") else "INCOMPLETE"
                failed |= not fetched.get("complete", False)
            except Exception as exc:
                row["status"] = "FETCH_FAILED"
                row["error"] = f"{type(exc).__name__}: {exc}"
                failed = True
        results.append(row)

    manifest = {
        "schema_version": 1,
        "target": {"minecraft": "26.3", "namespace": "official", "obfuscated": False},
        "cache": str(args.cache.resolve()),
        "plan_only": args.plan_only,
        "profiles": results,
        "complete": not failed,
        "note": "Historical mappings are migration evidence. 26.3 target names remain official/unobfuscated. Legacy MCP named mappings require exact source declarations and are never guessed."
    }
    out = args.manifest or args.cache / "mapping-prewarm-manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if not failed else "INCOMPLETE", "manifest": str(out), "profiles": len(results)}, indent=2))
    return 0 if not failed else 4


if __name__ == "__main__":
    raise SystemExit(main())
