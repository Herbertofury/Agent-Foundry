# Active Learned Pitfalls

## P-001 — Premature completion after superficial checks

- **Scope:** universal
- **Trigger:** A task has code edits, configuration changes, a passing build, lint, mocks, health checks, or logs but the exact user flow has not run.
- **Failure:** The agent reports success before the real runtime behavior is proven.
- **Required behavior:** Continue through the actual client, runtime, backend, persistence, and exact user flow; keep a requirement-to-evidence ledger.
- **Verification:** Exercise the requested path in the current production-equivalent build and record the observed result.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-002 — Missing tooling treated as a final blocker

- **Scope:** universal
- **Trigger:** A required tool, runtime, service, plugin, dependency, browser capability, or process is absent or stopped.
- **Failure:** The agent routes around the missing capability or gives up while a realistic recovery path exists.
- **Required behavior:** Diagnose, install, repair, configure, start, reconnect, build, or use a fully capable supported compatibility path before claiming a blocker.
- **Verification:** Use the recovered capability in the intended end-to-end workflow.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-003 — Rendered controls mistaken for working features

- **Scope:** user-facing software
- **Trigger:** A control exists visually or has a handler, toast, modal, log, mock result, or hardcoded success path.
- **Failure:** The interface promises functionality that is dead, fake, disconnected, or only partially wired.
- **Required behavior:** Connect every affected control through validation, real domain logic, backend or storage, observable result, truthful errors, and persistence where relevant.
- **Verification:** Inventory and click-test every in-scope control in the real build, including success and failure paths.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-004 — Generic destination substituted for exact contextual action

- **Scope:** navigation and contextual actions
- **Trigger:** An action promises to open, show, guide, continue, locate, download, or navigate to a specific current item or step.
- **Failure:** The action opens a generic root, homepage, search screen, empty workspace, or unrelated destination and leaves the user to finish manually.
- **Required behavior:** Resolve and preserve the exact entity, route, selection, coordinates, tab, filters, version, and authorization state promised by the control.
- **Verification:** Start from each relevant context and confirm the final visible state exactly matches the promised destination.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-005 — Cosmetic theater substituted for evolution

- **Scope:** product improvement
- **Trigger:** The request uses broad outcome language such as evolve, upgrade, magical, smarter, seamless, or next-generation.
- **Failure:** The agent renames things, adds slogans, decorations, wrappers, novelty UI, or documentation without meaningful capability improvement.
- **Required behavior:** Translate the outcome into measurable gains in capability, usability, speed, reliability, intelligence, integration, or polish, then prove them.
- **Verification:** Show before-and-after evidence in the affected workflow; renamed files or added UI alone do not count.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-006 — Project example copied into universal policy

- **Scope:** instruction authoring
- **Trigger:** The user provides a product-specific label, screenshot, route, quest, file, or repository as an example of a broader failure.
- **Failure:** The universal AGENTS contract becomes contaminated with one-off names or implementation details.
- **Required behavior:** Extract the general acceptance pattern and keep project-specific language in local instructions only.
- **Verification:** Review universal files for product names, paths, labels, or domain details that were not explicitly requested as universal.
- **Basis:** explicit-user-correction, objective-reproduction
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-007 — Stale familiarity preferred over stronger current tools

- **Scope:** research and tool selection
- **Trigger:** The task asks for current, best, bleeding-edge, latest, or high-capability tools and approaches.
- **Failure:** The agent recommends a familiar older option after shallow research or rejects a superior newer option merely because it needs hardening.
- **Required behavior:** Search the current ecosystem broadly, compare serious candidates, prefer the strongest fit, and treat fixable rough edges as engineering work.
- **Verification:** Provide current source-backed maintenance, capability, compatibility, and tradeoff evidence for the selected option and qualified alternatives.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-008 — Wrong target or stale build mistaken for current work

- **Scope:** repositories, builds, and runtimes
- **Trigger:** Multiple repositories, worktrees, branches, copies, generated outputs, installations, profiles, or cached builds may exist.
- **Failure:** The agent edits or tests the wrong target and reports success from stale output.
- **Required behavior:** Resolve the canonical target before editing and prove the runtime loaded the new artifact using path plus version, hash, timestamp, or unmistakable behavior.
- **Verification:** Launch or install from a fresh canonical output and confirm the exact changed behavior after reload or restart.
- **Basis:** explicit-user-correction, repeated-independent-failure
- **Confidence:** high
- **Next review:** 2027-01-29T05:07:42.769801+00:00

## P-009 — Existing project restarted or duplicated without continuity resolution

- **Scope:** project continuity
- **Trigger:** A user names, resumes, revisits, or starts work resembling an existing project, repository, artifact, or prior research effort.
- **Failure:** The agent initializes a new project, edits a similarly named copy, or starts over before locating and validating prior work, causing divergence, duplication, corruption, or loss of continuity.
- **Required behavior:** Search available memory and files, inspect project identity markers, Git remotes, manifests, artifacts, handoffs, and registry candidates, then resolve the canonical project before any mutation; remain read-only while identity is ambiguous.
- **Verification:** Record the selected project ID, canonical path, remote/fingerprint, loaded handoff, and current repository baseline before editing; prove no unresolved duplicate candidate was ignored.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-29T06:00:42.105394+00:00

## P-010 — Stale or unsourced research memory treated as current truth

- **Scope:** research and toolchain memory
- **Trigger:** A prior chat, handoff, note, or project ledger contains a tool recommendation, coding method, version claim, benchmark, compatibility statement, or best-option decision.
- **Failure:** The agent reuses remembered research without provenance or freshness checks, or repeats an old decision after the ecosystem, project constraints, or evidence changed.
- **Required behavior:** Store source, date, version, applicability, evidence, confidence, alternatives, decision rationale, and review date; search prior research first, then revalidate stale or version-sensitive claims before reuse and mark superseded findings without deleting history.
- **Verification:** The selected method cites current evidence or a still-valid verified record, identifies the research record used, and records whether the prior decision was confirmed, updated, or overturned.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-29T06:00:42.105394+00:00

## P-011 — New cross-chat artifact missed or left unreconciled

- **Scope:** project continuity and artifact progression
- **Trigger:** A named project resumes and another chat may have created a newer file, version, build, prompt, research result, or reference artifact, including one that reuses an older filename.
- **Failure:** The agent continues from stale memory or an older artifact because it did not sweep recent cross-chat sources, did not open the newer candidate, or found it but failed to record it in durable project memory.
- **Required behavior:** Before planning or editing, sweep recent project sources, open plausible candidates, compare source identity and content, preserve same-name versions with lineage, reconcile them into the artifact ledger, update STATUS and HANDOFF, and reread the durable state.
- **Verification:** The current session identifies and opens every plausible newer candidate since the last checkpoint, records stable identity or content signature plus lineage in artifacts.jsonl, refreshes STATUS.json and HANDOFF.md, rereads them, and proves no newer unresolved candidate was ignored.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-29T07:05:48.454685+00:00

## P-012 — Project progress exists but the master project catalog is not updated

- **Scope:** cross-chat project tracking
- **Trigger:** A chat discovers, creates, versions, packages, checkpoints, merges, renames, or supersedes work for any ongoing project.
- **Failure:** The agent updates only the current chat or project-local memory, leaving the user's cross-project database stale so another chat resumes an older version, loses relationships, or starts over.
- **Required behavior:** Load the live cross-project catalog before named project work; reconcile every verified project, version, artifact, repository, relationship, checkpoint, confidence change, and next action; render and reread the Markdown mirror; preserve all older versions; export the catalog when durable storage is unavailable.
- **Verification:** The catalog JSON, Markdown mirror, and append-only event log contain the new or changed project state; the changed entry is reread; the catalog doctor passes; older versions remain present; and the next chat can locate the latest verified state without relying on conversation memory.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-29T11:54:49.835074+00:00

## P-013 — Unsafe or untracked artifact-library cleanup loses project history

- **Scope:** artifact library, storage, and bundle management
- **Trigger:** The user has storage pressure, duplicate files, repeated exports, same-name versions, or scattered project bundles and asks the agent to organize or delete files.
- **Failure:** The agent deletes or replaces files from names, dates, or appearances alone; removes a canonical or referenced artifact; scatters bundle dependencies; or claims ChatGPT Library cleanup without a real delete action, causing lost versions, broken handoffs, or false storage reports.
- **Required behavior:** Inventory every candidate, source current usage, classify canonical/protected/versioned/referenced items, require exact SHA-256 equality for automatic duplicate quarantine, preserve same-name different-content versions, keep bundles and dependencies together, require explicit cleanup approval, quarantine local removals, and treat external Library deletion as manual unless a supported delete action succeeds.
- **Verification:** The library catalog and Markdown mirror list every in-scope item with identity, version, hash/signature, source, protection, references, and storage impact; the cleanup plan names the kept copy and reasons; local removals are restorable; external deletion is confirmed or remains manual; organized project bundles include manifests and dependencies; and the library doctor passes.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-29T12:16:33.274966+00:00

## P-014 — Substantial project session closes without durable verified artifact

- **Scope:** project implementation, builds, repairs, and artifact delivery
- **Trigger:** A substantial task has valid source changes or partial verification but more solvable work remains, the workspace may be ephemeral, or the user requested a final build or publication.
- **Failure:** The agent stops with an unfinished-status response or leaves progress only in temporary source state, so later cleanup, compaction, restart, or workspace loss destroys the work and no usable build reaches the user.
- **Required behavior:** Continue through all realistically solvable defects. Before any closeout or interruption-prone handoff, create a durable source checkpoint and a complete verified runnable artifact. When delivery was requested, publish it and verify remote bytes. If a hard external blocker truly remains, preserve and deliver the latest verified full artifact plus exact checkpoint and evidence instead of leaving only mutable source.
- **Verification:** Confirm the final response links or precisely identifies a complete verified artifact, its hash, durable checkpoint or handoff, and remote byte verification when publication was requested; confirm no substantive progress exists only in an ephemeral workspace.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-01-30T02:29:20.796632+00:00

## P-015 — First working state mistaken for final project quality

- **Scope:** universal project work
- **Trigger:** A project task reaches its first correct or requested working state.
- **Failure:** The agent stops at the first working solution and leaves material capability, performance, reliability, integration, or polish improvements unexplored.
- **Required behavior:** Apply the Maximum Improvement Rule: establish the relevant starting state or baseline when useful, use the strongest current technique and relevant bleeding-edge research, treat 100x better as non-numeric shorthand for maximum-effort improvement, continue evidence-backed improvements to convergence, then run an independent outside-the-box pass and finish fully testable and ready to run.
- **Verification:** The evidence ledger records the starting state or meaningful baseline, final observed result, current-tech decision when material, convergence pass, outside-the-box pass, and complete real-runtime tests/artifact verification.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-02-06T09:25:47.253396+00:00

## P-016 — Status and test ceremony displaces the runnable session build

- **Scope:** project chat closeout and artifact readiness
- **Trigger:** A project chat approaches closeout after implementation work, or spends substantial time on repeated broad tests, STATUS/HANDOFF files, catalogs, or reports.
- **Failure:** The session consumes time on testing/status ceremony and ends without a current usable build ready for immediate user testing.
- **Required behavior:** Enforce the build-first session invariant: every project chat retains a usable build; implementation-changing chats produce a fresh build from current canonical source before status work; research-only chats reuse the latest verified build. Run exact/targeted tests during iteration, broad required suites once at convergence, then write concise status deltas.
- **Verification:** Confirm a runnable artifact/build ID exists at closeout, fresh-copy or install smoke testing passed for implementation changes, closeout receipt records build proof, and status/handoff work occurred only after artifact availability.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-02-06T10:22:37.884438+00:00

## P-017 — Skill transition resets execution state

- **Scope:** cross-skill orchestration
- **Trigger:** A task activates, transitions to, or composes multiple skills after work has already begun.
- **Failure:** The newly active skill treats itself as a fresh workflow, repeats resolved discovery or status reads, drops the current acceptance ledger or exact next action, and stalls without advancing the task.
- **Required behavior:** Treat domain skills as overlays on persistent Zero-Loss continuity. Carry acceptance requirements, canonical identifiers, loaded evidence, hashes, run/job IDs, latest durable checkpoint/mutation/test, blocker, no-repeat history, and exact next action across skill transitions; reuse existing evidence unless invalidated; after two unchanged waves change strategy.
- **Verification:** During a multi-skill task, verify that transition into a domain skill reuses prior IDs/evidence and advances from the preserved next action without restarting discovery; audit every personal skill for an explicit Zero-Loss composition bridge.
- **Basis:** explicit-user-universal-rule
- **Confidence:** high
- **Next review:** 2027-02-26T18:36:04.980406+00:00
