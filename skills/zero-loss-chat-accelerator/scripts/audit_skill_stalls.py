#!/usr/bin/env python3
"""Static stall-risk audit for personal ChatGPT skills.

Checks hot-path size, cross-skill continuity, known workflow-owner conflicts,
and obvious unbounded external waits in bundled Python helpers.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


@dataclass
class Finding:
    skill: str
    severity: str
    message: str


def discover_skill_dirs(root: Path) -> list[Path]:
    root = root.resolve()
    if (root / "SKILL.md").is_file():
        return [root]
    found: dict[str, Path] = {}
    for p in root.rglob("SKILL.md"):
        d = p.parent
        name = d.name
        # Prefer the shallowest occurrence when duplicate extracted/package trees exist.
        if name not in found or len(d.parts) < len(found[name].parts):
            found[name] = d
    return [found[k] for k in sorted(found)]


def frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def description_from_frontmatter(front: str) -> str:
    match = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", front, re.M)
    return match.group(1) if match else ""


def call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        bits = [f.attr]
        v = f.value
        while isinstance(v, ast.Attribute):
            bits.append(v.attr)
            v = v.value
        if isinstance(v, ast.Name):
            bits.append(v.id)
        return ".".join(reversed(bits))
    return ""


def kw_names(node: ast.Call) -> set[str]:
    return {kw.arg for kw in node.keywords if kw.arg}


def audit_python(skill: str, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        return [Finding(skill, "FAIL", f"{path.name}: Python syntax error: {exc}")]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        kws = kw_names(node)
        if name in {"subprocess.run", "subprocess.check_output", "subprocess.check_call"} and "timeout" not in kws:
            findings.append(Finding(skill, "FAIL", f"{path.name}:{node.lineno}: {name} has no timeout"))
        if name.endswith("urlopen") and "timeout" not in kws and len(node.args) < 2:
            findings.append(Finding(skill, "FAIL", f"{path.name}:{node.lineno}: urlopen has no timeout"))

    # Flag retry defaults that can hold an interactive run for too long.
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args.args
            defaults = node.args.defaults
            if not defaults:
                continue
            start = len(args) - len(defaults)
            for arg, default in zip(args[start:], defaults):
                if arg.arg in {"retries", "max_retries", "attempts"} and isinstance(default, ast.Constant) and isinstance(default.value, int) and default.value > 3:
                    findings.append(Finding(skill, "FAIL", f"{path.name}:{node.lineno}: default {arg.arg}={default.value} exceeds interactive retry ceiling 3"))
    return findings


def require(findings: list[Finding], skill: str, text: str, phrase: str, label: str | None = None) -> None:
    if phrase.lower() not in text.lower():
        findings.append(Finding(skill, "FAIL", label or f"missing stall guard: {phrase}"))


def audit_skill(d: Path) -> list[Finding]:
    findings: list[Finding] = []
    skill = d.name
    p = d / "SKILL.md"
    text = p.read_text(encoding="utf-8", errors="replace")
    front = frontmatter(text)
    desc = description_from_frontmatter(front)
    size = len(text.encode("utf-8"))
    lines = len(text.splitlines())

    size_limits = {
        "zero-loss-chat-accelerator": 11_000,
        "project-brain-orchestrator": 13_000,
        "minecraft-dev-kit": 12_000,
        "minecraft-repair": 11_000,
        "artifact-browser-companion": 11_000,
        "project-visual-qa-showcase": 10_000,
        "no-image-generation": 6_000,
        "revenue-operator": 7_000,
    }
    limit = size_limits.get(skill, 12_000)
    if size > limit:
        findings.append(Finding(skill, "FAIL", f"hot-path SKILL.md {size} bytes exceeds {limit}"))
    if lines > 200:
        findings.append(Finding(skill, "FAIL", f"hot-path SKILL.md {lines} lines exceeds 200"))
    if len(desc) > 1200:
        findings.append(Finding(skill, "FAIL", f"frontmatter description is {len(desc)} chars; narrow activation metadata"))

    if skill == "zero-loss-chat-accelerator":
        for phrase in (
            "## Cross-skill continuity",
            "continuity capsule",
            "overlay rather than a replacement",
            "still-applicable domain constraint",
            "guardrail skill",
            "exact next action",
            "Do not enumerate a whole skill directory",
            "two unchanged status observations",
            "## Embedded Stall Brain",
            "references/stall-brain.md",
            "references/stall-patterns.json",
        ):
            require(findings, skill, text, phrase)
        for rel in ("references/stall-brain.md", "references/stall-patterns.json", "scripts/stall_brain.py"):
            if not (d / rel).is_file():
                findings.append(Finding(skill, "FAIL", f"missing embedded Stall Brain resource: {rel}"))
    else:
        require(findings, skill, text, "## Zero-Loss composition")
        require(findings, skill, text, "zero-loss-chat-accelerator")
        require(findings, skill, text, "exact next action")
        if skill != "no-image-generation":
            require(findings, skill, text, "two unchanged")
        require(findings, skill, text, "Do not enumerate")
        if "zero-loss-chat-accelerator" not in front:
            findings.append(Finding(skill, "FAIL", "frontmatter does not declare Zero-Loss composition"))

    specific: dict[str, tuple[str, ...]] = {
        "no-image-generation": (
            "non-orchestrating guardrail",
            "Do not take workflow ownership",
            "immediately resume the prior domain workflow",
        ),
        "minecraft-dev-kit": (
            "Do not run the entire static + server + client + package stack after every edit",
            "record the exact PID/run identity",
            "bounded subroutine",
        ),
        "minecraft-repair": (
            "one targeted Repair Brain lookup",
            "Do not reread the full history",
            "return to its preserved exact next action",
        ),
        "project-brain-orchestrator": (
            "Do not run the full suite after every edit",
            "Batch related Drive/GitHub writes",
            "Never list/preload the whole skill package",
        ),
        "artifact-browser-companion": (
            "process only changed sources",
            "Do not build both merely as ceremony",
            "Do not perform a full source re-enumeration",
        ),
        "project-visual-qa-showcase": (
            "complement rather than replace Minecraft Dev Kit",
            "Do not rerender the same unchanged state",
            "observe milestones/output files",
        ),
        "revenue-operator": (
            "reuse a fresh sourced snapshot",
            "Do not repeatedly poll an unchanged",
            "Never duplicate a mutation",
        ),
    }
    for phrase in specific.get(skill, ()):
        require(findings, skill, text, phrase)

    for script in sorted((d / "scripts").glob("*.py")) if (d / "scripts").is_dir() else []:
        findings.extend(audit_python(skill, script))

    if not findings:
        findings.append(Finding(skill, "PASS", f"hot path {size} bytes/{lines} lines; composition and bounded-wait guards present"))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="skill dir or parent containing skill dirs")
    args = ap.parse_args()
    dirs = discover_skill_dirs(args.root)
    if not dirs:
        print("FAIL no SKILL.md files found", file=sys.stderr)
        return 2
    all_findings: list[Finding] = []
    for d in dirs:
        all_findings.extend(audit_skill(d))
    failed = False
    for f in all_findings:
        print(f"{f.severity:4} {f.skill}: {f.message}")
        failed |= f.severity == "FAIL"
    print(f"Audited {len(dirs)} skill(s); {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
