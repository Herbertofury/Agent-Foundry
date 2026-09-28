#!/usr/bin/env python3
"""Record, search, revalidate, supersede, and summarize project research memory."""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def memory_path(root: Path) -> Path:
    return root.expanduser().resolve() / ".agents-memory" / "research.jsonl"


def project_id(root: Path) -> str:
    marker = root.expanduser().resolve() / ".agents-memory" / "PROJECT.json"
    if not marker.is_file():
        raise FileNotFoundError(f"Project memory is not initialized: {marker}")
    return json.loads(marker.read_text(encoding="utf-8"))["project_id"]


def append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def events(root: Path) -> list[dict[str, Any]]:
    path = memory_path(root)
    if not path.is_file(): return []
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        try: item = json.loads(line)
        except json.JSONDecodeError as exc: raise ValueError(f"{path}:{number}: {exc}") from exc
        if not isinstance(item, dict): raise ValueError(f"{path}:{number}: expected object")
        out.append(item)
    return out


def parse_date(value: str) -> datetime | None:
    if not value: return None
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None


def current_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for event in events(root):
        action = event.get("action")
        rid = event.get("research_id")
        if not rid: continue
        if action == "add":
            records[rid] = dict(event)
        elif rid in records and action in {"verify", "supersede", "reject", "annotate"}:
            if action == "verify":
                records[rid].update({
                    "status": "verified", "last_verified_at_utc": event.get("at_utc"),
                    "source_url": event.get("source_url") or records[rid].get("source_url"),
                    "source_version": event.get("source_version") or records[rid].get("source_version"),
                    "evidence": event.get("evidence") or records[rid].get("evidence"),
                    "review_after": event.get("review_after") or records[rid].get("review_after"),
                })
            elif action == "supersede":
                records[rid].update({"status": "superseded", "superseded_by": event.get("replacement_id"), "supersede_reason": event.get("reason")})
            elif action == "reject":
                records[rid].update({"status": "rejected", "rejection_reason": event.get("reason")})
            else:
                records[rid].setdefault("annotations", []).append(event.get("note"))
    return records


def is_stale(record: dict[str, Any]) -> bool:
    review = parse_date(str(record.get("review_after", "")))
    return bool(review and review <= datetime.now(timezone.utc))


def add_record(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve(); pid = project_id(root)
    if args.status == "verified" and (not args.source_url or not args.evidence):
        print("Verified research requires --source-url and --evidence.", file=sys.stderr); return 2
    if args.source_url and not re.match(r"^(?:https?|file)://", args.source_url):
        print("--source-url must be an http(s) or file URL.", file=sys.stderr); return 2
    rid = "res-" + uuid.uuid4().hex[:12]
    record = {
        "schema_version": SCHEMA_VERSION, "action": "add", "research_id": rid,
        "project_id": pid, "at_utc": now(), "query": args.query, "claim": args.claim,
        "source_url": args.source_url, "source_title": args.source_title,
        "publisher": args.publisher, "source_version": args.source_version,
        "applies_to": args.applies_to, "decision": args.decision,
        "why": args.why, "tradeoffs": args.tradeoff, "alternatives": args.alternative,
        "evidence": args.evidence, "confidence": args.confidence, "status": args.status,
        "review_after": args.review_after, "tags": args.tag,
    }
    append(memory_path(root), record); print(rid); return 0


def search_records(args: argparse.Namespace) -> int:
    records = current_records(args.root)
    tokens = [x for x in re.split(r"\W+", args.query.lower()) if x]
    hits = []
    for record in records.values():
        if not args.include_stale and is_stale(record): continue
        haystack = json.dumps(record, ensure_ascii=False).lower()
        score = sum(haystack.count(token) for token in tokens)
        if score:
            item = dict(record); item["score"] = score; item["stale"] = is_stale(record); hits.append(item)
    hits.sort(key=lambda x: (-x["score"], x.get("status") != "verified", x.get("claim", "")))
    print(json.dumps(hits[:args.limit], indent=2, ensure_ascii=False))
    return 0 if hits else 1


def verify_record(args: argparse.Namespace) -> int:
    records = current_records(args.root)
    if args.id not in records:
        print(f"Unknown research ID: {args.id}", file=sys.stderr); return 2
    if not args.source_url and not records[args.id].get("source_url"):
        print("Verification requires a source URL.", file=sys.stderr); return 2
    if not args.evidence:
        print("Verification requires evidence.", file=sys.stderr); return 2
    append(memory_path(args.root), {
        "schema_version": SCHEMA_VERSION, "action": "verify", "research_id": args.id,
        "at_utc": now(), "source_url": args.source_url, "source_version": args.source_version,
        "evidence": args.evidence, "review_after": args.review_after,
    })
    print(args.id); return 0


def supersede_record(args: argparse.Namespace) -> int:
    records = current_records(args.root)
    if args.id not in records or args.replacement_id not in records:
        print("Both original and replacement research IDs must exist.", file=sys.stderr); return 2
    append(memory_path(args.root), {
        "schema_version": SCHEMA_VERSION, "action": "supersede", "research_id": args.id,
        "replacement_id": args.replacement_id, "reason": args.reason, "at_utc": now(),
    })
    print(args.id); return 0


def digest(args: argparse.Namespace) -> int:
    records = list(current_records(args.root).values())
    active = [r for r in records if r.get("status") not in {"superseded", "rejected"}]
    active.sort(key=lambda r: (is_stale(r), r.get("status") != "verified", r.get("query", "")))
    lines = ["# Research Memory Digest", ""]
    for r in active:
        stale = "STALE — REVERIFY" if is_stale(r) else r.get("status", "observed").upper()
        lines += [
            f"## {r.get('claim', 'Untitled claim')}", "",
            f"- ID: `{r.get('research_id')}`", f"- Status: **{stale}**",
            f"- Query: {r.get('query', '')}", f"- Applies to: {r.get('applies_to', '')}",
            f"- Decision: {r.get('decision', '')}", f"- Source: {r.get('source_url', '')}",
            f"- Version: {r.get('source_version', '')}", f"- Review after: {r.get('review_after', '')}", "",
        ]
    text = "\n".join(lines).rstrip() + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8"); print(args.output)
    else: print(text)
    return 0


def doctor(args: argparse.Namespace) -> int:
    errors = []; warnings = []
    try: records = current_records(args.root)
    except Exception as exc: print(f"Research memory doctor FAILED\nERROR: {exc}", file=sys.stderr); return 1
    for rid, r in records.items():
        for field in ("query", "claim", "status", "confidence"):
            if not str(r.get(field, "")).strip(): errors.append(f"{rid}: missing {field}")
        if r.get("status") == "verified" and (not r.get("source_url") or not r.get("evidence")):
            errors.append(f"{rid}: verified without source/evidence")
        if is_stale(r) and r.get("status") == "verified": warnings.append(f"{rid}: verified research is stale and must be revalidated before reuse")
    if errors:
        print("Research memory doctor FAILED", file=sys.stderr)
        for x in errors: print(f"ERROR: {x}", file=sys.stderr)
    for x in warnings: print(f"WARNING: {x}", file=sys.stderr)
    if errors or (warnings and args.strict_warnings): return 1
    print(f"Research memory doctor passed: {len(records)} records, {len(warnings)} stale")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("add"); a.add_argument("root", type=Path); a.add_argument("--query", required=True); a.add_argument("--claim", required=True); a.add_argument("--source-url", default=""); a.add_argument("--source-title", default=""); a.add_argument("--publisher", default=""); a.add_argument("--source-version", default=""); a.add_argument("--applies-to", required=True); a.add_argument("--decision", required=True); a.add_argument("--why", required=True); a.add_argument("--tradeoff", action="append", default=[]); a.add_argument("--alternative", action="append", default=[]); a.add_argument("--evidence", default=""); a.add_argument("--confidence", choices=("low", "medium", "high"), default="medium"); a.add_argument("--status", choices=("hypothesis", "observed", "verified"), default="observed"); a.add_argument("--review-after", default=""); a.add_argument("--tag", action="append", default=[])
    a = sub.add_parser("search"); a.add_argument("root", type=Path); a.add_argument("query"); a.add_argument("--include-stale", action="store_true"); a.add_argument("--limit", type=int, default=20)
    a = sub.add_parser("verify"); a.add_argument("root", type=Path); a.add_argument("id"); a.add_argument("--source-url", default=""); a.add_argument("--source-version", default=""); a.add_argument("--evidence", required=True); a.add_argument("--review-after", default="")
    a = sub.add_parser("supersede"); a.add_argument("root", type=Path); a.add_argument("id"); a.add_argument("--replacement-id", required=True); a.add_argument("--reason", required=True)
    a = sub.add_parser("digest"); a.add_argument("root", type=Path); a.add_argument("--output", type=Path)
    a = sub.add_parser("doctor"); a.add_argument("root", type=Path); a.add_argument("--strict-warnings", action="store_true")
    args = p.parse_args()
    return {"add": add_record, "search": search_records, "verify": verify_record, "supersede": supersede_record, "digest": digest, "doctor": doctor}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
