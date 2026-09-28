#!/usr/bin/env python3
"""Validate a challenger/integration discovery receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED = {"adopt", "merge", "port", "wrap", "backport", "compose", "reject", "unresolved"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("receipt", type=Path)
    args = ap.parse_args()
    data = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors: list[str] = []

    if not str(data.get("scope", "")).strip():
        errors.append("missing non-empty scope")
    sources = data.get("searched_sources")
    if not isinstance(sources, list) or not any(str(x).strip() for x in sources):
        errors.append("searched_sources must contain at least one source family")
    if data.get("coverage_complete") is not True:
        errors.append("coverage_complete must be true before challenger closeout")
    if data.get("implementation_ready") is not True:
        errors.append("implementation_ready must be true before closeout")
    if not str(data.get("decision", "")).strip():
        errors.append("missing non-empty decision")

    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be a list")
        candidates = []
    if not candidates and not str(data.get("no_candidate_evidence", "")).strip():
        errors.append("no candidates recorded; provide no_candidate_evidence if the bounded scan found none")

    for i, c in enumerate(candidates):
        if not isinstance(c, dict):
            errors.append(f"candidate[{i}] must be an object")
            continue
        for key in ("name", "source", "disposition", "reason", "permission"):
            if not str(c.get(key, "")).strip():
                errors.append(f"candidate[{i}] missing {key}")
        disp = str(c.get("disposition", "")).strip().lower()
        if disp and disp not in ALLOWED:
            errors.append(f"candidate[{i}] invalid disposition: {disp}")
        ev = c.get("evidence")
        if disp != "unresolved" and (not isinstance(ev, list) or not any(str(x).strip() for x in ev)):
            errors.append(f"candidate[{i}] needs evidence for disposition {disp or '<missing>'}")

    unresolved = [c for c in candidates if isinstance(c, dict) and str(c.get("disposition", "")).lower() == "unresolved"]
    if unresolved and not str(data.get("unresolved_plan", "")).strip():
        errors.append("unresolved candidates require unresolved_plan")

    if errors:
        for e in errors:
            print(f"FAIL {e}")
        return 1
    print(f"PASS challenger receipt: {len(candidates)} candidates across {len(sources)} source families")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
