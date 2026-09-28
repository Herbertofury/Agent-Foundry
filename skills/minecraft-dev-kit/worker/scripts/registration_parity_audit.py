#!/usr/bin/env python3
"""Compare high-confidence code-registered content IDs between source and a 26.3 target source tree."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from registration_identity_inventory import inventory
from port_26_3_common import write_json


def audit(source_inventory: dict, target: Path, exclusions: list[dict] | None = None) -> dict:
    target_inventory = inventory(target)
    src = {(x["category"], x["id"]): x for x in source_inventory.get("entries") or []}
    dst = {(x["category"], x["id"]): x for x in target_inventory.get("entries") or []}
    excluded = {}
    for x in exclusions or []:
        if x.get("status") in {"intentionally_excluded", "superseded"} and x.get("reason"):
            excluded[(x.get("category"), x.get("id"))] = x
    missing, accepted = [], []
    for key, row in src.items():
        if key in dst:
            continue
        if key in excluded:
            accepted.append({"source": row, "exclusion": excluded[key]})
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
        "accepted_exclusions": accepted,
        "extras": extras,
        "counts": {"missing": len(missing), "accepted_exclusions": len(accepted), "extras": len(extras), "missing_categories": dict(Counter(x["category"] for x in missing))},
        "target_inventory": target_inventory,
        "rule": "High-confidence code-registered IDs may not disappear silently. Intentional removals/supersessions require explicit reason evidence.",
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
        exclusions = exclusions.get("registration_exclusions") or []
    result = audit(source, args.target, exclusions)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_missing and result["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())