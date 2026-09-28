#!/usr/bin/env python3
"""Shared helpers for deterministic Minecraft 26.3 port intake and gates."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "references" / "minecraft-26.3-port-rules.json"
TEXT_SUFFIXES = {
    ".java", ".kt", ".kts", ".groovy", ".gradle", ".properties", ".toml", ".json",
    ".mcmeta", ".cfg", ".conf", ".txt", ".md", ".yml", ".yaml", ".xml", ".accesswidener", ".classtweaker"
}
MAX_TEXT_BYTES = 2 * 1024 * 1024


class Bundle:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.is_zip = self.root.is_file() and zipfile.is_zipfile(self.root)
        self.zf = zipfile.ZipFile(self.root) if self.is_zip else None
        if not self.is_zip and not self.root.is_dir():
            raise ValueError(f"input is neither a directory nor a ZIP/JAR: {root}")

    def names(self) -> list[str]:
        if self.is_zip:
            return sorted(n for n in self.zf.namelist() if not n.endswith("/"))
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())

    def read(self, name: str, limit: int | None = None) -> bytes:
        if self.is_zip:
            with self.zf.open(name) as fh:
                return fh.read() if limit is None else fh.read(limit)
        path = self.root / PurePosixPath(name)
        with path.open("rb") as fh:
            return fh.read() if limit is None else fh.read(limit)

    def size(self, name: str) -> int:
        if self.is_zip:
            return self.zf.getinfo(name).file_size
        return (self.root / PurePosixPath(name)).stat().st_size

    def close(self) -> None:
        if self.zf:
            self.zf.close()


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def safe_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def is_text_path(name: str) -> bool:
    low = name.lower()
    if low.endswith(("gradlew", "gradlew.bat")):
        return True
    return Path(low).suffix in TEXT_SUFFIXES or low.endswith((".geo.json", ".png.mcmeta"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def input_identity(path: Path) -> dict:
    path = path.resolve()
    if path.is_file():
        return {
            "kind": "archive" if zipfile.is_zipfile(path) else "file",
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
    names = sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file())
    h = hashlib.sha256()
    total = 0
    for rel in names:
        p = path / rel
        size = p.stat().st_size
        total += size
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("ascii"))
        h.update(b"\0")
        # Hash small text/config sources fully; large binaries contribute path+size only to keep intake fast.
        if size <= 4 * 1024 * 1024:
            with p.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
    return {"kind": "directory", "path": str(path), "file_count": len(names), "size": total, "sha256": h.hexdigest()}


def normalize_loader(value: str) -> str:
    v = value.lower().strip()
    if v in {"forge", "neoforge", "fabric", "quilt"}:
        return v
    if v in {"neo", "neo-forge"}:
        return "neoforge"
    raise ValueError(f"unsupported loader: {value}")


def collect_text(bundle: Bundle, names: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        if not is_text_path(name):
            continue
        try:
            out[name] = safe_text(bundle.read(name, min(bundle.size(name), MAX_TEXT_BYTES)))
        except Exception:
            continue
    return out


def scan_rules(names: list[str], text_files: dict[str, str], target_loader: str | None = None) -> list[dict]:
    config = load_rules()
    findings: list[dict] = []
    for rule in config.get("rules", []):
        rule_loader = rule.get("loader", "any")
        if target_loader and rule_loader not in {"any", target_loader}:
            continue
        kind = rule.get("kind")
        pattern = rule.get("pattern", "")
        evidence: list[dict] = []
        if kind == "path_exact":
            for name in names:
                if name == pattern or name.endswith("/" + pattern):
                    evidence.append({"path": name})
        elif kind == "path_regex":
            rx = re.compile(pattern, re.IGNORECASE)
            for name in names:
                if rx.search(name):
                    evidence.append({"path": name})
                    if len(evidence) >= 20:
                        break
        elif kind == "content_regex":
            rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for name, text in text_files.items():
                match = rx.search(text)
                if match:
                    line = text.count("\n", 0, match.start()) + 1
                    snippet = text[max(0, match.start() - 80): min(len(text), match.end() + 120)].replace("\n", " ").strip()
                    evidence.append({"path": name, "line": line, "match": match.group(0)[:160], "context": snippet[:300]})
                    if len(evidence) >= 20:
                        break
        if evidence:
            findings.append({
                "id": rule["id"],
                "severity": rule["severity"],
                "loader": rule_loader,
                "summary": rule["summary"],
                "remediation": rule["remediation"],
                "evidence": evidence,
            })
    severity_order = {"blocker": 0, "high": 1, "medium": 2, "info": 3}
    return sorted(findings, key=lambda f: (severity_order.get(f["severity"], 9), f["id"]))


def write_json(path: Path | None, data: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")