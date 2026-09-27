# Wiki Publishing

The <code>wiki/</code> directory on <code>main</code> is the version-controlled source mirror for this GitHub Wiki.

The <code>Publish Wiki</code> GitHub Actions workflow mirrors these Markdown pages to the repository's <code>.wiki.git</code> backend.

## First-time bootstrap
GitHub requires the Wiki backend to exist before automation can clone it. If the first publish run reports that the wiki repository does not exist, create one temporary page in the GitHub Wiki UI once, then rerun the workflow. After that, <code>wiki/</code> remains the canonical source and the automation owns synchronization.

## Why this exists
Keeping Wiki source in the main repository gives us:
- reviewable diffs;
- branch/commit history;
- validation;
- one canonical source;
- automatic publishing;
- no invisible drift between documentation and governance.
