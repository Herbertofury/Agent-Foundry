# Minecraft Repair Diagnostic Playbook

## Contents

1. Baseline identity
2. Startup failures
3. Binary/API incompatibility
4. Mixin failures
5. Registry and data failures
6. Rendering and native failures
7. Network failures
8. World/save failures
9. Performance failures
10. Evidence discipline

## 1. Baseline identity

Capture before changing anything:

- Minecraft version
- loader family and exact loader version
- Java runtime/vendor/major version
- client or dedicated server
- OS and architecture
- launcher's game directory
- exact mod filenames and embedded mod versions
- last known working state if available
- whether the failure occurs at bootstrap, mod construction, client setup, world load, connection, or gameplay

Do not infer compatibility from filenames alone. Inspect embedded metadata when a JAR is available.

## 2. Startup failures

High-value signatures:

- `Missing mandatory dependencies`
- `DuplicateModsFoundException`
- `ModLoadingException`
- `UnsupportedClassVersionError`
- `ClassNotFoundException`
- `NoClassDefFoundError`
- `NoSuchMethodError`
- `NoSuchFieldError`
- `VerifyError`
- `ExceptionInInitializerError`
- `MixinApplyError`
- `MixinTransformerError`
- `InjectionError`
- `InvalidInjectionException`

Trace nested `Caused by:` chains to the deepest meaningful cause, then walk back up to the mod/event that triggered it.

## 3. Binary/API incompatibility

### Missing class

A missing class can mean:

- a required dependency is absent;
- the wrong loader build is installed;
- the dependency changed package/class name;
- the addon targets an older/newer dependency API;
- a class is client-only but referenced on server;
- a compatibility module was built for a different branch.

Prove which case applies by inspecting the failing addon's class reference and the installed dependency's actual classes/source.

### Missing method/field

For `NoSuchMethodError` and `NoSuchFieldError`, capture the full owner, member name, and descriptor. Compare the caller's constant pool against the installed callee. A same-named method with a changed descriptor is still binary-incompatible.

### Class verification

`VerifyError`, stack-map errors, or `Insufficient maximum stack size` may come from a transformer producing invalid bytecode. Identify which transformer last modified the class before blaming the JVM or memory settings.

## 4. Mixin failures

Record:

- mixin config and class
- owning mod
- target class
- target member descriptor
- injection type and `@At`
- required/expected injection count
- priority
- competing mixin/transformer if shown

Common root causes:

- target bytecode changed between versions;
- mappings or descriptors changed;
- another mod already redirected/overwrote the same instruction;
- optional compatibility mixin applied when its assumed dependency variant is absent;
- loader bridge such as Connector changed the transformed class surface.

Fix the compatibility assumption, not merely the warning text.

## 5. Registry and data failures

Differentiate:

- duplicate registry keys;
- missing registry entries from removed/renamed mods;
- invalid datapack JSON/tag/recipe/loot data;
- codec/datafixer failures;
- world registry remap failures.

For world-specific failures, reproduce with a new temporary world when possible. If new worlds work but one save fails, prioritize save data/registry history over global mod code.

## 6. Rendering and native failures

Capture GPU/vendor/driver, OpenGL version, renderer stack, shaders, optimization mods, native library path, and the first render-thread fatal error.

Warnings that Embeddium/Sodium/Oculus/Iris internals are modified can be useful risk signals but are not automatically the crash cause. Follow the fatal render-thread chain.

For shader/render mixins, compare the exact renderer class and vertex format expected by the addon with the installed renderer version.

## 7. Network failures

Separate:

- authentication/session failure;
- protocol/version mismatch;
- client/server mod-list mismatch;
- custom packet decode/encode failure;
- registry sync failure;
- timeout/performance symptom.

Compare client and server mod IDs/versions plus loader/network protocol before changing gameplay mods.

## 8. World/save failures

Always preserve a recoverable copy. Inspect:

- `level.dat` and `level.dat_old`
- `region/*.mca`
- dimension region data
- `playerdata`
- `data`
- server configs/datapacks
- mod-specific world data

Repair the smallest corrupt scope. Avoid broad chunk deletion unless coordinates and corruption are proven.

## 9. Performance failures

Classify CPU, GPU, memory/GC, disk/chunk generation, network, entity AI, or renderer bottlenecks. Use profiler evidence rather than mod-list folklore.

For startup slowness, compare stage timestamps. For runtime lag, use tick time and profiler stacks. For FPS, use frame-time and renderer/GPU evidence.

## 10. Evidence discipline

Strong evidence:

- exact fatal stack chain
- class/method/field descriptor mismatch
- source or bytecode comparison between expected and installed API
- minimal reproducer
- before/after runtime log
- verified artifact diff/hash

Weak evidence:

- a warning merely appears before the crash
- a mod is old or unpopular
- a generic internet report with different versions
- launcher labels without embedded metadata
- removing half the mods happens to make the crash disappear
