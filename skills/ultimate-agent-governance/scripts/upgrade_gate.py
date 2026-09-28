#!/usr/bin/env python3
"""Decide whether an upgrade candidate earned promotion without protected regressions."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return data


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be numeric')
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f'{label} must be finite')
    return value


def compare(baseline: dict[str, Any], candidate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    metrics_out: dict[str, Any] = {}
    improvements: list[str] = []
    regressions: list[str] = []

    identity_fields = policy.get('identity_fields', ['scenario', 'workload_identity', 'result_identity', 'capability_identity'])
    if not isinstance(identity_fields, list) or not all(isinstance(x, str) for x in identity_fields):
        raise ValueError('policy.identity_fields must be an array of strings')
    for field in identity_fields:
        if baseline.get(field) != candidate.get(field):
            errors.append(f'{field} differs; upgrade comparison is not equivalent')

    base_metrics = baseline.get('metrics')
    cand_metrics = candidate.get('metrics')
    rules = policy.get('metrics')
    if not isinstance(base_metrics, dict) or not isinstance(cand_metrics, dict):
        errors.append('baseline and candidate must each contain a metrics object')
        base_metrics, cand_metrics = {}, {}
    if not isinstance(rules, dict) or not rules:
        errors.append('policy must contain at least one metric rule')
        rules = {}

    for name, rule in rules.items():
        if not isinstance(rule, dict):
            errors.append(f'metric policy {name!r} must be an object')
            continue
        if name not in base_metrics or name not in cand_metrics:
            errors.append(f'metric {name!r} missing from baseline or candidate')
            continue
        base = finite_number(base_metrics[name], f'baseline metric {name}')
        cand = finite_number(cand_metrics[name], f'candidate metric {name}')
        direction = rule.get('direction', 'lower')
        if direction not in {'lower', 'higher'}:
            errors.append(f'metric {name!r} has invalid direction {direction!r}')
            continue
        protected = bool(rule.get('protected', True))
        required_improvement = bool(rule.get('required_improvement', False))
        max_regression = finite_number(rule.get('max_regression_percent', 0), f'policy max_regression_percent for {name}')
        min_improvement = finite_number(rule.get('min_improvement_percent', 0), f'policy min_improvement_percent for {name}')

        if base == 0:
            normalized_regression = 0.0 if cand == 0 else (math.inf if direction == 'lower' else -math.inf)
        else:
            raw = (cand - base) / abs(base) * 100.0
            normalized_regression = raw if direction == 'lower' else -raw
        improvement = -normalized_regression

        if improvement > 0:
            improvements.append(name)
        if normalized_regression > max_regression:
            regressions.append(name)

        passed = True
        if protected and normalized_regression > max_regression:
            passed = False
            errors.append(f'metric {name!r} regressed {normalized_regression:.3f}% beyond allowed {max_regression:.3f}%')
        if required_improvement and improvement < min_improvement:
            passed = False
            errors.append(f'metric {name!r} improved {improvement:.3f}% but requires at least {min_improvement:.3f}%')
        elif required_improvement and improvement <= 0:
            passed = False
            errors.append(f'metric {name!r} is a required improvement dimension but did not improve')

        metrics_out[name] = {
            'baseline': base,
            'candidate': cand,
            'direction': direction,
            'protected': protected,
            'required_improvement': required_improvement,
            'improvement_percent': improvement,
            'normalized_regression_percent': normalized_regression,
            'max_regression_percent': max_regression,
            'min_improvement_percent': min_improvement,
            'passed': passed,
        }

    require_any = bool(policy.get('require_any_material_improvement', True))
    min_material = finite_number(policy.get('min_any_improvement_percent', 0), 'policy min_any_improvement_percent')
    material = [name for name in improvements if metrics_out.get(name, {}).get('improvement_percent', 0) > min_material]
    if require_any and not material:
        errors.append('candidate has no material measured improvement; newer alone does not earn promotion')

    mixed = bool(improvements and regressions)
    if mixed:
        errors.append('mixed upgrade candidate: improvements and protected regressions coexist; decompose/bisect, keep the useful gains, repair or replace regressive internals, then retest')

    return {
        'passed': not errors,
        'mixed_upgrade': mixed,
        'material_improvements': material,
        'regressions': regressions,
        'errors': errors,
        'metrics': metrics_out,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('policy', type=Path)
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    try:
        result = compare(load_json(args.baseline), load_json(args.candidate), load_json(args.policy))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, metric in result['metrics'].items():
            state = 'PASS' if metric['passed'] else 'FAIL'
            print(f"{state}: {name}: {metric['baseline']} -> {metric['candidate']} ({metric['improvement_percent']:.3f}% improvement)")
        if result['mixed_upgrade']:
            print('MIXED: candidate contains both gains and protected regressions; decomposition required')
        for error in result['errors']:
            print(f'ERROR: {error}')
        print('Upgrade promotion gate:', 'PASS' if result['passed'] else 'FAIL')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
