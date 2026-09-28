# REAL VERIFICATION, EVIDENCE, AND DELIVERABLES

## Proof standards

Use status words only when their proof standard is met:

- **Installed:** present on the target machine, version confirmed, and launches successfully.
- **Configured:** the intended process loaded and used the active configuration.
- **Integrated:** the intended client discovers it in a fresh session and completes a real call through it.
- **Fixed:** the original reproducer passes because the root cause was corrected.
- **Working:** the exact requested workflow succeeds in the real runtime without task-related errors.
- **Verified:** relevant real-runtime checks were executed in this run.
- **Complete:** every acceptance item and completion gate in this file is satisfied.

The following are intermediate evidence only and never prove completion alone:

- copied files
- edited configuration
- installed packages
- compilation
- lint or type-check
- health endpoints
- protocol handshakes
- exposed tools
- mocked tests
- code review
- "it should work"

Never launder intermediate progress into a completion claim.

## Evidence ledger

Maintain a task-local mapping for every explicit acceptance item:

**requirement -> implementation location -> verification action -> observed result**

- Update the ledger as work progresses.
- Evidence must come from the current run or be independently revalidated in the current run.
- A requirement without direct evidence remains incomplete.
- For optimization work, record baseline and final metrics when they are meaningful. When scalar metrics are not useful, verify improvement through direct runtime, correctness, reliability, UX, integration, or quality evidence. Qualitative maximum-effort language is never a numeric proof obligation.
- A subagent summary, edited file, passing build, health endpoint, or plausible explanation is not proof of user-visible behavior.

## Real verification

Run all applicable repository-provided checks: format, lint, type-check, unit, integration, build, package, migration, end-to-end, installation, and deployment checks.

Then prove the actual behavior:

- Start the real services and runtimes.
- Launch or load the actual application, extension, executable, plugin, or integration.
- Exercise the exact edited feature through the real user or system flow.
- For integrations, verify both ends and confirm the intended client discovers and calls the provider after a fresh restart.
- For browser and UI work, interact with the affected flow and inspect relevant console, network, background/service-worker, and application logs.
- For external-site or protocol work, use real representative targets when access exists. Mocks may supplement proof but may never be the only proof.
- For bug fixes, run the original reproducer, add regression coverage when practical, and inspect directly related paths for the same failure pattern.
- Review the final diff and artifacts for accidental changes, incomplete wiring, duplicate logic, exposed secrets, encoding damage, and unintended generated or vendor edits.
- Prove the runtime is using the new result, not a stale binary, cached bundle, old extension, wrong profile, duplicate install, or previous output. Confirm the loaded path plus a version, hash, timestamp, or unmistakable behavior change.
- For stateful behavior, restart the real client and verify configuration, data, enabled state, and integrations persist and still work after restart.
- For authentication-dependent behavior, use available authorized user state or the project's approved authenticated test profile. Do not test anonymously, hit a login wall, and misreport the feature as unsupported or broken.

## Session build availability and efficient verification

For every project chat, keep a usable build available at closeout. If implementation state changed, the build must be regenerated from the latest canonical source; if the chat was research/planning-only, the latest verified build may be reused.

Verification is **risk-tiered and convergence-based**, not ceremonial:

- During iteration, prioritize the exact reproducer, changed-path tests, and fast targeted regressions.
- At convergence, run the canonical build/package, a fresh-copy/install critical-path smoke test, affected regressions, and any project-mandated full suite once.
- Do not rerun unchanged broad suites or regenerate status reports after every micro-edit unless new changes invalidate prior evidence.
- Artifact creation precedes status/HANDOFF/catalog polishing. A status file can record proof; it can never substitute for the runnable artifact.
- For implementation-changing work, machine-readable closeout proof must name the runnable artifact/build ID and its fresh-copy/install smoke-test result.

## Deliverable integrity

When the user requests a build, archive, installer, app, extension, plugin, or complete project:

- produce the full runnable deliverable in the requested format and location, including required assets, manifests, dependencies, and generated outputs
- do not substitute a patch, diff, source fragment, instructions, or partial folder unless explicitly requested
- package from the verified canonical source, extract or install into a fresh location, launch that fresh copy, and smoke-test the requested workflow
- ensure the handoff file is accessible, correctly named, non-empty, and linked or identified precisely in the final response

A passing build with an untested runtime is incomplete. A healthy provider with an untested client is incomplete. A rendered UI that does not perform the requested action is incomplete.

## Durable closeout proof

For substantial project or build work, completion evidence must also prove that:

- the verified source state is checkpointed durably rather than existing only in temporary storage;
- the complete runnable artifact was produced and revalidated from a fresh extraction or installation;
- every material saved artifact/checkpoint created or changed in the run was published to connected Google Drive and verified by trusted metadata/digest or complete reread/redownload when required; additional requested publication targets were verified too;
- the final response does not substitute an unfinished-status report while realistically solvable defects remain.

