#!/usr/bin/env python3
"""Validate evidence for complete/exhaustive external-data claims."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def nonneg_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not nonempty(data.get("scope")):
        errors.append("scope must be a non-empty string")
    claim = data.get("claim")
    if claim not in {"complete", "partial"}:
        errors.append("claim must be 'complete' or 'partial'")

    expected = data.get("expected_count")
    if expected is not None and not nonneg_int(expected):
        errors.append("expected_count must be null or a non-negative integer")

    keys = ["discovered_count", "accepted_count", "rejected_count", "unresolved_count"]
    for key in keys:
        if not nonneg_int(data.get(key)):
            errors.append(f"{key} must be a non-negative integer")
    if not errors:
        discovered = data["discovered_count"]
        accounted = data["accepted_count"] + data["rejected_count"] + data["unresolved_count"]
        if accounted != discovered:
            errors.append(
                f"count reconciliation failed: accepted+rejected+unresolved={accounted}, discovered={discovered}"
            )
        if expected is not None and discovered != expected:
            errors.append(f"expected_count={expected} but discovered_count={discovered}")
        if data["rejected_count"] and not data.get("rejection_reasons"):
            errors.append("rejection_reasons are required when rejected_count > 0")

    pagination = data.get("pagination")
    if not isinstance(pagination, dict):
        errors.append("pagination must be an object")
    else:
        if not isinstance(pagination.get("terminal_proven"), bool):
            errors.append("pagination.terminal_proven must be boolean")
        if not nonneg_int(pagination.get("pages_visited")):
            errors.append("pagination.pages_visited must be a non-negative integer")
        exp_pages = pagination.get("expected_pages")
        if exp_pages is not None and not nonneg_int(exp_pages):
            errors.append("pagination.expected_pages must be null or a non-negative integer")
        if nonneg_int(exp_pages) and nonneg_int(pagination.get("pages_visited")):
            if pagination["pages_visited"] != exp_pages:
                errors.append(
                    f"pagination expected_pages={exp_pages} but pages_visited={pagination['pages_visited']}"
                )

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("surfaces must contain at least one coverage surface")
        surfaces = []
    for i, item in enumerate(surfaces):
        if not isinstance(item, dict):
            errors.append(f"surfaces[{i}] must be an object")
            continue
        if not nonempty(item.get("name")):
            errors.append(f"surfaces[{i}].name must be non-empty")
        if item.get("status") not in {"pass", "not_applicable"}:
            errors.append(f"surfaces[{i}].status must be pass or not_applicable")
        if item.get("status") == "pass" and not nonempty(item.get("evidence")):
            errors.append(f"surfaces[{i}].evidence is required when status=pass")

    if claim == "complete":
        if isinstance(data.get("unresolved_count"), int) and data.get("unresolved_count") != 0:
            errors.append("complete claim requires unresolved_count == 0")
        if isinstance(pagination, dict) and pagination.get("terminal_proven") is not True:
            errors.append("complete claim requires terminal pagination/coverage proof")
        bad = [i for i, item in enumerate(surfaces) if isinstance(item, dict) and item.get("status") not in {"pass", "not_applicable"}]
        if bad:
            errors.append(f"complete claim has unresolved coverage surfaces: {bad}")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evidence", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("evidence root must be an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if args.json:
        print(json.dumps({"passed": not errors, "errors": errors}, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}")
        print("Completeness gate:", "PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
