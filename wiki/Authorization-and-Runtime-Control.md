# Authorization & Runtime Control

A prompt that says “do not do dangerous things” is guidance. It is not a complete enforcement boundary.

## Foundry model

<code>agent proposes → policy decides → enforcement point acts/blocks → trace records</code>

Sensitive decisions should consider:
- principal/agent identity;
- user delegation;
- action;
- resource;
- context/risk;
- tool provenance;
- prior approval.

OPA/Rego, Cedar, provider policies, or an ACS Guardian are all possible engines.

## Runtime dispositions

Foundry normalizes:
<code>allow</code> · <code>deny</code> · <code>modify</code> · <code>ask</code> · <code>defer</code>

OWASP Agent Control Standard is an important interoperability target for portable lifecycle hooks, Guardian decisions, tracing, and AgBOM. Its young reference implementation is not treated as a magic complete security boundary.

[Read AUTHORIZATION_CONTROL_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/AUTHORIZATION_CONTROL_STANDARD.md)
