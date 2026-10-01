# Wiki Publishing

The <code>wiki/</code> directory on <code>main</code> is the version-controlled source mirror for this GitHub Wiki.

The <code>Publish Wiki</code> GitHub Actions workflow mirrors these Markdown pages to the repository's <code>.wiki.git</code> backend.

## First-time bootstrap
GitHub creates the Wiki Git backend only after an initial Wiki page exists. Agent Foundry therefore treats a missing Wiki as **unfinished work**, not as a reason to fall back to the repo-side mirror. The executing agent must create/bootstrap the first page through an authorized supported route (for example, the GitHub Wiki UI when browser control is available), establish <code>Home</code>, then rerun publication. After that, <code>wiki/</code> remains the canonical source and automation owns synchronization.

## Why this exists
Keeping Wiki source in the main repository gives us:
- reviewable diffs;
- branch/commit history;
- validation;
- one canonical source;
- automatic publishing;
- no invisible drift between documentation and governance.


## Live-publication acceptance

The source mirror is only half of the contract. A Wiki update is accepted only when:
- the canonical page changes are committed on the intended source lineage;
- the Publish Wiki workflow succeeds;
- the workflow re-clones the live <code>.wiki.git</code> backend and byte-compares the published pages against <code>wiki/</code>;
- required pages such as <code>Home.md</code> and <code>_Sidebar.md</code> are present;
- a missing Wiki backend is surfaced as unresolved bootstrap work rather than silently ignored.

This prevents a broken or stale chat from being the only place where documentation progress exists and prevents the repository mirror from drifting away from what readers actually see on GitHub.
