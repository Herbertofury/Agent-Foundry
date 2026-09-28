# Research + Retrieval Fast Path

Load only for broad web research, file-library sweeps, recommendation catalogs, or repeated requests to search again without losing breadth.

## Coverage ledger

Freeze the requested coverage dimensions before repeated search waves: topic/entity classes, platforms/sources, versions/time windows, regions, formats, and explicit exclusions. Keep a normalized ledger of discovered entities and canonical URLs/IDs so alternate spellings or mirror links do not trigger duplicate investigation.

## Frontier search

1. Batch diverse, non-overlapping queries across uncovered coverage dimensions early.
2. Deduplicate entities/sources before opening or following them.
3. Use returned snippets/metadata directly when the governing tool permits and they already establish the needed fact; open/fetch only when stronger evidence, context, or exact details are required.
4. Follow high-value evidence gaps in parallel where independent.
5. In later waves, query only unresolved dimensions or ambiguity clusters instead of rerunning the same broad searches with cosmetic wording changes.
6. For exhaustive intent, continue until planned coverage dimensions are addressed and additional gap-directed waves stop producing material new relevant entities/evidence. State any unavoidable external-search completeness limits honestly; never impose an arbitrary result cap.

## File retrieval

- Use semantic search first for unknown locations; exact find/read only after the relevant file/range is known.
- Read the smallest contiguous range that fully answers the question; follow explicit continuation pointers instead of restarting.
- Materialize only when raw bytes are needed for code, conversion, or mutation.
- Reuse file IDs, ranges, versions, and response resources already returned.

## Recommendation/catalog work

Track each candidate by canonical identity plus source URL/ID, not display name alone. Merge duplicates before ranking. Preserve every qualified candidate for comprehensive requests; optimize by reducing rediscovery, not by shrinking the catalog.
