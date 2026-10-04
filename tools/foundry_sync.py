#!/usr/bin/env python3
"""Agent Foundry desired-state multi-agent skill synchronizer.

Commands:
  plan   - show non-destructive changes/conflicts
  apply  - reconcile managed targets without clobbering unmanaged files
  status - report drift/conflicts; exit nonzero when reconciliation is needed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STATE_DIR = ".agent-foundry"
LOCK_FILE = "lock.json"
MANAGED_MARKER = ".agent-foundry-managed.json"


def norm(p: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(p)))).resolve()


def tree_digest(path: Path) -> str:
    h = hashlib.sha256()
    if not path.is_dir():
        return ""
    for f in sorted(p for p in path.rglob("*") if p.is_file() and p.name != MANAGED_MARKER):
        rel = f.relative_to(path).as_posix()
        h.update(rel.encode("utf-8")); h.update(b"\0")
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        h.update(b"\n")
    return h.hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@dataclass
class Action:
    action: str
    target: str
    skill: str
    destination: str
    mode: str
    reason: str
    sourceDigest: str
    currentDigest: str | None = None


class FoundrySync:
    def __init__(self, repo: Path, config_path: Path, state_path: Path | None = None):
        self.repo = repo.resolve()
        self.config_path = config_path.resolve()
        self.config = load_json(self.config_path, None)
        if not isinstance(self.config, dict) or self.config.get("schemaVersion") != SCHEMA_VERSION:
            raise ValueError(f"{self.config_path}: schemaVersion must be {SCHEMA_VERSION}")
        self.targets = {t["name"]: t for t in self.config.get("targets", []) if t.get("enabled", True)}
        if not self.targets:
            raise ValueError("at least one enabled target is required")
        self.state_path = (state_path or (self.repo / STATE_DIR / LOCK_FILE)).resolve()
        self.state = load_json(self.state_path, {"schemaVersion": SCHEMA_VERSION, "managed": {}})
        self.state.setdefault("managed", {})

    def _source(self, spec: dict[str, Any]) -> Path:
        source = norm(self.repo / spec["source"])
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            raise ValueError(f"invalid skill source: {source}")
        return source

    def _destination(self, target: dict[str, Any], skill_name: str) -> Path:
        root = norm(target["root"])
        return root / skill_name

    def _managed_entry(self, dest: Path) -> dict[str, Any] | None:
        return self.state["managed"].get(str(dest))

    def _marker(self, dest: Path) -> dict[str, Any] | None:
        if dest.is_dir() and not dest.is_symlink():
            p = dest / MANAGED_MARKER
            try:
                return load_json(p, None)
            except Exception:
                return None
        return None

    def plan(self) -> list[Action]:
        actions: list[Action] = []
        for spec in self.config.get("skills", []):
            name = spec["name"]
            source = self._source(spec)
            src_digest = tree_digest(source)
            for target_name in spec.get("targets", list(self.targets)):
                if target_name not in self.targets:
                    continue
                target = self.targets[target_name]
                mode = target.get("mode", "symlink")
                if mode not in {"symlink", "copy"}:
                    raise ValueError(f"target {target_name}: unsupported mode {mode}")
                dest = self._destination(target, name)
                entry = self._managed_entry(dest)

                if not dest.exists() and not dest.is_symlink():
                    actions.append(Action("create", target_name, name, str(dest), mode, "destination missing", src_digest))
                    continue

                if mode == "symlink":
                    if dest.is_symlink():
                        resolved = dest.resolve(strict=False)
                        if resolved == source:
                            actions.append(Action("noop", target_name, name, str(dest), mode, "symlink already points to source", src_digest, src_digest))
                        elif entry and entry.get("mode") == "symlink":
                            actions.append(Action("update", target_name, name, str(dest), mode, "managed symlink target changed", src_digest))
                        else:
                            actions.append(Action("conflict", target_name, name, str(dest), mode, "unmanaged symlink exists", src_digest))
                    else:
                        actions.append(Action("conflict", target_name, name, str(dest), mode, "unmanaged path exists", src_digest, tree_digest(dest) if dest.is_dir() else None))
                    continue

                marker = self._marker(dest)
                current = tree_digest(dest) if dest.is_dir() else None
                managed = bool(entry and entry.get("mode") == "copy") or bool(marker and marker.get("managedBy") == "agent-foundry")
                if not dest.is_dir():
                    actions.append(Action("conflict", target_name, name, str(dest), mode, "non-directory path exists", src_digest, current))
                elif not managed:
                    actions.append(Action("conflict", target_name, name, str(dest), mode, "unmanaged directory exists", src_digest, current))
                elif current != (entry or marker or {}).get("sourceDigest"):
                    actions.append(Action("conflict", target_name, name, str(dest), mode, "managed copy locally edited; preserve customization", src_digest, current))
                elif current == src_digest:
                    actions.append(Action("noop", target_name, name, str(dest), mode, "managed copy matches source", src_digest, current))
                else:
                    actions.append(Action("update", target_name, name, str(dest), mode, "managed copy drifted or source changed", src_digest, current))
        return actions

    def apply(self) -> list[Action]:
        actions = self.plan()
        conflicts = [a for a in actions if a.action == "conflict"]
        if conflicts:
            raise RuntimeError(f"refusing to clobber {len(conflicts)} unmanaged/conflicting destination(s)")

        managed = self.state["managed"]
        for a in actions:
            if a.action == "noop":
                continue
            dest = Path(a.destination)
            source = self._source(next(s for s in self.config["skills"] if s["name"] == a.skill))
            dest.parent.mkdir(parents=True, exist_ok=True)
            if a.mode == "symlink":
                if dest.is_symlink():
                    dest.unlink()
                elif dest.exists():
                    raise RuntimeError(f"unexpected destination appeared during apply: {dest}")
                dest.symlink_to(source, target_is_directory=True)
            else:
                if dest.exists():
                    if not dest.is_dir() or dest.is_symlink():
                        raise RuntimeError(f"unexpected destination type during apply: {dest}")
                    shutil.rmtree(dest)
                shutil.copytree(source, dest, symlinks=True)
                atomic_json(dest / MANAGED_MARKER, {
                    "schemaVersion": SCHEMA_VERSION,
                    "managedBy": "agent-foundry",
                    "skill": a.skill,
                    "source": str(source),
                    "sourceDigest": a.sourceDigest,
                })
            managed[str(dest)] = {
                "skill": a.skill,
                "target": a.target,
                "mode": a.mode,
                "source": str(source),
                "sourceDigest": a.sourceDigest,
            }
        atomic_json(self.state_path, self.state)
        return self.plan()


def render(actions: list[Action], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(a) for a in actions], indent=2))
        return
    counts: dict[str, int] = {}
    for a in actions:
        counts[a.action] = counts.get(a.action, 0) + 1
        print(f"{a.action.upper():8} {a.target:12} {a.skill:34} {a.destination}  # {a.reason}")
    print("\n" + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["plan", "apply", "status"])
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--state", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args()
    repo = ns.repo.resolve()
    cfg = ns.config or (repo / "config" / "foundry-sync.json")
    try:
        sync = FoundrySync(repo, cfg, ns.state)
        actions = sync.apply() if ns.command == "apply" else sync.plan()
        render(actions, ns.json)
        if ns.command == "status":
            return 0 if all(a.action == "noop" for a in actions) else 2
        if ns.command == "plan":
            return 2 if any(a.action == "conflict" for a in actions) else 0
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"foundry-sync: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
