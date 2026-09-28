# Verification Contract

## Definition of success

An upload is successful only when all applicable checks pass:

1. Local source exists and the requested build/test process completed.
2. Local artifact size and SHA-256 were recorded before upload.
3. Every part has an independent size, SHA-256, and MD5 record.
4. Multipart files reassemble locally to the final artifact SHA-256.
5. The provider confirms the final remote object is complete.
6. Remote size equals local size.
7. Remote provider digest equals the local digest when provided.
8. If no cryptographic remote digest is available, a complete authenticated re-download hashes to the local SHA-256.
9. The returned link is observed from the provider response or readback.
10. Access permissions were checked and described accurately.

## Provider-specific evidence

### Google Drive

Require:

- upload result with file ID;
- metadata readback;
- exact `size` match;
- `md5Checksum` match for binary files when available;
- observed `webViewLink` or `webContentLink`;
- explicit permission result when sharing was requested.

### GitHub Release

Require:

- release ID and repository;
- asset state `uploaded`;
- exact asset size;
- `digest` equal to `sha256:<local hash>` when returned;
- otherwise a full authenticated download and SHA-256 comparison;
- observed `browser_download_url`;
- final release readback after draft publication.

### Generic HTTPS host

Require:

- a 2xx upload response;
- extracted download URL;
- remote `Content-Length` match plus provider digest, or full re-download SHA-256;
- authenticated verification when the download is private.

## Multipart rules

- Use zero-padded sequential names starting at `.part000`.
- Never omit an empty or final short part from the manifest.
- Upload parts sequentially when a connector is fragile.
- Keep reassembly helpers beside the parts.
- Include final artifact SHA-256, not only per-part hashes.
- Never call a directory of parts a completed artifact until reassembly verification passes.

## Reporting rules

Never say:

- "uploaded" when only a local file exists;
- "public" when the object is private or merely shared to one account;
- "verified" when only the HTTP response code was checked;
- "complete project" when the archive contains only scripts, manifests, patches, or recovery instructions.
