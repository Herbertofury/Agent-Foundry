#!/usr/bin/env python3
"""Static audit for the Ultimate Agent Governance package or an adopted repository."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED = [
    "AGENTS.md",
    "PRODUCT_INVARIANTS.md",
    "MODERNIZATION_STANDARD.md",
    "FAILURE_INTELLIGENCE_STANDARD.md",
    "APP_INVARIANTS.md",
    "MOD_INVARIANTS.md",
    "SITE_ADAPTERS.md",
    "CHAT_EXECUTION_STANDARD.md",
    "RUNTIME_PROOF.md",
    "PERFORMANCE_ACCEPTANCE.md",
    "COMPLETION_RECEIPT.md",
    "PLANS.md",
]

REQUIRED_TOOLS = [
    "scripts/challenger_gate.py",
    "scripts/audit_agent_governance.py",
    "scripts/invariant_harness.py",
    "scripts/performance_gate.py",
    "scripts/upgrade_gate.py",
    "scripts/completeness_gate.py",
    "scripts/failure_incident.py",
    "scripts/completion_receipt.py",
    "scripts/site_adapter_manifest_check.py",
]

ADAPTER_EXPECTATIONS = {
    "CLAUDE.md": ["AGENTS.md", "PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "FAILURE_INTELLIGENCE_STANDARD.md", "APP_INVARIANTS.md", "MOD_INVARIANTS.md", "SITE_ADAPTERS.md", "CHAT_EXECUTION_STANDARD.md"],
    "GEMINI.md": ["AGENTS.md", "PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "FAILURE_INTELLIGENCE_STANDARD.md", "APP_INVARIANTS.md", "MOD_INVARIANTS.md", "SITE_ADAPTERS.md", "CHAT_EXECUTION_STANDARD.md"],
    ".github/copilot-instructions.md": ["AGENTS.md", "PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "FAILURE_INTELLIGENCE_STANDARD.md", "APP_INVARIANTS.md", "MOD_INVARIANTS.md", "SITE_ADAPTERS.md", "CHAT_EXECUTION_STANDARD.md"],
    ".continue/rules/00-governance.md": ["AGENTS.md", "PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "FAILURE_INTELLIGENCE_STANDARD.md", "APP_INVARIANTS.md", "MOD_INVARIANTS.md", "SITE_ADAPTERS.md", "CHAT_EXECUTION_STANDARD.md"],
}

PLACEHOLDER_PATTERNS = [
    re.compile(r"\b" + "TO" + "DO" + r"\b", re.I),
    re.compile(r"\[" + "TO" + "DO" + r"[:\]]", re.I),
    re.compile(r"example" + "_asset", re.I),
]


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def numbered_invariants(text: str, pattern: str) -> list[int]:
    return [int(n) for n in re.findall(pattern, text, re.M)]


def audit(root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    for rel in REQUIRED + REQUIRED_TOOLS:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    agents = root / "AGENTS.md"
    if agents.is_file():
        lines = line_count(agents)
        if lines > 220:
            warnings.append(f"AGENTS.md is {lines} lines; consider moving conditional detail to scoped rules/references")
        agent_text = agents.read_text(encoding="utf-8")
        for token in ["PRODUCT_INVARIANTS.md", "MODERNIZATION_STANDARD.md", "FAILURE_INTELLIGENCE_STANDARD.md", "APP_INVARIANTS.md", "MOD_INVARIANTS.md", "SITE_ADAPTERS.md", "CHAT_EXECUTION_STANDARD.md", "RUNTIME_PROOF.md", "PERFORMANCE_ACCEPTANCE.md"]:
            if token not in agent_text:
                errors.append(f"AGENTS.md does not reference {token}")
        if "NO-EXCUSES COMPLETION; FAILURE IS A ROUTING SIGNAL" not in agent_text:
            errors.append("AGENTS.md is missing the top no-excuses completion/recovery rule")
        if "UNKNOWN IS NOT ABSENT; BLOCKERS NEVER CLOSE OUT; NEVER SUFFER THE SAME FAILURE TWICE" not in agent_text:
            errors.append("AGENTS.md is missing the major unknown-not-absent/blocker/recovery-memory rule")
        if "CONTINUOUS MODERNIZATION; FIX FORWARD; ALWAYS ADVANCE THE BASELINE" not in agent_text:
            errors.append("AGENTS.md is missing the top continuous-modernization/fix-forward rule")
        if "UPGRADE PROMOTION GATE — PROVE BETTER, THEN PROMOTE" not in agent_text:
            errors.append("AGENTS.md is missing the evidence-based upgrade promotion gate")
        if "Solved once must stay solved" not in agent_text:
            errors.append("AGENTS.md is missing the solved-once recovery-memory rule")
        if "MAXIMUM PERFORMANCE AND MAXIMUM QUALITY, TOGETHER" not in agent_text:
            errors.append("AGENTS.md is missing the prime maximum-performance-plus-quality rule")
        if "PERFORMANCE WORK HAS TWO MANDATORY SUCCESS CONDITIONS" not in agent_text:
            errors.append("AGENTS.md is missing the direct dual-success performance gate")
        if "Never obtain apparent success by doing less than the user requested" not in agent_text:
            errors.append("AGENTS.md is missing the absolute full-request preservation rule")
        if "A build passing is not proof that the product works" not in agent_text:
            errors.append("AGENTS.md is missing the direct real-runtime proof gate")
        if "PRESERVATION-FIRST ENGINEERING" not in agent_text:
            errors.append("AGENTS.md is missing the direct preservation-first engineering rule")
        if "EVIDENCE-BOUND COMPLETION" not in agent_text:
            errors.append("AGENTS.md is missing the direct evidence-bound completion rule")
        if "ALIVE COMPANION PRODUCT STANDARD" not in agent_text:
            errors.append("AGENTS.md is missing the direct alive-companion product standard")
        if "AUTH-FIRST INTEGRATION STANDARD" not in agent_text:
            errors.append("AGENTS.md is missing the direct auth-first integration standard")
        if "REUSABLE SITE-ADAPTER STANDARD" not in agent_text:
            errors.append("AGENTS.md is missing the direct reusable site-adapter standard")
        if "LIVE CHAT / DOMAIN-SKILL EXECUTION PARITY" not in agent_text:
            errors.append("AGENTS.md is missing the direct live-chat/domain-skill execution parity rule")

    inv = root / "PRODUCT_INVARIANTS.md"
    if inv.is_file():
        text = inv.read_text(encoding="utf-8")
        if "Status:** Binding project policy" not in text:
            warnings.append("PRODUCT_INVARIANTS.md does not declare binding policy status")
        if "# Invariant 000 — Never Obtain Apparent Success by Doing Less Than Requested" not in text:
            errors.append("PRODUCT_INVARIANTS.md is missing Invariant 000 full-request preservation")
        if "# Invariant 001 — Continuously Modernize; Fix Forward; Never Settle Into Staleness" not in text:
            errors.append("PRODUCT_INVARIANTS.md is missing Invariant 001 continuous modernization/fix-forward")
        nums = numbered_invariants(text, r"^# Invariant\s+(\d{3})\s+—")
        if not nums:
            errors.append("PRODUCT_INVARIANTS.md contains no numbered '# Invariant NNN —' headings")
        elif nums != sorted(set(nums)):
            errors.append(f"invariant numbers are duplicated or out of order: {nums}")
        for heading in ["## Rule", "## Regression requirements", "## Acceptance test"]:
            if heading not in text:
                errors.append(f"PRODUCT_INVARIANTS.md is missing required invariant section heading: {heading}")
        for required_phrase in ["Mandatory dual-success rule", "preservation without the requested performance gain is incomplete performance work"]:
            if required_phrase.lower() not in text.lower():
                errors.append(f"PRODUCT_INVARIANTS.md is missing performance dual-success language: {required_phrase}")

    failure = root / "FAILURE_INTELLIGENCE_STANDARD.md"
    if failure.is_file():
        ftext = failure.read_text(encoding="utf-8")
        if "Status:** Binding cross-domain engineering and live-execution policy" not in ftext:
            warnings.append("FAILURE_INTELLIGENCE_STANDARD.md does not declare binding cross-domain policy status")
        for required_phrase in [
            "Unknown Is Not Absent",
            "Blockers Are Never Closeout States for Required Work",
            "External Completeness Must Be Proven, Not Assumed",
            "Never Suffer the Same Failure Twice",
            "Black-Box Incident Capture Is Mandatory for Nontrivial Recovered Failures",
            "Recovered Failures Must Improve the System",
        ]:
            if required_phrase not in ftext:
                errors.append(f"FAILURE_INTELLIGENCE_STANDARD.md is missing required rule: {required_phrase}")

    modern = root / "MODERNIZATION_STANDARD.md"
    if modern.is_file():
        mtext = modern.read_text(encoding="utf-8")
        if "Status:** Binding cross-domain engineering policy" not in mtext:
            warnings.append("MODERNIZATION_STANDARD.md does not declare binding cross-domain policy status")
        for required_phrase in [
            "Every Substantive Task Gets a Freshness Pass",
            "Latest Production-Worthy Version Is the Default Baseline",
            "Explicit Target Envelopes Must Be Preserved and Modernized Within",
            "Bleeding-Edge Better Methods Must Be Evaluated and Adopted When They Win",
            "Integrate Superior Tools Fully, Not as Decorative Sidecars",
            "Fix Forward Through Upgrade Breakage",
            "Every Improvement Becomes the New Reusable Baseline",
            "Upgrades Must Earn Promotion Through Comparative Proof",
            "Mixed Upgrades Must Be Decomposed; Keep the Gains and Excise the Regressions",
        ]:
            if required_phrase not in mtext:
                errors.append(f"MODERNIZATION_STANDARD.md is missing required modernization rule: {required_phrase}")

    app_inv = root / "APP_INVARIANTS.md"
    if app_inv.is_file():
        text = app_inv.read_text(encoding="utf-8")
        if "Status:** Binding domain policy" not in text:
            warnings.append("APP_INVARIANTS.md does not declare binding domain policy status")
        nums = numbered_invariants(text, r"^# App Invariant A(\d{3})\s+—")
        if not nums:
            errors.append("APP_INVARIANTS.md contains no numbered '# App Invariant ANNN —' headings")
        elif nums != sorted(set(nums)):
            errors.append(f"app invariant numbers are duplicated or out of order: {nums}")
        for required_phrase in [
            "Stale Asynchronous Work Must Never Override Newer User Intent",
            "Important Mutations Must Be Atomic or Recoverable",
            "First Useful Render Must Not Wait on Nonessential Enrichment",
            "Installed/Updated/Downloaded/Completed State Requires Artifact-Level Proof",
            "Desktop Applications Must Feel Native, Direct, and Predictable",
            "No Dead, Decorative, or Disconnected Architecture",
            "Apps Must Feel Alive, Proactive, and Companion-Like",
            "Authenticated Integrations Must Be First-Class, Persistent, and Retry-Safe",
            "Provider Integrations Must Use the Reusable Site Adapter Platform",
            "Applications Must Continuously Modernize and Fix Forward",
        ]:
            if required_phrase not in text:
                errors.append(f"APP_INVARIANTS.md is missing required app rule: {required_phrase}")

    mod_inv = root / "MOD_INVARIANTS.md"
    if mod_inv.is_file():
        text = mod_inv.read_text(encoding="utf-8")
        if "Status:** Binding domain policy" not in text:
            warnings.append("MOD_INVARIANTS.md does not declare binding domain policy status")
        nums = numbered_invariants(text, r"^# Mod Invariant M(\d{3})\s+—")
        if not nums:
            errors.append("MOD_INVARIANTS.md contains no numbered '# Mod Invariant MNNN —' headings")
        elif nums != sorted(set(nums)):
            errors.append(f"mod invariant numbers are duplicated or out of order: {nums}")
        if "never an acceptable repair" not in text.lower() and "removal is not a repair path" not in text.lower():
            errors.append("MOD_INVARIANTS.md does not encode the no-removal-as-repair invariant")
        if "Maximum Performance, Fidelity, Content, and QoL Must Be Pursued Together" not in text:
            errors.append("MOD_INVARIANTS.md is missing the joint performance/fidelity/content rule")
        if "Mods Must Continuously Modernize Within the Exact Target Envelope" not in text:
            errors.append("MOD_INVARIANTS.md is missing the exact-target modernization/fix-forward rule")
        for required_phrase in [
            "preservation is not permission to leave the performance problem unsolved",
            "both at once",
            "Blockers are not acceptable closeout states",
        ]:
            if required_phrase.lower() not in text.lower():
                errors.append(f"MOD_INVARIANTS.md is missing mandatory dual-success language: {required_phrase}")


    chat_exec = root / "CHAT_EXECUTION_STANDARD.md"
    if chat_exec.exists():
        ctext = chat_exec.read_text(encoding="utf-8")
        for required_phrase in [
            "No-Excuses Completion; Failure Is a Routing Signal",
            "Domain Skills Own Workflow; This Standard Owns Acceptance",
            "Repair the Root Cause; Do Not Delete the Symptom",
            "Performance Work Requires Dual Success",
            "Solvable Blockers Force a Strategy Change",
            "Runtime Proof Beats Build-Pass Theater",
            "Continuity Is Part of Correctness",
            "Freshness and Fix-Forward Are Part of Live Work",
            "Upgrades Must Prove They Are Better; Mixed Upgrades Must Be Dissected",
            "Unknown Is Not Absent; Required Unknowns Stay Active",
            "External Completeness Must Reconcile Every Item",
            "Never Suffer the Same Failure Twice",
        ]:
            if required_phrase not in ctext:
                errors.append(f"CHAT_EXECUTION_STANDARD.md is missing required live-execution rule: {required_phrase}")

    # Do not allow the old blocker escape-hatch wording to creep back into canonical execution policy.
    for rel in ["AGENTS.md", "PRODUCT_INVARIANTS.md", "MOD_INVARIANTS.md", "FAILURE_INTELLIGENCE_STANDARD.md", "CHAT_EXECUTION_STANDARD.md", "PERFORMANCE_ACCEPTANCE.md", "COMPLETION_RECEIPT.md"]:
        path = root / rel
        if path.is_file():
            low = path.read_text(encoding="utf-8").lower()
            for banned in ["only a genuinely external constraint", "genuine external constraints", "may close with blockers"]:
                if banned in low:
                    errors.append(f"{rel} contains obsolete blocker escape-hatch wording: {banned}")

    site = root / "SITE_ADAPTERS.md"
    if site.is_file():
        text = site.read_text(encoding="utf-8")
        if "Status:** Binding domain policy" not in text:
            warnings.append("SITE_ADAPTERS.md does not declare binding domain policy status")
        nums = numbered_invariants(text, r"^# Site Adapter Invariant SA(\d{3})\s+-")
        if not nums:
            errors.append("SITE_ADAPTERS.md contains no numbered site-adapter invariants")
        elif nums != sorted(set(nums)):
            errors.append(f"site-adapter invariant numbers are duplicated or out of order: {nums}")
        for required_phrase in [
            "One Shared Adapter Contract, No Disposable Scrapers",
            "Capability-Driven Routing",
            "Exhaustive Pagination and Complete Logical Results",
            "Continuous Adapter Improvement Is Required",
            "Legitimate Access Boundary Is Non-Negotiable",
            "Adapters Must Track Current Provider Capabilities and Migrate Forward",
            "Completeness Claims Require End-to-End Coverage Proof",
        ]:
            if required_phrase not in text:
                errors.append(f"SITE_ADAPTERS.md is missing required site-adapter rule: {required_phrase}")
    if not (root / "schemas/site-adapter-manifest.schema.json").is_file():
        errors.append("missing required file: schemas/site-adapter-manifest.schema.json")

    runtime = root / "RUNTIME_PROOF.md"
    if runtime.is_file():
        text = runtime.read_text(encoding="utf-8")
        for phrase in ["Build identity", "Fresh artifact", "Launch identity", "Workflow exercise", "Observed result"]:
            if phrase not in text:
                errors.append(f"RUNTIME_PROOF.md is missing proof-chain element: {phrase}")

    perf = root / "PERFORMANCE_ACCEPTANCE.md"
    if perf.is_file():
        text = perf.read_text(encoding="utf-8")
        for phrase in ["same intended workload and output semantics", "first useful result/render", "Concurrency/hardware scaling", "maximize performance and result quality together", "Dual-success gate", "preserving the existing result without improving the requested performance dimension is not a pass", "Upgrade promotion: newer must prove faster/better, not merely newer"]:
            if phrase not in text:
                errors.append(f"PERFORMANCE_ACCEPTANCE.md is missing required concept: {phrase}")

    receipt = root / "COMPLETION_RECEIPT.md"
    if receipt.is_file():
        rtext = receipt.read_text(encoding="utf-8")
        if "requirement -> implementation location -> verification action -> observed result -> status" not in rtext:
            errors.append("COMPLETION_RECEIPT.md is missing the requirement-to-evidence mapping")
        if "Modernization proof" not in rtext:
            errors.append("COMPLETION_RECEIPT.md is missing mandatory modernization proof")
        for phrase in ["comparison_evidence", "mixed_upgrade_resolution", "external_completeness_proof", "failure_learning_proof", "incident_fingerprint"]:
            if phrase not in rtext:
                errors.append(f"COMPLETION_RECEIPT.md is missing required evidence field: {phrase}")

    for rel, tokens in ADAPTER_EXPECTATIONS.items():
        path = root / rel
        if not path.exists():
            warnings.append(f"optional cross-agent adapter absent: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                errors.append(f"{rel} does not point to canonical {token}")
        if line_count(path) > 80:
            warnings.append(f"{rel} is unusually long; adapters should point to canonical policy rather than duplicate it")

    # Check internal Markdown links for local targets. Ignore anchors and web URLs.
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:") or target.startswith("/"):
                continue
            local = (path.parent / target).resolve()
            try:
                local.relative_to(root.resolve())
            except ValueError:
                continue
            if not local.exists():
                errors.append(f"broken local Markdown link in {path.relative_to(root)} -> {target}")

    # Flag scaffold leftovers anywhere except research source names.
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".yaml", ".yml", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in PLACEHOLDER_PATTERNS:
            if pat.search(text):
                errors.append(f"unresolved scaffold/placeholder marker in {path.relative_to(root)}: {pat.pattern}")
                break

    if not errors:
        notes.append("canonical governance files, proof standards, tools, and adapters passed static audit")

    return {"root": str(root), "errors": errors, "warnings": warnings, "notes": notes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(Path(args.root).resolve())
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key in ("errors", "warnings", "notes"):
            for item in result[key]:
                print(f"{key[:-1].upper()}: {item}")
        print(f"Summary: {len(result['errors'])} error(s), {len(result['warnings'])} warning(s)")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
