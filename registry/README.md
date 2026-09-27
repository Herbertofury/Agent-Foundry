# Agent Foundry Registry

Machine-readable compatibility/status data lives here so version-sensitive facts do not get duplicated across long prose.

## Files

- <code>protocols.json</code> — interoperability targets, roles, maturity and freshness.

## Update rule

Refresh entries from primary sources when:
- a protocol releases a new stable version;
- a draft becomes stable;
- a deprecation materially changes an adapter;
- conformance/testing expectations change.

Prose standards should reference the registry instead of hardcoding a version everywhere.
