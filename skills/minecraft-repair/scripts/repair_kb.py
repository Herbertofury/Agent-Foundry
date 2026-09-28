#!/usr/bin/env python3
"""Maintain a JSONL Minecraft repair history file."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSONL at line {n}: {e}") from e
    return rows


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def normalize_tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_.$/@:+-]{3,}", text)}


def searchable(row: dict) -> str:
    fields = [
        row.get("id", ""), row.get("minecraft", ""), row.get("root_cause", ""), row.get("outcome", "")
    ]
    loader = row.get("loader") or {}
    if isinstance(loader, dict):
        fields += [str(loader.get("name", "")), str(loader.get("version", ""))]
    for key in ("symptoms", "signatures", "applicability", "anti_patterns"):
        value = row.get(key, [])
        if isinstance(value, list):
            fields.extend(map(str, value))
    for mod in row.get("mods", []) or []:
        if isinstance(mod, dict):
            fields.extend(str(mod.get(k, "")) for k in ("id", "version", "filename"))
    repair = row.get("repair") or {}
    if isinstance(repair, dict):
        fields.append(str(repair.get("type", "")))
        changes = repair.get("changes", [])
        if isinstance(changes, list):
            fields.extend(map(str, changes))
    return "\n".join(fields)


def score(row: dict, query: str) -> int:
    hay = searchable(row).lower()
    q = query.lower().strip()
    if not q:
        return 0
    s = 0
    if q in hay:
        s += 100
    q_tokens = normalize_tokens(q)
    h_tokens = normalize_tokens(hay)
    s += 8 * len(q_tokens & h_tokens)
    # Exact technical signatures get extra weight.
    for token in q_tokens:
        if any(x in token for x in ("exception", "error", "/", ".", "@")) and token in hay:
            s += 10
    outcome = row.get("outcome")
    if outcome == "success":
        s += 4
    elif outcome == "failed":
        s -= 2
    return s


def cmd_init(args) -> int:
    path: Path = args.path
    rows = load(path)
    existing = {r.get("id") for r in rows}
    if args.seed:
        for r in load(args.seed):
            if r.get("id") not in existing:
                rows.append(r)
                existing.add(r.get("id"))
    save(path, rows)
    print(json.dumps({"path": str(path), "records": len(rows)}))
    return 0


def read_record_arg(args) -> dict:
    if args.record_file:
        return json.loads(args.record_file.read_text(encoding="utf-8"))
    if args.record_json:
        return json.loads(args.record_json)
    return json.load(sys.stdin)


def cmd_add(args) -> int:
    rows = load(args.path)
    rec = read_record_arg(args)
    if not rec.get("id"):
        raise ValueError("record must contain id")
    stamp = now_iso()
    rec.setdefault("schema_version", 1)
    rec.setdefault("recorded_at", stamp)
    rec["updated_at"] = stamp
    existing = {r.get("id"): i for i, r in enumerate(rows)}
    if rec["id"] in existing:
        if not args.upsert:
            raise ValueError(f"record id already exists: {rec['id']}")
        old = rows[existing[rec["id"]]]
        rec.setdefault("recorded_at", old.get("recorded_at", stamp))
        rows[existing[rec["id"]]] = rec
        action = "updated"
    else:
        rows.append(rec)
        action = "added"
    save(args.path, rows)
    print(json.dumps({"action": action, "id": rec["id"], "records": len(rows)}))
    return 0


def cmd_search(args) -> int:
    rows = load(args.path)
    ranked = []
    for row in rows:
        sc = score(row, args.query)
        if sc > 0:
            ranked.append((sc, row))
    ranked.sort(key=lambda x: (-x[0], str(x[1].get("updated_at", "")), str(x[1].get("id", ""))))
    result = [{"score": sc, "record": row} for sc, row in ranked[:args.limit]]
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


def cmd_mark(args) -> int:
    rows = load(args.path)
    found = False
    for row in rows:
        if row.get("id") == args.id:
            row["outcome"] = args.outcome
            row["updated_at"] = now_iso()
            verification = row.setdefault("verification", {})
            if args.note:
                notes = verification.setdefault("runtime", [])
                if args.note not in notes:
                    notes.append(args.note)
            if args.user_feedback:
                verification["user_feedback"] = args.user_feedback
            found = True
            break
    if not found:
        raise ValueError(f"record not found: {args.id}")
    save(args.path, rows)
    print(json.dumps({"id": args.id, "outcome": args.outcome}))
    return 0


def cmd_supersede(args) -> int:
    rows = load(args.path)
    by_id = {r.get("id"): r for r in rows}
    if args.old not in by_id or args.new not in by_id:
        raise ValueError("both --old and --new IDs must exist")
    old = by_id[args.old]
    new = by_id[args.new]
    old["outcome"] = "superseded"
    old["superseded_by"] = args.new
    old["updated_at"] = now_iso()
    sup = new.setdefault("supersedes", [])
    if args.old not in sup:
        sup.append(args.old)
    new["updated_at"] = now_iso()
    save(args.path, rows)
    print(json.dumps({"superseded": args.old, "by": args.new}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--path", type=Path, required=True)
    p.add_argument("--seed", type=Path)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add")
    p.add_argument("--path", type=Path, required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--record-file", type=Path)
    g.add_argument("--record-json")
    p.add_argument("--upsert", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("search")
    p.add_argument("--path", type=Path, required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--pretty", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("mark")
    p.add_argument("--path", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--outcome", choices=["success", "partial", "failed", "superseded"], required=True)
    p.add_argument("--note")
    p.add_argument("--user-feedback")
    p.set_defaults(func=cmd_mark)

    p = sub.add_parser("supersede")
    p.add_argument("--path", type=Path, required=True)
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.set_defaults(func=cmd_supersede)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
