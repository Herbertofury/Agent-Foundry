#!/usr/bin/env python3
"""Strict integrity, quality, size, and policy-consistency gate for the AGENTS bundle."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

MALFORMED = [
    re.compile(r"^#{1,6}\s+.+(?:failure|theater|gate|contract|rules)Every\b", re.I),
    re.compile(r"^#{1,6}\s+.*\S(?<![.!?:])Every\b"),
]
PLACEHOLDERS = [
    re.compile(r"\bTODO(?:\(|:|\b)", re.I),
    re.compile(r"\bFIXME\b", re.I),
    re.compile(r"\bcoming soon\b", re.I),
    re.compile(r"\btest candidate\b", re.I),
    re.compile(r"\bexample only\b", re.I),
]
NORMATIVE = re.compile(r"\b(must|never|required|do not|cannot|incomplete|fails? the task)\b", re.I)

SECRET_LIKE = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]{8,}", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_markdown(path: Path, production_markers: list[str]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = set()
    for i, line in enumerate(lines, 1):
        if line.startswith("#"):
            if line in headings:
                warnings.append(f"{path}:{i}: duplicate heading: {line}")
            headings.add(line)
            for pattern in MALFORMED:
                if pattern.search(line):
                    errors.append(f"{path}:{i}: malformed merged heading: {line}")
        for pattern in PLACEHOLDERS:
            if pattern.search(line):
                lowered = line.lower()
                if any(guard in lowered for guard in ("never ", "do not ", "forbid", "no placeholder", "without placeholder", "detect placeholder")):
                    continue
                errors.append(f"{path}:{i}: production placeholder/test marker: {line.strip()}")
        if "�" in line:
            errors.append(f"{path}:{i}: Unicode replacement character")
    for marker in production_markers:
        if marker.lower() in text.lower():
            errors.append(f"{path}: forbidden production marker: {marker}")
    if text and not text.endswith("\n"):
        warnings.append(f"{path}: missing trailing newline")
    return errors, warnings


def normative_fingerprints(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        stripped = re.sub(r"[`*_#>-]", " ", line).strip().lower()
        if NORMATIVE.search(stripped):
            words = re.findall(r"[a-z0-9]+", stripped)
            if len(words) >= 5:
                out.add(" ".join(words[:12]))
    return out


def check_project_memory(repo: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    mem = repo / ".agents-memory"
    if not mem.exists():
        return errors, warnings
    if not mem.is_dir():
        return [f"project memory path is not a directory: {mem}"], warnings
    required = ("PROJECT.json", "STATUS.json", "HANDOFF.md", "sessions.jsonl")
    for name in required:
        if not (mem / name).is_file():
            errors.append(f"project memory missing {mem / name}")
    try:
        project = load_json(mem / "PROJECT.json") if (mem / "PROJECT.json").is_file() else {}
        status = load_json(mem / "STATUS.json") if (mem / "STATUS.json").is_file() else {}
        if project.get("schema_version") != 1:
            errors.append("PROJECT.json has unsupported schema_version")
        if not str(project.get("project_id", "")).startswith("prj-"):
            errors.append("PROJECT.json has invalid project_id")
        if status.get("project_id") != project.get("project_id"):
            errors.append("STATUS.json project_id does not match PROJECT.json")
        canonical = project.get("canonical_root")
        if canonical and Path(canonical).expanduser().resolve() != repo.resolve():
            warnings.append(f"project memory canonical_root differs from current path: {canonical}")
    except Exception as exc:
        errors.append(f"invalid project memory JSON: {exc}")
    for path in mem.rglob("*"):
        if not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_LIKE:
            if pattern.search(content):
                errors.append(f"secret-like content in project memory: {path}")
                break
    if (mem / "HANDOFF.md").is_file() and (mem / "HANDOFF.md").stat().st_size < 80:
        warnings.append("project HANDOFF.md is unusually small")
    return errors, warnings


def repository_mode(repo: Path, strict_warnings: bool) -> int:
    errors, warnings = [], []
    root_agents = repo / "AGENTS.md"
    if not root_agents.is_file():
        errors.append(f"missing root AGENTS.md: {root_agents}")
        files = []
    else:
        files = [root_agents]
    module_dir = repo / ".agents"
    if module_dir.is_dir():
        files.extend(sorted(module_dir.glob("*.md")))
    for path in files:
        e, w = check_markdown(path, ["Test candidate", "test only", "test evidence", "EXAMPLE ONLY"])
        errors.extend(e); warnings.extend(w)
    e, w = check_project_memory(repo)
    errors.extend(e); warnings.extend(w)
    if root_agents.is_file():
        size = root_agents.stat().st_size
        if size > 32768:
            errors.append(f"root AGENTS.md exceeds 32768 bytes: {size}")
        elif size > 30720:
            warnings.append(f"root AGENTS.md near 32 KiB limit: {size}")
        text = root_agents.read_text(encoding="utf-8")
        refs = re.findall(r"`?(\.agents/[A-Za-z0-9_.-]+\.md)`?", text)
        for rel in refs:
            if not (repo / rel).is_file():
                errors.append(f"broken module reference: {rel}")
    if errors:
        print("AGENTS repository doctor FAILED", file=sys.stderr)
        for error in errors: print(f"ERROR: {error}", file=sys.stderr)
    for warning in warnings: print(f"WARNING: {warning}", file=sys.stderr)
    if errors or (warnings and strict_warnings): return 1
    print(f"AGENTS repository doctor passed: {len(files)} instruction files")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--strict-warnings", action="store_true")
    args = parser.parse_args()
    if args.repository:
        return repository_mode(args.repository.resolve(), args.strict_warnings)
    root = args.skill_root.resolve()
    catalog_path = root / "policies" / "policy-catalog.json"
    errors, warnings = [], []
    try:
        catalog = load_json(catalog_path)
    except Exception as exc:
        print(f"Cannot load policy catalog: {exc}", file=sys.stderr)
        return 2

    compile_check = subprocess.run(
        [sys.executable, str(root / "scripts" / "compile_policy.py"), "--skill-root", str(root), "--check"],
        capture_output=True, text=True, timeout=60,
    )
    if compile_check.returncode:
        errors.append(compile_check.stderr.strip() or compile_check.stdout.strip())

    bundle = root / "assets" / "agents-md-hybrid"
    files = [bundle / "AGENTS.md", bundle / "AGENTS.modular.md", bundle / "README.md"]
    files += [bundle / ".agents" / f"{name}.md" for name in catalog["module_order"]]
    required_runtime_files = [
        root / "references" / "MEMORY-CONTINUITY.md",
        root / "scripts" / "project_memory.py",
        root / "scripts" / "project_catalog.py",
        root / "scripts" / "research_memory.py",
        root / "assets" / "memory" / "README.md",
        root / "assets" / "memory" / "USER-PROJECTS-DATABASE.seed.md",
        root / "assets" / "memory" / "PROJECT-CATALOG.template.json",
        root / "references" / "PROJECT-CATALOG.md",
        root / "references" / "LIBRARY-STORAGE.md",
        root / "scripts" / "library_manager.py",
        root / "assets" / "library" / "README.md",
        root / "assets" / "library" / "quota-profiles.json",
    ]
    for required in required_runtime_files:
        if not required.is_file() or required.stat().st_size == 0:
            errors.append(f"missing required second-brain component: {required}")

    markers = catalog.get("forbidden_production_markers", [])
    for path in files:
        if not path.is_file():
            errors.append(f"missing required file: {path}")
            continue
        e, w = check_markdown(path, markers)
        errors.extend(e); warnings.extend(w)

    limits = catalog.get("size_limits", {})
    standalone_size = (bundle / "AGENTS.md").stat().st_size
    root_size = (bundle / "AGENTS.modular.md").stat().st_size
    if standalone_size > limits.get("standalone_hard_bytes", 32768):
        errors.append(f"standalone AGENTS.md exceeds hard limit: {standalone_size} bytes")
    elif standalone_size > limits.get("standalone_warning_bytes", 30720):
        warnings.append(f"standalone AGENTS.md near limit: {standalone_size} bytes")
    if root_size > limits.get("root_warning_bytes", 10240):
        warnings.append(f"modular root is large: {root_size} bytes")

    approved = load_json(root / "references" / "pitfalls-approved.json")
    ids, semantic = set(), set()
    for entry in approved.get("entries", []):
        eid = str(entry.get("id", ""))
        if not re.fullmatch(r"P-\d{3,}", eid): errors.append(f"invalid active pitfall id: {eid}")
        if eid in ids: errors.append(f"duplicate active pitfall id: {eid}")
        ids.add(eid)
        joined = " ".join(str(entry.get(k, "")) for k in ("title","scope","failure","replacement")).lower()
        if any(marker.lower() in joined for marker in markers): errors.append(f"active pitfall contains fixture marker: {eid}")
        fp = re.sub(r"\W+", " ", str(entry.get("failure", "")).lower()).strip()
        if fp and fp in semantic: errors.append(f"duplicate semantic pitfall failure: {eid}")
        semantic.add(fp)
        for field in ("trigger","failure","replacement","verification"):
            if not str(entry.get(field, "")).strip(): errors.append(f"{eid}: missing {field}")

    full = (bundle / "AGENTS.md").read_text(encoding="utf-8")
    modules_text = "\n".join((bundle / ".agents" / f"{name}.md").read_text(encoding="utf-8") for name in catalog["module_order"])
    full_norm = normative_fingerprints(full); modular_norm = normative_fingerprints(modules_text)
    if full_norm and modular_norm:
        overlap = len(full_norm & modular_norm) / max(1, min(len(full_norm), len(modular_norm)))
        if overlap < 0.25: warnings.append(f"low lexical normative overlap between standalone and modules: {overlap:.1%}; review coverage phrases")

    if errors:
        print("AGENTS doctor FAILED", file=sys.stderr)
        for error in errors: print(f"ERROR: {error}", file=sys.stderr)
    for warning in warnings: print(f"WARNING: {warning}", file=sys.stderr)
    if errors or (warnings and args.strict_warnings): return 1
    print(f"AGENTS doctor passed: {len(files)} policy files, {len(approved.get('entries', []))} active pitfalls, standalone={standalone_size} bytes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
