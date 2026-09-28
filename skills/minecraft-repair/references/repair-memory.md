# Minecraft Repair Memory Protocol

## Contents

1. Canonical store
2. Record schema
3. Search/matching
4. Success and failure updates
5. Deduplication and supersession
6. Privacy and portability

## 1. Canonical store

Use one persistent JSONL file named `repair-history.jsonl` under `Minecraft Repair Brain`.

Each line is one JSON object. JSONL is append-friendly, diffable, searchable, and easy to materialize for scripts.

A bundled `seed-repairs.jsonl` provides initial known repairs. Copy/import those records only if the canonical store does not already contain their IDs.

## 2. Record schema

Recommended fields:

```json
{
  "schema_version": 1,
  "id": "stable-unique-id",
  "recorded_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "outcome": "success|partial|failed|superseded",
  "confidence": "high|medium|low",
  "minecraft": "1.20.1",
  "loader": {"name": "Forge", "version": "47.4.20"},
  "java": "17",
  "mods": [{"id": "example", "version": "1.2.3", "filename": "example.jar"}],
  "symptoms": ["human-readable symptom"],
  "signatures": ["exact exception/symbol strings"],
  "root_cause": "proven root cause",
  "repair": {
    "type": "version-swap|jar-patch|source-patch|config|world-data|loader|other",
    "changes": ["exact change"]
  },
  "verification": {
    "static": ["checks"],
    "runtime": ["checks"],
    "user_feedback": "optional"
  },
  "artifacts": [{"filename": "patched.jar", "sha256": "..."}],
  "visual_identity": {
    "policy": "repair-mark-v2",
    "canonical_art_url": "https://...",
    "normalized_art_sha256": "...",
    "marked_art_sha256": "...",
    "integration": "embedded|sidecar|launcher-mapping",
    "marker_only_diff": "PASS"
  },
  "applicability": ["conditions required before reuse"],
  "anti_patterns": ["failed ideas to avoid"],
  "supersedes": [],
  "superseded_by": null
}
```

Avoid secrets, account tokens, access tokens, UUIDs, or unrelated personal data.

## 3. Search/matching

Search strongest-to-weakest:

1. exact missing class/member/descriptor;
2. exception type plus mod ID;
3. pair/group of implicated mod IDs;
4. exact mod versions;
5. Minecraft + loader version;
6. subsystem keywords.

A prior record is a hypothesis until current applicability is checked.

Useful match keys include:

- `ClassNotFoundException` class path
- `NoSuchMethodError` owner/name/descriptor
- mixin config and target member
- registry key
- mod ID and version pair
- crash event/modid
- native library name
- world dimension/registry identifier

## 4. Success and failure updates

For shippable repaired mod artifacts, also follow `repair-mark.md` and retain official-art provenance plus marker-only verification.

If the user confirms a fix works:

- set `outcome=success`;
- raise confidence appropriately;
- store the exact successful artifact hash if known;
- add concise user confirmation to verification;
- preserve the original root-cause evidence.

If a fix fails:

- set the attempt to `failed` or `partial`;
- record the new failure signature;
- add the attempted repair to `anti_patterns` when it should not be repeated;
- continue diagnosis from the new evidence.

Do not overwrite history to pretend the first idea worked.

## 5. Deduplication and supersession

Prefer updating a record when the same repair case gains stronger evidence. Create a new record when versions, root cause, or repair mechanism materially differ.

When a newer repair replaces an older one, mark the old record `superseded` and cross-link IDs.

Use `scripts/repair_kb.py` to search and update local copies deterministically.

## 6. Privacy and portability

Store technical repair evidence only. Normalize local paths when they are not needed for reuse. Do not save authentication tokens or launcher credentials from logs.

If the persistent store cannot be written, produce the updated JSONL as a downloadable artifact so the user can retain it. Never claim durable memory was updated unless the write actually succeeded.
