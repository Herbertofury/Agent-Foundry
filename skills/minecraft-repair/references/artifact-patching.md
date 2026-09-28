# Minecraft Artifact Patching and Verification

## Contents

1. Patch preflight
2. Compatibility identity preservation
3. Constant-pool repairs
4. Method-level, control-flow, and mixin repairs
5. JAR integrity
6. Repair Mark v2 visual identity
7. Verification ladder
8. Reusable artifact record

## 1. Patch preflight

Before editing a JAR:

- hash the original;
- inspect loader metadata and embedded version;
- identify signatures under `META-INF`;
- locate the exact classes containing the failing symbol;
- confirm the installed dependency exposes the intended replacement symbol;
- preserve the original as a separate artifact.

Do not edit the user's only copy in place.

## 2. Compatibility identity preservation

Treat the original mod's compatibility identity as part of the API surface. By default preserve:

- internal mod ID and advertised mod version;
- display name and loader metadata identity;
- namespaces, registry/resource IDs, serialized IDs, and config/world keys;
- network/protocol/channel identifiers;
- mixin config names and entrypoints;
- public class names, fields, methods, descriptors, interfaces, and dependency IDs/ranges when they remain valid.

A repaired filename may include a suffix for humans, but do not change the internal ID/version merely to mark the repair. Addons and dependency resolvers must continue detecting the expected original mod/version. Before delivery, extract and compare loader metadata from original and repaired JARs. Unrelated metadata should be byte-identical. If an identity change is technically required, document the migration consequences and repair downstream compatibility rather than silently changing identity.

## 3. Constant-pool repairs

A class-name/API rename can often be repaired by changing `CONSTANT_Utf8` entries when all of these are true:

- the new class is behaviorally compatible for the caller;
- constructors/methods/fields used by the caller still exist with compatible descriptors;
- generic type and inheritance assumptions still hold;
- the change does not require new control flow, fields, stack behavior, or mappings.

Use `scripts/class_utf8_patch.py` for this narrow case. It rewrites only UTF-8 constant-pool payloads and updates lengths. It can also change descriptors that contain the old owner type.

Do not use raw global byte replacement across a class file because changed string lengths can corrupt the constant pool.

## 4. Method-level, control-flow, and mixin repairs

If behavior or descriptors changed materially, rebuild from source or perform a structured bytecode patch rather than forcing a constant rename.

When editing bytecode control flow:

- treat StackMapTable/frame validity as mandatory on modern JVM class versions;
- remember that ASM `ClassWriter.COMPUTE_MAXS` computes stack/local maxima but does not compute stack-map frames;
- prefer an equivalent branch-free patch when it cleanly avoids new frame edges;
- otherwise use valid explicit frames or `COMPUTE_FRAMES` with a class hierarchy resolver appropriate to the target environment;
- verify the changed class with `javap -v`/a bytecode parser and a JVM/class verifier before packaging;
- never ship a branch/control-flow edit that has only passed ZIP integrity.

For source builds:

- pin the exact Minecraft/loader dependency versions under test;
- update imports, owners, descriptors, mixin targets, and compatibility guards;
- build with the project's own Gradle/Maven workflow;
- inspect the produced reobfuscated JAR, not only dev classes.

For mixins, verify target bytecode after all relevant loader mappings/transform assumptions, especially with cross-loader bridges.

## 5. JAR integrity

After patching:

- run `zipfile.testzip()` or equivalent;
- compare entry names/counts;
- compare decompressed hashes of unchanged entries;
- ensure no accidental resource/config metadata changes;
- compare loader metadata and verify internal mod ID/version are unchanged unless intentionally migrated;
- inspect changed class-file magic, major version, and StackMapTable/frame validity when control flow changed;
- note whether archive signatures were present and whether the chosen repair strategy accounts for them.

`jar_diff.py` reports added, removed, and content-changed entries. A narrow patch should have an explainable changed set.

## 6. Repair Mark v2 visual identity

After the gameplay repair has a verified unmarked baseline, follow `repair-mark.md` for every shippable repaired mod/compatibility artifact. Resolve the exact official CurseForge/Modrinth project artwork, apply the red double-frame/corner/check Repair Mark v2 treatment, and embed only when archive signature safety is proven. The marker-only diff must change only the resolved icon entry; gameplay classes/resources and compatibility metadata must remain byte-identical to the verified repair. If embedding is unsafe or the launcher uses external project artwork, ship/use the marked official art as a sidecar/launcher badge instead.

## 7. Verification ladder

Use the strongest available steps:

1. Archive integrity.
2. Entry-level diff.
3. Constant-pool old/new symbol scan.
4. Class parser or `javap -verbose` validation.
5. Dependency symbol existence check.
6. Original-vs-repaired mod ID/version/loader metadata parity check.
7. Bytecode frame/verifier check when control flow changed.
8. Launch exact instance.
9. Reproduce original failure path.
10. Inspect fresh log for disappearance of original signature and new fatal errors.
11. Restart/persistence check for stateful fixes.

Do not skip directly from step 1 to claiming runtime success.

## 8. Reusable artifact record

Store:

- original filename and SHA-256
- patched filename and SHA-256
- changed entries
- original and repaired internal mod ID/version plus metadata parity result
- exact symbol/member substitutions
- dependency versions against which the patch was verified
- static verification results
- runtime verification result
- user feedback
- Repair Mark v2 official-art source/project IDs, unmarked/marked artwork hashes, integration mode, and marker-only diff result when applicable

This makes a future similar crash matchable without blindly reusing a stale binary.
