#!/usr/bin/env python3
"""Versioned shared-policy snapshots; preserve repository-specific instructions.

plan/status are read-only. apply never replaces AGENTS.md or edited snapshots.
This is separate from foundry_sync.py's explicitly selected Skill installs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from foundry_sync import atomic_json, load_json

SOURCE_URL = "https://github.com/Herbertofury/Agent-Foundry"
MANIFEST = "registry/repository-governance.json"
LOCK = ".agent-foundry/governance-lock.json"
SNAPSHOT = ".agents/foundry"
POLICY_FILES = (
    "PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "DESIGN_QUALITY_STANDARD.md",
    "FAILURE_INTELLIGENCE_STANDARD.md", "CHALLENGER_INTEGRATION_STANDARD.md",
    "PERFORMANCE_ACCEPTANCE.md", "RUNTIME_PROOF.md", "DURABLE_EXECUTION_STANDARD.md",
    "EVALUATION_STANDARD.md", "OBSERVABILITY_STANDARD.md", "INTEROPERABILITY_STANDARD.md",
    "AUTHORIZATION_CONTROL_STANDARD.md", "THIRD_PARTY_SKILL_SECURITY.md",
    "SUPPLY_CHAIN_STANDARD.md", "DISTRIBUTION_STANDARD.md", "templates/AGENTS.repository.md",
)


def content(path: Path) -> bytes:
    # Markdown snapshots are portable across Git's Windows line-ending conversion.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def release(repo: Path, version: str) -> dict:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be major.minor.patch")
    ids = re.findall(r"^## (\d+)\. ", (repo / POLICY_FILES[0]).read_text(encoding="utf-8"), re.M)
    return {"schemaVersion": 1, "version": version, "sourceRepository": SOURCE_URL,
            "digestFormat": "sha256-utf8-lf", "invariantIds": [int(x) for x in ids],
            "files": {name: digest(content(repo / name)) for name in POLICY_FILES}}


def checked_release(repo: Path) -> dict:
    manifest = load_json(repo / MANIFEST, None)
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise ValueError("missing/unsupported repository governance manifest")
    if manifest != release(repo, manifest["version"]):
        raise ValueError("canonical policy drift; publish a new manifest version before adoption")
    return manifest


def destination(name: str) -> str:
    filename = "AGENTS-adapter.md" if name.startswith("templates/") else name
    return f"{SNAPSHOT}/{filename}"


def safe_path(target: Path, relative: str) -> Path:
    # Never write through a symlink/junction into another project or user directory.
    path = target / relative
    for item in [path, *path.parents]:
        if item == target:
            break
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError(f"linked destination refused: {item}")
    if not path.resolve().is_relative_to(target):
        raise ValueError(f"destination escapes target: {relative}")
    return path


def plan(repo: Path, target: Path) -> tuple[dict, dict, list[dict]]:
    if not target.is_dir() or target == repo:
        raise ValueError("target must be an existing consumer directory, separate from Foundry")
    manifest = checked_release(repo)
    lock = load_json(safe_path(target, LOCK), {})
    if lock and (lock.get("schemaVersion") != 1 or lock.get("sourceRepository") != SOURCE_URL):
        raise ValueError("foreign or unsupported governance lock; preserve and review it")
    managed = lock.get("files", {})
    actions = []
    for source, wanted in manifest["files"].items():
        rel = destination(source)
        path = safe_path(target, rel)
        current = digest(content(path)) if path.is_file() else None
        previous = managed.get(rel)
        if path.exists() and (not path.is_file() or not previous):
            action, reason = "conflict", "unmanaged destination exists"
        elif previous and current != previous:
            action, reason = "conflict", "managed snapshot locally edited or removed"
        elif current == wanted:
            action, reason = "noop", "pinned snapshot matches"
        else:
            action, reason = ("update" if previous else "create"), "canonical snapshot changed or missing"
        actions.append({"action": action, "path": rel, "reason": reason, "sha256": wanted})
    # Root instructions are project-owned. Add a new router only when absent.
    root = safe_path(target, "AGENTS.md")
    if root.exists() and not root.is_file():
        actions.append({"action": "conflict", "path": "AGENTS.md", "reason": "not a regular file"})
    elif not root.exists():
        actions.append({"action": "create", "path": "AGENTS.md", "reason": "add thin repository router"})
    elif not re.search(r"\.agents/foundry/(?:PRODUCT_INVARIANTS|AGENTS-adapter)\.md", root.read_text(encoding="utf-8")):
        actions.append({"action": "review", "path": "AGENTS.md", "reason": "preserved; add a reviewed reference to .agents/foundry/AGENTS-adapter.md"})
    override = safe_path(target, "AGENTS.override.md")
    if override.exists():
        if not override.is_file():
            actions.append({"action": "conflict", "path": "AGENTS.override.md", "reason": "not a regular file"})
        elif not re.search(r"\.agents/foundry/(?:PRODUCT_INVARIANTS|AGENTS-adapter)\.md", override.read_text(encoding="utf-8")):
            actions.append({"action": "review", "path": "AGENTS.override.md",
                            "reason": "preserved; review harness precedence and add adapter integration to the override"})
    lock_current = lock.get("version") == manifest["version"] and managed == {
        destination(k): v for k, v in manifest["files"].items()}
    actions.append({"action": "noop" if lock_current else "update", "path": LOCK,
                    "reason": "adoption lock matches" if lock_current else "record adoption version and lineage"})
    return manifest, lock, actions


def apply(repo: Path, target: Path) -> list[dict]:
    manifest, _, actions = plan(repo, target)
    if any(a["action"] == "conflict" for a in actions):
        raise ValueError("conflicts detected; no files changed")
    # Preflight the whole write set before starting any writes.
    for action in actions:
        safe_path(target, action["path"])
    data = {destination(name): content(repo / name) for name in manifest["files"]}
    if any(digest(data[destination(name)]) != expected for name, expected in manifest["files"].items()):
        raise ValueError("source changed during planning; no files changed")
    data["AGENTS.md"] = content(repo / "templates/AGENTS.repository.md")
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                           capture_output=True, text=True, check=True).stdout.strip()
    for action in actions:
        rel = action["path"]
        if action["action"] not in {"create", "update"} or rel == LOCK:
            continue
        path = safe_path(target, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data[rel])
    if any(a["path"] == LOCK and a["action"] == "update" for a in actions):
        atomic_json(safe_path(target, LOCK), {"schemaVersion": 1, "sourceRepository": SOURCE_URL,
                    "sourceCommit": commit, "sourceWorkingTreeDirty": bool(dirty),
                    "version": manifest["version"], "digestFormat": manifest["digestFormat"],
                    "files": {destination(k): v for k, v in manifest["files"].items()}})
    return plan(repo, target)[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("manifest", "check", "plan", "status", "apply"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--target", type=Path)
    parser.add_argument("--version", help="explicit new version for manifest generation")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        if args.command == "manifest":
            if not args.version:
                raise ValueError("manifest requires --version")
            new = release(repo, args.version)
            old = load_json(repo / MANIFEST, {})
            if old and new != old and tuple(map(int, args.version.split('.'))) <= tuple(map(int, old["version"].split('.'))):
                raise ValueError("changed shared policy requires a newer version")
            atomic_json(repo / MANIFEST, new)
            print(f"Recorded repository governance {args.version}")
        elif args.command == "check":
            print(f"Canonical repository governance {checked_release(repo)['version']} verified")
        else:
            if not args.target:
                raise ValueError("consumer command requires --target; targets are never discovered automatically")
            target = args.target.expanduser().resolve()
            actions = apply(repo, target) if args.command == "apply" else plan(repo, target)[2]
            print(json.dumps(actions, indent=2))
            if any(a["action"] == "conflict" for a in actions):
                return 2
            if args.command in {"status", "apply"} and any(a["action"] != "noop" for a in actions):
                return 2
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"repository-governance: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
