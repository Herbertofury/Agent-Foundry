#!/usr/bin/env python3
"""Compile every AGENTS representation from the structured policy catalog."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def load_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("Unsupported policy catalog schema")
    docs = data.get("documents", {})
    if not all(k in docs for k in ("standalone", "root", "readme", "modules")):
        raise ValueError("Catalog is missing required documents")
    return data


def compile_bundle(root: Path, catalog: dict) -> dict:
    bundle = root / "assets" / "agents-md-hybrid"
    refs = root / "references"
    docs = catalog["documents"]
    write_text(bundle / "AGENTS.md", docs["standalone"])
    write_text(bundle / "AGENTS.modular.md", docs["root"])
    write_text(bundle / "README.md", docs["readme"])
    write_text(refs / "FULL-CONTRACT.md", docs["standalone"])
    write_text(refs / "CORE.md", docs["root"])
    write_text(refs / "BUNDLE-README.md", docs["readme"])
    dynamic = {"PITFALLS", "PITFALLS-QUARANTINE"}
    for name in catalog["module_order"]:
        content = (refs / f"{name}.md").read_text(encoding="utf-8") if name in dynamic else docs["modules"][name]
        write_text(bundle / ".agents" / f"{name}.md", content)
        write_text(refs / f"{name}.md", content)

    files = {}
    ordered = [bundle / "AGENTS.md", bundle / "AGENTS.modular.md", bundle / "README.md"]
    ordered += [bundle / ".agents" / f"{name}.md" for name in catalog["module_order"]]
    for path in ordered:
        raw = path.read_bytes()
        files[path.relative_to(bundle).as_posix()] = {"sha256": sha256_bytes(raw), "bytes": len(raw)}
    catalog_path = root / "policies" / "policy-catalog.json"
    manifest = {
        "schema_version": 2,
        "bundle_version": catalog.get("bundle_version"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_sha256": sha256_bytes(catalog_path.read_bytes()),
        "canonical_root": "assets/agents-md-hybrid",
        "files": files,
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    write_text(bundle / "MANIFEST.json", text)
    write_text(refs / "SOURCE-MANIFEST.json", text)
    return manifest


def check_outputs(root: Path, catalog: dict) -> list[str]:
    errors = []
    bundle = root / "assets" / "agents-md-hybrid"
    refs = root / "references"
    docs = catalog["documents"]
    pairs = [
        (bundle / "AGENTS.md", docs["standalone"]),
        (bundle / "AGENTS.modular.md", docs["root"]),
        (bundle / "README.md", docs["readme"]),
        (refs / "FULL-CONTRACT.md", docs["standalone"]),
        (refs / "CORE.md", docs["root"]),
        (refs / "BUNDLE-README.md", docs["readme"]),
    ]
    dynamic = {"PITFALLS", "PITFALLS-QUARANTINE"}
    for name in catalog["module_order"]:
        content = (refs / f"{name}.md").read_text(encoding="utf-8") if name in dynamic else docs["modules"][name]
        pairs += [(bundle / ".agents" / f"{name}.md", content), (refs / f"{name}.md", content)]
    for path, expected in pairs:
        normalized = expected if expected.endswith("\n") else expected + "\n"
        if not path.is_file():
            errors.append(f"missing generated file: {path}")
        elif path.read_text(encoding="utf-8") != normalized:
            errors.append(f"generated output drift: {path}")
    standalone = docs["standalone"].lower()
    for module, phrases in catalog.get("coverage_phrases", {}).items():
        for phrase in phrases:
            if phrase.lower() not in standalone:
                errors.append(f"standalone coverage missing [{module}]: {phrase}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.skill_root.resolve()
    catalog = load_catalog(root / "policies" / "policy-catalog.json")
    if args.check:
        errors = check_outputs(root, catalog)
        if errors:
            print("Policy compilation check failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("Policy catalog and generated AGENTS outputs are synchronized")
        return 0
    compile_bundle(root, catalog)
    errors = check_outputs(root, catalog)
    if errors:
        print("Policy compilation completed with errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Compiled policy catalog into standalone, modular, and skill-reference outputs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
