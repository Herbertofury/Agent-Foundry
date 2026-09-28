# Canonical Source Model

## Goal

Merge structured and narrative artifacts into one searchable app model without losing provenance or creating a new shadow source of truth.

## Source roles

Classify each source before extraction:

- **Canonical structured source**: usually the master Sheet/XLSX/CSV. Owns rows, scores, ranks, categories, status, direct project URLs, and sortable fields.
- **Narrative source**: Doc/DOCX/Markdown. Adds explanations, editorial guidance, workflows, notes, and long-form context.
- **Fixed publication source**: PDF. Useful for provenance, visual/reference reading, or a stable edition; do not treat rendered PDF text as more authoritative than a newer editable source unless the project says so.
- **Remote project source**: exact CurseForge/Modrinth/GitHub/official/etc. URLs.
- **Media source**: verified project icon, gallery image, author avatar, screenshot, diagram, or other source-grounded visual.

When sources conflict, resolve using explicit project authority, stable file ID/revision, current user edits, and evidence. Never choose solely by newer timestamp.

## Normalized catalog

Recommended top-level shape:

```json
{
  "schemaVersion": 1,
  "catalogId": "stable-id",
  "title": "Project Catalog",
  "generatedAt": "ISO-8601",
  "sources": [],
  "build": {},
  "facets": {},
  "items": []
}
```

### Item fields

Use only fields that exist or can be truthfully derived, but prefer:

- `id`: collision-proof stable ID. Prefer explicit row/project ID; otherwise derive from source file ID + stable row identity + canonical URL hash. Never use display-name slug alone.
- `name`
- `aliases`
- `summary`
- `why`
- `score`
- `rank`
- component scores such as `variety`, `depth`, `polish`, `freshness`
- `categories`
- `collections`
- `tags`
- `platforms`
- `editions`
- `versions`
- `loaders`
- `type`
- `status`
- `scour` / generation / batch metadata
- `authors`
- `sources`
- `gallery`
- `cautions`
- `evidence`
- `notesFromSource`
- `provenance`

### Source link fields

```json
{
  "provider": "Modrinth",
  "label": "Modrinth",
  "url": "https://modrinth.com/mod/...",
  "kind": "project",
  "verified": true,
  "lastChecked": "ISO-8601"
}
```

`verified` means the destination has been checked as the intended entity, not merely that the URL parses.

### Author fields

```json
{
  "name": "Creator",
  "url": "https://.../creator",
  "image": "asset://author/...",
  "provider": "CurseForge"
}
```

### Gallery fields

```json
{
  "id": "media-id",
  "src": "asset://gallery/...",
  "thumbnail": "asset://thumb/...",
  "alt": "Meaningful description",
  "sourceUrl": "https://...",
  "credit": "Provider/author",
  "kind": "project-gallery",
  "verified": true
}
```

## Provenance

Every important field should remain traceable. Keep compact provenance references rather than copying entire documents.

Examples:

- `Master Index!A42:W42`
- `Recommendations doc / Aquatic / River Fishing`
- `PDF page 71`
- remote provider project URL

## Source hashes

Record source identity and revision/hash in build metadata. Hash raw bytes for local/raw artifacts. For native cloud docs/sheets, preserve stable provider file ID plus exported-content hash or provider revision ID when available.

Only rebuild changed source slices when the architecture permits reliable delta processing.
