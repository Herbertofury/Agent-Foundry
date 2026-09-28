# Reusable Site Adapter Platform Governance

Use this reference when agent governance covers website/provider/API/scraping/auth/monitoring integrations.

## Goal

Treat providers as adapters on one reusable platform, not one-off scraper projects. A new adapter should mainly describe provider specifics while reusing shared infrastructure for auth/session ownership, transport, pagination, normalization/provenance, retries/backpressure, caching/invalidation, update diffs, health/diagnostics, cancellation, fixtures, and regression learning.

## Canonical repository policy

For repositories with provider integrations, create `SITE_ADAPTERS.md` as a binding domain policy and route site/provider work to it from root `AGENTS.md` and thin tool adapters.

High-value rules:

- one shared adapter contract/SDK; no disposable scraper stacks;
- capability-driven routing rather than provider-name branches in product code;
- canonical auth/session owner shared by workers;
- transport preference: official API -> documented/public structured endpoint -> embedded structured data -> HTML -> legitimate user-authorized browser session;
- complete pagination/cursor traversal without hidden caps;
- canonical normalized models while preserving source IDs/URLs/raw extension data needed for provenance;
- bounded parallel execution, pooling, prefetch, single-flight, conditional requests, rate-limit awareness, and cancellation;
- typed auth/rate-limit/outage/schema-drift/selector-drift/parse failures instead of silent empty success;
- bounded retries plus circuit breakers; no login or retry storms;
- meaningful update snapshot/diff categories rather than version-string-only notifications when data supports it;
- sanitized fixtures/replay for fragile provider logic and historical breakages;
- adapter versioning/migrations that preserve tracked state;
- first-class provider health/diagnostics with secret redaction;
- every real breakage becomes a regression fixture and, when reusable, a shared framework improvement;
- legitimate public or user-authorized access only; no paywall/auth/CAPTCHA/access-control bypass.

## Machine-readable manifest

A reusable provider platform should give each adapter a manifest with:

- stable provider ID/name/version;
- base URLs;
- supported capabilities;
- auth methods and capabilities requiring auth;
- ordered transport options;
- pagination modes;
- health-check support.

The skill bundles `assets/site-adapter-manifest.schema.json` and `scripts/site_adapter_manifest_check.py` as reusable starting points. Copy/adapt them into the target repository when the governance package is meant to enforce adapter contracts.

## Continuous improvement loop

For a verified provider failure:

1. capture sanitized deterministic evidence/fixture;
2. classify the failure (auth, throttle, provider outage, schema/DOM drift, parsing, transport, pagination, identity, etc.);
3. fix the earliest causal owner;
4. add the regression fixture;
5. move reusable logic into the shared adapter toolkit;
6. bump adapter/contract version when behavior changes;
7. verify unaffected providers still pass.

This is the core rule: provider repairs should make future providers and future breakages easier, not create another isolated patch.
