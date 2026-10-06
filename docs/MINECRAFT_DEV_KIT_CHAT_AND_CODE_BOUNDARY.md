# Minecraft Dev Kit — Chat and Code Boundary

## Purpose

Define the operating boundary for Minecraft Dev Kit work inside Agent Foundry so chat-oriented workflows and coding-agent workflows remain complementary instead of being mixed together.

## Chat-facing layer

The chat layer owns:

- understanding the user's intent and acceptance criteria;
- recovering project identity, checkpoints, artifacts, and known blockers;
- selecting the correct domain procedure;
- explaining decisions and verification evidence;
- maintaining continuity across conversations;
- requesting or recording human decisions when authorization or ambiguity matters.

The chat layer must not pretend a static plan is implementation evidence.

## Coding-agent layer

The coding layer owns:

- editing source files;
- running project-local tools and builds;
- applying migrations, ports, repairs, and refactors;
- collecting build and runtime evidence;
- producing commits, patches, or release artifacts.

Coding instructions should stay focused on the repository and task. They should not duplicate broad chat governance rules.

## Minecraft Dev Kit responsibilities

Minecraft Dev Kit procedure ownership includes:

- Minecraft version and loader migrations;
- mod conversion and compatibility work;
- implementation and asset pipeline support;
- benchmark and performance validation;
- release-quality checks.

Acceptance still requires preserved behavior, compatibility, and evidence appropriate to the requested change.

## Recovery order

For substantial work:

1. Resolve canonical project and artifact identity.
2. Read accepted checkpoints and active TODO state.
3. Preserve existing capabilities and constraints.
4. Choose the smallest coherent high-value implementation chunk.
5. Mutate, test, checkpoint, and publish evidence.

## Anti-patterns avoided

- turning chat instructions into bloated coding-agent prompts;
- replacing existing projects with simplified shells;
- marking work complete without verification;
- rediscovering settled project state after every tool transition.

This document supplements Agent Foundry governance. It does not replace domain-specific implementation instructions.
