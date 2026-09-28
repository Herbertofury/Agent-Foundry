#!/usr/bin/env python3
"""Add or refresh the compact shared execution-constitution bridge in a skill entrypoint."""
from __future__ import annotations
import argparse
from pathlib import Path

MARKER_PREFIX = "<!-- UAG_EXECUTION_CONSTITUTION:"
BLOCK = '''## Mandatory governance bootstrap

<!-- UAG_BOOTSTRAP:v0.3.2 -->
Before any substantive action, load `skills://ultimate-agent-governance/skill.md` once for the current continuity epoch, then return to this skill's domain workflow. Do **not** skip this because this skill is more specific. The domain skill owns procedure; Ultimate Agent Governance owns the shared acceptance boundary. If cross-skill loading is unavailable, fails, or is not supported in the current harness, enforce the embedded constitution below locally with no weakening.

This bootstrap is a **start gate**, not optional guidance: do not mutate, repair, build, optimize, migrate, scrape, package, or claim completion until the shared acceptance contract is active. Skill switches, compaction, retries, timeouts, handoffs, and tool changes never clear it.

## Shared execution constitution

<!-- UAG_EXECUTION_CONSTITUTION:v0.3.2 -->
- **No blocker closeout.** Failure is a routing signal, not a deliverable. Install/provision missing tools and dependencies; repair environment, DNS/network, cache, runtime, build, auth, or provider state; switch to materially different supported routes; and resume after interruption. Required unresolved work stays active and is never relabeled complete.
- **Unknown is not absent.** A search/list/API/parser/auth/provider miss becomes `unresolved-active`, not “does not exist.” Use alternate authoritative routes until found or absence is actually proven.
- **Never suffer the same failure twice.** Reuse prior verified recovery knowledge before rediscovery. After a nontrivial verified recovery, capture signature, environment, cause, failed routes, successful route, verification, invalidation conditions, and regression protection so recurrence is faster and deterministic.
- **No fake or partial success.** Never manufacture success through caps, sampling, truncation, hidden skips, placeholders, removed user-visible features/content/fidelity/coverage, downgraded quality, or weakened verification. Preserve the complete requested result.
- **Performance and quality improve together.** Equivalent-work performance tasks require a measured gain in the target metric/hot path **and** preservation of quality, quantity, correctness, content, fidelity, compatibility, and QoL. Faster-by-doing-less and preserved-but-flat both fail.
- **Modernize and fix forward.** Check current best compatible methods/tools/versions when freshness matters. Newer is a candidate until comparative proof shows it is better. Mixed upgrades must be profiled/bisected/decomposed: retain/backport gains, patch/replace regressive internals, then retest before promotion.
- **Real proof beats structural proof.** When the real runtime/workflow is available, exercise the actual final artifact and affected user path. Build/static success alone is not runtime proof.
- **Continuity is mandatory.** Preserve accepted requirements, identities, evidence, checkpoints, failed-route history, recovered fixes, and exact next action across skill switches, timeouts, handoffs, and retries. Never restart solved discovery without an invalidator.
- **Completeness must be proven.** For exhaustive external results, reconcile expected/discovered/accepted/rejected/unresolved counts and terminal pagination/coverage before claiming complete.

If progress reaches an action only the user can authorize or perform, preserve the exact checkpoint and request only that smallest action; the unresolved acceptance item remains in progress and must never be called complete.


# Minecraft Repair



Operate as a root-cause repair system, not a generic troubleshooting checklist. Preserve the modpack, features, worlds, and configuration whenever technically possible. Prefer a verified compatibility patch, update, adapter, config correction, or targeted data repair over broad removal/downgrade.
'''


def update(text: str) -> str:
    import re
    # Remove any previous bootstrap/constitution block, preserving all domain prose.
    patterns = [
        re.compile(r"\n## Mandatory governance bootstrap\n.*?(?=\n(?:#|##) [^\n]+\n|\Z)", re.S),
        re.compile(r"\n## Shared execution constitution\n.*?If progress requires a user-only authorization or action,.*?unresolved\.\n", re.S),
    ]
    for pat in patterns:
        text = pat.sub("\n", text, count=1)
    # Insert immediately after YAML frontmatter when present; otherwise at beginning.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            nl = text.find("\n", end + 1)
            pos = len(text) if nl < 0 else nl + 1
            return text[:pos] + "\n" + BLOCK + "\n" + text[pos:].lstrip("\n")
    return BLOCK + "\n" + text.lstrip("\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", type=Path)
    args = ap.parse_args()
    p = args.skill_dir / "SKILL.md" if args.skill_dir.is_dir() else args.skill_dir
    if not p.is_file():
        raise SystemExit(f"SKILL.md not found: {p}")
    text = p.read_text(encoding="utf-8")
    new = update(text)
    p.write_text(new, encoding="utf-8")
    print(f"UPDATED {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
