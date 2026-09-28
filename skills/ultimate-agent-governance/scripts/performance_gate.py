#!/usr/bin/env python3
"""Compare baseline and candidate performance evidence without allowing scope shrinkage."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def compare(baseline: dict[str, Any], candidate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    results: dict[str, Any] = {}

    if policy.get("require_same_workload_identity", True):
        if baseline.get("workload_identity") != candidate.get("workload_identity"):
            errors.append("workload_identity differs; performance comparison is not equivalent")

    if policy.get("require_same_result_identity", True):
        if baseline.get("result_identity") != candidate.get("result_identity"):
            errors.append("result_identity differs; candidate may be doing different/less work")

    if baseline.get("scenario") != candidate.get("scenario"):
        errors.append("scenario differs between baseline and candidate")

    base_metrics = baseline.get("metrics")
    cand_metrics = candidate.get("metrics")
    metric_policy = policy.get("metrics")
    if not isinstance(base_metrics, dict) or not isinstance(cand_metrics, dict):
        errors.append("baseline and candidate must each contain a metrics object")
        base_metrics, cand_metrics = {}, {}
    if not isinstance(metric_policy, dict) or not metric_policy:
        errors.append("policy must contain at least one metric rule")
        metric_policy = {}

    any_improved = False
    required_improvement_metrics: list[str] = []

    for name, rule in metric_policy.items():
        if not isinstance(rule, dict):
            errors.append(f"metric policy {name!r} must be an object")
            continue
        if name not in base_metrics or name not in cand_metrics:
            errors.append(f"metric {name!r} missing from baseline or candidate")
            continue
        try:
            base = finite_number(base_metrics[name], f"baseline metric {name}")
            cand = finite_number(cand_metrics[name], f"candidate metric {name}")
        except ValueError as exc:
            errors.append(str(exc))
            continue

        direction = rule.get("direction", "lower")
        max_regression = finite_number(rule.get("max_regression_percent", 0), f"policy max_regression_percent for {name}")
        min_improvement = finite_number(rule.get("min_improvement_percent", 0), f"policy min_improvement_percent for {name}")
        required_improvement = bool(rule.get("required_improvement", False))
        if required_improvement:
            required_improvement_metrics.append(name)

        if base == 0:
            delta_pct = 0.0 if cand == 0 else math.inf
        else:
            raw = (cand - base) / abs(base) * 100.0
            delta_pct = raw if direction == "lower" else -raw

        # delta_pct > 0 means regression after normalizing direction; < 0 means improvement.
        improvement_pct = -delta_pct
        if improvement_pct > 0:
            any_improved = True
        passed = delta_pct <= max_regression and improvement_pct >= min_improvement
        if required_improvement and improvement_pct <= 0:
            passed = False
        results[name] = {
            "baseline": base,
            "candidate": cand,
            "direction": direction,
            "normalized_regression_percent": delta_pct,
            "max_regression_percent": max_regression,
            "min_improvement_percent": min_improvement,
            "required_improvement": required_improvement,
            "passed": passed,
        }
        if direction not in {"lower", "higher"}:
            errors.append(f"metric {name!r} has invalid direction {direction!r}")
        elif not passed:
            if required_improvement and improvement_pct <= 0:
                errors.append(f"metric {name!r} failed: this primary metric must improve, but it did not")
            else:
                errors.append(
                    f"metric {name!r} failed: normalized regression {delta_pct:.3f}% exceeds policy or improvement floor"
                )

    require_any = bool(policy.get("require_any_metric_improvement", True))
    if require_any and metric_policy and not any_improved:
        errors.append("no measured performance metric improved; preservation-only is not completion for a performance task")
    if required_improvement_metrics:
        for name in required_improvement_metrics:
            metric = results.get(name)
            if metric and not metric.get("passed") and not any(e.startswith(f"metric {name!r} failed") for e in errors):
                errors.append(f"metric {name!r} failed required improvement")

    return {"passed": not errors, "errors": errors, "metrics": results}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("policy", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    try:
        result = compare(load_json(args.baseline), load_json(args.candidate), load_json(args.policy))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, metric in result["metrics"].items():
            state = "PASS" if metric["passed"] else "FAIL"
            print(f"{state}: {name}: {metric['baseline']} -> {metric['candidate']} ({metric['normalized_regression_percent']:.3f}% normalized regression)")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        print("Performance gate:", "PASS" if result["passed"] else "FAIL")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
