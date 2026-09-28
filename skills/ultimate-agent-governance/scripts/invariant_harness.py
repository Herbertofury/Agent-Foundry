#!/usr/bin/env python3
"""Small deterministic harness for repository-declared invariant checks."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("manifest must be an object containing a cases array")
    return data


def run_case(root: Path, case: dict[str, Any]) -> tuple[bool, str]:
    cid = case.get("id", "unnamed")
    kind = case.get("type")
    if kind == "file_exists":
        path = root / str(case["path"])
        ok = path.exists()
        return ok, f"{cid}: {'exists' if ok else 'missing'} {case['path']}"

    if kind in {"file_contains", "file_not_contains"}:
        path = root / str(case["path"])
        if not path.is_file():
            return False, f"{cid}: missing file {case['path']}"
        text = path.read_text(encoding="utf-8", errors="ignore")
        pattern = str(case["pattern"])
        found = re.search(pattern, text, re.MULTILINE) is not None
        ok = found if kind == "file_contains" else not found
        return ok, f"{cid}: pattern {'matched' if found else 'did not match'}"

    if kind == "command":
        command = case.get("command")
        if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
            return False, f"{cid}: command must be an array of strings"
        expected = int(case.get("expected_exit", 0))
        proc = subprocess.run(command, cwd=root, text=True, capture_output=True)
        combined = proc.stdout + proc.stderr
        ok = proc.returncode == expected
        if "output_pattern" in case:
            ok = ok and re.search(str(case["output_pattern"]), combined, re.MULTILINE) is not None
        msg = f"{cid}: exit {proc.returncode}, expected {expected}"
        if not ok and combined.strip():
            msg += f"; output={combined.strip()[:1000]}"
        return ok, msg

    return False, f"{cid}: unsupported case type {kind!r}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    root = args.root.resolve()
    try:
        manifest = load(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    results = []
    for raw in manifest["cases"]:
        if not isinstance(raw, dict):
            results.append({"id": "invalid", "passed": False, "message": "case must be an object"})
            continue
        passed, message = run_case(root, raw)
        results.append({"id": raw.get("id", "unnamed"), "passed": passed, "message": message})

    passed_all = all(item["passed"] for item in results)
    if args.json:
        print(json.dumps({"passed": passed_all, "results": results}, indent=2))
    else:
        for item in results:
            print(("PASS" if item["passed"] else "FAIL") + ": " + item["message"])
        print("Invariant harness:", "PASS" if passed_all else "FAIL")
    return 0 if passed_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
