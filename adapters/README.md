# Cross-Agent Adapters

Adapters translate Agent Foundry's canonical behavior into specific agent/runtime formats.

## Rule
Keep adapters thin. They should reference or import canonical policy wherever the harness allows it.

A new adapter must not silently weaken blocker handling, continuity, challenger discovery, performance acceptance, or runtime proof.
