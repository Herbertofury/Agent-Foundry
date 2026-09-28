# Failure Intelligence, Resolution, and Completeness Standard

**Status:** Binding cross-domain engineering and live-execution policy.

This policy exists to prevent search misses from becoming false absence claims, blockers from becoming closeout excuses, incomplete external extraction from being reported as complete, and solved failures from recurring as if they were new.

# F001 - Unknown Is Not Absent

A failed route does not prove nonexistence.

Use exactly these evidence states for existence/availability questions:

- `present` - positive evidence identifies the requested thing;
- `absent-proven` - authoritative evidence or convergent complete coverage proves it is absent from the claimed scope;
- `unresolved-active` - current routes have not yet resolved the question and work must continue.

The following produce `unresolved-active`, not `absent-proven`, unless independent evidence closes the gap:

- search returned zero results;
- one provider does not list it;
- a page/API is inaccessible, rate-limited, logged out, blocked, unavailable, or timed out;
- a parser/selector did not find the field;
- a file/listing connector did not surface the expected item;
- a cache/index is missing the record;
- a name/version/author lookup failed;
- a route returned an empty page, challenge page, error document, or partial response.

Before claiming absence, use the strongest relevant alternate routes: authoritative metadata, direct known URLs/IDs, source repositories, alternate providers, authenticated views, embedded page data, release assets, local/cached artifacts, project history, provider APIs, and other independent evidence appropriate to the task.

**Acceptance:** Could another valid route still reveal the requested thing? If yes, the state is unresolved-active, not absent.

# F002 - Blockers Are Never Closeout States for Required Work

A blocker is a routing state, not a completion state.

When required work is unresolved, continue the escalation ladder instead of closing out:

1. reuse a previously verified recovery recipe;
2. repair the environment, dependency, auth/session, cache, DNS/network, runtime, build, permissions, or tooling layer;
3. install/provision a missing capability or use a capable equivalent;
4. change transport, provider, endpoint, browser/API/connector path, build lane, runtime lane, or source route;
5. inspect source/artifact/state directly when an abstraction is the failing layer;
6. build a shim, adapter, compatibility patch, parser, migration, or local tool when existing tooling is insufficient;
7. restructure the implementation or verification route around the causal constraint;
8. preserve the exact checkpoint and continue from the next executable recovery action after any execution-window interruption.

Do not convert `could not fetch`, `could not find`, `site blocked`, `tool missing`, `network failed`, `parser failed`, `runtime unavailable`, `permission/path issue`, or `first approach failed` into a completed response when the acceptance item remains required.

**Acceptance:** Is the requested result actually resolved with evidence? If no, the task remains active and must take another materially different recovery route.

# F003 - External Completeness Must Be Proven, Not Assumed

Any claim that external content is complete, exhaustive, all-inclusive, or fully synchronized requires explicit completeness evidence.

Track at minimum when applicable:

- expected count, if authoritative or discoverable;
- discovered count;
- accepted/normalized count;
- rejected count plus reasons;
- unresolved count;
- pages/cursors traversed and terminal-pagination proof;
- tabs, carousels, lazy-loaded regions, alternate layouts, embedded JSON, APIs, authenticated-only surfaces, and other relevant content surfaces;
- deduplication/identity rules;
- provider/source identity and freshness.

A sample, first page, first N results, visible viewport, partial carousel, or one provider is never silently equivalent to the complete logical result.

When expected count is unknown, completeness requires traversal/terminal evidence for every applicable surface plus zero unresolved gaps.

Use `scripts/completeness_gate.py` for machine-checkable evidence when practical.

**Acceptance:** Can every discovered/expected item be accounted for as accepted or explicitly rejected, with zero unresolved items and terminal coverage proven?

# F004 - Never Suffer the Same Failure Twice

A verified hard-won recovery becomes reusable engineering knowledge immediately.

Before treating a failure as new:

1. fingerprint the failure using its strongest stable signature plus relevant environment/target identity;
2. query the current recovery/incident ledger for the same or equivalent signature;
3. reuse the verified recovery recipe first when its applicability still matches;
4. if the recipe no longer applies, identify the invalidator and update/supersede the recipe rather than discarding the history;
5. after the new resolution is proven, promote the stronger recipe as the new baseline.

The next occurrence of a solved failure should be faster, more deterministic, and require less rediscovery.

Examples include DNS/resolver failures, Gradle/JDK/toolchain issues, corrupted caches, launcher assets, OAuth/session expiry patterns, provider HTML/API drift, renderer/linkage problems, dependency resolution, packaging errors, and recurring runtime signatures.

**Acceptance:** Did the system consult and reuse prior verified recovery knowledge before rediscovering the failure from scratch?

# F005 - Black-Box Incident Capture Is Mandatory for Nontrivial Recovered Failures

After a nontrivial failure is successfully resolved, capture a sanitized incident record containing enough evidence to reproduce the diagnosis and recovery:

- stable fingerprint and human-readable signature;
- affected scope/target and environment identity;
- earliest causal root cause;
- failed routes and why they failed;
- successful route;
- exact reusable recovery recipe/commands/configuration as appropriate;
- verification proving the fix;
- applicability and invalidation conditions;
- regression fixture/test/monitor or shared architecture improvement when practical;
- superseded incident/recipe identity when replacing an older fix.

Do not store secrets, tokens, passwords, private cookies, or other sensitive credentials in the incident record.

Only a verified recovery is promoted to reusable knowledge. A guess or workaround without proof remains an experiment, not a recipe.

Use `scripts/failure_incident.py` to validate, record, and look up incident records when practical.

**Acceptance:** Could a future agent recognize the same failure and execute the proven recovery without repeating the original investigation?

# F006 - Recovered Failures Must Improve the System

A solved incident should improve at least one reusable layer when practical:

- regression test or fixture;
- repair/recovery knowledge base;
- shared adapter/toolkit;
- causal architecture fix;
- environment bootstrap/check;
- diagnostic classifier;
- self-test/audit rule;
- documentation/runbook generated from verified evidence.

Repeated one-off patches for the same failure class are a design smell. Move the fix toward the shared causal owner.

**Acceptance:** Did the recovery leave the system more capable of preventing, detecting, or resolving the same failure class next time?

# Closeout Gate

Before closing substantive work that involved external discovery, a blocker, or a nontrivial failure, verify:

1. no required item remains merely `unresolved-active`;
2. no blocker is being presented as completion;
3. any `absent-proven` claim has authoritative or complete convergent evidence;
4. any `complete` external-data claim passes completeness proof;
5. any nontrivial recovered failure has a verified reusable incident record;
6. any recurring failure reused or superseded prior recovery knowledge;
7. the final result is real, not inferred from a failed route.

If a required answer is no, continue the task rather than closing it.
