#!/usr/bin/env python3
"""Add or refresh the compact shared execution-constitution bridge in a skill entrypoint."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

START = "<!-- UAG_BRIDGE_START:v0.3.6 -->"
END = "<!-- UAG_BRIDGE_END:v0.3.6 -->"
BLOCK = f'''{START}
## Mandatory governance bootstrap

<!-- UAG_BOOTSTRAP:v0.3.6 -->
Before any substantive action, load `skills://ultimate-agent-governance/skill.md` once for the current continuity epoch, then return to this skill's domain workflow. Do **not** skip this because this skill is more specific. The domain skill owns procedure; Ultimate Agent Governance owns the shared acceptance boundary. If cross-skill loading is unavailable, fails, or is not supported in the current harness, enforce the embedded constitution below locally with no weakening.

This bootstrap is a **start gate**, not optional guidance: do not mutate, repair, build, optimize, migrate, scrape, package, or claim completion until the shared acceptance contract is active. Skill switches, compaction, retries, timeouts, handoffs, and tool changes never clear it.

## Shared execution constitution

<!-- UAG_EXECUTION_CONSTITUTION:v0.3.6 -->
- **No blocker closeout.** Failure is a routing signal, not a deliverable. Install/provision missing tools and dependencies; repair environment, DNS/network, cache, runtime, build, auth, or provider state; switch to materially different supported routes; and resume after interruption. Required unresolved work stays active and is never relabeled complete.
- **Unknown is not absent.** A search/list/API/parser/auth/provider miss becomes `unresolved-active`, not “does not exist.” Use alternate authoritative routes until found or absence is actually proven.
- **Never suffer the same failure twice.** Reuse prior verified recovery knowledge before rediscovery. After a nontrivial verified recovery, capture signature, environment, cause, failed routes, successful route, verification, invalidation conditions, and regression protection so recurrence is faster and deterministic.
- **No fake or partial success.** Never manufacture success through caps, sampling, truncation, hidden skips, placeholders, removed user-visible features/content/fidelity/coverage, downgraded quality, or weakened verification. Preserve the complete requested result.
- **Performance is an always-on zero-loss ratchet.** For substantive runtime-affecting work, perform a bounded free-speed pass on the touched or causal path and integrate verified no-loss wins. Explicit performance tasks require at least one measured target/hot-path gain plus no material regression across relevant protected behavior and performance/resource dimensions on equivalent work. Faster-by-doing-less, preservation-only, hidden cost-shifting, and one-metric wins that worsen another protected dimension fail. Every verified better baseline becomes the new floor.
- **Modernize and fix forward.** Check current best compatible methods/tools/versions when freshness matters. Newer is a candidate until comparative proof shows it is better. Mixed upgrades must be profiled/bisected/decomposed: retain/backport gains, patch/replace regressive internals, then retest before promotion.
- **Challenge before reinventing.** For substantive implementation, architecture, optimization, conversion, integration, or tooling work, run a bounded challenger/integration scan across relevant upstreams, repositories, forks, package/plugin ecosystems, standards, and reference implementations. Prefer authorized adopt/merge/port/wrap/backport/reuse of materially superior pieces over rebuilding weaker duplicates; compose the best pieces when no single candidate wins, preserve provenance/licensing/permission constraints, and record candidate dispositions.
- **Real proof beats structural proof.** When the real runtime/workflow is available, exercise the actual final artifact and affected user path. Build/static success alone is not runtime proof.
- **Continuity is mandatory.** Preserve accepted requirements, identities, evidence, checkpoints, failed-route history, recovered fixes, and exact next action across skill switches, timeouts, handoffs, and retries. Never restart solved discovery without an invalidator.
- **Cross-skill state integrity.** Skills compose as overlays and may not erase, replace, reset, downgrade, fork, or silently reinterpret another active skill's accepted requirements, canonical IDs/paths, verified evidence, checkpoints, blockers/no-repeat history, domain ownership, or exact next action. The narrower domain skill keeps procedure ownership; governance/continuity skills add acceptance and persistence constraints without stealing the workflow. Before a skill switch, preserve a continuity capsule; after a bounded helper/guardrail/subtask, return control to the prior owner and resume its exact next action. Never rewrite another skill bundle or shared state merely to make the current skill pass; governance itself changes only during explicit governance maintenance.
- **Remote durability is part of completion.** For substantive project work, persist every coherent material checkpoint to the canonical source remote (GitHub/VCS when applicable) and material artifacts/checkpoint exports to connected Google Drive when available, then verify remote identity/readback and record lineage. If a GitHub project uses a Wiki, keep the actual live GitHub Wiki synchronized from canonical docs; a repo-side `wiki/` mirror alone is not publication. If the required Wiki does not exist, create/bootstrap it through an authorized supported route. Unsynced required remotes remain `unresolved-active`; never let the only current copy live in chat, sandbox, Library, or local scratch space.
- **Completeness must be proven.** For exhaustive external results, reconcile expected/discovered/accepted/rejected/unresolved counts and terminal pagination/coverage before claiming complete.

If progress reaches an action only the user can authorize or perform, preserve the exact checkpoint and request only that smallest action; the unresolved acceptance item remains in progress and must never be called complete.
{END}
'''


def _frontmatter_insert_pos(text: str) -> int:
    if not text.startswith("---"):
        return 0
    end = text.find("\n---", 3)
    if end < 0:
        return 0
    nl = text.find("\n", end + 1)
    return len(text) if nl < 0 else nl + 1


def _skill_name(text: str) -> str:
    m = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", text)
    return m.group(1) if m else ""


def _remove_existing_bridge(text: str, skill_name: str) -> str:
    text = re.sub(
        r"\n?<!-- UAG_BRIDGE_START:[^>]+ -->.*?<!-- UAG_BRIDGE_END:[^>]+ -->\n?",
        "\n",
        text,
        count=1,
        flags=re.S,
    )

    start = text.find("## Mandatory governance bootstrap")
    if start >= 0:
        top = text.find("\n# ", start)
        if top >= 0:
            first_heading = text[top + 1:text.find("\n", top + 1)].strip()
            if skill_name != "minecraft-repair" and first_heading == "# Minecraft Repair":
                next_top = text.find("\n# ", top + 3)
                if next_top >= 0:
                    top = next_top
            text = text[:start] + text[top + 1:]
        else:
            patterns = [
                r"## Mandatory governance bootstrap.*?the unresolved acceptance item remains in progress and must never be called complete\.\n?",
                r"## Mandatory governance bootstrap.*?the unresolved item remains in progress and unresolved\.\n?",
            ]
            for pat in patterns:
                new = re.sub(pat, "", text, count=1, flags=re.S)
                if new != text:
                    text = new
                    break
    return text


def update(text: str) -> str:
    skill_name = _skill_name(text)
    text = _remove_existing_bridge(text, skill_name)
    pos = _frontmatter_insert_pos(text)
    before = text[:pos].rstrip("\n")
    after = text[pos:].lstrip("\n")
    sep = "\n\n" if before else ""
    tail = "\n\n" + after if after else "\n"
    return before + sep + BLOCK.rstrip() + tail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", type=Path)
    args = ap.parse_args()
    p = args.skill_dir / "SKILL.md" if args.skill_dir.is_dir() else args.skill_dir
    if not p.is_file():
        raise SystemExit(f"SKILL.md not found: {p}")
    text = p.read_text(encoding="utf-8")
    if _skill_name(text) == "ultimate-agent-governance":
        raise SystemExit("refusing to rewrite the canonical ultimate-agent-governance entrypoint with its child-skill bootstrap")
    new = update(text)
    p.write_text(new, encoding="utf-8")
    print(f"UPDATED {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
