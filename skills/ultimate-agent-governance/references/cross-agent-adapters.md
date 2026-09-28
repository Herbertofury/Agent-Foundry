# Cross-Agent Adapter Map

Keep `AGENTS.md` canonical when the harness supports it. Add a native adapter only when it improves discovery or scoped behavior without duplicating large policy text.

## Codex

- Root and nested `AGENTS.md` are the primary repository mechanism.
- Closer nested instructions apply to their subtree.
- Keep root rules concise; use `PLANS.md`/skills for detail.

## GitHub Copilot / VS Code

- `AGENTS.md` is supported for agent instructions.
- `.github/copilot-instructions.md` is repository-wide custom guidance.
- `.github/instructions/*.instructions.md` supports scoped instructions with `applyTo`.
- `.github/agents/*.agent.md` can define specialist agents.

Use a tiny `copilot-instructions.md` adapter if needed; do not restate the full `AGENTS.md`.

## Claude Code

- `CLAUDE.md` supports project instructions and `@path` imports.
- Import canonical files rather than copying them.

## Gemini CLI

- `GEMINI.md` supports hierarchical context and `@file` imports.
- Import canonical files rather than copying them.

## Cursor

- Project rules live in `.cursor/rules`.
- Cursor also supports `AGENTS.md` directly.
- Add `.mdc` rules only for Cursor-specific/scoped behavior that benefits from its native rule selectors.

## Cline

- Cline supports `.clinerules/` / `.cline/rules/` and recognizes `AGENTS.md`.
- Prefer the canonical `AGENTS.md` unless Cline-specific behavior is needed.

## Roo Code

- Roo supports `.roo/rules/` plus `AGENTS.md`.
- Prefer the canonical `AGENTS.md`; reserve Roo directories for mode-specific behavior.

## Continue

- Project rules live in `.continue/rules` and can use globs/conditional loading.
- Add a short always-on adapter pointing to canonical policy, then scoped rules only when needed.
