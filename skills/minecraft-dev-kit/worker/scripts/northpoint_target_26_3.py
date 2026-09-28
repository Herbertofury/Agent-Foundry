#!/usr/bin/env python3
"""Stable 26.3 materializer with separately pinned, regression-proven API rules.

The preserved core retains every v7 migration byte-for-byte. This entry point owns
new runtime-backed rules and orchestration; its pinned core digest also makes
Northpoint's existing engine fingerprint invalidate when the core is upgraded.
"""
from __future__ import annotations
import hashlib
import pathlib

_CORE_SHA256 = "72e17acba62a5cc30854d7dbd6c1676d8ef7865c8064d6149dce44e5cd58e9bd"
_core_path = pathlib.Path(__file__).with_name("northpoint_target_26_3_core.py")
if hashlib.sha256(_core_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != _CORE_SHA256:
    raise RuntimeError("26.3 core bytes do not match the pinned engine; restore the complete Dev Kit")
import northpoint_target_26_3_core as _core
from northpoint_target_26_3_core import *

_RUNTIME_RULES_SHA256 = "b2e330528041a3b4de5aeaf0a27b82e41efba62d4a77a834598640a23094e86d"
_runtime_path = pathlib.Path(__file__).with_name("northpoint_runtime_mixin_rules.py")
if hashlib.sha256(_runtime_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != _RUNTIME_RULES_SHA256:
    raise RuntimeError("runtime migration rules do not match the pinned engine")
from northpoint_runtime_mixin_rules import rewrite_runtime_mixins

_MOUSE_BRIDGE_SHA256 = "50c64f4d6af59b684c387c7eb76b6d1ae2600fbc39c95a970a89f4643e426d01"
_mouse_path = pathlib.Path(__file__).with_name("northpoint_mouse_invoker_rules.py")
if hashlib.sha256(_mouse_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != _MOUSE_BRIDGE_SHA256:
    raise RuntimeError("mouse bridge does not match the pinned engine")
from northpoint_mouse_invoker_rules import rewrite_mouse_invokers

_SHADER_RULES_SHA256 = "568b7214287bf7e2c7be5d22dfd8ae1bfd0cdc4769427a79d3d11fe04ae87960"
_shader_path = pathlib.Path(__file__).with_name("northpoint_shader_rules.py")
if hashlib.sha256(_shader_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != _SHADER_RULES_SHA256:
    raise RuntimeError("shader rules do not match the pinned engine")
from northpoint_shader_rules import rewrite_shader_interfaces

_CHUNK_RULES_SHA256 = "651d05ad93365cbf898ad2353f40123793bb749fef53a8be91f4af24059ce47e"
_chunk_path = pathlib.Path(__file__).with_name("northpoint_chunk_packet_rules.py")
if hashlib.sha256(_chunk_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != _CHUNK_RULES_SHA256:
    raise RuntimeError("chunk packet rules do not match the pinned engine")
from northpoint_chunk_packet_rules import rewrite_chunk_packet_mixins


def __getattr__(name):
    return getattr(_core, name)


def tree_digest(root: pathlib.Path) -> str:
    # Source-owned large files must participate in immutability and invalidation.
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(root.resolve()):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIGEST_DIRS)
        for name in sorted(files):
            path = pathlib.Path(base) / name
            relative = path.relative_to(root.resolve()).as_posix()
            digest.update(relative.encode("utf-8")); digest.update(b"\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def _annotation_end(text: str, start: int) -> int:
    depth, quote, escaped = 0, None, False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == quote: quote = None
        elif char in "\"'": quote = char
        elif char == "(": depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0: return index + 1
    raise ConversionBlock("unterminated Mixin annotation")


def rewrite_network_tick_mixins(output: pathlib.Path) -> list[dict[str, Any]]:
    """26.3 moved client packet emission from LocalPlayer.tick to sendChanges.

    Authority: official 26.3 client SHA256 4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d.
    Preserve exact invocation descriptor, ordinal, shift, cancellation and body.
    Local-capture/sliced/multi-target cases remain explicit semantic work.
    """
    rows = []
    descriptor = "Lnet/minecraft/client/multiplayer/ClientPacketListener;send(Lnet/minecraft/network/protocol/Packet;)V"
    for path in output.rglob("*.java"):
        text = path.read_text(encoding="utf-8")
        imported = re.search(r"import\s+net\.minecraft\.client\.player\.LocalPlayer\s*;", text)
        owner = r"(?:net\.minecraft\.client\.player\.)?LocalPlayer" if imported else r"net\.minecraft\.client\.player\.LocalPlayer"
        owners = list(re.finditer(r"@(?:org\.spongepowered\.asm\.mixin\.)?Mixin\s*\(\s*(?:value\s*=\s*)?" + owner + r"\.class\s*\)", text))
        regions = []
        for match in owners:
            declaration = re.search(r"\bclass\s+\w+[^{}]*\{", text[match.end():])
            if declaration:
                start = match.end() + declaration.end() - 1
                end = _core._find_matching_java_brace(text, start)
                if end is not None: regions.append((start, end))
        if not regions: continue
        edits = []
        for match in re.finditer(r"@(?:org\.spongepowered\.asm\.mixin\.injection\.)?Inject\s*\(", text):
            if not any(start < match.start() < end for start,end in regions): continue
            end = _annotation_end(text, match.end()-1)
            annotation = text[match.start():end]
            method = re.search(r'\bmethod\s*=\s*"tick(?:\(\)V)?"', annotation)
            if not method or not re.search(r'\btarget\s*=\s*"' + re.escape(descriptor) + '"', annotation):
                continue
            if not re.search(r'\bvalue\s*=\s*"INVOKE"', annotation): continue
            handler = re.match(r"\s*(?:private|protected|public)\s+void\s+\w+\s*\(\s*(?:org\.spongepowered\.asm\.mixin\.injection\.callback\.)?CallbackInfo\s+\w+\s*\)", text[end:])
            if not handler or re.search(r"\b(?:locals|slice)\s*=", annotation):
                raise ConversionBlock(f"network tick Mixin needs local/slice-aware migration: {path}")
            value = annotation[method.start():method.end()].replace('"tick', '"sendChanges')
            replacement = annotation[:method.start()] + value + annotation[method.end():]
            edits.append((match.start(), end, replacement))
        for start, end, replacement in reversed(edits):
            text = text[:start] + replacement + text[end:]
        if edits:
            path.write_text(text, encoding="utf-8")
            rows.append({"rule":"minecraft-26.3-localplayer-network-tick-to-send-changes", "path":path.relative_to(output).as_posix(), "count":len(edits)})
    return rows


def rewrite_minecraft_26_3_java(output: pathlib.Path) -> list[dict[str, Any]]:
    return _core.rewrite_minecraft_26_3_java(output) + rewrite_network_tick_mixins(output) + rewrite_runtime_mixins(output) + rewrite_mouse_invokers(output) + rewrite_shader_interfaces(output) + rewrite_chunk_packet_mixins(output)


def materialize_port(source: pathlib.Path, output: pathlib.Path, loader: str, *, pipeline_script: pathlib.Path | None = None) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ConversionBlock("source and output must be disjoint; original files were preserved")
    if not source.is_dir():
        raise ConversionBlock(f"source project does not exist: {source}")
    if loader == "fabric":
        identity = detect_fabric_identity(source)
    elif loader == "neoforge":
        identity = detect_neoforge_identity(source)
    else:
        raise ConversionBlock(f"automatic inferred-source 26.3 materialization is not implemented for loader {loader!r}")
    if identity["minecraft"] == TARGET_MINECRAFT:
        raise ConversionBlock("source already targets 26.3; conversion materialization is unnecessary")
    if output.exists():
        shutil.rmtree(output)
    source_before = tree_digest(source)
    run_pipeline(source, output, loader, identity, (pipeline_script or DEFAULT_PIPELINE).resolve())
    copied_sources = replace_source_roots(source, output)
    copied_resources = carry_resources(source, output, loader)
    wrapper_files = carry_wrapper(source, output)
    preserved_gradle_properties = merge_gradle_properties(source, output)
    preserved_build_files = carry_build_support_files(source, output)
    preserved_gradle_blocks = preserve_gradle_build_fragments(source, output, loader)
    applied: list[dict[str, Any]] = []
    if loader == "fabric" and preserved_gradle_blocks.get("loom_access_widener"):
        applied.append({"rule": "fabric-preserve-access-widener-path", "path": "northpoint-preserved.gradle", "count": int(preserved_gradle_blocks["loom_access_widener"])})
    if loader == "fabric":
        for rule in migrate_fabric_metadata(source, output):
            applied.append({"rule": rule, "path": "src/main/resources/fabric.mod.json"})
        applied.extend(adapt_fabric_source_layout(source, output))
        applied.extend(normalize_empty_fabric_access_wideners(output))
    elif loader == "neoforge":
        for rule in migrate_neoforge_metadata(source, output):
            applied.append({"rule": rule, "path": "src/main/templates/META-INF/neoforge.mods.toml"})
        applied.extend(rewrite_neoforge_property_factories(output))
    applied.extend(rewrite_minecraft_26_3_java(output))
    applied.extend(rewrite_resource_location_java(output))
    applied.extend(rewrite_mixin_java_level(output))
    resolved_semantic_ids = reconcile_semantic_ledger(output, applied)
    source_after = tree_digest(source)
    if source_after != source_before:
        raise ConversionBlock("source tree changed during materialization; conversion aborted to preserve source authority")
    manifest = {
        "schema_version": 1,
        "source": {"path": str(source), "sha256": source_before, "minecraft": identity.get("minecraft") or None, "loader": loader, "mod_id": identity["mod_id"]},
        "target": {"path": str(output), "minecraft": TARGET_MINECRAFT, "loader": loader, "java": TARGET_JAVA},
        "copied_source_roots": copied_sources,
        "copied_resource_roots": copied_resources,
        "wrapper_files": wrapper_files,
        "preserved_gradle_properties": preserved_gradle_properties,
        "preserved_build_files": preserved_build_files,
        "preserved_gradle_blocks": preserved_gradle_blocks,
        "applied_rewrites": applied,
        "applied_rule_ids": sorted({str(row.get("rule")) for row in applied}),
        "resolved_semantic_ids": resolved_semantic_ids,
        "unresolved_semantics_evidence": "devkit-evidence/semantic-port-plan.json",
        "target_sha256": tree_digest(output),
        "source_unchanged": True,
    }
    write_json(output / "devkit-evidence" / "northpoint-conversion.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--loader", choices=["fabric", "neoforge"], required=True)
    parser.add_argument("--pipeline", type=pathlib.Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        manifest = materialize_port(args.source, args.output, args.loader, pipeline_script=args.pipeline)
    except ConversionBlock as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 4
    print(json.dumps({"status": "PASS", "manifest": manifest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
