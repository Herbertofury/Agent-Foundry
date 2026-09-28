# Release QA Standard

## Data acceptance

Verify:

- expected record count;
- unique stable IDs;
- no accidental duplicate projects after normalization;
- all required names/links present;
- score/rank numeric types and ranges;
- source/scour/category counts reconcile with canonical source;
- build metadata source hashes/revisions are current;
- no formula-error tokens imported as data.

Run `scripts/validate_catalog.py` against the final normalized JSON.

## Link acceptance

For every source URL:

- parses as an allowed protocol;
- is the exact entity URL when known;
- provider label matches destination;
- no generic homepage/search link is presented as exact project navigation;
- external-browser action receives the exact active URL.

For current/researched web destinations, sample live validation using authoritative provider pages. Avoid brute-force web requests that trigger rate limits.

## Media acceptance

Verify:

- image bytes decode;
- role classification is correct;
- content-hash dedupe works;
- missing images have non-broken fallback UI;
- author avatar and project icon are not swapped;
- hover/focus zoom appears and dismisses cleanly;
- lightbox navigation and source attribution work;
- no generated imagery was introduced without explicit current-turn permission.

## Catalog interaction matrix

Exercise the actual production build:

- basic search;
- quoted search;
- numeric query;
- category/tag/provider filters;
- reset filters;
- each view mode;
- each sort mode;
- favorites add/remove and restart persistence;
- notes edit and restart persistence;
- compare add/remove/open/clear;
- export;
- saved/deep-link view if present;
- theme;
- keyboard shortcuts;
- help/source-center navigation;
- mobile/narrow portable HTML layout.

## Browser interaction matrix

Exercise at least two real HTTPS sites plus one controlled local/fixture destination where possible:

- open project `here`;
- same URL via `Open in your browser` action;
- back / forward;
- reload / stop;
- address navigation;
- new tab;
- close and reopen closed tab;
- target-blank/new-window becomes a controlled new tab;
- find in page;
- zoom controls;
- tab title/favicons;
- session/cookie persistence if the test site permits;
- download start/completion or truthful download failure;
- permission prompt path;
- navigation error/retry path;
- blocked non-http(s) scheme path;
- restart/session restore.

## Runtime evidence

A build passes only when the exact packaged artifact is launched and the changed workflow is exercised. Syntax/lint/unit tests are necessary but not sufficient.

Inspect renderer/main-process logs and browser console for uncaught errors. One dead primary control fails release acceptance.
