# Future Feature Bridge QA and production-linkage gates

## Purpose

Use this gate set for Minecraft mods that bridge a future/backported feature into an existing system, dynamically prefer an external provider when installed, fall back to an embedded implementation, or touch Forge APIs whose mapped-development surface can differ from production runtime descriptors.

These rules were generalized from a Forge 1.20.1 / Forge 47.4.23 Future Feature Bridge release. The preserved final-candidate checkpoint identifies the candidate only by the SHA-256 prefix `b20acda1e2d…`; never expand or substitute a full digest unless the exact artifact bytes are available and re-hashed.

## Non-negotiable production symbolic-linkage gate

A successful compile, ForgeGradle mapped-dev run, remap step, or ordinary bytecode scan does **not** prove that every method invocation will link in the shipped production runtime.

A proven failure mode was a Creative inventory crash caused by calling `BuildCreativeModeTabContentsEvent.accept(ItemLike)`: the mapped development environment exposed a convenience overload, but that exact method descriptor was absent from the production Forge 47.4.23 class. The result was a production `NoSuchMethodError` that compilation and the earlier remap checks missed.

Before release:

1. Resolve every changed/high-risk invocation against the exact production game/loader JARs, not only mapped development stubs.
2. Validate symbolic references as `(owner, name, descriptor)` triples after remap/packaging.
3. Make the validator fail on any unresolved method/field/class reference that the changed path can execute.
4. Keep a negative regression fixture for any linkage bug found in native QA. The previously broken candidate/path should fail offline under the validator before Minecraft launches.
5. Still exercise the real production client path. Static linkage validation complements native QA; it does not replace it.

For Creative/registry work, open the Creative inventory and visit the changed tab/content path on the exact final JAR. Treat a client-only `NoSuchMethodError`, `NoClassDefFoundError`, or linkage-related crash as a release blocker even if server QA is green.

## Exact-candidate discipline

Runtime evidence belongs to one immutable artifact identity.

1. Build the candidate twice from the frozen source/toolchain when reproducibility is expected.
2. Hash both builds and require byte-for-byte identity before using the candidate for release QA.
3. Record the full SHA-256 and size when bytes are available.
4. Any code/resource/build-script change invalidates the earlier runtime evidence. Build a new candidate, record a new digest, and rerun every affected lane.
5. After the complete QA matrix, re-hash the release artifact and verify it is byte-identical to the tested candidate.

Do not call a hash prefix an exact digest. A checkpoint such as `b20acda1e2d…` is useful continuity evidence but is not sufficient for cryptographic artifact verification.

## Optional-provider runtime matrix

When the bridge can use an embedded provider or an external mod/provider, verify all applicable lanes against the exact candidate:

| Lane | Required proof |
| --- | --- |
| Embedded client/integrated server | Resolver selects the embedded provider; changed gameplay behavior works; client-only UI/registry paths open safely. |
| Embedded dedicated server | Real `Done (...)!` readiness, changed/common systems active, no bridge-owned load/linkage failure, clean shutdown. |
| External-provider client | Resolver selects the external provider; the real external item/entity is consumed/used; bridge reaction happens exactly once. |
| Same-world provider removal | Remove the external provider and its provider-only dependencies, restart the same save, tolerate only expected missing-registry warnings, and prove resolver fallback to embedded mode with no stale provider lock-in. |
| External-provider dedicated server | Launch with the real provider and required dependencies, reach readiness, prove both base systems activate, then cleanly save/stop. |
| Cleanup / prepare-uninstall | Exercise the exact cleanup code path on the final binary and assert every targeted live entity/item/inventory location is removed. |

A provider-present launch and a provider-absent launch in two unrelated fresh worlds do not prove fallback durability. The same saved world restart is the important stale-binding test.

## Resolver assertions

Log a machine-readable or unambiguous resolver decision at runtime. The verified bridge pattern included results shaped like:

```text
minecraft:wind_charge -> ragdoll_reactions_future [EMBEDDED]
justtrialspawners [EXTERNAL] / PROJECTILE_IMPACT_OR_DISCARD
```

Treat provider identity and trigger strategy as separate assertions. Do not infer one from the other.

## Exactly-once semantics

An external provider bridge is especially vulnerable to duplicate reactions from overlapping hooks (spawn, tick, impact, discard, event bus, mixin, capability, etc.). Prove event cardinality, not merely visible success.

For one controlled external projectile/action:

1. Record pre-action inventory/count state.
2. Trigger one real provider action in Survival or another mode that proves physical consumption when relevant.
3. Assert the item/projectile count changed exactly as expected.
4. Assert exactly one bridge reaction/trigger.
5. Assert exactly one downstream result (for example one ragdoll), including topology/count invariants when they matter.
6. Search fresh logs for duplicate trigger IDs, duplicate entity creation, bridge-owned exceptions, or retries.

The source release that produced these rules used a one-action gate where the provider item count went `2 -> 1`, one Reactions trigger fired, and one ragdoll with `7` sublevels / `6` joints was produced. Keep such counts as project-specific regression fixtures, not as universal Minecraft constants.

## Gameplay state assertions

Prefer authoritative server/integrated-server state over visuals alone. A proven high-signal bridge fixture used two trapdoors that were both confirmed closed before the burst, then asserted:

- oak trapdoor: `open=true` after the action;
- iron trapdoor: `open=false` after the same action.

If the actor falls, drifts, unloads the chunk, or moves out of range, fix the QA fixture (platform, fixed coordinates, NoAI/teleport/scheduled action as appropriate) instead of weakening the assertion or blaming the mod.

## Cleanup / prepare-uninstall gate

Cleanup commands are destructive compatibility paths and must be tested on the exact release binary. Seed every storage/location category the cleanup claims to cover, then assert exact removal counts. Include, as applicable:

- loaded fallback projectile entities;
- dropped bridge/provider items;
- player inventory/offhand/armor if in scope;
- ender chest and other explicitly supported inventories;
- persistent bridge state/capabilities/attachments;
- scheduled tasks or spawned helper entities.

The verified bridge checkpoint removed `3` loaded fallback projectiles, `1` dropped charge, and `4` player/ender-chest charges in one run. Preserve project-specific counts in release evidence so a no-op cleanup cannot false-pass.

## Provider-removal and missing-registry warnings

Removing a previously installed provider from an existing save can produce normal Forge missing-registry warnings for provider-owned content. Do not hide them.

Classify the lane green only when:

1. warnings belong to the removed provider/dependencies, not the bridge;
2. Forge continues loading the same world safely;
3. the player/server reaches usable readiness;
4. the original/base systems activate;
5. resolver selects the embedded fallback;
6. there are zero bridge-owned linkage, mod-loading, registry, or runtime failures.

## Dedicated-server warning ownership

Client-class mixin warnings can pre-exist in a base mod stack on dedicated server. Preserve them in the log and classify ownership instead of suppressing them.

Use three buckets:

- **bridge-owned**: introduced by or executing through the changed bridge; must be fixed for release;
- **upstream/base-owned known warning**: reproduced without the bridge and unaffected by the change; document but do not relabel as bridge failure;
- **unknown**: investigate before release.

A green server lane still requires a real readiness marker and a clean shutdown sequence such as `Stopping server -> Saving worlds -> All dimensions are saved`.

## Release evidence template

Record at least:

```text
Minecraft / loader / Java:
Source revision:
Candidate filename:
Candidate SHA-256:
Candidate size:
Reproducible build #1 SHA-256:
Reproducible build #2 SHA-256:
Production-linkage validator:
Embedded client:
Embedded dedicated server:
External-provider client:
Same-world provider removal:
External-provider dedicated server:
Cleanup / prepare-uninstall:
Warnings (bridge-owned / upstream / unknown):
Final post-QA SHA-256:
Drive publication identity:
GitHub publication identity:
```

Never upgrade checkpoint evidence into stronger claims than the bytes/logs support. If a resumed chat has only a hash prefix or textual checkpoint, preserve it as continuity metadata and require the actual artifact before claiming cryptographic re-verification.

## Vanilla dependency-closure prerequisite

When the optional provider is supplying vanilla content from another Minecraft version, run the Vanilla Feature Atlas gate before this bridge matrix. Read `vanilla-feature-atlas.md` and classify the exact dependency as target-vanilla, proven external provider, or embedded dependency-closed fallback.

Provider presence is not proof of per-feature ownership. Do not suppress an embedded fallback until the exact provider lane is proven to own the requested registry/behavior/resource family. Conversely, when provider ownership is proven, do not duplicate-register or double-trigger the same vanilla feature.

For sounds, compare SoundEvent registration, `sounds.json` definition, and external OGG objects independently. A real registered event with no definition is a valid historical state and must not be “fixed” by inventing a resource merely to silence a warning.
