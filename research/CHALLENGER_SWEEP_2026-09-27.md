# Agent Foundry Challenger Sweep — 2026-09-27

Purpose: identify materially useful standards, frameworks, tools, and patterns missing from the first Agent Foundry architecture.

## Decisions

| Candidate / ecosystem | Decision | What Foundry takes |
|---|---|---|
| Agent Skills open specification | **adopt** | package/frontmatter/progressive-disclosure compatibility |
| AGENTS.md open convention | **adopt** | nested scoped instruction compatibility and closest-file precedence |
| MCP 2026-07-28 | **adopt** | current tool/context protocol profile, extensions, Tasks, Apps, auth/deprecation awareness |
| A2A 1.0 | **adopt** | agent↔agent capability/task/artifact interoperability |
| Agent Client Protocol | **adopt stable / watch drafts** | editor/client↔coding-agent interoperability |
| AG-UI | **compose** | application-facing streaming/shared UI state |
| OWASP Agent Control Standard 0.1 | **compose + watch** | runtime hooks, Guardian dispositions, OTel/OCSF trace concepts, AgBOM/provenance profiles |
| agent-skill-eval | **compose** | real-harness with/without Skill delta, state-diff grading, negative triggers, pass@k |
| Inspect AI | **compose** | agent eval/sandbox/checkpoint patterns |
| OpenTelemetry | **adopt** | vendor-neutral trace/event vocabulary |
| Phoenix / Langfuse | **adapter choices** | trace/eval/dataset/experiment backends; neither becomes canonical truth |
| Temporal / LangGraph durable execution | **implementation choices** | restart-safe/human-wait/checkpoint patterns |
| OPA / Cedar | **implementation choices** | decision/enforcement separation, default-deny policy-as-code patterns |
| Cisco AI Defense Skill Scanner | **compose** | pre-install/CI detection layer; never treated as security certification |
| GitHub Artifact Attestations / SLSA | **adopt for releases** | verifiable source→artifact provenance and SBOM path |
| skills CLI / skills.sh | **adopt compatibility** | discover/install/update/packs ecosystem |
| Botfile | **compose pattern** | desired-state plan/sync/status multi-agent fan-out |
| Agent Skills OCI proposals | **watch** | immutable registry/digest/signing ideas; not treated as settled official format |
| One universal orchestration framework | **reject as Foundry core** | stay framework-neutral; integrate superior patterns instead |
| Prompt-only security | **reject** | use enforcement boundaries for high-impact actions |
| Popularity/install counts as trust | **reject** | trust requires provenance/review/permission/security evidence |
| Single scanner = “safe” | **reject** | defense in depth + human review |

## High-value sources

### Skill/instruction standards
- https://agentskills.io/specification
- https://agents.md/
- https://www.skills.sh/docs
- https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem
- https://github.com/listfold/botfile

### Protocol interoperability
- https://modelcontextprotocol.io/
- https://tasks.extensions.modelcontextprotocol.io/
- https://a2a-protocol.org/
- https://agentclientprotocol.com/
- https://docs.ag-ui.com/

### Runtime control / authorization
- https://genai.owasp.org/resource/agent-control-standard-acs/
- https://github.com/genai-security-project/agent-control-standard
- https://www.openpolicyagent.org/
- https://www.cedarpolicy.com/

### Evaluation / observability / durability
- https://github.com/tardigrde/agent-skill-eval
- https://inspect.aisi.org.uk/
- https://opentelemetry.io/
- https://phoenix.arize.com/
- https://langfuse.com/
- https://docs.temporal.io/ai

### Skill and supply-chain security
- https://github.com/cisco-ai-defense/skill-scanner
- https://docs.github.com/en/actions/concepts/security/artifact-attestations
- https://slsa.dev/
- https://osv.dev/
- https://scorecard.dev/

## Net-new Foundry architecture from this sweep

1. <code>INTEROPERABILITY_STANDARD.md</code>
2. <code>DURABLE_EXECUTION_STANDARD.md</code>
3. <code>EVALUATION_STANDARD.md</code>
4. <code>OBSERVABILITY_STANDARD.md</code>
5. <code>AUTHORIZATION_CONTROL_STANDARD.md</code>
6. <code>THIRD_PARTY_SKILL_SECURITY.md</code>
7. <code>SUPPLY_CHAIN_STANDARD.md</code>
8. <code>DISTRIBUTION_STANDARD.md</code>
9. <code>registry/protocols.json</code>
10. <code>SECURITY.md</code>
11. <code>llms.txt</code>

## Follow-up implementation gates

- Full Skill source mirrors before enabling repository-wide automated Skill scanning.
- Pin/review scanner/action revisions before making them a blocking security gate.
- Generate artifact attestations when release packaging moves into GitHub Actions.
- Add trust/eval/release receipt schemas with deterministic validators.
- Prototype multi-agent sync with plan-first/no-clobber semantics.
- Build protocol adapters only when a real Foundry/Constellation workflow needs them; do not create ceremonial adapters.
