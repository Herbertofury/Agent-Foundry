# Feature Foundry Asset Intelligence

**Verified:** 2026-08-04T00:00:00Z
**Review due:** 2026-11-04

This document is generated from the machine-readable source-hub and object-intelligence catalogs. It is a capability and design registry, not a promise that every adapter is already implemented.

## Source capability matrix

| Source | Media | Preferred route | Status | Auth / access | Rights and attribution | Fallback |
|---|---|---|---|---|---|---|
| Openverse | images, audio | `public_api` | `active` | No auth required for ordinary public search; authenticated clients may receive higher limits. | Only import media whose license and downstream use fit the project. Preserve creator, source, license and attribution fields. | Open the source page or browser clipper when direct import is unavailable. |
| Wikimedia Commons | images, audio, video, 3d | `public_api` | `active` | Public MediaWiki APIs; authenticated editing is separate. | Reuser is responsible for verifying each file license and any non-copyright restrictions. Preserve author, source page, license template, attribution and modification requirements. | Open the Commons file page when rights metadata is incomplete. |
| Flickr | images, video | `official_api` | `active` | API key for public search; OAuth for private/user actions. | Use license filters and do not infer reuse rights from visibility. Preserve owner, title, source URL and license. | Browser clipper or manual URL import. |
| Unsplash | images | `official_api` | `restricted` | Access key; OAuth for user actions. Demo and production modes differ. | Follow API terms; do not replicate the core Unsplash experience. Required Unsplash attribution and API usage links must remain visible. | Browser clipper or source-page import with rights review. |
| Pexels | images, video | `official_api` | `active` | API key. | Use only under the Pexels API and content license terms. Credit Pexels and photographers where required/recommended. | Browser clipper or manual import. |
| Pixabay | images, illustrations, vectors, gif, video, audio | `official_api` | `active` | API key. | Follow Pixabay content license and API restrictions for each asset. Show Pixabay source attribution in search experiences. | Browser clipper or manual import. |
| Poly Haven | 3d, hdris, textures | `public_api` | `active` | No account required for public API; send a distinct User-Agent. | Assets are CC0; still preserve source and authorship metadata. Credit the API service as requested even though assets are CC0. | Direct website download/manual import. |
| Sketchfab | 3d | `oauth_api` | `active` | OAuth required for downloadable model access; public search has documented API routes. | Only download models marked downloadable and comply with the selected license. Preserve creator, model page and license attribution. | Open model page or manual GLB/glTF import. |
| Fab | 3d, materials, audio, plugins | `launcher` | `restricted` | Epic/Fab account through official launcher or website. | Respect Fab Standard/CC/other listing-specific licenses and seat/tier terms. Preserve seller, listing, license tier and source URL. | Manual import from an authorized Fab download. |
| Pinterest | images, video, boards | `browser_clipper` | `restricted` | Approved Pinterest app and user OAuth for documented account/board operations. | Do not treat Pinterest discovery as proof of reuse rights; follow the original source license. Preserve Pin, creator/site and source-link attribution. | Browser clipper is the default for arbitrary inspiration discovery. |
| DeviantArt | images, animation, literature | `oauth_api` | `active` | OAuth 2.0; scopes vary by browse, collections and user actions. | Do not infer download/reuse rights; preserve artist terms and source flags. Preserve artist, deviation page and any display requirements. | Browser clipper/manual source import. |
| Tumblr | images, gif, video, audio, text | `official_api` | `active` | API key for public endpoints; OAuth for user/private actions. | Respect copyright and post-specific permissions; visibility is not a reuse license. Preserve blog, post URL, creator and reblog/source chain. | Browser clipper/manual import. |
| Bluesky / AT Protocol | images, gif, video, posts | `public_api` | `active` | Many public AppView endpoints require no auth; user actions require authenticated sessions. | Visibility is not a reuse license; preserve source context and creator information. Preserve DID/handle, post URI, source URL, alt text and embed metadata. | oEmbed or browser clipper. |
| X | images, gif, video, posts | `browser_clipper` | `restricted` | Official API enrollment and an applicable paid/access plan; oEmbed for supported public posts. | Do not scrape private/internal endpoints or treat posts as reusable assets without permission. Preserve author, post URL and source context. | Browser clipper or oEmbed when API access is unavailable. |
| Reddit | images, gif, video, posts | `official_api` | `restricted` | OAuth/application identity for API usage. | Do not treat a post as a reusable-license grant; follow original source rights. Preserve subreddit, post, author and original linked source. | Browser clipper/manual source import. |
| Imgur | images, gif, video | `official_api` | `restricted` | Client ID for anonymous/public access; OAuth for account operations. | Do not assume upload or gallery visibility grants reuse rights. Preserve account/gallery/post URL and source context. | Browser clipper/manual import if API enrollment changes. |
| GIPHY | gif, stickers, clips | `official_api` | `active` | API key; beta and production keys have different review and quotas. | Use only through approved API terms; preserve creator/source metadata. Display Powered by GIPHY and provider attribution as required. | Manual GIF/WebP/video import or another approved GIF source. |
| Tenor | gif, stickers | `legacy_existing_clients` | `legacy_existing_clients` | Existing approved clients only; new API clients are no longer accepted. | Do not build a new dependency on unavailable enrollment. Retain Tenor attribution and content descriptions where required. | Use GIPHY, Openverse, Wikimedia, Imgur, Tumblr, or manual user import. |
| Are.na | images, links, text, channels | `browser_clipper` | `verify_before_enable` | OAuth/current API credentials if the current v3 developer route is available. | Treat blocks as references unless source rights permit import. Preserve channel, block, creator and source URL. | Browser clipper/manual import is the safe default. |
| ArtStation | images, animation, 3d, projects | `browser_clipper` | `clipper_only` | No verified general public developer API is assumed. | Do not download beyond user-authorized browser access; preserve NoAI and artist terms. Preserve artist, project URL, original source and NoAI metadata. | Manual download/import with provenance. |
| Behance | images, video, projects | `browser_clipper` | `clipper_only` | No general Asset Vault discovery API is assumed. | Treat as inspiration until rights are explicitly cleared. Preserve creator, project and source URL. | Manual authorized import. |
| Dribbble | images, animation, projects | `browser_clipper` | `clipper_only` | Do not assume new public API enrollment without current verification. | Treat as reference unless licensed or creator-authorized. Preserve designer, shot and source URL. | Manual authorized import. |
| Instagram | images, video, reels, posts | `browser_clipper` | `restricted` | Official Meta APIs apply to supported user/business content; not a general public scraping API. | Never scrape private endpoints or bypass login; import only user-authorized content. Preserve account, post and source URL. | oEmbed or browser clipper/manual import. |
| Pixiv | images, animation, manga | `browser_clipper` | `clipper_only` | No verified stable public developer API is assumed. | Follow creator permissions and Pixiv terms; do not scrape internal APIs. Preserve artist, work ID, page URL and tags. | Manual import. |
| Cara | images, animation, portfolio | `browser_clipper` | `clipper_only` | No verified public developer API is assumed. | Treat as reference unless creator-authorized/licensed. Preserve creator and post URL. | Manual import. |
| Cosmos | images, links, collections | `browser_clipper` | `clipper_only` | No verified general public API is assumed. | Treat as inspiration references unless rights are cleared. Preserve collection/source URL and original source. | Manual import. |
| Savee | images, collections | `browser_clipper` | `clipper_only` | No verified general public API is assumed. | Treat as inspiration references unless rights are cleared. Preserve collection/source URL and original source. | Manual import. |

### Adapter contract

- Use only documented provider capabilities
- Preserve source URL, creator, license and provider metadata
- Respect rate limits, attribution, moderation labels and cache rules
- Provide a clipper or manual fallback when discovery APIs are unavailable
- Never scrape private endpoints or invent an API
- Revalidate provider status before shipping an adapter

## Progressive object quality lanes

### instant-preview
- **Target:** interactive seconds
- **Purpose:** Produce a truthful cutout, animated sticker, layered card or rough proxy immediately without pretending it is finished 3D.
- **Promotion gate:** User can inspect uncertainty and request a better lane.

### interactive-draft
- **Target:** bounded background job
- **Purpose:** Create editable parts, depth/material hints, collision, pivots, sockets, affordances and optional draft mesh.
- **Promotion gate:** Geometry, materials, animations and behavior suggestions pass user review.

### high-fidelity
- **Target:** explicit queued job
- **Purpose:** Create the strongest available mesh/PBR/rig/LOD/collision result with deterministic export and full provenance.
- **Promotion gate:** Fresh import validation, visual comparisons and runtime performance budgets pass.

## Reversible derivation graph

1. **Preserve immutable original** (`preserve-original`) — content hash, source record, rights record, metadata snapshot
2. **Probe, validate and isolate** (`probe-and-sanitize`) — format report, dimensions, frame/scene inventory, security warnings
3. **Propose subjects and parts** (`subject-proposals`) — open-vocabulary boxes, object candidates, part candidates, uncertainty map
4. **Segment still or temporal masks** (`segmentation`) — editable masks, alpha mattes, occlusion order, tracked masks
5. **Choose simplest truthful representation** (`representation-selection`) — sticker, animated sticker, layered parallax, billboard, mesh card, reconstructed mesh, native 3D
6. **Infer depth and geometry** (`depth-and-geometry`) — depth map, normal hints, point cloud, draft mesh, backside uncertainty
7. **Infer editable materials and lighting separation** (`material-and-lighting`) — material regions, PBR hints, delighted texture, transparency classification
8. **Build part and affordance graph** (`part-affordance-graph`) — parts, joints, surfaces, handles, seats, screens, switches, containers, mascot affordances
9. **Create spatial contract** (`spatial-contract`) — baseline, pivot, scale hypothesis, orientation, sockets, snap planes, safe interaction lanes
10. **Generate editable physics proxies** (`physics-and-collision`) — colliders, mass/material hints, sensors, break states, grabbable zones
11. **Preserve or author motion** (`animation-and-loops`) — frame timing, loop policy, clips, rig suggestions, idle/reaction states
12. **Map object into theme behavior genome** (`theme-behavior-genome`) — material response family, interaction verbs, audio family, lighting response, mascot interactions, theme overrides
13. **Generate runtime variants** (`optimization`) — GLB, meshopt compression, KTX2 textures, LODs, thumbnail, silhouette, hit mask, shadow proxy
14. **Validate truth, quality and performance** (`validation`) — visual diff, metadata preservation report, collision test, animation fidelity test, device-tier budget
15. **Publish with complete lineage** (`publish-lineage`) — object manifest, derivation graph, tool/model versions, rights/attribution, editable source links

## Candidate tool and runtime registry

| Tool | Role | Status | Maturity | Key constraints / fallback |
|---|---|---|---|---|
| Grounded SAM 2 | Open-vocabulary detection plus image/video segmentation and tracking. | `candidate` | `active-research` | GPU/VRAM requirements vary; Predictions need editable review; Not a rights classifier; fallback: SAM 2.1 promptable masks; manual brush/point/box segmentation |
| Depth Anything V2 | Monocular depth and relative-layer inference. | `candidate` | `mature-research` | Single-view scale/backside ambiguity; depth is not collision-ready geometry; fallback: manual depth layers; simple foreground/midground/background planes |
| SPAR3D | Single-image editable 3D reconstruction with intermediate point cloud. | `candidate` | `research-grade` | Single-view uncertainty remains; GPU and model footprint; not every asset should become a mesh; fallback: Stable Fast 3D; TripoSR; layered or billboard representation |
| Stable Fast 3D | Fast single-image mesh, UV and material draft generation. | `candidate` | `research-grade` | Quality varies with topology and occlusion; needs geometry/material review; fallback: SPAR3D; TripoSR; billboard proxy |
| TRELLIS.2 | High-fidelity image-to-3D generation with complex topology and PBR-oriented output. | `candidate` | `research-grade` | Large model footprint; high-quality lane only; requires strong GPU and post-validation; fallback: Hunyuan3D 2.1; SPAR3D; Stable Fast 3D |
| Hunyuan3D 2.1 | High-fidelity shape and PBR texture synthesis. | `candidate` | `research-grade` | License review required; GPU-heavy; needs deterministic cleanup/optimization; fallback: TRELLIS.2; SPAR3D; manual Blender refinement |
| TripoSR | Fast single-image 3D fallback. | `candidate` | `research-grade` | Older quality ceiling than newer high-fidelity systems; requires mesh cleanup; fallback: Stable Fast 3D; billboard or layered representation |
| Blender 4.5 LTS | Isolated headless .blend inspection, semantic extraction, conversion and deterministic editing. | `recommended` | `production` | Never parse .blend directly in the runtime; disable auto-execution; sandbox files/process/time/memory/output; fallback: Ask user to export GLB/glTF; manual Blender conversion |
| meshoptimizer / gltfpack | glTF optimization, simplification, quantization and mesh compression. | `recommended` | `production` | Must preserve named nodes/extras required by object intelligence; quality settings need tests; fallback: Blender glTF export optimization; uncompressed GLB fallback |
| Basis Universal / KTX2 | GPU texture compression and mip-chain generation. | `recommended` | `production` | Choose UASTC/ETC1S and color/alpha settings correctly; retain editable source derivatives; fallback: PNG/JPEG/EXR derivatives |
| CoACD | Collision-aware convex decomposition for editable physics proxies. | `candidate` | `production-capable` | Must cap complexity and runtime; visual mesh is not default collider; fallback: primitive/compound authored colliders; Blender convex hulls |
| Rapier | Event-driven 2D/3D physics and sensor runtime for living object behavior. | `recommended` | `production` | Only enable events needed by authored behaviors; fixed-step and bounded wake-up required; fallback: simple tween/WAAPI behavior in reduced or safe modes |
| Rive | State-machine-driven vector/UI object behavior with data binding and observability. | `candidate` | `production-capable` | Do not require proprietary authoring for all assets; keep open fallback formats; fallback: Lottie/WAAPI/Pixi authored states |
| PixiJS | 2D object, sticker, mascot and particle runtime. | `recommended` | `production` | Must share authoritative scheduler and suspend hidden worlds; fallback: DOM/WAAPI safe mode |
| ONNX Runtime | Local inference host for segmentation, classification, material and affordance models. | `recommended` | `production` | Avoid GPU contention with live renderer; explicit warm-up/cancel/teardown; fallback: provider-specific native inference; manual processing |

## Runtime rules

- Use one authoritative command/event bus and one frame scheduler; do not start per-object endless loops.
- Objects settle into stable states and retain bounded material memory rather than snapping back to a generic idle clip.
- Every generated claim carries visible uncertainty, provenance, tool/model version and an editable override.
- User input preempts simulation immediately; import/conversion jobs remain cancellable and resume safely.
- No generated geometry, rights metadata, material, rig, socket or affordance is silently presented as verified truth.
