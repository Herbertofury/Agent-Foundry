#!/usr/bin/env python3
"""Normalize mirrored Skill entrypoints and propagate the canonical governance bridge."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

FOOTER_MARKER = "---\nTo read any file's contents"
UAG = "ultimate-agent-governance"
CHALLENGE_BULLET = "- **Challenge before reinventing.** For substantive implementation, architecture, optimization, conversion, integration, or tooling work, run a bounded challenger/integration scan across relevant upstreams, repositories, forks, package/plugin ecosystems, standards, and reference implementations. Prefer authorized adopt/merge/port/wrap/backport/reuse of materially superior pieces over rebuilding weaker duplicates; compose the best pieces when no single candidate wins, preserve provenance/licensing/permission constraints, and record candidate dispositions."
BEST_IN_CLASS_BULLET = "- **Best-in-class is the acceptance target.** For substantive design, implementation, repair, optimization, integration, conversion, research, or tooling work, identify the strongest credible current baseline/challengers and the user-valued dimensions that matter. Reuse or compose superior authorized pieces instead of recreating weaker versions. The default goal is not mere parity: preserve every protected dimension and, where constraints permit, materially beat the strongest credible baseline on at least one relevant dimension. Claims of superiority require equivalent-work evidence; if only parity is proven, say parity, and if no credible baseline can be established, keep the comparison unresolved rather than inventing a win."
FRONTIER_STACK_BULLET = "- **Frontier stack first, evidence-gated.** For new technical work and touched architecture where stack choice is available, start from the strongest current best-fit frontier/bleeding-edge stack, tools, APIs, runtimes, frameworks, build/test systems, storage, protocols, and integration methods supported by current primary-source evidence. Prefer frontier, preview, nightly, commit-level, or successor technology when it materially improves the result and can be proven compatible, secure, maintainable, supportable, and no-loss for the actual target; do not retain stale defaults merely because they are familiar. Pin provenance/versions, preserve explicit target envelopes, backport frontier techniques when the target must stay fixed, and reject novelty that regresses protected dimensions."
PERFORMANCE_BULLET = "- **Performance is an always-on zero-loss ratchet.** For substantive runtime-affecting work, perform a bounded free-speed pass on the touched or causal path and integrate verified no-loss wins. Explicit performance tasks require at least one measured target/hot-path gain plus no material regression across relevant protected behavior and performance/resource dimensions on equivalent work. Faster-by-doing-less, preservation-only, hidden cost-shifting, and one-metric wins that worsen another protected dimension fail. Every verified better baseline becomes the new floor."


def strip_registry_footer(text: str) -> str:
    idx = text.find(FOOTER_MARKER)
    if idx < 0:
        return text
    start = idx
    while start > 0 and text[start - 1] in "\r\n ":
        start -= 1
    return text[:start].rstrip() + "\n"


def normalize_uag(text: str) -> str:
    text = strip_registry_footer(text)
    text = text.replace("UAG_BOOTSTRAP:v0.3.2", "UAG_BOOTSTRAP:v0.3.4")
    text = text.replace("UAG_BOOTSTRAP:v0.3.3", "UAG_BOOTSTRAP:v0.3.4")
    text = text.replace("UAG_EXECUTION_CONSTITUTION:v0.3.2", "UAG_EXECUTION_CONSTITUTION:v0.3.4")
    text = text.replace("UAG_EXECUTION_CONSTITUTION:v0.3.3", "UAG_EXECUTION_CONSTITUTION:v0.3.4")
    if "proactively scan challengers/integrations" not in text:
        text = text.replace(
            "modernize/fix forward; decompose mixed upgrades;",
            "modernize/fix forward; proactively scan challengers/integrations and reuse superior authorized implementations before reinventing; decompose mixed upgrades;",
            1,
        )
    if "**Performance is an always-on zero-loss ratchet.**" not in text:
        old = "- **Performance and quality improve together.**"
        pos = text.find(old)
        if pos >= 0:
            line_end = text.find("\n", pos)
            text = text[:pos] + PERFORMANCE_BULLET + text[line_end:]
        else:
            anchor = "- **No fake or partial success.**"
            pos = text.find(anchor)
            if pos >= 0:
                line_end = text.find("\n", pos)
                text = text[: line_end + 1] + PERFORMANCE_BULLET + "\n" + text[line_end + 1 :]
            else:
                raise RuntimeError("UAG performance invariant anchor not found")
    if "**Best-in-class is the acceptance target.**" not in text:
        anchor = "- **Challenge before reinventing.**"
        pos = text.find(anchor)
        if pos >= 0:
            line_end = text.find("\n", pos)
            text = text[: line_end + 1] + BEST_IN_CLASS_BULLET + "\n" + FRONTIER_STACK_BULLET + "\n" + text[line_end + 1 :]
        else:
            raise RuntimeError("UAG challenger invariant anchor not found")
    if "**Challenge before reinventing.**" not in text:
        anchor = "- **Modernize and fix forward.**"
        pos = text.find(anchor)
        if pos >= 0:
            line_end = text.find("\n", pos)
            text = text[: line_end + 1] + CHALLENGE_BULLET + "\n" + text[line_end + 1 :]
        else:
            raise RuntimeError("UAG modernize invariant anchor not found")
    ref = "- `references/challenger-integration.md` — challenge the proposed implementation before reinventing; scan, compare, authorize, compose, and record challenger decisions."
    if "references/challenger-integration.md" not in text:
        marker = "## References"
        pos = text.find(marker)
        if pos < 0:
            raise RuntimeError("UAG References section missing")
        insert = text.find("\n", pos) + 1
        text = text[:insert] + "\n" + ref + "\n" + text[insert:]
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("skills"))
    args = ap.parse_args()
    root = args.root.resolve()
    uag_dir = root / UAG
    installer = uag_dir / "scripts" / "install_execution_constitution.py"
    if not installer.is_file():
        raise SystemExit(f"missing governance installer: {installer}")

    uag_md = uag_dir / "SKILL.md"
    uag_md.write_text(normalize_uag(uag_md.read_text(encoding="utf-8")), encoding="utf-8")

    updated = [UAG]
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        if skill_dir.name == UAG:
            continue
        skill_md = skill_dir / "SKILL.md"
        cleaned = strip_registry_footer(skill_md.read_text(encoding="utf-8"))
        skill_md.write_text(cleaned, encoding="utf-8")
        subprocess.run([sys.executable, str(installer), str(skill_dir)], check=True)
        updated.append(skill_dir.name)

    print("NORMALIZED", len(updated), "skills:", ", ".join(updated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
