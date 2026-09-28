# Repair Mark v2 Visual Identity

## Purpose

Make repaired Minecraft mods instantly recognizable without changing their compatibility identity or gameplay behavior. This is a deterministic artwork-compositing convention, not image generation.

## Hard default

For every shippable repaired mod JAR, compatibility JAR, or repair companion that can expose an icon safely:

1. Resolve the exact upstream project and its current official storefront artwork.
2. Preserve/download the highest-quality official project avatar/card artwork from an official CurseForge or Modrinth project/API/CDN source.
3. Keep the full recognizable artwork intact; do not crop away important content, redraw it, or substitute unrelated/historical art when the current storefront art is available.
4. Apply Repair Mark v2: a clearly visible red double frame/corner treatment plus a red verified check mark while keeping the underlying art recognizable, including at roughly 48x48 launcher/mod-list size.
5. Use the marked art as the repaired artifact's embedded display icon only when that resource can be changed safely; otherwise ship it as a sidecar/launcher badge.
6. Preserve the original unmarked repair baseline so marker-only verification is possible.

Do not invoke image generation for this workflow. Use the real official artwork and deterministic image compositing.


## Completion gate — mandatory, no deferral

Repair Mark v2 is a **closeout requirement**, not a best-effort decoration. Every shippable repaired mod JAR, compatibility JAR, or repair companion must finish in one of these states:

- `embedded` — a verified marked icon is embedded and marker-only diff proves no unrelated byte changes; or
- `sidecar/launcher-mapping` — a verified marked PNG is delivered separately and bound to the exact repaired JAR hash in a launcher/badge mapping.

`deferred`, `not run`, omitted visual identity, or "no `logoFile`" are **not valid completed states**. Use this decision table:

| Condition | Required result |
| --- | --- |
| Real declared icon exists, archive is unsigned/safe to mutate | Embed after gameplay verification, then prove marker-only diff |
| `mods.toml`/loader metadata has no `logoFile` or equivalent | **Mandatory sidecar/launcher mapping**; do not add loader metadata just for branding |
| Archive is signed or icon/resource mutation is unsafe | **Mandatory sidecar/launcher mapping** |
| Launcher/store card uses external artwork | Keep JAR identity unchanged and provide **sidecar/launcher mapping** |
| Current storefront bytes cannot be fetched, but exact upstream-authored art from the exact official release is proven | Use that exact upstream-authored art, record storefront URL/project identity and `remote_cdn_byte_hash_verified=false`, then still produce the mark |
| No trustworthy official-art basis can be established at all | Keep repair outcome `partial`; state the visual-identity blocker; do not claim completed closeout |

Before delivery, run `scripts/repair_mark_gate.py <repair-record.json>`. A nonzero exit means the repair is not closeout-complete.

## Official artwork resolution

Prefer exact project identity over visual guessing.

- Resolve CurseForge project/file IDs and/or Modrinth project/version IDs from known project pages, metadata, or exact current primary sources.
- Prefer the official platform project avatar/card image URL. Use the highest-resolution official source exposed by the platform when available.
- If CurseForge and Modrinth use different official artwork, prefer the art recognizable in the user's launcher/project card and record the alternate official source too.
- Never use arbitrary image-search results, fan art, gallery images, logos from unrelated pages, or a screenshot crop when an official project image is obtainable.
- Never synthesize a replacement logo merely because upstream art is inconvenient to fetch.

Record the canonical project URL(s), project/file/version IDs when known, artwork URL, source dimensions, and SHA-256 of the normalized unmarked artwork.

## Repair Mark v2 treatment

Use `scripts/apply_repair_mark.py` as the deterministic reference implementation when Pillow is available.

The mark must:

- use a red outer double-frame treatment;
- use red corner brackets so the repaired state remains legible when the icon is small;
- include a red verified check badge;
- avoid covering the main subject more than necessary;
- preserve transparency where practical;
- avoid altering the source artwork other than scaling/letterboxing needed to fit the icon canvas and adding the repair mark.

Visually inspect a downscaled 48x48 copy before shipping. The original project should remain immediately recognizable and the repair mark should still be visible.

## JAR integration safety

Apply the visual mark only after the gameplay repair has a verified unmarked baseline.

1. Determine the actual display-icon resource from loader metadata (`logoFile`/equivalent) or the established `pack.png` convention; do not assume blindly.
2. Check archive signatures before changing any resource.
3. If modifying the icon would invalidate a signature or otherwise make the artifact unsafe, do not modify the JAR. Keep the repaired JAR byte-for-byte as verified and ship the marked PNG plus launcher/project-side mapping instead.
4. If embedding is safe, replace only the resolved icon entry in the already-verified repaired JAR.
5. Compare the marked JAR against the unmarked repaired baseline. The marker-only diff must change only the icon entry; gameplay classes/resources, loader metadata, manifest, mod ID/version, registry IDs, and network identity must remain unchanged.
6. Re-run ZIP integrity after marking.

The repair mark must never be implemented by changing internal mod ID, advertised mod version, display identity fields, registry IDs, or protocol identifiers.

## Launchers and external cards

CurseForge/Modrinth launcher cards may use platform/cache artwork instead of the embedded JAR icon. Do not claim the launcher card changed merely because `pack.png` changed.

When launcher-side integration is part of the workflow, keep a `repair-badge-registry.json`-style mapping containing the target mod ID, exact repaired JAR hash, CurseForge project/file IDs, Modrinth project/version IDs, official artwork URL/hash, and marked artwork path/hash. Use that mapping to render the same Repair Mark v2 around the external storefront art without changing mod compatibility identity.

For a repair companion/additive patch JAR, the marked icon may use the official artwork of the mod it repairs, but the companion's own loader identity must remain truthful. For a bundle spanning multiple unrelated mods, use a bundle-level repair badge rather than pretending the bundle is one upstream mod.

## Repair Brain record

For every shippable repaired JAR, store a `visual_identity` or `storefront_identity` object. The gate requires this even when integration is sidecar-only. Example:

```json
{
  "policy": "repair-mark-v2",
  "official_source": "curseforge|modrinth",
  "curseforge_project_id": null,
  "curseforge_file_id": null,
  "modrinth_project_id": null,
  "modrinth_version_id": null,
  "canonical_art_url": "https://...",
  "source_dimensions": [800, 800],
  "normalized_art_sha256": "...",
  "marked_art_sha256": "...",
  "embedded_icon_entry": "pack.png",
  "integration": "embedded|sidecar|launcher-mapping",
  "marker_only_diff": "PASS"
}
```

Also record the unmarked repaired JAR hash and final marked repaired JAR hash when they differ.

## Performance invariant

Repair Mark v2 adds no runtime code, event hooks, threads, polling, rendering hooks, or gameplay logic. It is static artwork only. Do not accept any visual-mark implementation that adds runtime work merely to show the repaired state.


## Regression rule

When a repair supersedes or rebuilds an earlier repaired artifact, carry forward the prior validated visual identity unless the upstream project artwork changed. Rebinding is not optional: update the repaired filename/hash in the badge registry and include the sidecar/preview artifacts in the new repair record. A new gameplay/classfile replacement must never silently drop a previously valid Repair Mark.
