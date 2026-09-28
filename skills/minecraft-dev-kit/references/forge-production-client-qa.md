# Forge production-client and remap QA

Use this reference for Forge ports/backports where mapped development names, production SRG names, reflection, Mixin member targets, or packaged-client startup can differ from `runClient` / `forgeclientuserdev`.

## Production client is an independent release gate

A mapped ForgeGradle userdev client is useful but is not authoritative for the shipped namespace. For production-name defects, launch the packaged JARs through the real `forgeclient` target using the exact Forge/Minecraft profile and production artifacts.

Require all of the following when applicable:

1. Exact Java, Minecraft, Forge, MCP/mapping, mod, and dependency hashes are recorded.
2. A launcher-style Maven library tree contains the exact client SRG, client-extra, Forge patched-client, Forge universal, FML language-provider, BootstrapLauncher, and loader libraries expected by `LibraryFinder`.
3. Linux headless runs extract Linux LWJGL native classifier JARs and set both `org.lwjgl.librarypath` and `java.library.path`.
4. The official asset index/object cache is complete when resource/sound completeness is part of the gate. Verify object count and hashes before launch.
5. Long client runs are detached and polled by PID plus authoritative log milestones. Never interpret the orchestration wrapper timing out as Minecraft stalling.
6. Package the exact final JARs into `run/mods`; do not let source-set registration or a development mod path silently substitute project classes.
7. Reach a real integrated world and exercise changed client-only entry points such as Creative inventory, renderer construction, menus, key handling, and model bake.

### ForgeGradle/offline harness traps

- `DownloadMCMeta` can still attempt piston-meta access even under an offline build. Stage exact cached manifest/version outputs first; disable only the network task that is already satisfied, not unrelated build gates.
- Pin the Java toolchain explicitly when auto-detection is unreliable, and disable auto-download for truly offline QA.
- If a required build plugin/library such as `srgutils` is absent from the cache, recover the exact hashed artifact into a local Maven repository rather than weakening the build.
- A source-less userdev harness can lose expected output directories through `NO-SOURCE`; include a harmless non-mod anchor source/resource when the harness requires a materialized source set.

## Direct Mixin target-name audit

Ordinary owner-based bytecode remapping cannot infer every Mixin target member. Audit direct names in:

- `@Shadow`
- `@Accessor`
- `@Invoker`
- string-based Mixin selectors and member references

Resolve each against the actual production target owner and descriptor. A Mixin that works in mapped userdev can fail immediately in packaged Forge when a field/method name remains mapped instead of SRG.

Keep a production-client negative regression whenever a real failure is found so the stale form is demonstrably rejected.

## Reflection strings are outside bytecode remapping

Calls such as `getDeclaredField`, `getDeclaredMethod`, `Class.forName`, method-handle lookups, and string-built member names are not repaired by an ordinary class remapper.

For cross-namespace code:

1. Inventory all reflection/member-name strings on changed paths.
2. Prefer stable public APIs where possible.
3. When reflection is necessary, resolve mapped + production aliases deliberately (or resolve from the mapping table at build time).
4. Exercise the reflective path in the real production client.

A successful remap with zero stale bytecode member references is not enough if reflection literals still name mapped-only members.

## `invokedynamic` / LambdaMetafactory SAM remapping

Do not remap lambda call-site names by method name alone or by a "unique method on interface" heuristic.

For a `LambdaMetafactory` site:

1. Read the bootstrap SAM method type (bootstrap argument 0).
2. Derive the functional-interface owner from the invokedynamic call-site return type.
3. Resolve the SAM as `(owner, name, SAM descriptor)` against the production mapping.
4. Rewrite only when that exact tuple maps.
5. Include invokedynamic SAM references in production symbolic-linkage validation.

This catches failures where a packaged client throws `AbstractMethodError` because the lambda implements the mapped SAM name while production calls its SRG name.

## Resource-pack completeness for packaged mods

A mod JAR that contains valid assets can still load them incorrectly if pack metadata/resources are incomplete.

Before release, scan the real production client for task-owned:

- missing `pack.mcmeta` warnings;
- missing blockstate/model/item-model files;
- missing sound events/resources;
- model-bake exceptions;
- namespace-specific missing-resource messages.

For intentionally invisible blocks, provide a valid zero-geometry model/blockstate when the model bakery expects one; do not add a visible placeholder merely to silence the warning.

## Same-world optional-provider matrix

For optional external providers, prove three distinct modes on the exact final bridge bytes:

1. **Embedded only**: world loads, embedded provider resolves, gameplay path works.
2. **External installed**: exact provider/dependencies load, resolver selects external, one real item/projectile action produces the intended exactly-once semantic reaction.
3. **External removed from the same save**: expected missing-provider registry/datapack notices are classified, the world still loads, and resolver falls back to embedded without a bridge-owned crash.

When a cleanup/uninstall command exists, seed inventory + ender/dropped/projectile state and assert exact removal counts in server logs rather than trusting a UI-only result.
