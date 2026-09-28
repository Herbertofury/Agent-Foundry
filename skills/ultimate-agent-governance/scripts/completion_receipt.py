#!/usr/bin/env python3
"""Create and validate completion receipts for substantial agent work."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED = {"pass", "blocked", "not_applicable"}


def template(task: str) -> dict[str, Any]:
    return {
        "task": task,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "in_progress",
        "requirements": [],
        "runtime_proof": {
            "required": False,
            "artifact_identity": "",
            "launch_identity": "",
            "workflow_exercised": "",
            "observed_result": "",
            "diagnostics": [],
            "status": "not_applicable"
        },
        "performance_proof": {
            "required": False,
            "baseline": "",
            "candidate": "",
            "policy": "",
            "gate_result": "",
            "status": "not_applicable"
        },
        "modernization_proof": {
            "freshness_scope": "",
            "current_baseline": "",
            "selected_baseline": "",
            "comparison_evidence": "",
            "mixed_upgrade_resolution": "",
            "fix_forward_or_integration": "",
            "observed_result": "",
            "status": "blocked"
        },
        "external_completeness_proof": {
            "required": False,
            "evidence": "",
            "gate_result": "",
            "status": "not_applicable"
        },
        "failure_learning_proof": {
            "required": False,
            "incident_fingerprint": "",
            "recovery_record": "",
            "verification": "",
            "regression_or_shared_fix": "",
            "status": "not_applicable"
        },
        "tests": [],
        "blockers": [],
        "next_action": ""
    }


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not nonempty(data.get("task")):
        errors.append("task must be a non-empty string")
    overall = data.get("overall_status")
    if overall not in {"pass", "in_progress"}:
        errors.append("overall_status must be 'pass' or 'in_progress'")

    reqs = data.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        errors.append("requirements must contain at least one acceptance item")
        reqs = []
    for i, item in enumerate(reqs):
        prefix = f"requirements[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("requirement", "implementation", "verification", "observed_result"):
            if not nonempty(item.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if item.get("status") not in ALLOWED:
            errors.append(f"{prefix}.status must be one of {sorted(ALLOWED)}")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be an array")
        blockers = []
    for i, blocker in enumerate(blockers):
        if not isinstance(blocker, dict) or not nonempty(blocker.get("acceptance_item")) or not nonempty(blocker.get("reason")):
            errors.append(f"blockers[{i}] must contain non-empty acceptance_item and reason")

    modernization = data.get("modernization_proof")
    if not isinstance(modernization, dict):
        errors.append("modernization_proof must be an object")
    else:
        if modernization.get("status") not in {"pass", "blocked"}:
            errors.append("modernization_proof.status must be 'pass' or 'blocked'")
        if modernization.get("status") == "pass":
            for field in ("freshness_scope", "current_baseline", "selected_baseline", "comparison_evidence", "mixed_upgrade_resolution", "fix_forward_or_integration", "observed_result"):
                if not nonempty(modernization.get(field)):
                    errors.append(f"modernization_proof.{field} is required when modernization proof passes")

    for key, fields in {
        "external_completeness_proof": ("evidence", "gate_result"),
        "failure_learning_proof": ("incident_fingerprint", "recovery_record", "verification", "regression_or_shared_fix"),
    }.items():
        proof = data.get(key)
        if not isinstance(proof, dict):
            errors.append(f"{key} must be an object")
            continue
        required = proof.get("required")
        if not isinstance(required, bool):
            errors.append(f"{key}.required must be boolean")
            continue
        status = proof.get("status")
        if status not in ALLOWED:
            errors.append(f"{key}.status must be one of {sorted(ALLOWED)}")
        if required and status == "not_applicable":
            errors.append(f"{key} is required but marked not_applicable")
        if required and status == "pass":
            for field in fields:
                if not nonempty(proof.get(field)):
                    errors.append(f"{key}.{field} is required when proof passes")

    for key in ("runtime_proof", "performance_proof"):
        proof = data.get(key)
        if not isinstance(proof, dict):
            errors.append(f"{key} must be an object")
            continue
        required = proof.get("required")
        if not isinstance(required, bool):
            errors.append(f"{key}.required must be boolean")
            continue
        status = proof.get("status")
        if status not in ALLOWED:
            errors.append(f"{key}.status must be one of {sorted(ALLOWED)}")
        if required and status == "not_applicable":
            errors.append(f"{key} is required but marked not_applicable")
        if required and status == "pass":
            if key == "runtime_proof":
                for field in ("artifact_identity", "launch_identity", "workflow_exercised", "observed_result"):
                    if not nonempty(proof.get(field)):
                        errors.append(f"runtime_proof.{field} is required when runtime proof passes")
            else:
                for field in ("baseline", "candidate", "policy", "gate_result"):
                    if not nonempty(proof.get(field)):
                        errors.append(f"performance_proof.{field} is required when performance proof passes")

    if overall == "pass":
        bad_reqs = [i for i, item in enumerate(reqs) if isinstance(item, dict) and item.get("status") != "pass"]
        if bad_reqs:
            errors.append(f"overall_status is pass but requirements are not all pass: {bad_reqs}")
        if blockers:
            errors.append("overall_status is pass but blockers are present")
        for key in ("runtime_proof", "performance_proof", "external_completeness_proof", "failure_learning_proof"):
            proof = data.get(key, {})
            if isinstance(proof, dict) and proof.get("required") and proof.get("status") != "pass":
                errors.append(f"overall_status is pass but required {key} did not pass")
        modernization = data.get("modernization_proof", {})
        if not isinstance(modernization, dict) or modernization.get("status") != "pass":
            errors.append("overall_status is pass but modernization_proof did not pass")

    if overall == "in_progress":
        if not nonempty(data.get("next_action")):
            errors.append("overall_status is in_progress but next_action is empty")
        errors.append("receipt is still in_progress; completion validation requires overall_status pass")

    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("path", type=Path)
    init.add_argument("--task", required=True)
    val = sub.add_parser("validate")
    val.add_argument("path", type=Path)
    val.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.cmd == "init":
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_text(json.dumps(template(args.task), indent=2) + "\n", encoding="utf-8")
        print(args.path)
        return 0

    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("receipt root must be an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if args.json:
        print(json.dumps({"passed": not errors, "errors": errors}, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}")
        print("Completion receipt:", "PASS" if not errors else "FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
