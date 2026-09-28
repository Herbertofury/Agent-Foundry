# Artifact packaging and verified publication

Load this reference when the task creates/modifies material saved output that must be published to Drive, or when packaging, release delivery, multipart recovery, or deep remote verification is required. Read `references/DRIVE-PERSISTENCE.md` first for the mandatory persistence contract.

## Contract

1. Produce the complete intended artifact/checkpoint before publishing that checkpoint.
2. Publish every material saved artifact/checkpoint to connected Google Drive in the same run; GitHub/ProjectDump/other destinations are additional when applicable.
3. Calculate local SHA-256 and size before upload when raw bytes exist.
4. Never report success from an HTTP status, connector acknowledgement, or upload response alone.
5. Verify remote size and a trustworthy provider digest. If no trustworthy digest exists and byte identity matters, re-download the complete remote object and hash it.
6. Keep resumable state until verification passes.
7. Return or record observed direct links/IDs, part ordering, reassembly helpers when multipart, final size, and final SHA-256.
8. Preserve the local artifact, manifest, checksums, and upload state until remote verification succeeds.
9. Never expose, log, store, or echo passwords, OAuth tokens, cookies, PATs, or API keys.

Read `references/ARTIFACT-VERIFICATION-CONTRACT.md` for detailed proof rules, `references/ARTIFACT-PROVIDER-WORKFLOWS.md` for provider-specific flows, and `references/ARTIFACT-CREDENTIAL-HANDLING.md` when credentials are involved.

## Prepare and verify locally

Run publisher scripts with the container tool.

```bash
python scripts/artifact_publisher.py prepare /path/to/file-or-directory \
  --output-dir /path/to/prepared \
  --name Product-1.2.3.zip \
  --chunk-mib 85
```

The prepare command creates deterministic packaging metadata, checksums, multipart files when required, and reassembly helpers.

Verify before upload:

```bash
python scripts/artifact_publisher.py verify /path/to/prepared/UPLOAD-MANIFEST.json --reassemble
```

Prefer a single file for GitHub Releases or direct Drive uploads unless provider limits or user convenience require multipart delivery. Use 85 MiB parts for ChatGPT connector transfers unless the connector reports a smaller limit.

## Provider selection

Google Drive is mandatory whenever an authorized Drive path is available:

1. Connected Google Drive for every material user artifact/checkpoint and project-brain export.
2. Direct Google Drive resumable upload when authenticated local Drive credentials are already available and the connector path is unsuitable.
3. GitHub repository/release for repository-owned source and versioned deliverables, in addition to the required Drive checkpoint/artifact copy.
4. ProjectDump/Project Constellation for cross-project brain state, in addition to the required Drive checkpoint/export.
5. User-authorized HTTPS destinations when explicitly part of the workflow, again in addition to Drive unless Drive is genuinely unavailable.

Do not treat another provider as a substitute for Drive merely because it is easier. Do not use a paid or unrelated provider merely because it is connected.

## Google Drive connected workflow

1. Resolve the existing canonical Drive file/folder from project state when possible.
2. Prepare and locally verify the artifact/checkpoint.
3. If a canonical raw Drive file already exists and the connector supports update/replace, update it in place; otherwise create a versioned object and record lineage.
4. Attempt the whole artifact once when size permits.
5. If the connector rejects it for size, upload prepared parts sequentially or use a supported resumable path.
6. Read remote metadata after each required upload/update and compare byte size/digest to the manifest when available.
7. Use observed provider IDs/URLs only. Never synthesize a Drive URL.
8. State the observed access level accurately.
9. Include reassembly helpers and the final SHA-256 for multipart delivery.

Do not repeat an oversized whole-file upload after the connector has disclosed its limit.

## GitHub Release workflow

1. Resolve the authenticated account and exact repository with the GitHub connector when available.
2. Confirm required repository permission.
3. Use a Release for binary ZIPs and archives rather than repository text-file actions.
4. Prefer existing `gh` authentication or an approved environment secret. Never ask the user to paste tokens into ordinary chat.
5. Create or reuse a draft release, upload exact bytes, compare provider digest and size, re-list assets, and publish only after every asset verifies.
6. If GitHub omits a trustworthy digest, fully re-download and hash the asset.

Example:

```bash
python scripts/artifact_publisher.py github-release \
  --repo OWNER/REPOSITORY \
  --tag v1.2.3 \
  --title "Product 1.2.3" \
  --manifest /path/to/prepared/UPLOAD-MANIFEST.json \
  --receipt /path/to/GITHUB-UPLOAD-RECEIPT.json
```

Create a new repository only when explicitly authorized. Make a new repository public only when public visibility is explicitly requested.

## Direct Drive resumable workflow

Use only when an existing authenticated environment is available.

```bash
python scripts/artifact_publisher.py drive-upload \
  --manifest /path/to/prepared/UPLOAD-MANIFEST.json \
  --receipt /path/to/DRIVE-UPLOAD-RECEIPT.json
```

Use public sharing only when explicitly requested. Resume from the exact server-confirmed byte. If a session expires, start a new upload session without modifying the local artifact.

## User-authorized HTTPS workflow

Use `http-upload` only for a specific user-authorized service. Collect only missing non-secret connection details, keep secrets in connected tools or environment variables, and deep-verify the remote object.

## Failure recovery

- Retry transient failures with backoff.
- Remove or replace incomplete same-name remote assets only after identifying them precisely.
- Never silently accept an older same-name artifact.
- If no provider is reachable, return the locally verified artifact and the exact publication blocker.
- Keep resumable state so a failed upload does not require rebuilding the artifact.

## Project Constellation publication delta

After remote verification of a named project artifact, update an already-available Project Constellation/project-memory record with artifact identity, version/lineage, SHA-256, size, observed provider link or ID, verification evidence, timestamp, and changed next step when applicable. Never promote an artifact to latest by upload time alone. Preserve older publication history and user edits.

Keep this cheap. Do not broad-scan connectors solely to rediscover a Project Constellation object whose identity is already known, and do not rebuild the website/quick HTML unless that presentation artifact is in scope. The changed brain/checkpoint delta must still be mirrored to Drive after meaningful progress. Use `references/PROJECT-CONSTELLATION-BRAIN.md` for the shared synchronization contract.

## Publisher test

Run after changing `scripts/artifact_publisher.py`:

```bash
cd scripts
python -m unittest -v test_artifact_publisher.py
```
