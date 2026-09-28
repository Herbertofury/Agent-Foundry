#!/usr/bin/env python3
"""Organize, inventory, deduplicate, quarantine, and export project artifacts safely.

This tool manages a durable artifact vault for local files and a catalog for external
files such as ChatGPT Library entries. It never treats matching filenames as proof
of duplication. Exact SHA-256 equality is required for automatic duplicate cleanup.
External Library deletion remains manual unless a supported connector/API is present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
DEFAULT_THRESHOLDS = [0.70, 0.85, 0.95]
PLAN_PROFILES = {
    "free": 500 * 1024 * 1024,
    "go": 4 * 1024**3,
    "plus": 20 * 1024**3,
    "business": 20 * 1024**3,
    "pro": 100 * 1024**3,
}
FOLDER_LAYOUT = (
    "00-Inbox",
    "10-Projects",
    "20-Shared",
    "30-Reference",
    "40-Exports",
    "80-Archive",
    "90-Quarantine",
    "cleanup-plans",
)
KIND_BUCKETS = {
    "current": "00-Current",
    "source": "10-Versions",
    "version": "10-Versions",
    "research": "20-Research",
    "asset": "30-Assets",
    "bundle": "40-Bundles",
    "memory": "50-Memory",
    "prompt": "60-Prompts",
    "report": "70-Reports",
    "archive": "90-Archive",
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
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned or "unclassified"


def human_bytes(value: int | None) -> str:
    if value is None:
        return "Unknown"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


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


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def default_vault() -> Path:
    base = os.environ.get("AGENTS_LIBRARY_HOME")
    if base:
        return Path(base).expanduser().resolve()
    memory = Path(os.environ.get("AGENTS_MEMORY_HOME", "~/.agents-second-brain")).expanduser()
    return (memory / "library").resolve()


def catalog_path(vault: Path) -> Path:
    return vault / "library-catalog.json"


def markdown_path(vault: Path) -> Path:
    return vault / "LIBRARY-DATABASE.md"


def events_path(vault: Path) -> Path:
    return vault / "library-events.jsonl"


def ensure_layout(vault: Path) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    for name in FOLDER_LAYOUT:
        (vault / name).mkdir(parents=True, exist_ok=True)


def contains_secret(path: Path) -> bool:
    if path.stat().st_size > 2_000_000:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def new_catalog() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "Artifact Library and Storage Database",
        "created_at_utc": now(),
        "updated_at_utc": now(),
        "storage": {
            "plan": "unknown",
            "limit_bytes": None,
            "used_bytes_reported": None,
            "remaining_bytes_reported": None,
            "reported_at_utc": "",
            "source": "unknown",
            "thresholds": DEFAULT_THRESHOLDS,
        },
        "items": {},
        "cleanup_plans": [],
    }


def load_catalog(vault: Path, *, create: bool = False) -> dict[str, Any]:
    path = catalog_path(vault)
    if not path.is_file():
        if not create:
            raise FileNotFoundError(f"Library catalog is not initialized: {path}")
        data = new_catalog()
        save_catalog(vault, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("items"), dict):
        raise ValueError(f"Unsupported or invalid library catalog: {path}")
    return data


def save_catalog(vault: Path, data: dict[str, Any]) -> None:
    data["updated_at_utc"] = now()
    atomic_write_json(catalog_path(vault), data)
    atomic_write(markdown_path(vault), render_markdown(vault, data))


def event(vault: Path, event_type: str, **fields: Any) -> None:
    append_jsonl(events_path(vault), {"schema_version": 1, "at_utc": now(), "event_type": event_type, **fields})


def item_id() -> str:
    return "lib-" + uuid.uuid4().hex[:14]


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        path = path.expanduser().resolve()
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    yield child
        else:
            raise FileNotFoundError(path)


def project_folder(vault: Path, project_id: str, project_name: str = "") -> Path:
    label = slug(project_id)
    if project_name:
        label += "-" + slug(project_name)
    return vault / "10-Projects" / label


def destination_for(vault: Path, *, project_id: str, project_name: str, kind: str, version: str, name: str) -> Path:
    if project_id:
        root = project_folder(vault, project_id, project_name)
        bucket = KIND_BUCKETS.get(kind.lower(), "80-Misc")
        folder = root / bucket
        if version:
            folder = folder / slug(version)
        return folder / name
    return vault / "00-Inbox" / name


def collision_safe(path: Path, digest: str) -> Path:
    if not path.exists():
        return path
    try:
        if path.is_file() and sha256(path) == digest:
            return path
    except OSError:
        pass
    return path.with_name(f"{path.stem}--{digest[:10]}{path.suffix}")


def catalog_item_by_hash(data: dict[str, Any], digest: str) -> list[dict[str, Any]]:
    return [item for item in data["items"].values() if item.get("sha256") == digest and item.get("status") != "deleted"]


def add_local_file(
    vault: Path,
    data: dict[str, Any],
    source: Path,
    *,
    project_id: str,
    project_name: str,
    kind: str,
    version: str,
    status: str,
    protected: bool,
    copy_mode: str,
) -> dict[str, Any]:
    digest = sha256(source)
    existing = catalog_item_by_hash(data, digest)
    dest = destination_for(vault, project_id=project_id, project_name=project_name, kind=kind, version=version, name=source.name)
    dest = collision_safe(dest, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if copy_mode == "copy":
        if not dest.exists():
            shutil.copy2(source, dest)
    elif copy_mode == "move":
        if source.resolve() != dest.resolve():
            if dest.exists() and sha256(dest) == digest:
                source.unlink()
            else:
                shutil.move(str(source), str(dest))
    elif copy_mode == "catalog-only":
        dest = source
    else:
        raise ValueError(copy_mode)

    record = {
        "item_id": item_id(),
        "name": source.name,
        "project_id": project_id,
        "project_name": project_name,
        "kind": kind,
        "version": version,
        "status": status,
        "protected": bool(protected),
        "canonical": status.lower() in {"canonical", "verified-current"},
        "source_type": "local",
        "source_path": str(source),
        "source_id": "",
        "vault_path": str(dest.resolve()),
        "sha256": digest,
        "bytes": source.stat().st_size if source.exists() else dest.stat().st_size,
        "observed_at_utc": now(),
        "created_at_utc": datetime.fromtimestamp(dest.stat().st_mtime, timezone.utc).isoformat(),
        "duplicate_of": [item["item_id"] for item in existing],
        "supersedes": [],
        "references": [],
        "quarantine": None,
    }
    data["items"][record["item_id"]] = record
    event(vault, "item_ingested", item_id=record["item_id"], sha256=digest, vault_path=record["vault_path"], duplicate_of=record["duplicate_of"])
    return record


def import_external_manifest(vault: Path, data: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    added = []
    rows = manifest.get("items", manifest if isinstance(manifest, list) else [])
    if not isinstance(rows, list):
        raise ValueError("Manifest must be a list or contain an items list")
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            raise ValueError("Every external item requires name")
        source_type = str(row.get("source_type") or "chatgpt-library")
        source_id = str(row.get("source_id") or "")
        digest = str(row.get("sha256") or "")
        signature = str(row.get("content_signature") or "")
        duplicate = next((x for x in data["items"].values() if source_id and x.get("source_type") == source_type and x.get("source_id") == source_id and x.get("sha256") == digest and x.get("content_signature") == signature), None)
        if duplicate:
            continue
        record = {
            "item_id": item_id(),
            "name": str(row["name"]),
            "project_id": str(row.get("project_id") or ""),
            "project_name": str(row.get("project_name") or ""),
            "kind": str(row.get("kind") or "unknown"),
            "version": str(row.get("version") or row.get("explicit_version") or ""),
            "status": str(row.get("status") or "observed"),
            "protected": bool(row.get("protected", False)),
            "canonical": bool(row.get("canonical", False)),
            "source_type": source_type,
            "source_path": str(row.get("source_path") or ""),
            "source_id": source_id,
            "vault_path": "",
            "sha256": digest,
            "content_signature": signature,
            "bytes": row.get("bytes"),
            "observed_at_utc": str(row.get("observed_at_utc") or now()),
            "created_at_utc": str(row.get("created_at_utc") or row.get("uploaded_at_utc") or ""),
            "duplicate_of": [x["item_id"] for x in catalog_item_by_hash(data, digest)] if digest else [],
            "supersedes": list(row.get("supersedes") or []),
            "references": list(row.get("references") or []),
            "quarantine": None,
            "notes": str(row.get("notes") or ""),
        }
        data["items"][record["item_id"]] = record
        added.append(record)
        event(vault, "external_item_imported", item_id=record["item_id"], source_type=source_type, source_id=source_id, sha256=digest)
    return added


def local_vault_bytes(vault: Path) -> int:
    total = 0
    for path in vault.rglob("*"):
        if path.is_file() and path.name not in {"library-catalog.json", "LIBRARY-DATABASE.md", "library-events.jsonl"}:
            total += path.stat().st_size
    return total


def usage_state(data: dict[str, Any], vault: Path) -> dict[str, Any]:
    storage = data.get("storage", {})
    used = storage.get("used_bytes_reported")
    limit = storage.get("limit_bytes")
    local = local_vault_bytes(vault)
    ratio = (used / limit) if isinstance(used, int) and isinstance(limit, int) and limit > 0 else None
    thresholds = storage.get("thresholds") or DEFAULT_THRESHOLDS
    severity = "unknown"
    if ratio is not None:
        severity = "critical" if ratio >= thresholds[2] else "high" if ratio >= thresholds[1] else "warning" if ratio >= thresholds[0] else "healthy"
    return {"used_bytes_reported": used, "limit_bytes": limit, "ratio": ratio, "severity": severity, "local_vault_bytes": local}


def canonical_score(item: dict[str, Any]) -> tuple[int, str]:
    score = 0
    if item.get("protected"):
        score += 1000
    if item.get("canonical"):
        score += 500
    if str(item.get("status", "")).lower() in {"current", "canonical", "verified", "verified-current"}:
        score += 200
    if item.get("project_id"):
        score += 50
    if item.get("references"):
        score += 100
    if item.get("vault_path") and "10-Projects" in item.get("vault_path", ""):
        score += 30
    return score, str(item.get("observed_at_utc") or "")


def build_cleanup_plan(vault: Path, data: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in data["items"].values():
        digest = item.get("sha256")
        if digest and item.get("status") not in {"deleted", "quarantined"}:
            groups.setdefault(digest, []).append(item)
    actions = []
    review = []
    for digest, items in groups.items():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=canonical_score, reverse=True)
        keep = ordered[0]
        for candidate in ordered[1:]:
            if candidate.get("vault_path") and candidate.get("vault_path") == keep.get("vault_path"):
                review.append({"reason": "duplicate catalog record points to the kept payload; merge metadata instead of moving the file", "item_id": candidate["item_id"], "keep_item_id": keep["item_id"], "sha256": digest})
                continue
            if candidate.get("protected") or candidate.get("canonical") or candidate.get("references"):
                review.append({"reason": "duplicate is protected, canonical, or referenced", "item_id": candidate["item_id"], "keep_item_id": keep["item_id"], "sha256": digest})
                continue
            source_type = candidate.get("source_type")
            if source_type == "local" and candidate.get("vault_path"):
                action = "quarantine-local"
            else:
                action = "manual-delete-external"
            actions.append({
                "action": action,
                "item_id": candidate["item_id"],
                "keep_item_id": keep["item_id"],
                "name": candidate.get("name"),
                "source_type": source_type,
                "source_id": candidate.get("source_id"),
                "vault_path": candidate.get("vault_path"),
                "bytes": candidate.get("bytes"),
                "sha256": digest,
                "reason": "exact SHA-256 duplicate",
            })
    # Same-name different-content files are versions, not duplicates.
    names: dict[str, list[dict[str, Any]]] = {}
    for item in data["items"].values():
        if item.get("status") not in {"deleted", "quarantined"}:
            names.setdefault(str(item.get("name", "")).lower(), []).append(item)
    for name, items in names.items():
        hashes = {item.get("sha256") or item.get("content_signature") for item in items}
        hashes.discard("")
        hashes.discard(None)
        if len(items) > 1 and len(hashes) > 1:
            review.append({"reason": "same filename with different content; preserve as version lineage", "name": name, "item_ids": [item["item_id"] for item in items]})
    plan_id = "cleanup-" + uuid.uuid4().hex[:12]
    confirm_token = "QUARANTINE-" + plan_id.split("-", 1)[1].upper()
    plan = {
        "plan_id": plan_id,
        "created_at_utc": now(),
        "confirm_token": confirm_token,
        "status": "planned",
        "actions": actions,
        "review": review,
        "estimated_reclaim_bytes": sum(int(action.get("bytes") or 0) for action in actions),
        "rules": [
            "Only exact SHA-256 duplicates are eligible for automatic local quarantine.",
            "Same-name different-content files are preserved as versions.",
            "External ChatGPT Library deletion is manual unless a supported deletion API exists.",
            "Permanent deletion is separate and requires an explicit purge confirmation.",
        ],
    }
    data["cleanup_plans"].append({"plan_id": plan_id, "created_at_utc": plan["created_at_utc"], "status": "planned", "path": str(vault / "cleanup-plans" / f"{plan_id}.json")})
    atomic_write_json(vault / "cleanup-plans" / f"{plan_id}.json", plan)
    event(vault, "cleanup_plan_created", plan_id=plan_id, action_count=len(actions), estimated_reclaim_bytes=plan["estimated_reclaim_bytes"])
    return plan


def apply_cleanup(vault: Path, data: dict[str, Any], plan: dict[str, Any], confirm: str) -> dict[str, Any]:
    if confirm != plan.get("confirm_token"):
        raise PermissionError("Confirmation token does not match the cleanup plan")
    moved, manual, skipped = [], [], []
    for action in plan.get("actions", []):
        item = data["items"].get(action.get("item_id"))
        if not item or item.get("status") in {"deleted", "quarantined"}:
            skipped.append(action)
            continue
        if action.get("action") == "manual-delete-external":
            manual.append(action)
            continue
        source = Path(str(item.get("vault_path") or ""))
        if not source.is_file():
            skipped.append({**action, "skip_reason": "local file missing"})
            continue
        qid = "q-" + uuid.uuid4().hex[:12]
        destination = vault / "90-Quarantine" / qid / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        item["status"] = "quarantined"
        item["quarantine"] = {
            "quarantine_id": qid,
            "original_path": str(source),
            "quarantine_path": str(destination),
            "quarantined_at_utc": now(),
            "plan_id": plan["plan_id"],
        }
        item["vault_path"] = str(destination)
        moved.append(item["item_id"])
        event(vault, "item_quarantined", item_id=item["item_id"], plan_id=plan["plan_id"], quarantine_id=qid)
    plan["status"] = "applied-local"
    plan["applied_at_utc"] = now()
    plan["moved_item_ids"] = moved
    plan["manual_external_actions"] = manual
    plan["skipped_actions"] = skipped
    atomic_write_json(vault / "cleanup-plans" / f"{plan['plan_id']}.json", plan)
    for summary in data.get("cleanup_plans", []):
        if summary.get("plan_id") == plan["plan_id"]:
            summary["status"] = plan["status"]
    return {"moved": moved, "manual_external_actions": manual, "skipped": skipped}


def restore_item(vault: Path, data: dict[str, Any], item: dict[str, Any]) -> Path:
    quarantine = item.get("quarantine") or {}
    source = Path(str(quarantine.get("quarantine_path") or ""))
    destination = Path(str(quarantine.get("original_path") or ""))
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = collision_safe(destination, item.get("sha256", ""))
    shutil.move(str(source), str(destination))
    item["vault_path"] = str(destination)
    item["status"] = "restored"
    item["quarantine"] = None
    event(vault, "item_restored", item_id=item["item_id"], vault_path=str(destination))
    return destination


def purge_quarantine(vault: Path, data: dict[str, Any], *, older_than_days: int, confirm: str) -> list[str]:
    if confirm != "PERMANENTLY-DELETE-QUARANTINE":
        raise PermissionError("Permanent purge requires the exact confirmation phrase")
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    deleted = []
    for item in data["items"].values():
        quarantine = item.get("quarantine") or {}
        if item.get("status") != "quarantined" or not quarantine:
            continue
        timestamp = quarantine.get("quarantined_at_utc")
        try:
            when = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            continue
        if when > cutoff:
            continue
        path = Path(str(quarantine.get("quarantine_path") or ""))
        if path.is_file():
            path.unlink()
            try:
                path.parent.rmdir()
            except OSError:
                pass
        item["status"] = "deleted"
        item["deleted_at_utc"] = now()
        item["vault_path"] = ""
        deleted.append(item["item_id"])
        event(vault, "item_permanently_deleted", item_id=item["item_id"], quarantine_id=quarantine.get("quarantine_id"))
    return deleted


def render_markdown(vault: Path, data: dict[str, Any]) -> str:
    state = usage_state(data, vault)
    storage = data.get("storage", {})
    items = list(data.get("items", {}).values())
    active = [item for item in items if item.get("status") not in {"deleted"}]
    duplicate_groups: dict[str, list[dict[str, Any]]] = {}
    for item in active:
        if item.get("sha256"):
            duplicate_groups.setdefault(item["sha256"], []).append(item)
    duplicate_groups = {key: value for key, value in duplicate_groups.items() if len(value) > 1}
    lines = [
        "# Artifact Library and Storage Database",
        "",
        f"**Updated:** {data.get('updated_at_utc', '')}",
        f"**Vault:** `{vault}`",
        "",
        "> This database organizes project files, bundles, versions, research, and references. Exact-hash duplicates may be quarantined after approval. Same-name files with different content are versions, not duplicates.",
        "",
        "## Storage dashboard",
        "",
        f"- **Plan:** {storage.get('plan', 'unknown')}",
        f"- **Reported use:** {human_bytes(state['used_bytes_reported'])}",
        f"- **Reported limit:** {human_bytes(state['limit_bytes'])}",
        f"- **Storage state:** {state['severity']}",
        f"- **Local organized vault:** {human_bytes(state['local_vault_bytes'])}",
        f"- **Cataloged active items:** {len(active)}",
        f"- **Exact duplicate groups:** {len(duplicate_groups)}",
        "",
        "## Folder layout",
        "",
        "```text",
        "00-Inbox/",
        "10-Projects/<project-id-name>/",
        "  00-Current/",
        "  10-Versions/",
        "  20-Research/",
        "  30-Assets/",
        "  40-Bundles/",
        "  50-Memory/",
        "  60-Prompts/",
        "  70-Reports/",
        "  90-Archive/",
        "20-Shared/",
        "30-Reference/",
        "40-Exports/",
        "80-Archive/",
        "90-Quarantine/",
        "cleanup-plans/",
        "```",
        "",
        "## Project inventory",
        "",
        "| Project | Item | Kind | Version | Status | Size | Source | Hash |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for item in sorted(active, key=lambda x: (str(x.get("project_id")), str(x.get("name")), str(x.get("version")))):
        values = [
            item.get("project_id") or "Unassigned",
            item.get("name") or "",
            item.get("kind") or "",
            item.get("version") or "",
            item.get("status") or "",
            human_bytes(item.get("bytes")),
            item.get("source_type") or "",
            (item.get("sha256") or item.get("content_signature") or "")[:12],
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    lines += ["", "## Exact duplicate groups", ""]
    if not duplicate_groups:
        lines.append("_No exact-hash duplicate groups are currently cataloged._")
    else:
        for digest, group in sorted(duplicate_groups.items()):
            lines.append(f"### `{digest}`")
            for item in group:
                lines.append(f"- `{item['item_id']}` — {item.get('name')} — {item.get('source_type')} — {item.get('status')} — {human_bytes(item.get('bytes'))}")
            lines.append("")
    lines += ["", "## Cleanup safety rules", "", "- Inventory first; never clean from filenames alone.", "- Keep one verified canonical copy and preserve every distinct version.", "- Exact SHA-256 equality is required for automatic duplicate quarantine.", "- External Library deletion requires manual confirmation and must be reread afterward.", "- Local cleanup moves files to `90-Quarantine/` before any permanent purge.", "- Permanent deletion requires a separate explicit confirmation and age threshold.", ""]
    return "\n".join(lines)


def doctor(vault: Path, data: dict[str, Any]) -> list[str]:
    errors = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    ids = set()
    for key, item in data.get("items", {}).items():
        if key in ids:
            errors.append(f"duplicate item id: {key}")
        ids.add(key)
        if item.get("item_id") != key:
            errors.append(f"item key/id mismatch: {key}")
        if item.get("source_type") == "local" and item.get("status") not in {"deleted"}:
            path = Path(str(item.get("vault_path") or ""))
            if not path.is_file():
                errors.append(f"missing local file for {key}: {path}")
            if path.is_file() and item.get("sha256") and sha256(path) != item.get("sha256"):
                errors.append(f"hash drift for {key}: {path}")
    for summary in data.get("cleanup_plans", []):
        path = Path(str(summary.get("path") or ""))
        if not path.is_file():
            errors.append(f"cleanup plan missing: {path}")
    return errors


def write_project_bundle(vault: Path, data: dict[str, Any], project_id: str, output: Path) -> None:
    items = [item for item in data["items"].values() if item.get("project_id") == project_id and item.get("status") != "deleted"]
    if not items:
        raise ValueError(f"No cataloged items for project {project_id}")
    project_dirs = set()
    for item in items:
        raw = item.get("vault_path")
        if not raw:
            continue
        file_path = Path(raw)
        if not file_path.is_file():
            continue
        for ancestor in file_path.parents:
            if ancestor.parent.name == "10-Projects":
                project_dirs.add(ancestor)
                break
    project_dirs = sorted(project_dirs)
    manifest = {"schema_version": 1, "project_id": project_id, "created_at_utc": now(), "items": items}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("project-library/MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        zf.writestr("project-library/README.md", f"# {project_id} organized artifact bundle\n\nCreated: {now()}\n\nContains cataloged current files, versions, research, assets, bundles, memory, prompts, reports, and archive material available in the local organized vault.\n")
        for root in project_dirs:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, f"project-library/files/{root.name}/{path.relative_to(root).as_posix()}")


def export_catalog(vault: Path, data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in (catalog_path(vault), markdown_path(vault), events_path(vault)):
            if path.is_file():
                zf.write(path, f"library-catalog/{path.name}")
        for path in sorted((vault / "cleanup-plans").glob("*.json")):
            zf.write(path, f"library-catalog/cleanup-plans/{path.name}")
        zf.writestr("library-catalog/README.md", "# Artifact Library Catalog Export\n\nUse `library-catalog.json` as the machine-readable source and `LIBRARY-DATABASE.md` as the human-readable index. This export does not include all file payloads; create a per-project bundle when the payloads are required.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=default_vault())
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("paths", nargs="+", type=Path)
    ingest.add_argument("--project-id", default="")
    ingest.add_argument("--project-name", default="")
    ingest.add_argument("--kind", default="current")
    ingest.add_argument("--version", default="")
    ingest.add_argument("--status", default="current")
    ingest.add_argument("--protected", action="store_true")
    ingest.add_argument("--mode", choices=("copy", "move", "catalog-only"), default="copy")
    ingest.add_argument("--allow-secret-like", action="store_true")

    imp = sub.add_parser("import-manifest")
    imp.add_argument("input", type=Path)

    record = sub.add_parser("record-usage")
    record.add_argument("--plan", choices=("unknown", "free", "go", "plus", "business", "pro", "custom"), default="unknown")
    record.add_argument("--used-bytes", type=int, required=True)
    record.add_argument("--limit-bytes", type=int)
    record.add_argument("--remaining-bytes", type=int)
    record.add_argument("--source", default="ChatGPT Library Storage UI")

    sub.add_parser("status")
    sub.add_parser("list")
    sub.add_parser("render")
    sub.add_parser("plan-cleanup")

    apply_parser = sub.add_parser("apply-cleanup")
    apply_parser.add_argument("plan", type=Path)
    apply_parser.add_argument("--confirm", required=True)

    external = sub.add_parser("confirm-external-delete")
    external.add_argument("item_id")
    external.add_argument("--confirm", required=True, help="Use the exact item ID as confirmation.")

    restore = sub.add_parser("restore")
    restore.add_argument("item_id")

    purge = sub.add_parser("purge-quarantine")
    purge.add_argument("--older-than-days", type=int, default=30)
    purge.add_argument("--confirm", required=True)

    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--strict", action="store_true")

    bundle = sub.add_parser("bundle-project")
    bundle.add_argument("project_id")
    bundle.add_argument("--output", type=Path, required=True)

    export = sub.add_parser("export")
    export.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    vault = args.vault.expanduser().resolve()
    ensure_layout(vault)

    if args.command == "init":
        data = load_catalog(vault, create=True)
        save_catalog(vault, data)
        event(vault, "library_initialized", vault_path=str(vault))
        print(vault)
        return 0

    data = load_catalog(vault, create=True)

    if args.command == "ingest":
        records = []
        for path in iter_files(args.paths):
            if contains_secret(path) and not args.allow_secret_like:
                print(f"Refusing secret-like file without --allow-secret-like: {path}", file=sys.stderr)
                return 3
            records.append(add_local_file(vault, data, path, project_id=args.project_id, project_name=args.project_name, kind=args.kind, version=args.version, status=args.status, protected=args.protected, copy_mode=args.mode))
        save_catalog(vault, data)
        print(json.dumps(records, indent=2, ensure_ascii=False))
        return 0

    if args.command == "import-manifest":
        manifest = json.loads(args.input.read_text(encoding="utf-8"))
        added = import_external_manifest(vault, data, manifest)
        save_catalog(vault, data)
        print(json.dumps({"added": added}, indent=2, ensure_ascii=False))
        return 0

    if args.command == "record-usage":
        limit = args.limit_bytes
        if limit is None and args.plan in PLAN_PROFILES:
            limit = PLAN_PROFILES[args.plan]
        if limit is None and args.remaining_bytes is not None:
            limit = args.used_bytes + args.remaining_bytes
        if limit is not None and args.used_bytes > limit:
            print("Used bytes exceed limit bytes", file=sys.stderr)
            return 2
        data["storage"] = {
            "plan": args.plan,
            "limit_bytes": limit,
            "used_bytes_reported": args.used_bytes,
            "remaining_bytes_reported": args.remaining_bytes if args.remaining_bytes is not None else (limit - args.used_bytes if limit is not None else None),
            "reported_at_utc": now(),
            "source": args.source,
            "thresholds": data.get("storage", {}).get("thresholds") or DEFAULT_THRESHOLDS,
        }
        save_catalog(vault, data)
        state = usage_state(data, vault)
        event(vault, "storage_usage_recorded", **state)
        print(json.dumps(state, indent=2))
        return 0

    if args.command == "status":
        print(json.dumps(usage_state(data, vault), indent=2))
        return 0

    if args.command == "list":
        print(json.dumps(list(data["items"].values()), indent=2, ensure_ascii=False))
        return 0

    if args.command == "render":
        save_catalog(vault, data)
        print(markdown_path(vault))
        return 0

    if args.command == "plan-cleanup":
        plan = build_cleanup_plan(vault, data)
        save_catalog(vault, data)
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    if args.command == "apply-cleanup":
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = apply_cleanup(vault, data, plan, args.confirm)
        save_catalog(vault, data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "confirm-external-delete":
        if args.confirm != args.item_id:
            print("Confirmation must exactly match the item ID", file=sys.stderr)
            return 3
        item = data["items"].get(args.item_id)
        if not item:
            print(f"Unknown item: {args.item_id}", file=sys.stderr)
            return 2
        if item.get("source_type") == "local":
            print("Use cleanup/quarantine commands for local files", file=sys.stderr)
            return 3
        item["status"] = "deleted"
        item["deleted_at_utc"] = now()
        event(vault, "external_delete_confirmed", item_id=args.item_id, source_type=item.get("source_type"), source_id=item.get("source_id"))
        save_catalog(vault, data)
        print(args.item_id)
        return 0

    if args.command == "restore":
        item = data["items"].get(args.item_id)
        if not item:
            print(f"Unknown item: {args.item_id}", file=sys.stderr)
            return 2
        path = restore_item(vault, data, item)
        save_catalog(vault, data)
        print(path)
        return 0

    if args.command == "purge-quarantine":
        deleted = purge_quarantine(vault, data, older_than_days=args.older_than_days, confirm=args.confirm)
        save_catalog(vault, data)
        print(json.dumps({"deleted": deleted}, indent=2))
        return 0

    if args.command == "doctor":
        errors = doctor(vault, data)
        if errors:
            print("Library doctor FAILED", file=sys.stderr)
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        state = usage_state(data, vault)
        if args.strict and state["severity"] in {"high", "critical"}:
            print(f"Library doctor blocked by storage severity: {state['severity']}", file=sys.stderr)
            return 1
        print(f"Library doctor passed: {len(data['items'])} items, storage={state['severity']}, local={human_bytes(state['local_vault_bytes'])}")
        return 0

    if args.command == "bundle-project":
        write_project_bundle(vault, data, args.project_id, args.output.expanduser().resolve())
        print(args.output.expanduser().resolve())
        return 0

    if args.command == "export":
        export_catalog(vault, data, args.output.expanduser().resolve())
        print(args.output.expanduser().resolve())
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
