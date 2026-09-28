#!/usr/bin/env python3
"""Query and validate Zero Loss's embedded Stall Brain.

The bundled catalog is immutable at install time. This tool can search/diagnose it
and emit candidate incidents for a future skill-update working copy without
pretending the installed skill silently rewrote itself.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "stall-patterns.json"
REQUIRED = {"id", "slug", "scope", "failure", "required_behavior", "signals", "status"}


def load_catalog(path: Path = CATALOG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError("catalog must be an object with a rules array")
    return data


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    rules = data.get("rules", [])
    if len(rules) < 40:
        errors.append(f"expected at least 40 active learned patterns, found {len(rules)}")
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rule[{idx}] is not an object")
            continue
        missing = REQUIRED - set(rule)
        if missing:
            errors.append(f"rule[{idx}] missing: {', '.join(sorted(missing))}")
        rid = str(rule.get("id", ""))
        slug = str(rule.get("slug", ""))
        if not re.fullmatch(r"SB-\d{3}", rid):
            errors.append(f"rule[{idx}] invalid id {rid!r}")
        if rid in seen_ids:
            errors.append(f"duplicate id {rid}")
        if slug in seen_slugs:
            errors.append(f"duplicate slug {slug}")
        seen_ids.add(rid)
        seen_slugs.add(slug)
        signals = rule.get("signals")
        if not isinstance(signals, list) or not signals:
            errors.append(f"{rid or idx} must have non-empty signals")
        if rule.get("status") != "active":
            errors.append(f"{rid or idx} is not active")
    return errors


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def score(rule: dict[str, Any], query: str) -> int:
    q = tokenize(query)
    fields = " ".join([
        str(rule.get("slug", "")), str(rule.get("scope", "")),
        str(rule.get("failure", "")), str(rule.get("required_behavior", "")),
        " ".join(map(str, rule.get("signals", []))),
    ])
    words = tokenize(fields)
    score = len(q & words) * 4
    low = fields.lower()
    for signal in rule.get("signals", []):
        if str(signal).lower() in query.lower():
            score += 8
    if str(rule.get("slug", "")).replace("-", " ") in query.lower():
        score += 10
    return score


def matches(data: dict[str, Any], query: str, limit: int) -> list[tuple[int, dict[str, Any]]]:
    ranked = sorted(((score(r, query), r) for r in data["rules"]), key=lambda x: (-x[0], x[1]["id"]))
    return [(s, r) for s, r in ranked if s > 0][:limit]


def print_rule(rule: dict[str, Any], rank: int | None = None) -> None:
    prefix = f"score={rank} " if rank is not None else ""
    print(f"{prefix}{rule['id']} {rule['slug']} [{rule['scope']}]")
    print(f"  failure: {rule['failure']}")
    print(f"  do: {rule['required_behavior']}")
    print(f"  signals: {', '.join(rule['signals'])}")


def write_candidate(args: argparse.Namespace) -> None:
    item = {
        "schema_version": 1,
        "status": "candidate",
        "scope": args.scope,
        "symptom": args.symptom,
        "observed_failure": args.observed,
        "root_cause": args.cause,
        "required_replacement": args.replacement,
        "evidence": args.evidence,
        "promotion_basis": args.basis,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=True) + "\n")
    print(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    p_list = sub.add_parser("list")
    p_list.add_argument("--scope")
    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=8)
    p_diag = sub.add_parser("diagnose")
    p_diag.add_argument("symptom")
    p_diag.add_argument("--limit", type=int, default=5)
    p_new = sub.add_parser("new-incident")
    p_new.add_argument("--output", required=True)
    p_new.add_argument("--scope", required=True)
    p_new.add_argument("--symptom", required=True)
    p_new.add_argument("--observed", required=True)
    p_new.add_argument("--cause", default="unknown")
    p_new.add_argument("--replacement", required=True)
    p_new.add_argument("--evidence", action="append", default=[])
    p_new.add_argument("--basis", choices=["explicit-user-correction", "objective-reproduction", "repeated-independent-failure", "authoritative-spec-plus-observation"], required=True)
    args = ap.parse_args()

    if args.cmd == "new-incident":
        write_candidate(args)
        return 0

    data = load_catalog()
    errors = validate(data)
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        return 1

    if args.cmd == "validate":
        print(f"PASS stall brain: {len(data['rules'])} active patterns")
        return 0
    if args.cmd == "list":
        rules = [r for r in data["rules"] if not args.scope or r["scope"] == args.scope]
        for r in rules:
            print_rule(r)
        return 0
    query = args.query if args.cmd == "search" else args.symptom
    found = matches(data, query, args.limit)
    if not found:
        print("No matching embedded stall pattern.")
        return 3
    for s, r in found:
        print_rule(r, s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
