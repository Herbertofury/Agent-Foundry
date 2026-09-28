#!/usr/bin/env python3
"""Statically audit packaged JVM linkage against exact target/dependency class indexes.

The release gate is intentionally stronger than compile/remap success. It validates exact
owner/name/descriptor linkage, actual JVM invocation mode (static/instance/interface), Java class
version, Multi-Release/nested-JAR selection, packaged Mixin/config references, Fabric metadata
references, and ServiceLoader providers before the native packaged-runtime gate.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from classfile_symbol_index import (
    ACC_FINAL, ACC_INTERFACE, ACC_PRIVATE, ACC_PROTECTED, ACC_PUBLIC, ACC_STATIC,
    build_index, is_subclass, nest_host, resolve_member,
)
from access_rule_resolver import resolve_project as resolve_access_rules
from port_26_3_common import Bundle, write_json

DESC_CLASS_RX = re.compile(r"L([^;]+);")
DEFAULT_PREFIXES = ("net/minecraft/",)
STATIC_OPS = {"getstatic", "putstatic", "invokestatic"}
INSTANCE_OPS = {"getfield", "putfield", "invokevirtual", "invokespecial", "newinvokespecial", "invokeinterface"}
METHOD_HANDLE_OPS = {1: "getfield", 2: "getstatic", 3: "putfield", 4: "putstatic", 5: "invokevirtual", 6: "invokestatic", 7: "invokespecial", 8: "newinvokespecial", 9: "invokeinterface"}


def _merge_indexes(indexes: list[dict]) -> dict:
    classes = {}
    owners = {}
    for ix in indexes:
        source = ix.get("input") or "<index>"
        for name, cls in (ix.get("classes") or {}).items():
            if name not in classes:
                classes[name] = cls
                owners[name] = source
    return {"schema_version": 2, "input": ";".join(x.get("input") or "<index>" for x in indexes), "classes": classes, "owners": owners}


def _interesting(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name.startswith(p) for p in prefixes)


def _internal(name: str) -> str:
    return name.strip().replace(".", "/").split("::", 1)[0]


def _manifest_attributes(text: str) -> dict[str, str]:
    # Unfold continuation lines per the JAR manifest format.
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith(" ") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    out = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip().lower()] = value.strip()
    return out


def _packaging_audit(bundle: Bundle, candidate_index: dict, universe: dict, prefixes: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    names = set(bundle.names())
    classes = candidate_index.get("classes") or {}
    runtime_classes = universe.get("classes") or {}
    blockers: list[dict] = []
    warnings: list[dict] = []

    mixin_configs: set[str] = {n for n in names if n.lower().endswith(".mixins.json")}

    if "fabric.mod.json" in names:
        try:
            meta = json.loads(bundle.read("fabric.mod.json").decode("utf-8"))
            access = meta.get("accessWidener")
            if isinstance(access, str) and access not in names:
                blockers.append({"id": "missing-packaged-access-widener", "path": "fabric.mod.json", "message": f"fabric.mod.json references missing access widener {access}"})
            for item in meta.get("mixins") or []:
                config = item if isinstance(item, str) else item.get("config") if isinstance(item, dict) else None
                if config:
                    mixin_configs.add(config)
                    if config not in names:
                        blockers.append({"id": "missing-packaged-mixin-config", "path": "fabric.mod.json", "message": f"fabric.mod.json references missing Mixin config {config}"})
            for item in meta.get("jars") or []:
                nested = item.get("file") if isinstance(item, dict) else item if isinstance(item, str) else None
                if nested and nested not in names:
                    blockers.append({"id": "missing-packaged-nested-jar", "path": "fabric.mod.json", "message": f"fabric.mod.json references missing nested JAR {nested}"})
            for key, entries in (meta.get("entrypoints") or {}).items():
                for entry in entries if isinstance(entries, list) else [entries]:
                    value = entry.get("value") if isinstance(entry, dict) else entry if isinstance(entry, str) else None
                    if not value or value.startswith("kotlin:"):
                        continue
                    owner = _internal(value)
                    if owner and owner not in classes:
                        blockers.append({"id": "missing-packaged-entrypoint-class", "path": "fabric.mod.json", "message": f"Fabric entrypoint {key} references absent class {owner}", "reference": value})
        except Exception as exc:
            blockers.append({"id": "fabric-metadata-unreadable", "path": "fabric.mod.json", "message": f"Could not parse packaged fabric.mod.json: {exc}"})

    manifest_name = next((n for n in names if n.upper() == "META-INF/MANIFEST.MF"), None)
    if manifest_name:
        try:
            attrs = _manifest_attributes(bundle.read(manifest_name).decode("utf-8", errors="replace"))
            for config in re.split(r"\s*,\s*", attrs.get("mixinconfigs", "")):
                if config:
                    mixin_configs.add(config)
                    if config not in names:
                        blockers.append({"id": "missing-packaged-mixin-config", "path": manifest_name, "message": f"Manifest MixinConfigs references missing config {config}"})
        except Exception as exc:
            warnings.append({"id": "manifest-unreadable", "path": manifest_name, "message": str(exc)})

    for config in sorted(mixin_configs):
        if config not in names:
            continue
        try:
            data = json.loads(bundle.read(config).decode("utf-8"))
        except Exception as exc:
            blockers.append({"id": "packaged-mixin-config-unreadable", "path": config, "message": f"Could not parse packaged Mixin config: {exc}"})
            continue
        if not isinstance(data, dict):
            continue
        package = data.get("package") or ""
        for group in ("mixins", "client", "server"):
            for item in data.get(group) or []:
                if not isinstance(item, str):
                    continue
                fq = item if "." in item and not package else f"{package}.{item}" if package else item
                owner = _internal(fq)
                if owner not in classes:
                    blockers.append({"id": "missing-packaged-mixin-class", "path": config, "message": f"Mixin config references absent class {owner}", "environment": group})
        plugin = data.get("plugin")
        if isinstance(plugin, str) and _internal(plugin) not in classes:
            blockers.append({"id": "missing-packaged-mixin-plugin", "path": config, "message": f"Mixin config references absent plugin class {_internal(plugin)}"})
        refmap = data.get("refmap")
        if isinstance(refmap, str) and refmap and refmap not in names:
            warnings.append({"id": "missing-packaged-refmap", "path": config, "message": f"Mixin config references refmap {refmap}, but it is absent from the packaged JAR. This is only acceptable when the target runtime intentionally does not require a refmap."})

    # ServiceLoader files are executable linkage declarations even though no Java call site names
    # the provider directly. Missing providers otherwise survive compilation and fail at runtime.
    all_known = set(classes) | set(runtime_classes)
    for name in sorted(n for n in names if n.startswith("META-INF/services/") and not n.endswith("/")):
        try:
            text = bundle.read(name).decode("utf-8", errors="replace")
        except Exception as exc:
            blockers.append({"id": "service-provider-file-unreadable", "path": name, "message": str(exc)})
            continue
        for lineno, raw in enumerate(text.splitlines(), 1):
            provider = raw.split("#", 1)[0].strip()
            if not provider:
                continue
            owner = _internal(provider)
            if owner not in all_known:
                blockers.append({"id": "missing-service-provider-class", "path": name, "line": lineno, "message": f"Service provider {provider} is absent from the packaged candidate and supplied dependency indexes."})

    return blockers, warnings


def _package(owner: str) -> str:
    return owner.rsplit("/", 1)[0] if "/" in owner else ""


def _access_effects(candidate: Path, symbol_universe: dict) -> dict:
    """Translate packaged AW/ClassTweaker/AT declarations into linkage-time effects.

    The exact access resolver already proves the declaration exists on the named owner. Here we only
    consume resolved rules so direct-bytecode access checks model transformations that will actually
    run instead of flagging intentional widening as IllegalAccessError.
    """
    result = resolve_access_rules(candidate, symbol_universe)
    effects = {
        "accessible_classes": set(),
        "accessible_members": set(),
        "mutable_fields": set(),
        "extendable_classes": set(),
        "resolver": result,
    }
    for row in result.get("resolved") or []:
        op = str(row.get("operation") or "").lower()
        owner = str(row.get("owner") or "").replace(".", "/")
        kind = row.get("kind")
        makes_accessible = op in {"accessible", "extendable"} or op.startswith("public") or op.startswith("protected")
        removes_final = op in {"extendable", "mutable"} or "-f" in op
        if kind == "class":
            if makes_accessible:
                effects["accessible_classes"].add(owner)
            if removes_final:
                effects["extendable_classes"].add(owner)
            continue
        resolution = row.get("resolution") if isinstance(row.get("resolution"), dict) else {}
        for candidate_row in resolution.get("candidates") or []:
            declaring = candidate_row.get("declaring_owner") or owner
            desc = candidate_row.get("descriptor") or row.get("descriptor")
            key = (declaring, kind, row.get("name"), desc)
            if makes_accessible:
                effects["accessible_members"].add(key)
            if kind == "field" and removes_final:
                effects["mutable_fields"].add(key)
    return effects


def _class_accessible(universe: dict, caller: str, owner: str, effects: dict) -> bool:
    cls = (universe.get("classes") or {}).get(owner) or {}
    if owner in effects.get("accessible_classes", set()):
        return True
    if int(cls.get("access") or 0) & ACC_PUBLIC:
        return True
    return _package(caller) == _package(owner)


def _same_nest(universe: dict, a: str, b: str) -> bool:
    return nest_host(universe, a) == nest_host(universe, b)


def _member_accessible(universe: dict, caller: str, candidate: dict, kind: str, effects: dict) -> tuple[bool, str]:
    declaring = candidate.get("declaring_owner") or ""
    key = (declaring, kind, candidate.get("name"), candidate.get("descriptor"))
    if key in effects.get("accessible_members", set()):
        return True, "access-transformer/widener"
    flags = int(candidate.get("access") or 0)
    if flags & ACC_PUBLIC:
        return True, "public"
    if flags & ACC_PRIVATE:
        return (_same_nest(universe, caller, declaring), "private nest access")
    if flags & ACC_PROTECTED:
        if _package(caller) == _package(declaring):
            return True, "protected same-package"
        if is_subclass(universe, caller, declaring):
            return True, "protected subclass"
        return False, "protected member from unrelated package/class"
    return (_package(caller) == _package(declaring), "package-private member")


def _validate_access_and_special(path: str, caller: str, ref: dict, resolution: dict, universe: dict, effects: dict) -> tuple[list[dict], list[dict]]:
    blockers: list[dict] = []
    warnings: list[dict] = []
    candidates = resolution.get("candidates") or []
    if not candidates:
        return blockers, warnings
    # The symbolic owner itself must be accessible, and the selected declaration must also be
    # accessible. Multiple exact candidates are treated conservatively: at least one must satisfy
    # access, while unusual protected-subclass receiver cases remain a runtime-verifier warning.
    if not _class_accessible(universe, caller, ref["owner"], effects):
        blockers.append({"id": "linkage-owner-class-inaccessible", "path": path, "message": f"{caller} references non-public class {ref['owner']} from another package without a packaged access rule.", "reference": ref})
    accessible = []
    reasons = []
    for candidate in candidates:
        declaring = candidate.get("declaring_owner") or ref["owner"]
        if not _class_accessible(universe, caller, declaring, effects):
            reasons.append(f"declaring class {declaring} is inaccessible")
            continue
        ok, reason = _member_accessible(universe, caller, candidate, ref.get("kind") or "method", effects)
        if ok:
            accessible.append(candidate)
        else:
            reasons.append(f"{declaring}.{candidate.get('name')}{candidate.get('descriptor')}: {reason}")
    if not accessible:
        blockers.append({
            "id": "linkage-member-inaccessible",
            "path": path,
            "message": f"{caller} cannot legally access {ref['owner']}.{ref['name']}{ref['descriptor']} after target-side access resolution ({'; '.join(reasons) or 'inaccessible'}).",
            "reference": ref,
            "resolution": resolution,
        })
        return blockers, warnings

    op = ref.get("opcode_name")
    chosen = accessible[0]
    flags = int(chosen.get("access") or 0)
    if ref.get("kind") == "method" and ref.get("name") == "<init>":
        if op not in {"invokespecial", "newinvokespecial"}:
            blockers.append({"id": "linkage-constructor-invocation-mode", "path": path, "message": f"Constructor {ref['owner']}{ref['descriptor']} is invoked with {op}, expected invokespecial.", "reference": ref})
        if chosen.get("declaring_owner") != ref.get("owner"):
            blockers.append({"id": "linkage-constructor-owner-mismatch", "path": path, "message": f"Constructor resolution escaped owner {ref['owner']} to {chosen.get('declaring_owner')}; constructors are never inherited.", "reference": ref, "resolution": resolution})
    elif op == "newinvokespecial":
        blockers.append({"id": "linkage-newinvokespecial-nonconstructor", "path": path, "message": f"Method-handle REF_newInvokeSpecial targets non-constructor {ref['owner']}.{ref['name']}{ref['descriptor']}.", "reference": ref})

    if ref.get("kind") == "method" and (flags & ACC_PRIVATE) and not (flags & ACC_STATIC) and op not in {"invokespecial", "newinvokespecial"}:
        key = (chosen.get("declaring_owner"), "method", chosen.get("name"), chosen.get("descriptor"))
        if key not in effects.get("accessible_members", set()):
            blockers.append({"id": "linkage-private-invocation-mode", "path": path, "message": f"Private instance method {chosen.get('declaring_owner')}.{chosen.get('name')}{chosen.get('descriptor')} requires invokespecial unless widened before linkage.", "reference": ref})

    if ref.get("kind") == "field" and op in {"putfield", "putstatic"} and (flags & ACC_FINAL):
        key = (chosen.get("declaring_owner"), "field", chosen.get("name"), chosen.get("descriptor"))
        if key not in effects.get("mutable_fields", set()):
            required = "<clinit>" if op == "putstatic" else "<init>"
            if caller != chosen.get("declaring_owner") or ref.get("caller_name") != required:
                blockers.append({"id": "linkage-final-field-write", "path": path, "message": f"{caller}.{ref.get('caller_name')} writes final field {chosen.get('declaring_owner')}.{chosen.get('name')} with {op}; Java runtime permits this only in the declaring class {required} unless a packaged rule removes final.", "reference": ref})

    if flags & ACC_PROTECTED and _package(caller) != _package(chosen.get("declaring_owner") or "") and is_subclass(universe, caller, chosen.get("declaring_owner") or "") and op in {"getfield", "putfield", "invokevirtual", "invokespecial"}:
        warnings.append({"id": "protected-receiver-runtime-proof", "path": path, "message": f"Protected cross-package access {caller} -> {chosen.get('declaring_owner')}.{chosen.get('name')} passes subclass proof, but exact receiver-stack legality remains a native packaged-runtime gate.", "reference": ref})
    return blockers, warnings


def _validate_candidate_hierarchy(candidate_classes: dict, universe: dict, effects: dict, prefixes: tuple[str, ...]) -> list[dict]:
    blockers: list[dict] = []
    classes = universe.get("classes") or {}
    for owner, cls in candidate_classes.items():
        super_owner = cls.get("super")
        if super_owner and _interesting(super_owner, prefixes) and super_owner in classes:
            target = classes[super_owner]
            if int(target.get("access") or 0) & ACC_INTERFACE:
                blockers.append({"id": "linkage-superclass-became-interface", "path": cls.get("path"), "message": f"{owner} extends {super_owner}, but the exact runtime owner is now an interface."})
            if (int(target.get("access") or 0) & ACC_FINAL) and super_owner not in effects.get("extendable_classes", set()):
                blockers.append({"id": "linkage-final-superclass", "path": cls.get("path"), "message": f"{owner} extends final runtime class {super_owner}; packaged access rules do not remove final."})
            if not _class_accessible(universe, owner, super_owner, effects):
                blockers.append({"id": "linkage-superclass-inaccessible", "path": cls.get("path"), "message": f"{owner} extends inaccessible runtime class {super_owner}."})
        for iface in cls.get("interfaces") or []:
            if _interesting(iface, prefixes) and iface in classes and not (int(classes[iface].get("access") or 0) & ACC_INTERFACE):
                blockers.append({"id": "linkage-interface-became-class", "path": cls.get("path"), "message": f"{owner} implements {iface}, but the exact runtime owner is now a class."})
    return blockers


def _validate_invocation_mode(path: str, caller: str, ref: dict, resolution: dict, universe: dict) -> list[dict]:
    blockers: list[dict] = []
    op = ref.get("opcode_name")
    candidates = resolution.get("candidates") or []
    if not op or not candidates:
        return blockers
    static_states = {bool(int(x.get("access") or 0) & ACC_STATIC) for x in candidates}
    expected_static = op in STATIC_OPS
    if (expected_static and True not in static_states) or (op in INSTANCE_OPS and False not in static_states):
        blockers.append({
            "id": "linkage-staticness-mismatch",
            "path": path,
            "message": f"{caller} uses {op} for {ref['owner']}.{ref['name']}{ref['descriptor']}, but the exact target declaration has incompatible static/instance mode.",
            "reference": ref,
            "resolution": resolution,
        })

    owner_cls = (universe.get("classes") or {}).get(ref["owner"])
    owner_is_interface = bool(int((owner_cls or {}).get("access") or 0) & ACC_INTERFACE)
    if op == "invokeinterface" and not owner_is_interface:
        blockers.append({"id": "linkage-interface-mode-mismatch", "path": path, "message": f"{caller} uses invokeinterface for non-interface owner {ref['owner']}", "reference": ref})
    if op == "invokevirtual" and owner_is_interface:
        blockers.append({"id": "linkage-interface-mode-mismatch", "path": path, "message": f"{caller} uses invokevirtual for interface owner {ref['owner']}", "reference": ref})
    if op == "invokeinterface" and not ref.get("interface"):
        blockers.append({"id": "linkage-constant-pool-kind-mismatch", "path": path, "message": f"invokeinterface call site does not use an InterfaceMethodref for {ref['owner']}.{ref['name']}", "reference": ref})
    if op == "invokevirtual" and ref.get("interface"):
        blockers.append({"id": "linkage-constant-pool-kind-mismatch", "path": path, "message": f"invokevirtual call site incorrectly uses an InterfaceMethodref for {ref['owner']}.{ref['name']}", "reference": ref})
    if op in {"invokestatic", "invokespecial", "newinvokespecial"}:
        if owner_is_interface != bool(ref.get("interface")):
            blockers.append({"id": "linkage-constant-pool-kind-mismatch", "path": path, "message": f"{op} constant-pool reference kind disagrees with whether {ref['owner']} is an interface.", "reference": ref})
    return blockers


def audit(candidate: Path, indexes: list[dict], prefixes: tuple[str, ...] = DEFAULT_PREFIXES, runtime_java: int = 25) -> dict:
    universe = _merge_indexes(indexes)
    runtime_classes = universe["classes"]
    candidate_index = build_index(candidate, include_refs=True, runtime_java=runtime_java)
    candidate_classes = candidate_index.get("classes") or {}
    blockers: list[dict] = []
    warnings: list[dict] = []
    checked_refs = 0
    checked_bytecode_refs = 0
    checked_classes = len(candidate_classes)
    max_major = runtime_java + 44

    for failure in candidate_index.get("failures") or []:
        blockers.append({"id": "candidate-class-parse-failure", "path": failure.get("path"), "message": failure.get("error", "candidate class parse failure")})

    # A mod artifact must never make Minecraft/loader linkage "pass" by bundling shadow copies of
    # runtime classes. For user-supplied dependency prefixes, duplicate runtime classes are equally
    # hazardous because classpath order would decide behavior.
    for owner, cls in candidate_classes.items():
        if _interesting(owner, prefixes) and owner in runtime_classes:
            blockers.append({"id": "candidate-shadows-runtime-class", "path": cls.get("path"), "message": f"Packaged candidate contains runtime-owned class {owner}; do not shade/copy target classes to manufacture linkage success."})
        if int(cls.get("major") or 0) > max_major:
            blockers.append({"id": "candidate-class-version-too-new", "path": cls.get("path"), "message": f"{owner} uses classfile major {cls.get('major')}, newer than Java {runtime_java} permits (max {max_major})."})

    for dup in candidate_index.get("duplicate_owners") or []:
        owner = dup.get("owner") or ""
        if _interesting(owner, prefixes):
            blockers.append({"id": "candidate-duplicate-runtime-class", "path": dup.get("selected"), "message": f"Packaged candidate contains multiple variants/copies of audited runtime class {owner}; classpath/Multi-Release selection must be unambiguous.", "duplicate": dup})

    # Non-runtime-owned candidate classes can satisfy dependency references when intentionally
    # bundled. Runtime-owned classes above are never allowed to self-satisfy.
    resolution_universe = {**universe, "classes": dict(runtime_classes)}
    for owner, cls in candidate_classes.items():
        if owner not in resolution_universe["classes"] and not _interesting(owner, prefixes):
            resolution_universe["classes"][owner] = cls

    # Model packaged access transformations before deciding whether bytecode that compiled in a
    # widened dev environment will remain legal against the exact production runtime.
    access_effects = _access_effects(candidate, resolution_universe) if indexes else {
        "accessible_classes": set(), "accessible_members": set(), "mutable_fields": set(),
        "extendable_classes": set(), "resolver": {"status": "PASS", "blockers": [], "warnings": []},
    }
    for item in (access_effects.get("resolver") or {}).get("blockers") or []:
        blockers.append({"id": "packaged-access-rule-invalid", "path": item.get("path"), "line": item.get("line"), "message": item.get("message", "Packaged access rule failed exact declaration resolution."), "finding": item})
    for item in (access_effects.get("resolver") or {}).get("warnings") or []:
        warnings.append({"id": "packaged-access-rule-warning", "path": item.get("path"), "line": item.get("line"), "message": item.get("message", "Packaged access rule requires review."), "finding": item})
    blockers.extend(_validate_candidate_hierarchy(candidate_classes, resolution_universe, access_effects, prefixes))

    bundle = Bundle(candidate)
    try:
        pkg_blockers, pkg_warnings = _packaging_audit(bundle, candidate_index, universe, prefixes)
        blockers.extend(pkg_blockers)
        warnings.extend(pkg_warnings)
    finally:
        bundle.close()

    for path, cls in sorted((x.get("path") or name, x) for name, x in candidate_classes.items()):
        caller = cls["owner"]
        for ref in cls.get("class_refs") or []:
            base = ref
            while base.startswith("["):
                base = base[1:]
            if base.startswith("L") and base.endswith(";"):
                base = base[1:-1]
            if _interesting(base, prefixes) and base not in resolution_universe["classes"]:
                blockers.append({"id": "unresolved-class-reference", "path": path, "message": f"{caller} references absent class {base}", "reference": base})

        # Constant-pool references remain a conservative completeness sweep. Actual invocation-mode
        # proof below uses Code attributes and therefore catches static/interface drift specifically.
        for ref in cls.get("member_refs") or []:
            owner = ref["owner"]
            if not _interesting(owner, prefixes):
                continue
            checked_refs += 1
            if owner not in resolution_universe["classes"]:
                blockers.append({"id": "unresolved-member-owner", "path": path, "message": f"{caller} references {owner}.{ref['name']}{ref['descriptor']} but owner is absent", "reference": ref})
                continue
            rr = resolve_member(resolution_universe, owner, ref["kind"], ref["name"], ref["descriptor"])
            if rr["status"] != "RESOLVED":
                blockers.append({"id": "unresolved-member-reference", "path": path, "message": f"{caller} references {owner}.{ref['name']}{ref['descriptor']} but exact symbolic resolution failed ({rr['status']})", "reference": ref, "resolution": rr})
            for typ in DESC_CLASS_RX.findall(ref["descriptor"]):
                if _interesting(typ, prefixes) and typ not in resolution_universe["classes"]:
                    blockers.append({"id": "unresolved-descriptor-type", "path": path, "message": f"Descriptor for {owner}.{ref['name']} references absent type {typ}", "reference": ref, "missing_type": typ})

        for ref in cls.get("bytecode_member_refs") or []:
            owner = ref["owner"]
            if not _interesting(owner, prefixes) or owner not in resolution_universe["classes"]:
                continue
            checked_bytecode_refs += 1
            rr = resolve_member(resolution_universe, owner, ref["kind"], ref["name"], ref["descriptor"])
            if rr["status"] == "RESOLVED":
                blockers.extend(_validate_invocation_mode(path, caller, ref, rr, resolution_universe))
                access_blockers, access_warnings = _validate_access_and_special(path, caller, ref, rr, resolution_universe, access_effects)
                blockers.extend(access_blockers)
                warnings.extend(access_warnings)

        for indy in cls.get("invokedynamic_refs") or []:
            fi = indy.get("functional_interface")
            sam_name = indy.get("sam_name")
            sam_desc = indy.get("sam_descriptor")
            if fi and _interesting(fi, prefixes):
                checked_refs += 1
                if fi not in resolution_universe["classes"]:
                    blockers.append({"id": "unresolved-indy-sam-owner", "path": path, "message": f"{caller} lambda targets absent functional interface {fi}", "invokedynamic": indy})
                elif sam_name and sam_desc:
                    rr = resolve_member(resolution_universe, fi, "method", sam_name, sam_desc)
                    if rr["status"] != "RESOLVED":
                        blockers.append({"id": "unresolved-indy-sam", "path": path, "message": f"{caller} lambda SAM {fi}.{sam_name}{sam_desc} failed exact resolution ({rr['status']})", "invokedynamic": indy, "resolution": rr})
                else:
                    warnings.append({"id": "indy-sam-incomplete", "path": path, "message": f"Could not fully decode SAM descriptor for invokedynamic {sam_name} in {caller}", "invokedynamic": indy})
            impl = indy.get("implementation") or {}
            impl_owner = impl.get("owner")
            if impl_owner and _interesting(impl_owner, prefixes):
                checked_refs += 1
                rr = resolve_member(resolution_universe, impl_owner, impl.get("kind", "method"), impl.get("name", ""), impl.get("descriptor"))
                if rr["status"] != "RESOLVED":
                    blockers.append({"id": "unresolved-indy-implementation", "path": path, "message": f"{caller} invokedynamic implementation handle {impl_owner}.{impl.get('name')}{impl.get('descriptor')} failed exact resolution ({rr['status']})", "invokedynamic": indy, "resolution": rr})
                else:
                    handle_ref = dict(impl)
                    handle_ref["opcode_name"] = METHOD_HANDLE_OPS.get(int(impl.get("reference_kind") or 0))
                    handle_ref.setdefault("caller_name", "<invokedynamic>")
                    if handle_ref.get("opcode_name"):
                        blockers.extend(_validate_invocation_mode(path, caller, handle_ref, rr, resolution_universe))
                        access_blockers, access_warnings = _validate_access_and_special(path, caller, handle_ref, rr, resolution_universe, access_effects)
                        blockers.extend(access_blockers)
                        warnings.extend(access_warnings)

    seen = set()
    unique = []
    for item in blockers:
        key = (item["id"], item.get("path"), item.get("line"), item.get("message"))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    blockers = unique
    return {
        "schema_version": 3,
        "candidate": str(candidate.resolve()),
        "runtime_java": runtime_java,
        "indexes": [x.get("input") for x in indexes],
        "candidate_index": {
            "class_count": candidate_index.get("class_count"),
            "multi_release": candidate_index.get("multi_release"),
            "nested_archives": candidate_index.get("nested_archives"),
            "duplicate_owner_count": len(candidate_index.get("duplicate_owners") or []),
        },
        "status": "FAIL" if blockers else "PASS_WITH_WARNINGS" if warnings else "PASS",
        "checked_classes": checked_classes,
        "checked_member_refs": checked_refs,
        "checked_bytecode_member_refs": checked_bytecode_refs,
        "packaged_access_rules": {
            "status": (access_effects.get("resolver") or {}).get("status"),
            "resolved": len((access_effects.get("resolver") or {}).get("resolved") or []),
            "blockers": len((access_effects.get("resolver") or {}).get("blockers") or []),
            "warnings": len((access_effects.get("resolver") or {}).get("warnings") or []),
        },
        "blockers": blockers,
        "warnings": warnings,
        "counts": {"blockers": len(blockers), "warnings": len(warnings), "ids": dict(Counter(x["id"] for x in blockers + warnings))},
        "runtime_boundary": "Static packaged proof cannot prove dynamic reflection targets, Mixin PREPARE/APPLY/injection shape, resource/data semantics, side-only initialization, networking, saves, or gameplay. Launch the exact packaged artifact afterward.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--target-index", required=True, type=Path)
    ap.add_argument("--dependency-index", action="append", default=[], type=Path)
    ap.add_argument("--prefix", action="append", default=[])
    ap.add_argument("--runtime-java", type=int, default=25)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--fail-on-blocker", action="store_true")
    args = ap.parse_args()
    indexes = [json.loads(args.target_index.read_text(encoding="utf-8"))]
    indexes.extend(json.loads(p.read_text(encoding="utf-8")) for p in args.dependency_index)
    prefixes = tuple(args.prefix) if args.prefix else DEFAULT_PREFIXES
    result = audit(args.candidate, indexes, prefixes, runtime_java=args.runtime_java)
    if args.json_out:
        write_json(args.json_out, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if args.fail_on_blocker and result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())