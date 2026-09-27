# Trust & Supply Chain

Agent Foundry treats a downloaded Skill as **untrusted instructions + untrusted code + untrusted dependencies** until reviewed.

## Third-party Skill intake

<code>quarantine → provenance → format validation → scan → semantic review → permission manifest → composition-risk review → sandbox eval → pin/attest → promote</code>

A green scanner result is useful evidence. It is never a security certificate.

## Release trust

Foundry bundles should record:
- source commit;
- checksum + exact size;
- build/packaging workflow;
- validation/eval evidence;
- license/dependencies;
- supersession lineage.

GitHub Artifact Attestations/Sigstore/SLSA-style provenance are preferred when the build path supports them.

SBOM describes software composition; AgBOM describes the running agent's model/tool/Skill/control composition.

Canonical standards:
- [THIRD_PARTY_SKILL_SECURITY.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/THIRD_PARTY_SKILL_SECURITY.md)
- [SUPPLY_CHAIN_STANDARD.md](https://github.com/Herbertofury/Agent-Foundry/blob/main/SUPPLY_CHAIN_STANDARD.md)
