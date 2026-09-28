# Provider Workflows

## Google Drive connected connector

Use the connected Drive connector as the first mandatory durable publication path. When the exact canonical Drive file ID is known and an update/replace action is supported, update that file in place; otherwise create an explicit versioned object and record lineage. For new local files, use connector upload actions. If the connector reports a transfer ceiling, prepare parts below that ceiling and upload each part. Read metadata after every required upload/update. The current safe default for connectors with a 100 MiB intake ceiling is 85 MiB.

Do not assume a Drive `view` URL is public. Check metadata and sharing response. When only user-specific sharing is supported, share to the requested email and label the links accordingly.

## Google Drive API

The direct uploader uses Drive v3 resumable sessions. Large transfers are sent in chunks that are multiples of 256 KiB. A saved session URI can be queried after interruption. A `308 Resume Incomplete` response and its `Range` header determine the next byte. A `404` means the session expired and must be restarted.

Authentication options:

- `GOOGLE_DRIVE_ACCESS_TOKEN` environment variable;
- `GOOGLE_OAUTH_ACCESS_TOKEN` environment variable;
- authenticated `gcloud auth print-access-token`;
- connected Google Drive tool, which should be preferred inside ChatGPT.

For long-lived local automation, use a proper OAuth client and refresh-token flow rather than manually copying short-lived access tokens. Do not bundle OAuth client secrets in the skill.

## GitHub Releases

A GitHub repository must exist and the authenticated identity must have push access. Binary release assets are sent to `uploads.github.com` as raw bytes. A release is created as a draft and remains a draft until verification finishes.

Authentication options:

- connected GitHub account for discovery and permissions;
- `gh auth login`, then `gh auth token`;
- `GH_TOKEN` or `GITHUB_TOKEN` environment variable.

Fine-grained PAT: grant only the target repository and **Contents: write**. Add **Workflows: write** only when modifying workflow files, which normal release uploads do not require.

Do not use GitHub repository contents actions for large binary archives. Those actions are intended for repository files and may be text-only or subject to much smaller limits.

### Idempotency

For each asset name:

1. List existing release assets.
2. Keep an existing asset only when state, size, and digest match.
3. Delete `starter`, zero-byte, wrong-sized, or wrong-digest assets.
4. Upload the intended asset.
5. Re-list and verify before publishing the release.

## Generic HTTPS providers

The generic uploader supports:

- raw `PUT` or `POST`;
- multipart form uploads;
- bearer token, Basic Auth, cookies, and arbitrary secret headers from environment variables;
- URL extraction from a JSON dotted path or regex;
- HEAD size verification or full download verification.

Before using an unfamiliar service, obtain the official API endpoint and response schema. Browser-only upload pages with JavaScript, CAPTCHA, anti-bot checks, or interactive MFA require a dedicated connected app or browser workflow rather than pretending the HTTP uploader can bypass them.
