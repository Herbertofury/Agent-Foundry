# Roadmap

Agent Foundry is intended to grow into a complete reliability and capability layer for agentic work.

## Near-term
- publish full source mirrors for flagship Skills;
- package reusable AGENTS.md starter kits;
- add machine-readable policy catalog;
- add challenger receipts and completeness receipts;
- add cross-skill constitution parity audits;
- add incident/recovery knowledge format;
- add deterministic documentation integrity checks;
- keep Wiki synchronized automatically.

## Next layer
- searchable skill registry;
- compatibility matrix across agent runtimes;
- install/update tooling for skill bundles;
- reusable eval harness;
- signed/checksummed release bundles;
- project templates for apps, mods, research, repair, artifact work;
- automated provenance and release receipts.

## Long-term
A Foundry project should be able to answer:
- What are my invariants?
- Which skill owns this procedure?
- What prior art should I integrate?
- What failed before?
- What proof do I have?
- Where is the latest durable artifact?
- What exactly happens next?

…without rediscovering the answer every time.


## Second challenger sweep — landed

Added in the 2026-09-27 sweep:
- interoperability registry and MCP/A2A/ACP/AG-UI/ACS boundary model;
- durable execution/task semantics;
- real-harness Skill evaluation standard;
- OpenTelemetry-compatible observability standard;
- third-party Skill quarantine/security standard;
- authorization/runtime-control standard;
- supply-chain provenance + SBOM/AgBOM direction;
- skills.sh/open Agent Skills distribution compatibility;
- desired-state multi-agent synchronization model;
- agent-friendly <code>llms.txt</code> map;
- repository security policy.

## Next implementation wave

- mirror complete flagship Skill source trees under <code>skills/</code>;
- add trust/release/eval receipt schemas and generators;
- wire Agent Skills spec validation into CI when full Skill sources land;
- add security scanning to Skill PRs with a pinned reviewed scanner version;
- generate attestations for packaged releases;
- add an installer/sync prototype with plan → apply → status semantics;
- add ACP/AG-UI adapters to Project Constellation where they materially improve client interoperability;
- add ACS compatibility experiments without treating the young reference implementation as the sole enforcement boundary.
