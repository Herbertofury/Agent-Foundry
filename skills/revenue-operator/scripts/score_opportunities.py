#!/usr/bin/env python3
"""Rank revenue opportunities from a JSON file or stdin.

Input: a JSON array of objects. Each object may contain 0-10 numeric fields:
revenue_potential, time_to_cash, demand_evidence, skill_fit, autonomy,
repeatability, capital_efficiency, competition_advantage, confidence,
setup_burden, platform_dependency, identity_payment_blocker, uncertainty.

Output: the same objects sorted by score descending with `score` added.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

POSITIVE_WEIGHTS = {
    "revenue_potential": 1.55,
    "time_to_cash": 1.45,
    "demand_evidence": 1.40,
    "skill_fit": 1.25,
    "autonomy": 1.30,
    "repeatability": 1.00,
    "capital_efficiency": 0.85,
    "competition_advantage": 0.75,
    "confidence": 1.00,
}

PENALTY_WEIGHTS = {
    "setup_burden": 0.95,
    "platform_dependency": 0.55,
    "identity_payment_blocker": 0.80,
    "uncertainty": 1.15,
}


def clamp_0_10(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(10.0, max(0.0, numeric))


def score(item: dict[str, Any]) -> float:
    positive = sum(clamp_0_10(item.get(k, 0)) * w for k, w in POSITIVE_WEIGHTS.items())
    penalty = sum(clamp_0_10(item.get(k, 0)) * w for k, w in PENALTY_WEIGHTS.items())

    max_positive = 10.0 * sum(POSITIVE_WEIGHTS.values())
    max_penalty = 10.0 * sum(PENALTY_WEIGHTS.values())

    # Positive factors dominate, while penalties can reduce but not invert the score.
    normalized_positive = positive / max_positive
    normalized_penalty = penalty / max_penalty
    raw = 100.0 * (0.86 * normalized_positive - 0.36 * normalized_penalty + 0.18)
    return round(min(100.0, max(0.0, raw)), 2)


def load_input(path: str | None) -> list[dict[str, Any]]:
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise ValueError("Input must be a JSON array of objects")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and rank revenue opportunities")
    parser.add_argument("input", nargs="?", help="JSON input file; omit to read stdin")
    parser.add_argument("-o", "--output", help="Write ranked JSON to this file")
    args = parser.parse_args()

    try:
        items = load_input(args.input)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    ranked = []
    for original in items:
        item = dict(original)
        item["score"] = score(item)
        ranked.append(item)
    ranked.sort(key=lambda x: x["score"], reverse=True)

    rendered = json.dumps(ranked, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
