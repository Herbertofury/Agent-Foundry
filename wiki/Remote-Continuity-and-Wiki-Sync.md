# Remote Continuity & Wiki Sync

> **A chat is not a backup. A source mirror is not a live Wiki. A checkpoint is durable only after required remotes agree.**

Agent Foundry treats remote persistence as part of execution acceptance so long projects can survive stale chats, failed sessions, compaction, connector changes, local-machine loss, and interrupted handoffs without rediscovering or losing work.

## The durable checkpoint tuple

For a substantive project checkpoint, preserve the applicable tuple:

| Surface | What belongs there | Verification |
|---|---|---|
| **GitHub / canonical VCS** | Source, history, AGENTS/policy changes, project-owned continuity files | Repository + branch/ref + exact commit readback |
| **Google Drive** | Material user artifacts, builds/packages, exports, recovery/checkpoint bundles | Stable file/folder ID + metadata readback + size/digest when available |
| **Live GitHub Wiki** | Human-facing project documentation for repositories that use a Wiki | Successful publish + re-clone of `.wiki.git` + source/live comparison |
| **Project Constellation / project memory** | Cross-project locator, checkpoint receipts, blockers, exact next action | Updated lineage points at the verified remote tuple |

Chat history, sandbox files, local scratch directories, and ChatGPT Library are useful caches. They are not allowed to be the only current copy of material progress.

## Checkpoint cadence

Synchronize at **coherent milestones**, not every keystroke:

1. after a meaningful implementation/research milestone;
2. after a coherent build/package/export;
3. before context compaction or handoff;
4. before interruption-prone long gates;
5. before closeout.

This keeps recovery strong without turning persistence into connector spam.

## Live GitHub Wiki invariant

The repository `wiki/` directory is the **canonical source mirror**. Readers, however, see the repository's actual GitHub Wiki backed by `.wiki.git`.

Therefore:
- changing `wiki/` alone does **not** count as updating the Wiki;
- material feature, architecture, compatibility, installation, operations, and governance changes update relevant Wiki pages in the same coherent checkpoint;
- publication must push to the live Wiki backend;
- the publishing workflow must verify the live backend against the canonical source;
- if the Wiki backend does not exist, it must be created/bootstrap through an authorized supported route before documentation can be called complete.

## Failure semantics

A partial remote success is **not** full synchronization. Preserve successful remote identities plus the exact pending operation for any failed remote. Never delete the only good copy while repairing synchronization.

## Resume rule

A fresh chat should prefer the latest **verified remote lineage** over conversational recency. Resolve repository commit, Drive checkpoint/artifact identity, Wiki publish state, and exact next action; then continue from that boundary instead of restarting discovery.

## Acceptance gate

Before calling substantive project work durable or complete, answer **yes** to all applicable questions:
- Is the canonical source/history pushed and identified by exact commit?
- Are material artifacts/checkpoint exports in the canonical Drive location and read back?
- If the project uses GitHub Wiki, does the actual live Wiki match the canonical `wiki/` source?
- Is the remote tuple recorded so another chat can recover it?
- Would losing this entire conversation still leave the latest material progress recoverable?

If any required answer is **no**, synchronization is still active work.
