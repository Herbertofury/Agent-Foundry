# Update and Synchronization Standard

## Objective

Keep the companion app aligned with canonical source artifacts without creating duplicate current files or rebuilding unchanged data.

## Build metadata

Every release/snapshot should embed a machine-readable manifest containing:

- app/catalog title;
- generator standard version;
- build timestamp;
- source IDs/URLs;
- source revision IDs and/or hashes;
- normalized catalog hash;
- record count;
- media count by role;
- category/collection/scour counts when relevant;
- output SHA-256 and size after build.

## Refresh flow

1. Resolve the same stable canonical source IDs.
2. Read provider revision metadata or export current raw bytes.
3. Compare with the previous build manifest.
4. If unchanged, do nothing.
5. If changed, extract only affected sources/slices when safe.
6. Re-normalize and validate the whole resulting catalog.
7. Rebuild the portable HTML and desktop data/app as required.
8. Run full changed-path plus release acceptance QA.
9. Replace stable current Drive artifacts in place when supported.
10. Preserve a superseded build in History only when there is a meaningful prior release to retain.
11. Update repository source/checkpoint additively without reverting unrelated work.
12. Verify remote bytes/size/hash before declaring sync complete.

## Local source watching

For local project folders, optionally provide a developer/source mode that watches canonical source files and refreshes the normalized dataset. Do not make the packaged consumer app depend on Python or a development watcher unless the runtime explicitly bundles it.

## Cloud source access

Do not publish a private Google Sheet or Doc merely to make the app auto-refresh.

Preferred approaches:

- connected Drive/OAuth during build/update automation;
- a user-authorized app OAuth integration when live in-app cloud sync is explicitly desired;
- stable offline snapshot plus manual `Refresh sources` developer command.

Never embed OAuth access tokens, cookies, or credentials into HTML, source ZIPs, repositories, or build metadata.

## Automation behavior

When the user explicitly requests ongoing upkeep and task automation is available:

- use a condition watch;
- compare source revision/hash first;
- stay silent when nothing changed;
- rebuild only on real change;
- notify only after successful rebuild, QA, persistence, and verification.
