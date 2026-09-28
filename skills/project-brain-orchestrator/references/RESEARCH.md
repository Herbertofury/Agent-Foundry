# REFERENCES, RESEARCH, AND EXACTNESS


## Automatic implementation-research fast path

Automatic supporting research must be current **without becoming a serial research waterfall**:

1. Search the project's sourced research memory first.
2. If a record is fresh, compatible, and high-confidence, revalidate only its version-sensitive/load-bearing claim instead of repeating the entire ecosystem survey.
3. When new evidence can materially change implementation, query current primary sources in parallel: official docs/releases, the actual source repository/commits/issues, and relevant primary papers.
4. For an implementation choice, start depth-first with the strongest 3-5 serious candidates and inspect the 1-2 leaders deeply. Expand to the normal 8-15 distinct-option survey when the user explicitly asks for broad research, important categories remain uncovered, or the winner is still uncertain.
5. Cache the durable decision with source, access date, exact version, applicability, evidence, tradeoffs, and review date so later tasks can perform cheap freshness revalidation rather than start over.

This fast path changes retrieval strategy, not research quality: stale popularity, stars alone, or remembered conclusions still do not prove the strongest current option.

- Inspect every named repository, file, page, screenshot, product, implementation, protocol, or specification before implementing against it.
- When exact parity is requested, do not approximate, simplify, rename, redesign, or substitute; use only strictly necessary environment adapters.
- Treat every research request as current and broad unless explicitly limited. Do not stop at the first page, first plausible result, or a few familiar options.
- Search the full relevant ecosystem: official documentation and release notes, primary source code, GitHub repositories, releases, commits, issues and discussions, package registries, maintainer announcements, credible benchmarks, production implementations, and current user reports when they add real evidence.
- For tools and technical approaches, deliberately search for the strongest current options across mature, fast-moving, and bleeding-edge projects. Use present-year and recent-version searches so old popularity does not hide newer, better work.
- Do not default to an older or weaker "safe" choice merely because it is easier, more familiar, or more conservative. Prefer the most capable current option that best satisfies the goal. Treat instability, rough edges, missing polish, weak defaults, and integration problems as engineering work to harden through fixes, adapters, tests, observability, compatibility work, and recovery paths while preserving the tool's best current capabilities.
- Never downgrade, pin stale versions, or recommend an inferior mature alternative solely to avoid the work of making the stronger modern option reliable. Disclose material risks honestly, then mitigate and verify them instead of using them as an automatic disqualifier.
- Evaluate each serious candidate by current release and commit activity, issue responsiveness, CI health, documentation, platform compatibility, integration cost, license, adoption, security history, deprecation status, and evidence of real-world use. Stars and historical popularity alone are never proof of present quality.
- Exclude abandoned, stale, superseded, insecure, or incompatible projects unless they remain uniquely valuable; when included, label the limitation clearly and explain why a current replacement is insufficient.
- Cross-check load-bearing claims with multiple credible sources when available. Inspect the exact installed version and target platform rather than relying on memory.
- Provide a broad but curated option set, normally **8-15 genuinely distinct strong options** when the ecosystem supports it. If fewer qualified options exist, state that the smaller set is exhaustive. Never pad the list with weak, duplicate, abandoned, or near-identical entries.
- Present findings cleanly and beautifully: group options by use case or maturity, rank them by fit, and include direct official or repository links, best use, major strengths, meaningful drawbacks, compatibility, maintenance freshness, and why each earned inclusion. Identify the best overall current option, the highest-capability option, and the strongest bleeding-edge option when those categories differ.
- Distinguish stable, beta, experimental, and research-grade options. Never misrepresent maturity or unresolved risk, but do not omit or demote a superior bleeding-edge option merely because it requires hardening work.
- Continue until important categories are covered and further searching yields only duplicates or materially weaker choices; then synthesize rather than dump results.
- When recommending or naming a tool, utility, runtime, package, or external program, include the direct official install, download, repository, or usage location rather than a discussion or announcement page.
- Verify URLs, commands, package names, API fields, versions, platform support, release claims, and current maintenance status. Never fabricate plausible details or claim "latest" without current evidence.
- For GitHub or external references, prefer complete authoritative source inspection over partial snippets when the full source is available.
## Source adapters and asset hubs

- Build a current **source capability matrix** before enabling any media hub. Record media types, official/public/OAuth API vs oEmbed/clipper/manual/launcher/legacy mode, authentication, rate limits, pagination, attribution, license/rights, moderation, caching, provider status, fallback, evidence, access date, and review date.
- Never infer a public API from a website, scrape private/internal endpoints, bypass login, or present capture-only support as search/download integration. Disable unsupported actions truthfully and keep a browser-clipper or manual-import fallback.
- Preserve source URL, creator, provider IDs, license, attribution, mature-content labels, NoAI/reuse restrictions, content hashes, and derivation lineage through every generated asset and export.
