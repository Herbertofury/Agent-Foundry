# Catalog UI/UX Standard

## Information architecture

Default primary surfaces:

1. Home / dashboard
2. Browse / all items
3. Gallery
4. Saved / favorites
5. Compare
6. Sources / sync health
7. Browser workspace
8. History / previous editions when relevant

The exact navigation can adapt, but the user should never lose where they are in the catalog versus the live web.

## Search

Provide instant full-dataset search across at least:

- name and aliases;
- author;
- tags/categories/collections;
- platform/edition/version/loader/type/status;
- notes/why/evidence where practical;
- provider/source names.

Recommended structured queries:

- `score>=9`
- `rank<=25`
- `author:name`
- `tag:aquatic`
- `provider:modrinth`
- `edition:bedrock`
- `loader:forge`
- `scour:4`
- quoted exact phrases.

Show active query/filter tokens and make each removable.

## Browse views

At minimum support:

- card view;
- sortable table view;
- gallery view when media exists.

Recommended:

- compact density toggle;
- saved view presets;
- column chooser in table mode;
- multi-select batch open/compare/export.

## Detail view

Project/item detail should show:

- title and project icon;
- author/avatar;
- rank/score and component breakdown;
- why/summary;
- tags/categories/versions/loaders/status;
- verified provider homes;
- `Open here` for in-app browser;
- `Open in your browser` sibling action;
- copy URL;
- full gallery;
- source provenance;
- cautions/evidence;
- user notes and favorite state.

## Persistent QoL

Persist locally when permitted:

- favorites;
- notes;
- theme;
- saved filters/views;
- browse sort/view mode;
- last selected item;
- browser tabs/session state where designed.

Storage denial/corruption must never prevent the app from launching. Fall back to memory-only behavior and report persistence as unavailable.

## Compare

Support 2-4 items by default. Compare fields that actually help a decision: score/rank, platform, versions, loader, status, variety/depth/polish/freshness, sources, cautions, and user notes.

Do not show an empty compare tray or modal.

## Accessibility

- visible keyboard focus;
- semantic controls and labels;
- logical tab order;
- Escape closes transient overlays/modals;
- reduced-motion mode;
- color is not the only state signal;
- alt text for useful images;
- sufficient contrast;
- touch targets suitable for compact screens in the web snapshot.

## Responsiveness

The portable HTML must be usable on narrow screens. The desktop app should adapt down to a reasonable minimum window size without covering browser controls or leaving fixed overlays on top of results.
