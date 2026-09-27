# Interoperability Protocols

Agent Foundry now models interoperability by **boundary**, not by picking one universal protocol.

| Boundary | Foundry target |
|---|---|
| Agent ↔ tools/context | **MCP** |
| Agent ↔ agent | **A2A** |
| Coding agent ↔ editor/client | **ACP** |
| Agent ↔ application UI | **AG-UI** |
| Agent ↔ runtime Guardian/control plane | **OWASP ACS** |

## Why separate them?

Each protocol preserves different semantics. A tool call, collaborative agent task, editor permission request, streaming UI event, and security decision are not interchangeable just because they all use JSON.

Foundry adapters must preserve cancellation, task state, permissions, identity, streaming, provenance, and error semantics instead of flattening everything into a generic "tool."

## Version state

Version-sensitive facts live in the machine-readable [protocol registry](https://github.com/Herbertofury/Agent-Foundry/blob/main/registry/protocols.json).

This keeps the Wiki stable while protocols evolve.

[Read the canonical interoperability standard](https://github.com/Herbertofury/Agent-Foundry/blob/main/INTEROPERABILITY_STANDARD.md)
