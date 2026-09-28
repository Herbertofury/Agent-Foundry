#!/usr/bin/env python3
"""Gate a Minecraft 26.3 Fabric/NeoForge port candidate before expensive native runtime QA."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from port_intake import inspect
from port_26_3_common import write_json
from mixin_target_resolver import resolve_project as resolve_mixins_exact
from access_rule_resolver import resolve_project as resolve_access_exact
from packaged_linkage_audit import audit as audit_packaged_linkage
from content_parity_audit import audit as audit_content_parity
from api_reference_migration import audit as audit_api_references
from registration_parity_audit import audit as audit_registration_parity

EXPECTED = {
    "fabric": {
        "minecraft": "26.3",
        "java": 25,
        "required_paths": ["src/main/resources/fabric.mod.json", "build.gradle", "gradle.properties"],
    },
    "neoforge": {
        "minecraft": "26.3",
        "java": 25,
        "required_any": [
            "src/main/templates/META-INF/neoforge.mods.toml",
            "src/main/resources/META-INF/neoforge.mods.toml",
        ],
        "required_paths": ["build.gradle", "gradle.properties"],
    },
}


def load_json(path: Path | None) -> dict | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_lock(project: Path) -> dict | None:
    p = project / "devkit-26.3-lock.json"
    return load_json(p) if p.exists() else None


def read_ledger(project: Path, override: Path | None) -> dict | None:
    p = override or project / "porting-ledger.json"
    return load_json(p) if p and p.exists() else None


def path_exists(project: Path, rel: str) -> bool:
    return (project / rel).exists()


def evaluate(project: Path, loader: str, phase: str, allow: set[str], ledger_path: Path | None, strict_release: bool, target_index_path: Path | None = None, packaged_jar: Path | None = None, dependency_indexes: list[Path] | None = None, source_bytecode: Path | None = None, source_namespace: str | None = None, source_mapping_indexes: list[Path] | None = None) -> dict:
    project = project.resolve()
    intake = inspect(project, loader)
    blockers: list[dict] = []
    warnings: list[dict] = []

    expected = EXPECTED[loader]
    lock = read_lock(project)
    if not lock:
        blockers.append({"id": "missing-devkit-lock", "message": "devkit-26.3-lock.json is missing; target toolchain identity is not frozen."})
    else:
        target = lock.get("target") or {}
        if str(target.get("minecraft")) != "26.3":
            blockers.append({"id": "wrong-minecraft-target", "message": f"lock targets Minecraft {target.get('minecraft')!r}, expected 26.3"})
        if target.get("loader") != loader:
            blockers.append({"id": "wrong-loader-target", "message": f"lock loader {target.get('loader')!r}, expected {loader}"})
        try:
            java = int(target.get("java"))
        except Exception:
            java = 0
        if java < 25:
            blockers.append({"id": "java-below-25", "message": f"lock targets Java {java}, expected at least 25"})

    for rel in expected.get("required_paths", []):
        if not path_exists(project, rel):
            blockers.append({"id": "missing-target-file", "message": f"required {loader} 26.3 project file missing: {rel}"})
    required_any = expected.get("required_any") or []
    if required_any and not any(path_exists(project, rel) for rel in required_any):
        blockers.append({"id": "missing-target-metadata", "message": f"none of the expected {loader} metadata paths exist: {', '.join(required_any)}"})

    declared_mc = (intake.get("detected", {}).get("metadata", {}).get("declared_minecraft_version"))
    if declared_mc and str(declared_mc) != "26.3":
        blockers.append({"id": "gradle-minecraft-version", "message": f"gradle.properties declares minecraft_version={declared_mc}, expected 26.3"})
    elif not declared_mc:
        warnings.append({"id": "minecraft-version-unparsed", "message": "minecraft_version was not parsed from gradle.properties; verify target metadata manually."})

    explicit_java = intake.get("build_hints", {}).get("explicit_java_targets") or []
    if explicit_java and min(explicit_java) < 25:
        blockers.append({"id": "explicit-old-java", "message": f"project still declares Java target(s) below 25: {explicit_java}"})
    if not explicit_java:
        warnings.append({"id": "java-target-unparsed", "message": "No explicit Java target was parsed; verify Java 25 toolchain/release flags."})

    for finding in intake.get("findings", []):
        if finding["id"] in allow:
            warnings.append({"id": "allowed-risk", "message": f"explicitly allowed risk {finding['id']}", "finding": finding})
            continue
        if finding["severity"] in {"blocker", "high"}:
            blockers.append({"id": finding["id"], "message": finding["summary"], "finding": finding})
        else:
            warnings.append({"id": finding["id"], "message": finding["summary"], "finding": finding})

    # 26.3 is official/unobfuscated. Historical mappings are migration evidence only; they must
    # not leak into the finished target source/build or Mixin/access surfaces.
    mapping_hints = intake.get("mapping_hints") or {}
    if loader == "fabric" and mapping_hints.get("uses_yarn"):
        blockers.append({"id": "fabric-26.3-yarn-target", "message": "26.3 target still declares Yarn mappings; migrate the source to official names before the 26.x target."})
    if loader == "fabric" and mapping_hints.get("uses_intermediary"):
        blockers.append({"id": "fabric-26.3-intermediary-target", "message": "26.3 target still declares/depends on Intermediary mapping names; finished 26.3 source must use official names."})

    mixin_audit = intake.get("mixin_audit") or {}
    for item in mixin_audit.get("blockers") or []:
        if item.get("id") in allow:
            warnings.append({"id": "allowed-mixin-risk", "message": f"explicitly allowed Mixin/remap risk {item.get('id')}", "finding": item})
        else:
            blockers.append({"id": item.get("id", "mixin-remap-blocker"), "message": item.get("message", "Mixin/remap audit blocker"), "finding": item})
    for item in mixin_audit.get("warnings") or []:
        warnings.append({"id": item.get("id", "mixin-remap-warning"), "message": item.get("message", "Mixin/remap manual-review surface"), "finding": item})


    exact_evidence = {}
    target_index = None
    if target_index_path:
        try:
            target_index = load_json(target_index_path)
        except Exception as exc:
            blockers.append({"id": "target-symbol-index-unreadable", "message": f"Could not read target symbol index {target_index_path}: {exc}"})
        if target_index:
            mixin_exact = resolve_mixins_exact(project, target_index)
            access_exact = resolve_access_exact(project, target_index)
            exact_evidence["mixin_target_resolution"] = mixin_exact
            exact_evidence["access_target_resolution"] = access_exact
            for item in mixin_exact.get("blockers") or []:
                blockers.append({"id": item.get("id", "mixin-target-resolution"), "message": item.get("message", "Exact Mixin target resolution failed"), "finding": item})
            for item in mixin_exact.get("warnings") or []:
                warnings.append({"id": item.get("id", "mixin-target-resolution-warning"), "message": item.get("message", "Exact Mixin target resolution warning"), "finding": item})
            for item in access_exact.get("blockers") or []:
                blockers.append({"id": item.get("id", "access-target-resolution"), "message": item.get("message", "Exact access target resolution failed"), "finding": item})
            for item in access_exact.get("warnings") or []:
                warnings.append({"id": item.get("id", "access-target-resolution-warning"), "message": item.get("message", "Exact access target resolution warning"), "finding": item})

    mixin_audit_for_release = intake.get("mixin_audit") or {}
    has_exact_symbol_surfaces = bool(
        mixin_audit_for_release.get("source_mixin_surfaces")
        or mixin_audit_for_release.get("compiled_mixin_surfaces")
        or mixin_audit_for_release.get("class_tweakers")
        or mixin_audit_for_release.get("access_transformers")
    )
    if strict_release and has_exact_symbol_surfaces and not target_index_path:
        blockers.append({"id": "release-target-symbol-index-missing", "message": "Strict release contains Mixins/access rules but no exact 26.3 target symbol index was supplied; owner/member/descriptor proof is required."})

    if packaged_jar:
        if not packaged_jar.exists():
            blockers.append({"id": "packaged-candidate-missing", "message": f"Packaged candidate does not exist: {packaged_jar}"})
        elif target_index:
            indexes = [target_index]
            for dep in dependency_indexes or []:
                try:
                    indexes.append(load_json(dep))
                except Exception as exc:
                    blockers.append({"id": "dependency-symbol-index-unreadable", "message": f"Could not read dependency symbol index {dep}: {exc}"})
            linkage = audit_packaged_linkage(packaged_jar, indexes)
            exact_evidence["packaged_linkage"] = linkage
            for item in linkage.get("blockers") or []:
                blockers.append({"id": item.get("id", "packaged-linkage"), "message": item.get("message", "Packaged symbolic linkage failed"), "finding": item})
            for item in linkage.get("warnings") or []:
                warnings.append({"id": item.get("id", "packaged-linkage-warning"), "message": item.get("message", "Packaged linkage warning"), "finding": item})
        else:
            blockers.append({"id": "packaged-linkage-no-target-index", "message": "Packaged linkage audit requested without a target symbol index."})
    elif strict_release:
        blockers.append({"id": "release-packaged-candidate-missing", "message": "Strict release requires --packaged-jar so the exact shipped bytecode can receive symbolic linkage validation."})

    ledger = read_ledger(project, ledger_path)
    if ledger:
        phase_a = ledger.get("phase_a") or {}
        if phase == "a" and phase_a.get("future_vanilla_parity_enabled"):
            blockers.append({"id": "phase-a-parity-enabled", "message": "future-vanilla parity is enabled during Phase A; certify the mod-owned base first."})
        items = ledger.get("items") or []
        missing = [i for i in items if isinstance(i, dict) and i.get("status") == "missing"]
        if missing:
            blockers.append({"id": "inventory-gaps", "message": f"port ledger still contains {len(missing)} missing item(s)", "items": missing[:30]})
        invalid = [i for i in items if isinstance(i, dict) and i.get("status") not in {"carried", "regenerated", "superseded", "intentionally_excluded", "missing"}]
        if invalid:
            blockers.append({"id": "invalid-ledger-status", "message": f"port ledger contains {len(invalid)} item(s) with invalid/missing status"})
        source_manifest = ledger.get("source_manifest") or {}
        content_evidence_rel = source_manifest.get("content_identity_evidence")
        if content_evidence_rel:
            content_evidence_path = Path(content_evidence_rel)
            if not content_evidence_path.is_absolute():
                content_evidence_path = project / content_evidence_path
            if not content_evidence_path.exists():
                blockers.append({"id": "content-identity-evidence-missing", "message": f"Source content identity evidence is declared but missing: {content_evidence_path}"})
            else:
                try:
                    source_content = load_json(content_evidence_path)
                    parity = audit_content_parity(source_content, project, ledger.get("content_exclusions") or [])
                    exact_evidence["content_parity"] = parity
                    if parity.get("missing"):
                        blockers.append({
                            "id": "content-parity-loss",
                            "message": f"Target is missing {len(parity['missing'])} source content identity/identities; zero-loss release is blocked.",
                            "items": parity["missing"][:40],
                        })
                    for note in (parity.get("target_inventory") or {}).get("notes") or []:
                        warnings.append({"id": note.get("id", "content-inventory-note"), "message": f"Content inventory note: {note}"})
                except Exception as exc:
                    blockers.append({"id": "content-parity-audit-failed", "message": f"Could not evaluate source-to-target content parity: {exc}"})
        elif strict_release:
            blockers.append({"id": "release-content-identity-evidence-missing", "message": "Strict release requires a source content identity inventory so data/assets/content loss cannot hide behind a successful build."})

        registration_evidence_rel = source_manifest.get("registration_identity_evidence")
        if registration_evidence_rel:
            registration_evidence_path = Path(registration_evidence_rel)
            if not registration_evidence_path.is_absolute():
                registration_evidence_path = project / registration_evidence_path
            if not registration_evidence_path.exists():
                blockers.append({"id": "registration-identity-evidence-missing", "message": f"Source registration identity evidence is declared but missing: {registration_evidence_path}"})
            else:
                try:
                    source_regs = load_json(registration_evidence_path)
                    reg_parity = audit_registration_parity(source_regs, project, ledger.get("registration_exclusions") or [])
                    exact_evidence["registration_parity"] = reg_parity
                    if reg_parity.get("missing"):
                        blockers.append({
                            "id": "registration-parity-loss",
                            "message": f"Target is missing {len(reg_parity['missing'])} high-confidence code-registered source identity/identities.",
                            "items": reg_parity["missing"][:40],
                        })
                except Exception as exc:
                    blockers.append({"id": "registration-parity-audit-failed", "message": f"Could not evaluate source-to-target code registration parity: {exc}"})
        elif strict_release:
            blockers.append({"id": "release-registration-identity-evidence-missing", "message": "Strict release requires the source code-registration inventory so blocks/items/entities/etc. cannot disappear while resources still look complete."})

        compiled_source_count = int((source_manifest.get("inventory") or {}).get("compiled_classes") or 0)
        effective_source_bytecode = source_bytecode
        if not effective_source_bytecode and compiled_source_count:
            candidate = Path((source_manifest.get("identity") or {}).get("path") or "")
            if candidate.exists():
                effective_source_bytecode = candidate
        if effective_source_bytecode:
            if not source_namespace:
                blockers.append({"id": "source-bytecode-namespace-missing", "message": "Compiled source bytecode is available but its exact historical namespace was not supplied. Use --source-namespace (for example intermediary, srg, mcp_named, mojang_named); do not guess this for release proof."})
            elif not target_index:
                blockers.append({"id": "api-reference-target-index-missing", "message": "Compiled-source API migration audit requires the exact 26.3 --target-index."})
            else:
                try:
                    mapping_indexes = [load_json(x) for x in (source_mapping_indexes or [])]
                    api_migration = audit_api_references(effective_source_bytecode, source_namespace, mapping_indexes, target_index)
                    exact_evidence["api_reference_migration"] = api_migration
                    if api_migration.get("status") != "PASS":
                        blockers.append({"id": "api-reference-migration-gaps", "message": f"Compiled source still has {api_migration.get('counts',{}).get('blockers',0)} Minecraft API reference migration gap(s) against exact 26.3 symbols.", "items": (api_migration.get("blockers") or [])[:40]})
                except Exception as exc:
                    blockers.append({"id": "api-reference-migration-audit-failed", "message": f"Could not evaluate compiled-source API migration: {exc}"})
        elif strict_release and compiled_source_count:
            blockers.append({"id": "release-source-bytecode-audit-missing", "message": "Strict release began from compiled source/JAR content but no source bytecode is available for exact historical-API reference migration proof."})

        if strict_release:
            if not source_manifest:
                blockers.append({"id": "release-source-manifest-missing", "message": "strict release gate requires porting-ledger.json source_manifest identity."})
            if not items:
                blockers.append({"id": "release-inventory-empty", "message": "strict release gate requires a populated source inventory ledger."})
    elif strict_release:
        blockers.append({"id": "release-ledger-missing", "message": "strict release gate requires porting-ledger.json."})
    else:
        warnings.append({"id": "ledger-missing", "message": "No porting ledger was found; full conversion accounting still has to be proven before release."})

    loaders = set(intake.get("detected", {}).get("loaders") or [])
    if loader not in loaders:
        warnings.append({"id": "loader-metadata-not-detected", "message": f"intake did not positively detect {loader} metadata; detected={sorted(loaders)}"})

    return {
        "schema_version": 1,
        "target": {"minecraft": "26.3", "loader": loader, "java": 25, "phase": phase},
        "project": str(project),
        "status": "PASS" if not blockers else "FAIL",
        "blockers": blockers,
        "warnings": warnings,
        "finding_counts": dict(Counter(f.get("finding", {}).get("severity", "gate") for f in blockers)),
        "intake": intake,
        "exact_symbol_evidence": exact_evidence,
    }


def render_md(result: dict) -> str:
    lines = [
        "# Minecraft 26.3 Port Guard",
        "",
        f"**Status: {result['status']}**",
        "",
        f"Project: `{result['project']}`",
        f"Target: Minecraft 26.3 / {result['target']['loader']} / Java 25 / Phase {result['target']['phase'].upper()}",
        "",
        "## Blockers",
        "",
    ]
    if not result["blockers"]:
        lines.append("None detected by the static guard.")
    else:
        for item in result["blockers"]:
            lines.append(f"- **{item['id']}** — {item['message']}")
    lines += ["", "## Warnings", ""]
    if not result["warnings"]:
        lines.append("None.")
    else:
        for item in result["warnings"]:
            lines.append(f"- **{item['id']}** — {item['message']}")
    lines += [
        "",
        "## Runtime boundary",
        "",
        "A PASS here means the configured static 26.3 gate is clear. It does **not** replace Gradle build, dedicated-server, native-client/integrated-server, visual, network, save or restart proof required by the Dev Kit acceptance contract.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--loader", required=True, choices=["fabric", "neoforge"])
    ap.add_argument("--phase", choices=["a", "b"], default="a")
    ap.add_argument("--allow-risk", action="append", default=[], help="rule id explicitly reviewed/allowed; repeatable")
    ap.add_argument("--ledger", type=Path)
    ap.add_argument("--strict-release", action="store_true")
    ap.add_argument("--target-index", type=Path, help="classfile_symbol_index.py JSON for exact 26.3 target classes")
    ap.add_argument("--packaged-jar", type=Path, help="exact built mod JAR for packaged symbolic linkage audit")
    ap.add_argument("--dependency-index", action="append", default=[], type=Path, help="additional exact dependency class index; repeatable")
    ap.add_argument("--source-bytecode", type=Path, help="old compiled mod JAR/class directory for whole-mod API reference migration audit")
    ap.add_argument("--source-namespace", help="exact historical namespace of --source-bytecode, e.g. intermediary, srg, mcp_named, mojang_named")
    ap.add_argument("--source-mapping-index", action="append", default=[], type=Path, help="normalized same-source-version mapping index used to bridge old compiled names; repeatable")
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--md-out", type=Path)
    args = ap.parse_args()
    result = evaluate(args.project, args.loader, args.phase, set(args.allow_risk), args.ledger, args.strict_release, args.target_index, args.packaged_jar, args.dependency_index, args.source_bytecode, args.source_namespace, args.source_mapping_index)
    if args.json_out:
        write_json(args.json_out, result)
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_md(result), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
