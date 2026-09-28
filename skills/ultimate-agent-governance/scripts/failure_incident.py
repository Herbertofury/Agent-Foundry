#!/usr/bin/env python3
"""Validate, record, and look up reusable verified failure-recovery incidents."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "incident_id", "fingerprint", "signature", "scope", "environment",
        "root_cause", "successful_route", "verification", "regression_or_shared_fix",
    ]
    for field in required:
        if not nonempty(data.get(field)):
            errors.append(f"{field} must be a non-empty string")
    if data.get("status") != "resolved":
        errors.append("status must be 'resolved' before reusable promotion")
    if data.get("sanitized") is not True:
        errors.append("sanitized must be true")
    for field in ("failed_routes", "recovery_recipe", "invalidation_conditions"):
        value = data.get(field)
        if not isinstance(value, list) or not value or not all(nonempty(x) for x in value):
            errors.append(f"{field} must be a non-empty array of non-empty strings")
    return errors


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("incident root must be an object")
    return data


def iter_ledger(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            yield item


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    val = sub.add_parser("validate")
    val.add_argument("incident", type=Path)
    val.add_argument("--json", action="store_true")
    rec = sub.add_parser("record")
    rec.add_argument("ledger", type=Path)
    rec.add_argument("incident", type=Path)
    look = sub.add_parser("lookup")
    look.add_argument("ledger", type=Path)
    look.add_argument("--fingerprint", required=True)
    args = ap.parse_args()

    if args.cmd in {"validate", "record"}:
        try:
            data = load_json(args.incident)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        errors = validate(data)
        if args.cmd == "validate":
            if args.json:
                print(json.dumps({"passed": not errors, "errors": errors}, indent=2))
            else:
                for error in errors:
                    print(f"ERROR: {error}")
                print("Failure incident:", "PASS" if not errors else "FAIL")
            return 0 if not errors else 1
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        data["recorded_at"] = datetime.now(timezone.utc).isoformat()
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        with args.ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(data, sort_keys=True) + "\n")
        print(f"Recorded {data['fingerprint']} -> {args.ledger}")
        return 0

    matches = [x for x in iter_ledger(args.ledger) if x.get("fingerprint") == args.fingerprint]
    if not matches:
        print("NOT_FOUND")
        return 1
    print(json.dumps(matches[-1], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
