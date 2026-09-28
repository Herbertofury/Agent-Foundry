#!/usr/bin/env python3
"""Compare a source content identity inventory with a 26.3 target and block unexplained loss."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from content_identity_inventory import inventory
from port_26_3_common import write_json


def _key(row: dict) -> tuple:
    # Translation values may legitimately change; locale + key identity is what parity cares about.
    return (row.get("category"), row.get("subtype"), row.get("id"))


def audit(source_inventory: dict, target: Path, exclusions: list[dict] | None = None) -> dict:
    target_inventory = inventory(target)
    src = {_key(x): x for x in source_inventory.get("entries") or []}
    dst = {_key(x): x for x in target_inventory.get("entries") or []}
    exclusion_map = {}
    for x in exclusions or []:
        if x.get("status") not in {"intentionally_excluded", "superseded"}:
            continue
        exclusion_map[(x.get("category"), x.get("subtype"), x.get("id"))] = x
    missing = []
    accepted_exclusions = []
    for key, row in src.items():
        if key in dst:
            continue
        if key in exclusion_map and exclusion_map[key].get("reason"):
            accepted_exclusions.append({"source": row, "exclusion": exclusion_map[key]})
        else:
            missing.append(row)
    extras = [row for key, row in dst.items() if key not in src]
    return {
        "schema_version": 1,
        "source": source_inventory.get("input"),
        "target": str(target.resolve()),
        "status": "FAIL" if missing else "PASS",
        "source_count": len(src),
        "target_count": len(dst),
        "missing": missing,
        "accepted_exclusions": accepted_exclusions,
        "extras": extras,
        "counts": {"missing": len(missing), "accepted_exclusions": len(accepted_exclusions), "extras": len(extras), "missing_categories": dict(Counter(x["category"] for x in missing))},
        "target_inventory": target_inventory,
        "rule": "Missing source content blocks release unless the target contains the same canonical identity or the ledger records an evidence-backed intentional exclusion/supersession. Extras are allowed and reported.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_inventory", type=Path)
    ap.add_argument("target", type=Path)
    ap.add_argument("--exclusions", type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--fail-on-missing", action="store_true")
    args = ap.parse_args()
    source = json.loads(args.source_inventory.read_text(encoding="utf-8"))
    exclusions = json.loads(args.exclusions.read_text(encoding="utf-8")) if args.exclusions else []
    if isinstance(exclusions, dict):
        exclusions = exclusions.get("content_exclusions") or []
    result = audit(source, args.target, exclusions)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_missing and result["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())