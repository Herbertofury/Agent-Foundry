#!/usr/bin/env python3
"""Maintain a durable cross-project catalog and human-readable project database.

The per-project `.agents-memory/` directory remains the source of truth for one
project. This catalog is the cross-project index used to locate projects, track
version/artifact progression, and prevent a later chat from silently restarting or
continuing an older copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]{8,}", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def default_vault() -> Path:
    return Path(os.environ.get("AGENTS_MEMORY_HOME", "~/.agents-second-brain")).expanduser().resolve()


def catalog_path(vault: Path) -> Path:
    return vault / "project-catalog.json"


def markdown_path(vault: Path) -> Path:
    return vault / "USER-PROJECTS-DATABASE.md"


def events_path(vault: Path) -> Path:
    return vault / "project-catalog-events.jsonl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def contains_secret(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def locate_seed() -> Path | None:
    script = Path(__file__).resolve()
    candidates = [
        script.parents[1] / "assets" / "memory" / "USER-PROJECTS-DATABASE.seed.md",
        script.parent.parent / "memory" / "USER-PROJECTS-DATABASE.seed.md",
        script.parent.parent / "USER-PROJECTS-DATABASE.seed.md",
        script.parent / "USER-PROJECTS-DATABASE.seed.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def next_project_id(projects: dict[str, Any]) -> str:
    numbers = []
    for project_id in projects:
        match = re.fullmatch(r"PRJ-(\d+)", project_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"PRJ-{max(numbers, default=0) + 1:03d}"


def split_markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(PRJ-\d+)\s+—\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.start():end].rstrip() + "\n"
    return sections


def parse_seed_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    sections = split_markdown_sections(text)
    projects: dict[str, Any] = {}
    row_pattern = re.compile(
        r"^\|\s*(PRJ-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(High|Medium|Low)\s*\|\s*(.*?)\s*\|$"
    )
    for line in text.splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        project_id, name, status, latest, confidence, next_action = match.groups()
        details = sections.get(project_id, "")
        aliases: list[str] = []
        alias_match = re.search(r"(?m)^\*\*Aliases:\*\*\s*(.+)$", details)
        if alias_match:
            aliases = [item.strip() for item in alias_match.group(1).split(",") if item.strip()]
        projects[project_id] = {
            "project_id": project_id,
            "name": name.strip(),
            "aliases": aliases,
            "status": status.strip(),
            "confidence": confidence.strip(),
            "latest_version_or_artifact": latest.strip(),
            "canonical_roots": [],
            "relationships": [],
            "risks": [],
            "sources": [{
                "kind": "seed-markdown",
                "path": str(path),
                "sha256": sha256(path),
                "observed_at_utc": now(),
            }],
            "versions": [{
                "id": "ver-" + uuid.uuid4().hex[:12],
                "label": latest.strip(),
                "artifact": latest.strip(),
                "status": "recovered",
                "confidence": confidence.strip().lower(),
                "observed_at_utc": now(),
                "is_latest": True,
                "source": "seed-markdown",
            }],
            "artifacts": [],
            "last_checkpoint_at_utc": "",
            "next_action": next_action.strip(),
            "details_markdown": details,
            "created_at_utc": now(),
            "updated_at_utc": now(),
        }
    if not projects:
        raise ValueError(f"No project rows found in seed database: {path}")
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "Bert's Cross-Chat Project Database",
        "created_at_utc": now(),
        "updated_at_utc": now(),
        "seed": {"path": str(path), "sha256": sha256(path), "imported_at_utc": now()},
        "projects": projects,
    }


def load_catalog(vault: Path) -> dict[str, Any]:
    data = load_json(catalog_path(vault), None)
    if data is None:
        raise FileNotFoundError(f"Project catalog is not initialized: {catalog_path(vault)}")
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("projects"), dict):
        raise ValueError(f"Unsupported or invalid project catalog: {catalog_path(vault)}")
    return data


def save_catalog(vault: Path, data: dict[str, Any], *, render: bool = True) -> None:
    data["updated_at_utc"] = now()
    atomic_write_json(catalog_path(vault), data)
    if render:
        atomic_write(markdown_path(vault), render_markdown(data))


def unique_extend(current: list[Any], incoming: list[Any]) -> list[Any]:
    output = list(current)
    fingerprints = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in output}
    for item in incoming:
        fingerprint = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if fingerprint not in fingerprints:
            output.append(item)
            fingerprints.add(fingerprint)
    return output


def render_markdown(data: dict[str, Any]) -> str:
    projects = data.get("projects", {})
    lines = [
        "# Bert's Cross-Chat Project Database",
        "",
        f"**Updated:** {data.get('updated_at_utc', '')}",
        "**Purpose:** Preserve project identity, versions, artifacts, checkpoints, relationships, and next actions across chats and agents.",
        "",
        "> This is the durable human-readable mirror of `project-catalog.json`. Preserve lineage. Do not delete older versions merely because a newer artifact exists. Resolve the canonical repository and verify the latest-good state before mutation.",
        "",
        "## Executive project dashboard",
        "",
        "| ID | Project / family | Current tracked state | Latest known version or artifact | Confidence | Immediate continuity action |",
        "|---|---|---|---|---|---|",
    ]
    for project_id in sorted(projects):
        project = projects[project_id]
        values = [
            project_id,
            project.get("name", ""),
            project.get("status", ""),
            project.get("latest_version_or_artifact", ""),
            project.get("confidence", ""),
            project.get("next_action", ""),
        ]
        safe = [str(value).replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(safe) + " |")
    lines.extend(["", "## Project records", ""])
    for project_id in sorted(projects):
        project = projects[project_id]
        lines.extend([
            f"### {project_id} — {project.get('name', '')}",
            "",
            f"- **Status:** {project.get('status', '')}",
            f"- **Confidence:** {project.get('confidence', '')}",
            f"- **Latest:** {project.get('latest_version_or_artifact', '')}",
            f"- **Last checkpoint:** {project.get('last_checkpoint_at_utc') or 'Not recorded'}",
            f"- **Next action:** {project.get('next_action') or 'Not recorded'}",
        ])
        aliases = project.get("aliases", [])
        if aliases:
            lines.append(f"- **Aliases:** {', '.join(aliases)}")
        roots = project.get("canonical_roots", [])
        if roots:
            lines.append(f"- **Known roots:** {', '.join(f'`{root}`' for root in roots)}")
        versions = project.get("versions", [])
        if versions:
            lines.extend(["", "#### Version and artifact lineage"])
            ordered = sorted(versions, key=lambda item: str(item.get("observed_at_utc", "")), reverse=True)
            for item in ordered:
                latest = " **LATEST**" if item.get("is_latest") else ""
                label = item.get("label") or item.get("artifact") or "Unlabeled version"
                detail = item.get("artifact") if item.get("artifact") and item.get("artifact") != label else ""
                suffix = f" — {detail}" if detail else ""
                lines.append(f"- {label}{suffix}{latest}; status={item.get('status', 'candidate')}; confidence={item.get('confidence', 'unknown')}; observed={item.get('observed_at_utc', '')}")
        artifacts = project.get("artifacts", [])
        if artifacts:
            lines.extend(["", "#### Tracked artifacts"])
            for item in artifacts[-20:]:
                lines.append(f"- `{item.get('name', 'unnamed')}` — version={item.get('version', '') or 'unknown'} — hash={item.get('sha256', '') or 'unavailable'} — source={item.get('source_id', '') or item.get('source', '') or 'unknown'}")
        if project.get("risks"):
            lines.extend(["", "#### Preservation and regression warnings"])
            lines.extend(f"- {item}" for item in project["risks"])
        details = project.get("details_markdown", "").strip()
        if details:
            lines.extend(["", "<details>", "<summary>Recovered source detail (preserved)</summary>", "", details, "", "</details>"])
        lines.extend(["", "---", ""])
    lines.extend([
        "## Catalog update protocol",
        "",
        "1. Search cross-chat sources and recent uploads before continuing a named project.",
        "2. Open plausible newer artifacts and compare content, not filenames alone.",
        "3. Reconcile project, version, artifact, hash, source, checkpoint, confidence, and supersession into the JSON catalog.",
        "4. Render this Markdown mirror and reread the changed project record before editing code.",
        "5. Export the catalog when no writable durable store is available.",
        "",
    ])
    return "\n".join(lines)


def find_project(data: dict[str, Any], project_id: str = "", name: str = "") -> tuple[str | None, list[str]]:
    projects = data.get("projects", {})
    if project_id:
        return (project_id, []) if project_id in projects else (None, [])
    query = normalize(name)
    if not query:
        return None, []
    exact: list[str] = []
    partial: list[str] = []
    for pid, project in projects.items():
        names = [project.get("name", ""), *project.get("aliases", [])]
        normalized = {normalize(str(value)) for value in names if str(value).strip()}
        if query in normalized:
            exact.append(pid)
        elif any(query and query in value for value in normalized):
            partial.append(pid)
    if len(exact) == 1:
        return exact[0], exact
    if len(exact) > 1:
        return None, exact
    return (partial[0], partial) if len(partial) == 1 else (None, partial)


def normalize_version_record(record: dict[str, Any]) -> dict[str, Any]:
    output = {
        "id": str(record.get("id") or "ver-" + uuid.uuid4().hex[:12]),
        "label": str(record.get("label") or record.get("version") or record.get("artifact") or "Unlabeled candidate"),
        "artifact": str(record.get("artifact", "")),
        "status": str(record.get("status", "candidate")),
        "confidence": str(record.get("confidence", "medium")),
        "observed_at_utc": str(record.get("observed_at_utc") or record.get("created_at_utc") or now()),
        "source": str(record.get("source", "")),
        "source_id": str(record.get("source_id", "")),
        "sha256": str(record.get("sha256", "")),
        "supersedes": list(record.get("supersedes", [])),
        "is_latest": bool(record.get("is_latest") or record.get("make_latest")),
        "notes": str(record.get("notes", "")),
    }
    if contains_secret(output):
        raise ValueError("version record contains secret-like content")
    return output


def version_key(item: dict[str, Any]) -> str:
    material = [item.get("label", ""), item.get("artifact", ""), item.get("source_id", ""), item.get("sha256", "")]
    return hashlib.sha256("\x1f".join(str(value) for value in material).encode("utf-8")).hexdigest()


def reconcile_entry(project: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    if contains_secret(incoming):
        raise ValueError("project update contains secret-like content")
    for field in ("name", "status", "confidence", "next_action"):
        if str(incoming.get(field, "")).strip():
            project[field] = str(incoming[field]).strip()
    for field in ("aliases", "canonical_roots", "relationships", "risks", "sources"):
        values = incoming.get(field, [])
        if isinstance(values, list):
            project[field] = unique_extend(project.get(field, []), values)
    if str(incoming.get("details_markdown", "")).strip():
        project["details_markdown"] = str(incoming["details_markdown"]).strip() + "\n"
    incoming_versions: list[dict[str, Any]] = []
    if isinstance(incoming.get("version"), dict):
        incoming_versions.append(incoming["version"])
    if isinstance(incoming.get("versions"), list):
        incoming_versions.extend(item for item in incoming["versions"] if isinstance(item, dict))
    versions = list(project.get("versions", []))
    keys = {version_key(item): item for item in versions}
    latest_candidate: dict[str, Any] | None = None
    for raw in incoming_versions:
        item = normalize_version_record(raw)
        key = version_key(item)
        if key not in keys:
            versions.append(item)
            keys[key] = item
        else:
            existing = keys[key]
            for field, value in item.items():
                if value not in ("", [], None, False):
                    existing[field] = value
            item = existing
        if item.get("is_latest"):
            latest_candidate = item
    if latest_candidate:
        for item in versions:
            item["is_latest"] = item is latest_candidate
        project["latest_version_or_artifact"] = latest_candidate.get("label") or latest_candidate.get("artifact") or project.get("latest_version_or_artifact", "")
    elif str(incoming.get("latest_version_or_artifact", "")).strip():
        # Do not silently promote an unproven latest value. Keep it as a candidate note.
        candidate = normalize_version_record({
            "label": str(incoming["latest_version_or_artifact"]).strip(),
            "status": "candidate",
            "confidence": incoming.get("confidence", "medium"),
            "source": "unpromoted-catalog-update",
        })
        key = version_key(candidate)
        if key not in keys:
            versions.append(candidate)
    project["versions"] = versions
    artifacts = list(project.get("artifacts", []))
    incoming_artifacts: list[dict[str, Any]] = []
    if isinstance(incoming.get("artifact"), dict):
        incoming_artifacts.append(incoming["artifact"])
    if isinstance(incoming.get("artifacts"), list):
        incoming_artifacts.extend(item for item in incoming["artifacts"] if isinstance(item, dict))
    artifact_keys = {
        (str(item.get("sha256", "")), str(item.get("source_id", "")), str(item.get("name", "")), str(item.get("version", "")))
        for item in artifacts
    }
    for raw in incoming_artifacts:
        item = {
            "id": str(raw.get("id") or "art-" + uuid.uuid4().hex[:12]),
            "name": str(raw.get("name", "")),
            "version": str(raw.get("version", "")),
            "sha256": str(raw.get("sha256", "")),
            "source": str(raw.get("source", "")),
            "source_id": str(raw.get("source_id", "")),
            "created_at_utc": str(raw.get("created_at_utc", "")),
            "observed_at_utc": str(raw.get("observed_at_utc") or now()),
            "status": str(raw.get("status", "candidate")),
            "supersedes": list(raw.get("supersedes", [])),
            "notes": str(raw.get("notes", "")),
        }
        if not item["name"]:
            raise ValueError("artifact record requires name")
        if contains_secret(item):
            raise ValueError("artifact record contains secret-like content")
        key = (item["sha256"], item["source_id"], item["name"], item["version"])
        if key not in artifact_keys:
            artifacts.append(item)
            artifact_keys.add(key)
    project["artifacts"] = artifacts
    if str(incoming.get("last_checkpoint_at_utc", "")).strip():
        project["last_checkpoint_at_utc"] = str(incoming["last_checkpoint_at_utc"]).strip()
    project["updated_at_utc"] = now()
    return project


def bootstrap(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve()
    existing = catalog_path(vault)
    if existing.is_file() and not args.force:
        data = load_catalog(vault)
        save_catalog(vault, data)
        print(f"Project catalog already initialized with {len(data['projects'])} projects: {existing}")
        return 0
    seed = args.seed.expanduser().resolve() if args.seed else locate_seed()
    if not seed or not seed.is_file():
        print("No project database seed found; pass --seed.", file=sys.stderr)
        return 2
    data = parse_seed_markdown(seed)
    save_catalog(vault, data)
    append_jsonl(events_path(vault), {
        "id": "evt-" + uuid.uuid4().hex[:12],
        "at_utc": now(),
        "kind": "catalog-bootstrap",
        "seed": str(seed),
        "seed_sha256": sha256(seed),
        "project_count": len(data["projects"]),
    })
    print(f"Initialized project catalog with {len(data['projects'])} projects")
    print(catalog_path(vault))
    print(markdown_path(vault))
    return 0


def reconcile(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve()
    data = load_catalog(vault)
    manifest = load_json(args.input.expanduser().resolve(), None)
    updates = manifest.get("projects", manifest.get("entries", [])) if isinstance(manifest, dict) else manifest
    if not isinstance(updates, list) or not updates:
        print("Update manifest must be a non-empty list or contain projects/entries.", file=sys.stderr)
        return 2
    changed: list[str] = []
    created: list[str] = []
    for index, incoming in enumerate(updates, 1):
        if not isinstance(incoming, dict):
            print(f"Update {index} must be an object.", file=sys.stderr)
            return 2
        project_id, matches = find_project(data, str(incoming.get("project_id", "")), str(incoming.get("name", "")))
        if project_id is None:
            if matches:
                print(f"Ambiguous project update {index}: matches {matches}", file=sys.stderr)
                return 3
            if not args.allow_new:
                print(f"Unknown project update {index}; use --allow-new only after identity is resolved.", file=sys.stderr)
                return 3
            project_id = str(incoming.get("project_id") or next_project_id(data["projects"]))
            if project_id in data["projects"]:
                print(f"Project ID already exists: {project_id}", file=sys.stderr)
                return 3
            name = str(incoming.get("name", "")).strip()
            if not name:
                print(f"New project update {index} requires name.", file=sys.stderr)
                return 2
            data["projects"][project_id] = {
                "project_id": project_id,
                "name": name,
                "aliases": [],
                "status": "UNRESOLVED IDENTITY",
                "confidence": "Low",
                "latest_version_or_artifact": "Not yet verified",
                "canonical_roots": [],
                "relationships": [],
                "risks": [],
                "sources": [],
                "versions": [],
                "artifacts": [],
                "last_checkpoint_at_utc": "",
                "next_action": "Resolve canonical project identity before mutation.",
                "details_markdown": "",
                "created_at_utc": now(),
                "updated_at_utc": now(),
            }
            created.append(project_id)
        try:
            reconcile_entry(data["projects"][project_id], incoming)
        except ValueError as exc:
            print(f"Update {index} rejected: {exc}", file=sys.stderr)
            return 2
        changed.append(project_id)
    save_catalog(vault, data)
    append_jsonl(events_path(vault), {
        "id": "evt-" + uuid.uuid4().hex[:12],
        "at_utc": now(),
        "kind": "catalog-reconcile",
        "source_manifest": str(args.input.expanduser().resolve()),
        "changed_project_ids": changed,
        "created_project_ids": created,
    })
    print(json.dumps({"changed": changed, "created": created, "catalog": str(catalog_path(vault)), "markdown": str(markdown_path(vault))}, indent=2))
    return 0


def sync_project(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    vault = args.vault.expanduser().resolve()
    if not catalog_path(vault).is_file():
        seed = locate_seed()
        if not seed:
            print("Project catalog is missing and no bundled seed is available.", file=sys.stderr)
            return 2
        code = bootstrap(argparse.Namespace(vault=vault, seed=seed, force=False))
        if code:
            return code
    project_path = root / ".agents-memory" / "PROJECT.json"
    status_path = root / ".agents-memory" / "STATUS.json"
    if not project_path.is_file() or not status_path.is_file():
        print(f"Project memory is not initialized in {root}", file=sys.stderr)
        return 2
    project = load_json(project_path, {}) or {}
    status = load_json(status_path, {}) or {}
    artifact_records = []
    artifacts_path = root / ".agents-memory" / "artifacts.jsonl"
    if artifacts_path.is_file():
        for line in artifacts_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                artifact_records.append(json.loads(line))
    aliases = [str(value) for value in project.get("aliases", [])]
    incoming = {
        "project_id": project.get("catalog_project_id", ""),
        "name": project.get("name", root.name),
        "aliases": aliases,
        "canonical_roots": [project.get("canonical_root", str(root)), str(root)],
        "status": status.get("catalog_status") or ("ACTIVE" if status.get("current_goal") else "RECOVERED"),
        "confidence": status.get("catalog_confidence") or "High",
        "last_checkpoint_at_utc": status.get("updated_at_utc", ""),
        "next_action": (status.get("next_steps") or ["Verify the current runtime and continue from the latest checkpoint."])[0],
        "sources": [{
            "kind": "project-memory",
            "project_id": project.get("project_id", ""),
            "root": str(root),
            "observed_at_utc": now(),
        }],
        "artifacts": [{
            "name": item.get("name", "unnamed"),
            "version": item.get("explicit_version", ""),
            "sha256": item.get("content_sha256", ""),
            "source": item.get("source_type", ""),
            "source_id": item.get("source_id", ""),
            "created_at_utc": item.get("created_at_utc", ""),
            "status": item.get("status", "candidate"),
            "notes": item.get("notes", ""),
            "supersedes": item.get("lineage", {}).get("supersedes", []),
        } for item in artifact_records[-50:]],
    }
    if artifact_records:
        newest = sorted(artifact_records, key=lambda item: str(item.get("created_at_utc") or item.get("observed_at_utc") or ""))[-1]
        incoming["version"] = {
            "label": newest.get("explicit_version") or newest.get("name") or "Latest reconciled artifact",
            "artifact": newest.get("name", ""),
            "status": newest.get("status", "candidate"),
            "confidence": newest.get("confidence", "medium"),
            "observed_at_utc": newest.get("created_at_utc") or newest.get("observed_at_utc") or now(),
            "source": newest.get("source_type", ""),
            "source_id": newest.get("source_id", ""),
            "sha256": newest.get("content_sha256", ""),
            "is_latest": newest.get("status") == "verified",
        }
    data = load_catalog(vault)
    project_id, matches = find_project(data, "", str(incoming["name"]))
    if project_id is None:
        # A repository-owned project ID is not the same namespace as the recovered PRJ IDs.
        # Create only when there is no ambiguous name/alias match.
        if matches:
            print(f"Ambiguous project catalog identity for {incoming['name']}: {matches}", file=sys.stderr)
            return 3
        project_id = next_project_id(data["projects"])
        data["projects"][project_id] = {
            "project_id": project_id,
            "name": incoming["name"],
            "aliases": aliases,
            "status": "ACTIVE",
            "confidence": "High",
            "latest_version_or_artifact": "Project memory initialized",
            "canonical_roots": [],
            "relationships": [],
            "risks": [],
            "sources": [],
            "versions": [],
            "artifacts": [],
            "last_checkpoint_at_utc": "",
            "next_action": incoming["next_action"],
            "details_markdown": "",
            "created_at_utc": now(),
            "updated_at_utc": now(),
        }
    incoming["project_id"] = project_id
    reconcile_entry(data["projects"][project_id], incoming)
    save_catalog(vault, data)
    append_jsonl(events_path(vault), {
        "id": "evt-" + uuid.uuid4().hex[:12],
        "at_utc": now(),
        "kind": "project-memory-sync",
        "catalog_project_id": project_id,
        "project_memory_id": project.get("project_id", ""),
        "root": str(root),
    })
    print(json.dumps({"catalog_project_id": project_id, "catalog": str(catalog_path(vault)), "markdown": str(markdown_path(vault))}, indent=2))
    return 0


def list_projects(args: argparse.Namespace) -> int:
    data = load_catalog(args.vault.expanduser().resolve())
    rows = []
    query = normalize(args.query or "")
    for project_id, project in data["projects"].items():
        haystack = normalize(" ".join([project_id, project.get("name", ""), *project.get("aliases", []), project.get("latest_version_or_artifact", ""), project.get("status", "")]))
        if query and query not in haystack:
            continue
        rows.append({
            "project_id": project_id,
            "name": project.get("name", ""),
            "status": project.get("status", ""),
            "latest": project.get("latest_version_or_artifact", ""),
            "confidence": project.get("confidence", ""),
            "last_checkpoint_at_utc": project.get("last_checkpoint_at_utc", ""),
            "next_action": project.get("next_action", ""),
        })
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            print(f"{row['project_id']} | {row['name']} | {row['status']} | {row['latest']} | {row['confidence']} | {row['next_action']}")
    return 0 if rows else 1


def show(args: argparse.Namespace) -> int:
    data = load_catalog(args.vault.expanduser().resolve())
    project_id, matches = find_project(data, args.project_id or "", args.query or "")
    if project_id is None:
        if matches:
            print(json.dumps({"ambiguous": matches}, indent=2), file=sys.stderr)
            return 3
        print("Project not found.", file=sys.stderr)
        return 1
    print(json.dumps(data["projects"][project_id], indent=2, ensure_ascii=False))
    return 0


def render(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve()
    data = load_catalog(vault)
    output = args.output.expanduser().resolve() if args.output else markdown_path(vault)
    atomic_write(output, render_markdown(data))
    print(output)
    return 0


def doctor(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = load_catalog(vault)
    except Exception as exc:
        print(f"Project catalog doctor FAILED: {exc}", file=sys.stderr)
        return 2
    projects = data.get("projects", {})
    seen_names: dict[str, str] = {}
    for project_id, project in projects.items():
        if not re.fullmatch(r"PRJ-\d{3,}", project_id):
            errors.append(f"invalid project ID: {project_id}")
        if project.get("project_id") != project_id:
            errors.append(f"project_id mismatch: {project_id}")
        name = str(project.get("name", "")).strip()
        if not name:
            errors.append(f"{project_id}: missing name")
        normalized = normalize(name)
        if normalized in seen_names and seen_names[normalized] != project_id:
            warnings.append(f"duplicate normalized project name: {seen_names[normalized]} and {project_id}: {name}")
        seen_names[normalized] = project_id
        if not project.get("status"):
            errors.append(f"{project_id}: missing status")
        if not project.get("confidence"):
            errors.append(f"{project_id}: missing confidence")
        if not project.get("next_action"):
            warnings.append(f"{project_id}: missing next action")
        if contains_secret(project):
            errors.append(f"{project_id}: secret-like content")
        latest = [item for item in project.get("versions", []) if item.get("is_latest")]
        if len(latest) > 1:
            errors.append(f"{project_id}: multiple latest versions")
    rendered = render_markdown(data)
    existing = markdown_path(vault)
    if not existing.is_file():
        errors.append(f"missing Markdown mirror: {existing}")
    elif existing.read_text(encoding="utf-8") != rendered:
        errors.append("Markdown mirror drift; run render or reconcile")
    if errors:
        print("Project catalog doctor FAILED", file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors or (warnings and args.strict_warnings):
        return 1
    print(f"Project catalog doctor passed: {len(projects)} projects, {len(warnings)} warnings")
    return 0


def export_catalog(args: argparse.Namespace) -> int:
    vault = args.vault.expanduser().resolve()
    code = doctor(argparse.Namespace(vault=vault, strict_warnings=False))
    if code:
        return code
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, arcname in (
            (catalog_path(vault), "project-catalog/project-catalog.json"),
            (markdown_path(vault), "project-catalog/USER-PROJECTS-DATABASE.md"),
            (events_path(vault), "project-catalog/project-catalog-events.jsonl"),
        ):
            if path.is_file():
                info = zipfile.ZipInfo(arcname)
                info.date_time = (2026, 1, 1, 0, 0, 0)
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
    print(output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("bootstrap")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--seed", type=Path)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=bootstrap)

    p = subparsers.add_parser("reconcile")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--allow-new", action="store_true")
    p.set_defaults(func=reconcile)

    p = subparsers.add_parser("sync-project")
    p.add_argument("root", type=Path)
    p.add_argument("--vault", type=Path, default=default_vault())
    p.set_defaults(func=sync_project)

    p = subparsers.add_parser("list")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=list_projects)

    p = subparsers.add_parser("show")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--project-id", default="")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.set_defaults(func=show)

    p = subparsers.add_parser("render")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--output", type=Path)
    p.set_defaults(func=render)

    p = subparsers.add_parser("doctor")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--strict-warnings", action="store_true")
    p.set_defaults(func=doctor)

    p = subparsers.add_parser("export")
    p.add_argument("--vault", type=Path, default=default_vault())
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=export_catalog)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
