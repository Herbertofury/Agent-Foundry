#!/usr/bin/env python3
"""Maintain a persistent, project-owned second brain and a cross-project registry.

The repository-local `.agents-memory/` directory is the durable source of truth for
project state. A user-level registry helps locate the same project across chats,
clones, worktrees, and directories without treating similarly named projects as the
same thing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MEMORY_DIR = ".agents-memory"
LEDGERS = {
    "decision": "decisions.jsonl",
    "research": "research.jsonl",
    "tool": "tools.jsonl",
    "incident": "incidents.jsonl",
    "milestone": "milestones.jsonl",
    "artifact": "artifacts.jsonl",
    "note": "notes.jsonl",
    "hypothesis": "hypotheses.jsonl",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]{8,}", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "project"


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSONL: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{number}: expected object")
        out.append(item)
    return out


def run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def normalize_remote(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    value = re.sub(r"^[^@/]+@([^:]+):", r"ssh://\1/", value)
    value = re.sub(r"(https?://)[^/@]+@", r"\1", value)
    value = value.rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


def git_snapshot(root: Path) -> dict[str, Any]:
    remotes: list[str] = []
    remote_lines = run_git(root, "remote", "-v").splitlines()
    for line in remote_lines:
        parts = line.split()
        if len(parts) >= 2:
            remote = normalize_remote(parts[1])
            if remote and remote not in remotes:
                remotes.append(remote)
    status = run_git(root, "status", "--short")
    return {
        "toplevel": run_git(root, "rev-parse", "--show-toplevel"),
        "branch": run_git(root, "branch", "--show-current"),
        "head": run_git(root, "rev-parse", "HEAD"),
        "remotes": remotes,
        "dirty": bool(status),
        "changed_paths": status.splitlines()[:200],
    }


def manifest_identity(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    package = root / "package.json"
    if package.is_file():
        try:
            name = json.loads(package.read_text(encoding="utf-8")).get("name")
            if name:
                found["package.json"] = str(name)
        except Exception:
            pass
    for filename, pattern in (
        ("pyproject.toml", r"(?m)^name\s*=\s*[\"']([^\"']+)[\"']"),
        ("Cargo.toml", r"(?m)^name\s*=\s*[\"']([^\"']+)[\"']"),
        ("go.mod", r"(?m)^module\s+([^\s]+)"),
    ):
        path = root / filename
        if path.is_file():
            match = re.search(pattern, path.read_text(encoding="utf-8", errors="replace"))
            if match:
                found[filename] = match.group(1)
    return found


def identity_evidence(root: Path) -> dict[str, Any]:
    root = root.resolve()
    git = git_snapshot(root)
    manifests = manifest_identity(root)
    marker = load_json(root / MEMORY_DIR / "PROJECT.json", {}) or {}
    material = {
        "remotes": git["remotes"],
        "manifests": manifests,
        "marker_project_id": marker.get("project_id", ""),
    }
    fingerprint = hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "root": str(root),
        "directory_name": root.name,
        "git": git,
        "manifests": manifests,
        "marker": marker,
        "fingerprint": fingerprint,
    }


def default_vault() -> Path:
    return Path(os.environ.get("AGENTS_MEMORY_HOME", "~/.agents-second-brain")).expanduser().resolve()


def registry_path(vault: Path) -> Path:
    return vault / "registry.json"


def load_registry(vault: Path) -> dict[str, Any]:
    data = load_json(registry_path(vault), None)
    if data is None:
        return {"schema_version": SCHEMA_VERSION, "updated_at_utc": now(), "projects": {}}
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("projects"), dict):
        raise ValueError(f"Unsupported or invalid registry: {registry_path(vault)}")
    return data


def save_registry(vault: Path, data: dict[str, Any]) -> None:
    data["updated_at_utc"] = now()
    atomic_write_json(registry_path(vault), data)


def memory_root(root: Path) -> Path:
    return root.resolve() / MEMORY_DIR


def project_marker(root: Path) -> dict[str, Any]:
    path = memory_root(root) / "PROJECT.json"
    data = load_json(path, None)
    if not isinstance(data, dict):
        raise FileNotFoundError(f"Project memory is not initialized: {path}")
    return data


def candidate_scores(registry: dict[str, Any], evidence: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    query_l = query.strip().lower()
    current_remotes = set(evidence.get("git", {}).get("remotes", []))
    marker_id = evidence.get("marker", {}).get("project_id", "")
    current_path = evidence.get("root", "")
    manifest_names = {str(v).lower() for v in evidence.get("manifests", {}).values()}
    results: list[dict[str, Any]] = []
    for pid, project in registry.get("projects", {}).items():
        score = 0
        reasons: list[str] = []
        locations = [str(Path(p).expanduser().resolve()) for p in project.get("locations", [])]
        remotes = set(project.get("remotes", []))
        names = {str(project.get("name", "")).lower(), *(str(x).lower() for x in project.get("aliases", []))}
        names.discard("")
        if marker_id and pid == marker_id:
            score += 100; reasons.append("project marker ID")
        if current_path in locations:
            score += 100; reasons.append("registered path")
        overlap = current_remotes & remotes
        if overlap:
            score += 90; reasons.append("matching git remote")
        if evidence.get("fingerprint") and evidence.get("fingerprint") == project.get("fingerprint"):
            score += 70; reasons.append("matching repository fingerprint")
        if manifest_names & names:
            score += 45; reasons.append("matching manifest/project name")
        if evidence.get("directory_name", "").lower() in names:
            score += 35; reasons.append("matching directory alias")
        if query_l:
            haystack = " ".join([pid, project.get("name", ""), *project.get("aliases", []), *locations]).lower()
            if query_l in haystack:
                score += 60; reasons.append("query match")
            elif all(token in haystack for token in query_l.split()):
                score += 35; reasons.append("query token match")
        if score:
            results.append({"project_id": pid, "score": score, "reasons": reasons, **project})
    return sorted(results, key=lambda x: (-x["score"], x.get("name", "")))


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def sync_cross_project_catalog(root: Path, vault: Path) -> tuple[bool, str]:
    """Synchronize project-owned memory into the durable cross-project catalog."""
    script = Path(__file__).with_name("project_catalog.py")
    if not script.is_file():
        return True, "project catalog tool not installed"
    result = subprocess.run(
        [sys.executable, str(script), "sync-project", str(root), "--vault", str(vault)],
        text=True, capture_output=True, timeout=120,
    )
    if result.returncode:
        return False, (result.stderr or result.stdout).strip()
    return True, result.stdout.strip()


def sync_artifacts_to_library(project: dict[str, Any], artifacts: list[dict[str, Any]], memory_vault: Path) -> tuple[bool, str]:
    """Mirror reconciled artifact metadata into the organized library catalog."""
    if not artifacts:
        return True, "no new artifacts to sync"
    script = Path(__file__).with_name("library_manager.py")
    if not script.is_file():
        return True, "library manager tool not installed"
    configured = os.environ.get("AGENTS_LIBRARY_HOME")
    library_vault = Path(configured).expanduser().resolve() if configured else (memory_vault / "library").resolve()
    manifest = {
        "items": [
            {
                "name": item.get("name", ""),
                "project_id": project.get("project_id", ""),
                "project_name": project.get("name", ""),
                "kind": "artifact",
                "version": item.get("explicit_version", ""),
                "status": item.get("status", "observed"),
                "source_type": item.get("source_type", "file-library"),
                "source_id": item.get("source_id", ""),
                "source_path": item.get("source", ""),
                "sha256": item.get("content_sha256", ""),
                "content_signature": item.get("content_signature", ""),
                "created_at_utc": item.get("created_at_utc", ""),
                "observed_at_utc": item.get("observed_at_utc", ""),
                "supersedes": item.get("lineage", {}).get("supersedes", []),
                "notes": item.get("notes", ""),
            }
            for item in artifacts
        ]
    }
    temp = memory_vault / f".library-sync-{uuid.uuid4().hex[:10]}.json"
    try:
        atomic_write_json(temp, manifest)
        result = subprocess.run(
            [sys.executable, str(script), "--vault", str(library_vault), "import-manifest", str(temp)],
            text=True, capture_output=True, timeout=120,
        )
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    if result.returncode:
        return False, (result.stderr or result.stdout).strip()
    return True, f"library catalog synced at {library_vault}"


def render_handoff(project: dict[str, Any], status: dict[str, Any]) -> str:
    lines = [
        f"# {project['name']} — Project Handoff",
        "",
        f"- Project ID: `{project['project_id']}`",
        f"- Canonical root: `{project.get('canonical_root', '')}`",
        f"- Updated: `{status.get('updated_at_utc', '')}`",
        f"- Current goal: {status.get('current_goal') or 'Not recorded'}",
        "",
        "## Last verified state",
        status.get("summary") or "No checkpoint summary recorded.",
        "",
        "## Next steps",
    ]
    next_steps = status.get("next_steps", [])
    lines.extend([f"- {item}" for item in next_steps] or ["- No next step recorded."])
    lines.extend(["", "## Latest reconciled artifacts"])
    artifacts = status.get("latest_artifacts", [])
    if artifacts:
        for item in artifacts[-10:]:
            version = f" ({item.get('explicit_version')})" if item.get('explicit_version') else ""
            source = item.get('source_type') or item.get('source') or 'unknown source'
            created = item.get('created_at_utc') or item.get('observed_at_utc') or ''
            lines.append(f"- `{item.get('name', 'unnamed')}`{version} — {source} — {created} — `{item.get('id', '')}`")
    else:
        lines.append("- No cross-chat artifact has been reconciled yet.")
    lines.extend(["", "## Blockers"])
    blockers = status.get("blockers", [])
    lines.extend([f"- {item}" for item in blockers] or ["- None recorded."])
    git = status.get("git", {})
    lines.extend([
        "",
        "## Repository state at checkpoint",
        f"- Branch: `{git.get('branch', '')}`",
        f"- Commit: `{git.get('head', '')}`",
        f"- Dirty: `{git.get('dirty', False)}`",
        "",
        "Before changing this project in a new chat, confirm the project ID, canonical root, remote, and current repository state. Do not initialize a replacement project when this handoff identifies an existing one.",
    ])
    return "\n".join(lines) + "\n"


def init_project(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"Project root does not exist: {root}", file=sys.stderr); return 2
    vault = args.vault.expanduser().resolve()
    registry = load_registry(vault)
    evidence = identity_evidence(root)
    existing_marker = evidence["marker"]
    if existing_marker and not args.refresh:
        print(f"Project memory already initialized: {memory_root(root)}")
        print(existing_marker.get("project_id", ""))
        return 0
    candidates = candidate_scores(registry, evidence, args.name)
    dangerous = [c for c in candidates if c["score"] >= 80 and str(root) not in c.get("locations", [])]
    name_collision = [c for c in candidates if c["score"] >= 60 and c not in dangerous]
    if dangerous and not args.adopt_existing and not args.force_new:
        print("Refusing to initialize a likely duplicate project before continuity is resolved.", file=sys.stderr)
        for c in dangerous[:5]:
            print(f"- {c['project_id']} {c.get('name')} score={c['score']} locations={c.get('locations', [])} reasons={','.join(c['reasons'])}", file=sys.stderr)
        print("Use --adopt-existing after confirming it is the same project, or --force-new only when it is intentionally distinct.", file=sys.stderr)
        return 3
    if name_collision and not args.force_new and not args.adopt_existing:
        print("A similarly identified project already exists; refusing silent restart.", file=sys.stderr)
        for c in name_collision[:5]:
            print(f"- {c['project_id']} {c.get('name')} score={c['score']} locations={c.get('locations', [])}", file=sys.stderr)
        return 3
    if args.adopt_existing:
        if not candidates:
            print("No existing project candidate to adopt.", file=sys.stderr); return 3
        chosen = candidates[0]
        if len(candidates) > 1 and candidates[1]["score"] == chosen["score"]:
            print("Ambiguous adoption candidates; specify a unique name/path first.", file=sys.stderr); return 3
        project_id = chosen["project_id"]
        created_at = chosen.get("created_at_utc", now())
        aliases = sorted(set(chosen.get("aliases", []) + args.alias + [root.name]))
        canonical_root = str(root) if args.make_canonical else chosen.get("canonical_root", str(root))
    else:
        primary = evidence["git"]["remotes"][0] if evidence["git"]["remotes"] else ""
        project_id = "prj-" + (hashlib.sha256(primary.encode()).hexdigest()[:16] if primary else uuid.uuid4().hex[:16])
        created_at = now()
        aliases = sorted(set(args.alias + [root.name]))
        canonical_root = str(root)
    project = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "name": args.name,
        "aliases": aliases,
        "purpose": args.purpose,
        "canonical_root": canonical_root,
        "registry_hint": str(vault),
        "created_at_utc": created_at,
        "updated_at_utc": now(),
        "identity": {
            "remotes": evidence["git"]["remotes"],
            "manifests": evidence["manifests"],
            "fingerprint": evidence["fingerprint"],
        },
        "memory_policy": {
            "secrets": "never store",
            "verified_facts_require_provenance": True,
            "stale_research_requires_revalidation": True,
        },
    }
    mem = memory_root(root)
    mem.mkdir(parents=True, exist_ok=True)
    atomic_write_json(mem / "PROJECT.json", project)
    status_path = mem / "STATUS.json"
    if not status_path.exists():
        atomic_write_json(status_path, {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "created_at_utc": now(),
            "updated_at_utc": now(),
            "current_goal": "",
            "summary": "Project memory initialized; baseline not yet captured.",
            "next_steps": [],
            "blockers": [],
            "git": evidence["git"],
        })
    for filename in set(LEDGERS.values()) | {"sessions.jsonl"}:
        (mem / filename).touch(exist_ok=True)
    status = load_json(status_path, {})
    (mem / "HANDOFF.md").write_text(render_handoff(project, status), encoding="utf-8")
    record = registry["projects"].get(project_id, {})
    locations = sorted(set(record.get("locations", []) + [str(root)]))
    registry["projects"][project_id] = {
        "name": args.name,
        "aliases": sorted(set(record.get("aliases", []) + aliases)),
        "purpose": args.purpose or record.get("purpose", ""),
        "canonical_root": canonical_root,
        "locations": locations,
        "remotes": sorted(set(record.get("remotes", []) + evidence["git"]["remotes"])),
        "fingerprint": evidence["fingerprint"],
        "created_at_utc": created_at,
        "last_seen_at_utc": now(),
        "last_checkpoint_at_utc": record.get("last_checkpoint_at_utc", ""),
    }
    save_registry(vault, registry)
    synced, detail = sync_cross_project_catalog(root, vault)
    if not synced:
        print(f"Project memory initialized, but cross-project catalog sync failed: {detail}", file=sys.stderr)
        return 4
    print(f"Initialized project memory: {mem}")
    print(f"Project ID: {project_id}")
    if detail:
        print(detail)
    return 0


def identify_project(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    vault = args.vault.expanduser().resolve()
    evidence = identity_evidence(root)
    results = candidate_scores(load_registry(vault), evidence, args.query)
    output = {"evidence": evidence, "candidates": results}
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if evidence["marker"]:
            print(f"Local project marker: {evidence['marker'].get('project_id')} {evidence['marker'].get('name')}")
        for item in results[:10]:
            print(f"{item['score']:3} {item['project_id']} {item.get('name')} :: {', '.join(item['reasons'])} :: {item.get('locations', [])}")
    if len(results) >= 2 and results[0]["score"] == results[1]["score"] and results[0]["score"] >= 60:
        return 3
    return 0 if results or evidence["marker"] else 1


def checkpoint(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve(); vault = args.vault.expanduser().resolve()
    project = project_marker(root); mem = memory_root(root)
    git = git_snapshot(root)
    status_path = mem / "STATUS.json"
    previous = load_json(status_path, {}) or {}
    status = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project["project_id"],
        "created_at_utc": previous.get("created_at_utc", now()),
        "updated_at_utc": now(),
        "current_goal": args.goal if args.goal is not None else previous.get("current_goal", ""),
        "summary": args.summary,
        "next_steps": args.next_step,
        "blockers": args.blocker,
        "latest_artifacts": previous.get("latest_artifacts", []),
        "git": git,
        "active_task": str((root / ".agents" / "ACTIVE-TASK.json")) if (root / ".agents" / "ACTIVE-TASK.json").is_file() else "",
    }
    atomic_write_json(status_path, status)
    snapshots = mem / "snapshots"; snapshots.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    atomic_write_json(snapshots / f"{stamp}.json", {"project": project, "status": status})
    append_jsonl(mem / "sessions.jsonl", {
        "id": "session-" + uuid.uuid4().hex[:12], "at_utc": now(), "kind": "checkpoint",
        "summary": args.summary, "goal": status["current_goal"], "next_steps": args.next_step,
        "blockers": args.blocker, "git": git,
    })
    (mem / "HANDOFF.md").write_text(render_handoff(project, status), encoding="utf-8")
    registry = load_registry(vault)
    rec = registry["projects"].setdefault(project["project_id"], {})
    rec.update({
        "name": project["name"], "aliases": project.get("aliases", []),
        "canonical_root": project.get("canonical_root", str(root)), "locations": sorted(set(rec.get("locations", []) + [str(root)])),
        "remotes": project.get("identity", {}).get("remotes", []),
        "fingerprint": project.get("identity", {}).get("fingerprint", ""),
        "last_seen_at_utc": now(), "last_checkpoint_at_utc": status["updated_at_utc"],
    })
    save_registry(vault, registry)
    synced, detail = sync_cross_project_catalog(root, vault)
    if not synced:
        print(f"Checkpoint written, but cross-project catalog sync failed: {detail}", file=sys.stderr)
        return 4
    print(mem / "HANDOFF.md")
    if detail:
        print(detail)
    return 0


def remember(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve(); project = project_marker(root)
    combined = "\n".join(filter(None, [args.title, args.details, args.source, args.url]))
    if contains_secret(combined):
        print("Refusing to store content that resembles a secret or credential.", file=sys.stderr); return 4
    status = args.status
    if status == "verified" and not (args.source or args.url):
        print("Verified memories require provenance via --source or --url.", file=sys.stderr); return 2
    record = {
        "id": f"{args.kind[:3]}-{uuid.uuid4().hex[:12]}",
        "project_id": project["project_id"],
        "kind": args.kind,
        "title": args.title,
        "details": args.details,
        "source": args.source,
        "url": args.url,
        "version": args.version,
        "confidence": args.confidence,
        "status": status,
        "tags": args.tag,
        "observed_at_utc": now(),
        "last_verified_at_utc": now() if status == "verified" else "",
        "review_after": args.review_after,
    }
    append_jsonl(memory_root(root) / LEDGERS[args.kind], record)
    append_jsonl(memory_root(root) / "sessions.jsonl", {
        "id": "event-" + uuid.uuid4().hex[:12], "at_utc": now(), "kind": "memory-added",
        "memory_id": record["id"], "memory_kind": args.kind, "title": args.title,
    })
    print(record["id"])
    return 0



def artifact_identity(record: dict[str, Any]) -> str:
    for key in ("content_sha256", "content_signature", "source_id"):
        value = str(record.get(key, "")).strip()
        if value:
            return f"{key}:{value.lower()}"
    material = {
        "name": record.get("name", ""),
        "source_type": record.get("source_type", ""),
        "source": record.get("source", ""),
        "created_at_utc": record.get("created_at_utc", ""),
    }
    return "fallback:" + hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()


def normalize_artifact_candidate(candidate: dict[str, Any], project_id: str) -> dict[str, Any]:
    name = str(candidate.get("name") or candidate.get("filename") or candidate.get("title") or "").strip()
    if not name:
        raise ValueError("artifact candidate requires name, filename, or title")
    status = str(candidate.get("status", "observed"))
    if status not in {"observed", "verified", "superseded", "rejected"}:
        raise ValueError(f"unsupported artifact status: {status}")
    record = {
        "id": "art-" + uuid.uuid4().hex[:12],
        "project_id": project_id,
        "kind": "artifact",
        "name": name,
        "source_type": str(candidate.get("source_type", "file-library")),
        "source": str(candidate.get("source", "")),
        "source_id": str(candidate.get("source_id", "")),
        "created_at_utc": str(candidate.get("created_at_utc", "")),
        "modified_at_utc": str(candidate.get("modified_at_utc", "")),
        "explicit_version": str(candidate.get("explicit_version", "")),
        "content_sha256": str(candidate.get("content_sha256", "")),
        "content_signature": str(candidate.get("content_signature", "")),
        "notes": str(candidate.get("notes", "")),
        "status": status,
        "confidence": str(candidate.get("confidence", "medium")),
        "observed_at_utc": now(),
        "lineage": {"same_name_new_content": False, "supersedes": [], "related": []},
    }
    combined = json.dumps(record, ensure_ascii=False)
    if contains_secret(combined):
        raise ValueError("artifact candidate contains secret-like content")
    record["identity_key"] = artifact_identity(record)
    return record


def reconcile_artifacts(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    project = project_marker(root)
    mem = memory_root(root)
    raw = load_json(args.input.expanduser().resolve(), None)
    if isinstance(raw, dict):
        candidates = raw.get("artifacts", raw.get("entries", []))
    else:
        candidates = raw
    if not isinstance(candidates, list) or not candidates:
        print("Artifact input must contain a non-empty list or an artifacts/entries list.", file=sys.stderr)
        return 2
    existing = read_jsonl(mem / LEDGERS["artifact"])
    by_identity = {str(item.get("identity_key") or artifact_identity(item)): item for item in existing}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in existing:
        by_name.setdefault(str(item.get("name", "")).lower(), []).append(item)
    added: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            errors.append(f"candidate {index}: expected object")
            continue
        try:
            record = normalize_artifact_candidate(candidate, project["project_id"])
        except ValueError as exc:
            errors.append(f"candidate {index}: {exc}")
            continue
        duplicate = by_identity.get(record["identity_key"])
        if duplicate:
            skipped.append({"name": record["name"], "reason": "already reconciled", "existing_id": duplicate.get("id")})
            continue
        peers = by_name.get(record["name"].lower(), [])
        if peers:
            record["lineage"]["same_name_new_content"] = True
            record["lineage"]["related"] = [str(item.get("id", "")) for item in peers if item.get("id")]
            newest = sorted(peers, key=lambda item: str(item.get("created_at_utc") or item.get("observed_at_utc") or ""))[-1]
            incoming_time = record.get("created_at_utc") or record.get("observed_at_utc") or ""
            prior_time = newest.get("created_at_utc") or newest.get("observed_at_utc") or ""
            if record.get("explicit_version") or (incoming_time and prior_time and incoming_time >= prior_time):
                if newest.get("id"):
                    record["lineage"]["supersedes"] = [newest["id"]]
        append_jsonl(mem / LEDGERS["artifact"], record)
        existing.append(record)
        by_identity[record["identity_key"]] = record
        by_name.setdefault(record["name"].lower(), []).append(record)
        added.append(record)
    if errors:
        print("Artifact reconciliation rejected invalid candidates:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    status_path = mem / "STATUS.json"
    status = load_json(status_path, {}) or {}
    latest = sorted(existing, key=lambda item: str(item.get("created_at_utc") or item.get("observed_at_utc") or ""))[-20:]
    status["latest_artifacts"] = [
        {key: item.get(key, "") for key in ("id", "name", "explicit_version", "source_type", "source_id", "created_at_utc", "observed_at_utc", "status")}
        for item in latest
    ]
    status["updated_at_utc"] = now()
    atomic_write_json(status_path, status)
    (mem / "HANDOFF.md").write_text(render_handoff(project, status), encoding="utf-8")
    append_jsonl(mem / "sessions.jsonl", {
        "id": "sync-" + uuid.uuid4().hex[:12],
        "at_utc": now(),
        "kind": "cross-chat-artifact-reconciliation",
        "added_artifact_ids": [item["id"] for item in added],
        "skipped": skipped,
        "source_manifest": str(args.input.expanduser().resolve()),
    })
    memory_vault = args.vault.expanduser().resolve()
    synced, detail = sync_cross_project_catalog(root, memory_vault)
    if not synced:
        print(f"Artifacts reconciled locally, but cross-project catalog sync failed: {detail}", file=sys.stderr)
        return 4
    library_synced, library_detail = sync_artifacts_to_library(project, added, memory_vault)
    if not library_synced:
        print(f"Artifacts and project catalog were updated, but library catalog sync failed: {library_detail}", file=sys.stderr)
        return 5
    print(json.dumps({
        "project_id": project["project_id"],
        "added": added,
        "skipped": skipped,
        "handoff": str(mem / "HANDOFF.md"),
        "catalog_sync": detail,
        "library_sync": library_detail,
    }, indent=2, ensure_ascii=False))
    return 0


def list_artifacts(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    project_marker(root)
    artifacts = read_jsonl(memory_root(root) / LEDGERS["artifact"])
    artifacts.sort(key=lambda item: str(item.get("created_at_utc") or item.get("observed_at_utc") or ""), reverse=True)
    if args.json:
        print(json.dumps(artifacts, indent=2, ensure_ascii=False))
    else:
        for item in artifacts:
            version = f" ({item.get('explicit_version')})" if item.get('explicit_version') else ""
            relation = " same-name-new-content" if item.get("lineage", {}).get("same_name_new_content") else ""
            print(f"{item.get('id')} {item.get('name')}{version} {item.get('source_type')} {item.get('created_at_utc')}{relation}")
    return 0

def choose_project(registry: dict[str, Any], query: str) -> tuple[dict[str, Any] | None, int]:
    fake = {"root": "", "directory_name": "", "git": {"remotes": []}, "manifests": {}, "marker": {}, "fingerprint": ""}
    candidates = candidate_scores(registry, fake, query)
    if not candidates:
        return None, 1
    if len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"]:
        return {"ambiguous": candidates[:10]}, 3
    return candidates[0], 0


def resume(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve(); registry = load_registry(vault)
    if args.root:
        root = args.root.expanduser().resolve()
        if not (memory_root(root) / "PROJECT.json").is_file():
            evidence = identity_evidence(root)
            candidates = candidate_scores(registry, evidence, args.query or root.name)
            if not candidates:
                print("No matching remembered project found.", file=sys.stderr); return 1
            if len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"]:
                print(json.dumps({"ambiguous": candidates[:10]}, indent=2), file=sys.stderr); return 3
            root = Path(candidates[0]["canonical_root"])
    else:
        selected, code = choose_project(registry, args.query)
        if code:
            print(json.dumps(selected or {"error": "not found"}, indent=2), file=sys.stderr); return code
        root = Path(selected["canonical_root"])
    project = project_marker(root); status = load_json(memory_root(root) / "STATUS.json", {}) or {}
    output = {
        "project": project,
        "status": status,
        "handoff": (memory_root(root) / "HANDOFF.md").read_text(encoding="utf-8") if (memory_root(root) / "HANDOFF.md").is_file() else "",
        "identity": identity_evidence(root),
    }
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(output["handoff"])
    return 0


def search(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve(); registry = load_registry(vault)
    selected, _ = choose_project(registry, args.query)
    projects = []
    fake = {"root": "", "directory_name": "", "git": {"remotes": []}, "manifests": {}, "marker": {}, "fingerprint": ""}
    projects = candidate_scores(registry, fake, args.query)
    hits: list[dict[str, Any]] = []
    q = args.query.lower()
    for project in registry.get("projects", {}).values():
        root = Path(project.get("canonical_root", ""))
        mem = memory_root(root)
        if not mem.is_dir():
            continue
        for filename in set(LEDGERS.values()) | {"sessions.jsonl"}:
            try:
                entries = read_jsonl(mem / filename)
            except ValueError:
                continue
            for entry in entries:
                if q in json.dumps(entry, ensure_ascii=False).lower():
                    hits.append({"project": project.get("name"), "root": str(root), "ledger": filename, "entry": entry})
    print(json.dumps({"projects": projects[:20], "memory_hits": hits[:100]}, indent=2, ensure_ascii=False))
    return 0 if projects or hits else 1


def list_projects(args: argparse.Namespace) -> int:
    registry = load_registry(args.vault.expanduser().resolve())
    rows = [{"project_id": pid, **record} for pid, record in registry.get("projects", {}).items()]
    rows.sort(key=lambda r: r.get("last_seen_at_utc", ""), reverse=True)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def doctor(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve(); vault = args.vault.expanduser().resolve()
    errors: list[str] = []; warnings: list[str] = []
    mem = memory_root(root)
    for required in ("PROJECT.json", "STATUS.json", "HANDOFF.md", "sessions.jsonl"):
        if not (mem / required).is_file(): errors.append(f"missing {mem / required}")
    try:
        project = project_marker(root)
    except Exception as exc:
        errors.append(str(exc)); project = {}
    try:
        status = load_json(mem / "STATUS.json", {}) or {}
        if status.get("project_id") != project.get("project_id"):
            errors.append("STATUS.json project_id does not match PROJECT.json")
    except Exception as exc:
        errors.append(f"invalid STATUS.json: {exc}")
    for filename in set(LEDGERS.values()) | {"sessions.jsonl"}:
        try:
            for entry in read_jsonl(mem / filename):
                if contains_secret(json.dumps(entry, ensure_ascii=False)):
                    errors.append(f"secret-like content in {filename}:{entry.get('id', '<unknown>')}")
        except Exception as exc:
            errors.append(str(exc))
    try:
        artifacts = read_jsonl(mem / LEDGERS["artifact"])
        identities: dict[str, str] = {}
        artifact_ids = {str(item.get("id", "")) for item in artifacts}
        for item in artifacts:
            identity = str(item.get("identity_key") or artifact_identity(item))
            if identity in identities:
                errors.append(f"duplicate artifact identity: {identity} ({identities[identity]} and {item.get('id')})")
            identities[identity] = str(item.get("id", ""))
        latest_ids = {str(item.get("id", "")) for item in status.get("latest_artifacts", [])}
        missing_latest = sorted(latest_ids - artifact_ids)
        if missing_latest:
            errors.append(f"STATUS.json references missing artifact IDs: {missing_latest}")
    except Exception as exc:
        errors.append(f"artifact ledger error: {exc}")
    try:
        registry = load_registry(vault)
        rec = registry.get("projects", {}).get(project.get("project_id"))
        if not rec:
            errors.append("project is missing from central registry")
        else:
            if str(root) not in [str(Path(p).expanduser().resolve()) for p in rec.get("locations", [])]:
                errors.append("current root is not registered as a project location")
            current = identity_evidence(root)
            registered_remotes = set(rec.get("remotes", []))
            current_remotes = set(current.get("git", {}).get("remotes", []))
            if registered_remotes and current_remotes and not (registered_remotes & current_remotes):
                warnings.append("current git remotes do not match remembered remotes")
    except Exception as exc:
        errors.append(f"registry error: {exc}")
    if errors:
        print("Project memory doctor FAILED", file=sys.stderr)
        for item in errors: print(f"ERROR: {item}", file=sys.stderr)
    for item in warnings: print(f"WARNING: {item}", file=sys.stderr)
    if errors or (warnings and args.strict_warnings): return 1
    print(f"Project memory doctor passed: {project.get('project_id')} at {root}")
    return 0


def export_memory(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve(); project = project_marker(root); mem = memory_root(root)
    output = args.output.expanduser().resolve() if args.output else Path.cwd() / f"{slug(project['name'])}-project-memory.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(mem.rglob("*")):
            if path.is_file():
                zf.write(path, f"project-memory/{path.relative_to(mem).as_posix()}")
        zf.writestr("project-memory/IMPORT-README.txt", (
            "This archive is a portable project-memory snapshot. Extract its contents into a project's .agents-memory directory only after confirming the project ID and canonical repository. Do not overwrite a newer memory state blindly.\n"
        ))
    print(output)
    return 0


def add_common_vault(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vault", type=Path, default=default_vault())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init"); p.add_argument("root", type=Path); p.add_argument("--name", required=True); p.add_argument("--alias", action="append", default=[]); p.add_argument("--purpose", default=""); p.add_argument("--adopt-existing", action="store_true"); p.add_argument("--make-canonical", action="store_true"); p.add_argument("--force-new", action="store_true"); p.add_argument("--refresh", action="store_true"); add_common_vault(p)
    p = sub.add_parser("identify"); p.add_argument("root", type=Path); p.add_argument("--query", default=""); p.add_argument("--json", action="store_true"); add_common_vault(p)
    p = sub.add_parser("checkpoint"); p.add_argument("root", type=Path); p.add_argument("--summary", required=True); p.add_argument("--goal"); p.add_argument("--next-step", action="append", default=[]); p.add_argument("--blocker", action="append", default=[]); add_common_vault(p)
    p = sub.add_parser("remember"); p.add_argument("root", type=Path); p.add_argument("--kind", choices=sorted(LEDGERS), required=True); p.add_argument("--title", required=True); p.add_argument("--details", required=True); p.add_argument("--source", default=""); p.add_argument("--url", default=""); p.add_argument("--version", default=""); p.add_argument("--confidence", choices=("low", "medium", "high"), default="medium"); p.add_argument("--status", choices=("hypothesis", "observed", "verified", "superseded", "rejected"), default="observed"); p.add_argument("--review-after", default=""); p.add_argument("--tag", action="append", default=[])
    p = sub.add_parser("reconcile-artifacts"); p.add_argument("root", type=Path); p.add_argument("--input", type=Path, required=True); add_common_vault(p)
    p = sub.add_parser("list-artifacts"); p.add_argument("root", type=Path); p.add_argument("--json", action="store_true")
    p = sub.add_parser("resume"); p.add_argument("--root", type=Path); p.add_argument("--query", default=""); p.add_argument("--json", action="store_true"); add_common_vault(p)
    p = sub.add_parser("search"); p.add_argument("query"); add_common_vault(p)
    p = sub.add_parser("list"); add_common_vault(p)
    p = sub.add_parser("doctor"); p.add_argument("root", type=Path); p.add_argument("--strict-warnings", action="store_true"); add_common_vault(p)
    p = sub.add_parser("export"); p.add_argument("root", type=Path); p.add_argument("--output", type=Path)

    args = parser.parse_args()
    return {
        "init": init_project,
        "identify": identify_project,
        "checkpoint": checkpoint,
        "remember": remember,
        "reconcile-artifacts": reconcile_artifacts,
        "list-artifacts": list_artifacts,
        "resume": resume,
        "search": search,
        "list": list_projects,
        "doctor": doctor,
        "export": export_memory,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
