#!/usr/bin/env python3
"""Deterministic runtime watchdog for Zero-Loss Chat Accelerator.

Tracks monotonic progress, wait leases, escalation, stall fingerprints, and a
portable recovery capsule. Uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

SCHEMA = 1
DEFAULT_LEASES = {
    "connector": 60,
    "network": 60,
    "subprocess": 120,
    "ci": 120,
    "native": 120,
    "upload": 120,
}


def now() -> float:
    return time.time()


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": SCHEMA,
            "created_at": now(),
            "continuity": {
                "acceptance": [],
                "completed": [],
                "canonical": {},
                "evidence": {},
                "hashes": {},
                "runs": {},
                "latest_checkpoint": None,
                "latest_mutation": None,
                "latest_test": None,
                "blocker": None,
                "no_repeat": [],
                "exact_next_action": None,
            },
            "watchdog": {
                "progress_seq": 0,
                "dead_waves": 0,
                "last_progress_at": None,
                "waits": {},
                "stall_count": 0,
                "fingerprints": [],
            },
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA:
        raise ValueError("unsupported watchdog schema")
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_kv(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected KEY=VALUE, got {value!r}")
        k, v = value.split("=", 1)
        if not k:
            raise ValueError("empty key")
        out[k] = v
    return out


def append_unique(seq: list[str], values: list[str]) -> bool:
    changed = False
    for value in values:
        if value not in seq:
            seq.append(value)
            changed = True
    return changed


def apply_update(args: argparse.Namespace) -> int:
    path = Path(args.state)
    data = load(path)
    c = data["continuity"]
    w = data["watchdog"]
    progress = False

    progress |= append_unique(c["acceptance"], args.accept)
    progress |= append_unique(c["completed"], args.complete)
    append_unique(c["no_repeat"], args.no_repeat)  # useful state, not progress by itself

    for field, values in (
        ("canonical", args.canonical),
        ("evidence", args.evidence),
        ("hashes", args.hash),
        ("runs", args.run),
    ):
        incoming = parse_kv(values)
        for k, v in incoming.items():
            if c[field].get(k) != v:
                c[field][k] = v
                progress = True

    for field, value in (
        ("latest_checkpoint", args.checkpoint),
        ("latest_mutation", args.mutation),
        ("latest_test", args.test),
    ):
        if value is not None and c.get(field) != value:
            c[field] = value
            progress = True

    # A materially changed blocker counts as uncertainty reduction/progress.
    if args.blocker is not None and c.get("blocker") != args.blocker:
        c["blocker"] = args.blocker or None
        progress = True
    if args.next_action is not None:
        c["exact_next_action"] = args.next_action or None

    if args.no_progress:
        progress = False

    if progress:
        w["progress_seq"] += 1
        w["dead_waves"] = 0
        w["last_progress_at"] = now()
        status = "PROGRESS"
    else:
        w["dead_waves"] += 1
        status = "STALL" if w["dead_waves"] >= 2 else "NO_PROGRESS"
        if status == "STALL":
            w["stall_count"] += 1

    save(path, data)
    print(json.dumps({
        "status": status,
        "progress_seq": w["progress_seq"],
        "dead_waves": w["dead_waves"],
        "exact_next_action": c.get("exact_next_action"),
        "blocker": c.get("blocker"),
    }, sort_keys=True))
    return 2 if status == "STALL" else 0


def wait_start(args: argparse.Namespace) -> int:
    path = Path(args.state)
    data = load(path)
    w = data["watchdog"]
    lease = args.lease if args.lease is not None else DEFAULT_LEASES.get(args.kind, 60)
    started = now()
    w["waits"][args.key] = {
        "kind": args.kind,
        "identity": args.identity,
        "started_at": started,
        "lease_seconds": lease,
        "deadline": started + lease,
        "last_status": args.status,
        "last_meaningful_at": started if args.status else None,
        "closed": False,
    }
    save(path, data)
    print(json.dumps(w["waits"][args.key], sort_keys=True))
    return 0


def wait_observe(args: argparse.Namespace) -> int:
    path = Path(args.state)
    data = load(path)
    waits = data["watchdog"]["waits"]
    if args.key not in waits:
        raise KeyError(f"unknown wait key {args.key!r}")
    item = waits[args.key]
    t = now()
    meaningful = args.meaningful or (args.status is not None and args.status != item.get("last_status"))
    if args.status is not None:
        item["last_status"] = args.status
    if meaningful:
        item["last_meaningful_at"] = t
    expired = t >= item["deadline"] and not item.get("closed")
    save(path, data)
    result = {
        "status": "LEASE_EXPIRED" if expired else ("MILESTONE" if meaningful else "UNCHANGED"),
        "identity": item["identity"],
        "deadline": item["deadline"],
        "preserve_identity": True,
        "recommended_action": (
            "checkpoint, stop unchanged observation, advance independent work, and resume only after a real invalidator"
            if expired else None
        ),
    }
    print(json.dumps(result, sort_keys=True))
    return 3 if expired else 0


def wait_close(args: argparse.Namespace) -> int:
    path = Path(args.state)
    data = load(path)
    item = data["watchdog"]["waits"].get(args.key)
    if item is None:
        raise KeyError(f"unknown wait key {args.key!r}")
    item["closed"] = True
    item["final_status"] = args.status
    item["closed_at"] = now()
    save(path, data)
    print(json.dumps(item, sort_keys=True))
    return 0


def decision(args: argparse.Namespace) -> int:
    data = load(Path(args.state))
    c = data["continuity"]
    w = data["watchdog"]
    t = now()
    expired = [
        {"key": k, "identity": v.get("identity"), "kind": v.get("kind")}
        for k, v in w["waits"].items()
        if not v.get("closed") and t >= v.get("deadline", float("inf"))
    ]
    if w["dead_waves"] >= 2:
        action = "CHANGE_STRATEGY_NOW"
        reason = "two consecutive no-progress waves"
        code = 2
    elif expired:
        action = "RELEASE_HOSTAGE_WAIT"
        reason = "one or more interactive wait leases expired"
        code = 3
    elif c.get("exact_next_action") and not c.get("blocker") and w["dead_waves"] >= 1:
        action = "EXECUTE_KNOWN_NEXT_ACTION"
        reason = "next action is known and no blocker is recorded"
        code = 4
    else:
        action = "CONTINUE"
        reason = "no stall threshold reached"
        code = 0
    print(json.dumps({
        "action": action,
        "reason": reason,
        "dead_waves": w["dead_waves"],
        "expired_waits": expired,
        "exact_next_action": c.get("exact_next_action"),
        "blocker": c.get("blocker"),
    }, sort_keys=True))
    return code


def capsule(args: argparse.Namespace) -> int:
    data = load(Path(args.state))
    c = data["continuity"]
    out = {
        "schema_version": 1,
        "acceptance": c["acceptance"],
        "completed": c["completed"],
        "canonical": c["canonical"],
        "evidence": c["evidence"],
        "hashes": c["hashes"],
        "runs": c["runs"],
        "latest_checkpoint": c["latest_checkpoint"],
        "latest_mutation": c["latest_mutation"],
        "latest_test": c["latest_test"],
        "blocker": c["blocker"],
        "no_repeat": c["no_repeat"],
        "exact_next_action": c["exact_next_action"],
    }
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(target)
    else:
        print(text, end="")
    return 0


def fingerprint(args: argparse.Namespace) -> int:
    path = Path(args.state)
    data = load(path)
    item = {
        "at": now(),
        "skill_stack": args.skill_stack,
        "owner": args.owner,
        "operation": args.operation,
        "target": args.target,
        "elapsed_seconds": args.elapsed,
        "repeats": args.repeat,
        "blocker": args.blocker,
        "recovery": args.recovery,
        "lesson": args.lesson,
    }
    data["watchdog"]["fingerprints"].append(item)
    save(path, data)
    print(json.dumps(item, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("update")
    p.add_argument("--state", required=True)
    p.add_argument("--accept", action="append", default=[])
    p.add_argument("--complete", action="append", default=[])
    p.add_argument("--canonical", action="append", default=[])
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--hash", action="append", default=[])
    p.add_argument("--run", action="append", default=[])
    p.add_argument("--checkpoint")
    p.add_argument("--mutation")
    p.add_argument("--test")
    p.add_argument("--blocker")
    p.add_argument("--next-action")
    p.add_argument("--no-repeat", action="append", default=[])
    p.add_argument("--no-progress", action="store_true")
    p.set_defaults(func=apply_update)

    p = sub.add_parser("wait-start")
    p.add_argument("--state", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--kind", choices=sorted(DEFAULT_LEASES), default="connector")
    p.add_argument("--identity", required=True)
    p.add_argument("--lease", type=int)
    p.add_argument("--status")
    p.set_defaults(func=wait_start)

    p = sub.add_parser("wait-observe")
    p.add_argument("--state", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--status")
    p.add_argument("--meaningful", action="store_true")
    p.set_defaults(func=wait_observe)

    p = sub.add_parser("wait-close")
    p.add_argument("--state", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--status", required=True)
    p.set_defaults(func=wait_close)

    p = sub.add_parser("decision")
    p.add_argument("--state", required=True)
    p.set_defaults(func=decision)

    p = sub.add_parser("capsule")
    p.add_argument("--state", required=True)
    p.add_argument("--output")
    p.set_defaults(func=capsule)

    p = sub.add_parser("fingerprint")
    p.add_argument("--state", required=True)
    p.add_argument("--skill-stack", action="append", default=[])
    p.add_argument("--owner", required=True)
    p.add_argument("--operation", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--elapsed", type=float, required=True)
    p.add_argument("--repeat", action="append", default=[])
    p.add_argument("--blocker")
    p.add_argument("--recovery", required=True)
    p.add_argument("--lesson", required=True)
    p.set_defaults(func=fingerprint)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
