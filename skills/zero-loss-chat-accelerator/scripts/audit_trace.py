#!/usr/bin/env python3
"""Audit JSON/JSONL execution traces for avoidable orchestration latency.

Accepted input: JSON array or JSONL objects.
Useful optional fields:
  id, tool, op, target, fingerprint, status, depends_on, start_ms, end_ms,
  category, repo, branch, run_id, route, error, message, http_status,
  version, revision, sha, etag, head_sha, state_version, satisfies,
  intentional_boundary, invalidator, retry_after_ms, ci_state, quality_satisfies.

Findings are review candidates. They never authorize removing mandatory work.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

DISCOVERY_TOKENS = ("schema", "discover", "list_resources", "capabilities")
READ_TOKENS = ("read", "open", "fetch", "get", "search", "list")
RETRY_FAILURES = {"error", "failed", "timeout", "timed_out"}
CI_TOKENS = ("workflow", "check_run", "check_suite", "pipeline", "job_status", "ci_status", "actions")
WRITE_TOKENS = (
    "update_file", "create_file", "put_file", "commit", "create_tree", "batch_update",
    "apply_patch", "upload", "write", "delete", "move", "rename",
)
VALIDATION_TOKENS = (
    "build", "test", "lint", "validate", "verify", "render", "package", "compile",
    "check", "smoke", "qa",
)
HARD_ROUTE_TOKENS = (
    "no outbound", "network unreachable", "name resolution", "dns", "permission denied",
    "unsupported", "not supported", "connection refused", "host unreachable",
)
RATE_LIMIT_TOKENS = ("rate limit", "too many requests", "throttl", "quota exceeded", "retry-after")
BROAD_CI_DISCOVERY_TOKENS = ("list", "search", "workflow_runs", "runs", "recent")


def load_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON root must be an array")
        events = data
    else:
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not all(isinstance(e, dict) for e in events):
        raise ValueError("Every trace event must be an object")
    return events


def norm(event: dict[str, Any], key: str) -> str:
    value = event.get(key, "")
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value).strip().lower()


def truthy(event: dict[str, Any], key: str) -> bool:
    value = event.get(key, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def as_str_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, (list, tuple, set)):
        return {str(v) for v in value if str(v)}
    return {str(value)}


def call_signature(event: dict[str, Any]) -> str:
    fp = norm(event, "fingerprint")
    if fp:
        return fp
    return "|".join((norm(event, "tool"), norm(event, "op"), norm(event, "target")))


def dependency_set(event: dict[str, Any]) -> set[str]:
    return as_str_set(event.get("depends_on"))


def duration(event: dict[str, Any]) -> float | None:
    try:
        value = float(event["end_ms"]) - float(event["start_ms"])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value >= 0 else None


def start(event: dict[str, Any]) -> float | None:
    try:
        return float(event["start_ms"])
    except (KeyError, TypeError, ValueError):
        return None


def end(event: dict[str, Any]) -> float | None:
    try:
        return float(event["end_ms"])
    except (KeyError, TypeError, ValueError):
        return None


def error_text(event: dict[str, Any]) -> str:
    return " ".join((norm(event, "error"), norm(event, "message"), norm(event, "detail")))


def state_token(event: dict[str, Any]) -> str:
    parts = []
    for key in ("state_version", "head_sha", "sha", "revision", "version", "etag"):
        value = norm(event, key)
        if value:
            parts.append(f"{key}={value}")
    return "|".join(parts)


def has_invalidator(event: dict[str, Any]) -> bool:
    return bool(norm(event, "invalidator"))


def same_scope(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ar, br = norm(a, "repo"), norm(b, "repo")
    ab, bb = norm(a, "branch"), norm(b, "branch")
    at, bt = norm(a, "target"), norm(b, "target")
    if ar or br or ab or bb:
        return ar == br and ab == bb
    return bool(at and bt and at == bt)


def is_ci_poll(event: dict[str, Any]) -> bool:
    if norm(event, "category") == "ci_poll":
        return True
    hay = f"{norm(event, 'tool')} {norm(event, 'op')}"
    return any(token in hay for token in CI_TOKENS) and any(k in hay for k in ("get", "status", "read", "check"))


def is_ci_discovery(event: dict[str, Any]) -> bool:
    if norm(event, "category") == "ci_discovery":
        return True
    hay = f"{norm(event, 'tool')} {norm(event, 'op')} {norm(event, 'target')}"
    return any(t in hay for t in CI_TOKENS) and any(t in hay for t in BROAD_CI_DISCOVERY_TOKENS) and not norm(event, "run_id")


def ci_key(event: dict[str, Any]) -> str:
    run_id = norm(event, "run_id")
    return run_id or norm(event, "target") or f"{norm(event, 'repo')}|{norm(event, 'branch')}"


def ci_scope(event: dict[str, Any]) -> str:
    """Return a conservative CI scope; empty means the trace lacks safe scope evidence."""
    repo = norm(event, "repo")
    branch = norm(event, "branch")
    workflow = norm(event, "workflow") or norm(event, "workflow_id")
    if not (repo or branch or workflow):
        return ""
    return f"{norm(event, 'tool')}|{repo}|{branch}|{workflow}"


def ci_state(event: dict[str, Any]) -> str:
    for key in ("ci_state", "observed_state", "result_state", "workflow_state", "conclusion"):
        value = norm(event, key)
        if value:
            return value
    return ""


def is_continuity(event: dict[str, Any]) -> bool:
    if norm(event, "category") == "continuity":
        return True
    tool = norm(event, "tool")
    op = norm(event, "op")
    target = norm(event, "target")
    return (
        ("github" in tool or "drive" in tool)
        and any(t in op for t in ("search", "list", "head", "state", "metadata"))
        and any(t in target for t in ("head", "project", "checkpoint", "state", "canonical"))
    )


def continuity_key(event: dict[str, Any]) -> str:
    repo = norm(event, "repo")
    branch = norm(event, "branch")
    if repo or branch:
        return f"{norm(event, 'tool')}|{repo}|{branch}|{norm(event, 'target')}"
    return f"{norm(event, 'tool')}|{norm(event, 'target')}"


def is_repo_write(event: dict[str, Any]) -> bool:
    if norm(event, "category") == "repo_write":
        return True
    return "github" in norm(event, "tool") and any(t in norm(event, "op") for t in WRITE_TOKENS)


def is_any_write(event: dict[str, Any]) -> bool:
    if norm(event, "category") in {"write", "repo_write", "mutation", "persistence_write"}:
        return True
    return any(t in norm(event, "op") for t in WRITE_TOKENS)


def is_validation(event: dict[str, Any]) -> bool:
    if norm(event, "category") in {"validation", "qa", "test", "build", "render"}:
        return True
    hay = f"{norm(event, 'tool')} {norm(event, 'op')} {norm(event, 'target')}"
    return any(token in hay for token in VALIDATION_TOKENS) and not is_ci_poll(event)


def had_any_write_between(events: list[dict[str, Any]], a: int, b: int) -> bool:
    return any(is_any_write(events[j]) for j in range(a + 1, b))


def repo_write_key(event: dict[str, Any]) -> str:
    return f"{norm(event, 'repo')}|{norm(event, 'branch')}"


def is_discovery(event: dict[str, Any]) -> bool:
    hay = f"{norm(event, 'tool')} {norm(event, 'op')}"
    return any(token in hay for token in DISCOVERY_TOKENS)


def is_read(event: dict[str, Any]) -> bool:
    if norm(event, "category") in {"read", "repo_read", "source_read"}:
        return True
    hay = f"{norm(event, 'tool')} {norm(event, 'op')}"
    return any(token in hay for token in READ_TOKENS) and not is_ci_poll(event) and not is_continuity(event)


def is_repo_read(event: dict[str, Any]) -> bool:
    if norm(event, "category") in {"repo_read", "source_read"}:
        return True
    return "github" in norm(event, "tool") and is_read(event) and bool(norm(event, "target"))


def is_hard_failure(event: dict[str, Any]) -> bool:
    return norm(event, "status") in RETRY_FAILURES and any(t in error_text(event) for t in HARD_ROUTE_TOKENS)


def is_rate_limited(event: dict[str, Any]) -> bool:
    status = norm(event, "status")
    http = norm(event, "http_status")
    return http == "429" or (status in RETRY_FAILURES and any(t in error_text(event) for t in RATE_LIMIT_TOKENS))


def route_key(event: dict[str, Any]) -> str:
    return norm(event, "route") or f"{norm(event, 'tool')}|{norm(event, 'repo')}|{norm(event, 'target')}"


def had_scope_write_between(events: list[dict[str, Any]], a: int, b: int) -> bool:
    left = events[a]
    for j in range(a + 1, b):
        candidate = events[j]
        if is_any_write(candidate) and same_scope(left, candidate):
            return True
    return False


def declared_critical_path(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events or not all(duration(e) is not None for e in events):
        return {"critical_path_ms": None, "cycle": False, "unresolved_dependencies": []}

    ids = [str(e.get("id", i)) for i, e in enumerate(events)]
    if len(set(ids)) != len(ids):
        return {"critical_path_ms": None, "cycle": False, "unresolved_dependencies": ["duplicate event ids"]}

    id_to_event = dict(zip(ids, events))
    deps: dict[str, set[str]] = {}
    unresolved: set[str] = set()
    children: defaultdict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {event_id: 0 for event_id in ids}

    any_declared_dep = False
    for event_id, event in zip(ids, events):
        dset = dependency_set(event)
        if dset:
            any_declared_dep = True
        valid = set()
        for dep in dset:
            if dep not in id_to_event:
                unresolved.add(dep)
            else:
                valid.add(dep)
                children[dep].add(event_id)
                indegree[event_id] += 1
        deps[event_id] = valid

    if unresolved or not any_declared_dep:
        return {
            "critical_path_ms": None,
            "cycle": False,
            "unresolved_dependencies": sorted(unresolved),
        }

    q = deque([event_id for event_id in ids if indegree[event_id] == 0])
    longest: dict[str, float] = {}
    seen = 0
    while q:
        event_id = q.popleft()
        seen += 1
        base = max((longest[d] for d in deps[event_id]), default=0.0)
        longest[event_id] = base + float(duration(id_to_event[event_id]) or 0.0)
        for child in children[event_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                q.append(child)

    if seen != len(ids):
        return {"critical_path_ms": None, "cycle": True, "unresolved_dependencies": []}
    return {
        "critical_path_ms": round(max(longest.values(), default=0.0), 3),
        "cycle": False,
        "unresolved_dependencies": [],
    }


def audit(events: list[dict[str, Any]], rapid_ci_ms: float, rapid_rate_ms: float) -> dict[str, Any]:
    signatures = [call_signature(e) for e in events]
    sig_counts = Counter(s for s in signatures if s.strip("|"))
    exact_duplicates = {s: n for s, n in sig_counts.items() if n > 1}

    # Reads/discovery/state observations have version-aware specialized rules below.
    # Keep the generic duplicate detector for other stateless operations only so a
    # legitimate reread after a version change is not misclassified.
    # Generic duplicate review is intentionally conservative. Reads, discovery, CI,
    # validation, and mutations have version/state-aware rules elsewhere so a
    # legitimate revalidation or second coherent write is never discouraged.
    stateless_signatures = [
        call_signature(e)
        for e in events
        if (
            not is_ci_poll(e)
            and not is_continuity(e)
            and not is_read(e)
            and not is_discovery(e)
            and not is_validation(e)
            and not is_any_write(e)
            and call_signature(e).strip("|")
        )
    ]
    stateless_counts = Counter(stateless_signatures)
    duplicate_review_signatures = {s: n for s, n in stateless_counts.items() if n > 1}

    discoveries: defaultdict[str, list[int]] = defaultdict(list)
    reads: defaultdict[str, list[int]] = defaultdict(list)
    continuity: defaultdict[str, list[int]] = defaultdict(list)
    ci_polls: defaultdict[str, list[int]] = defaultdict(list)
    repo_writes: defaultdict[str, list[int]] = defaultdict(list)
    repo_reads: defaultdict[str, list[int]] = defaultdict(list)
    validations: defaultdict[str, list[int]] = defaultdict(list)
    unchanged_retry_pairs: list[tuple[int, int, str]] = []

    for i, event in enumerate(events):
        tool = norm(event, "tool")
        target = norm(event, "target")
        if is_discovery(event):
            discoveries[call_signature(event)].append(i)
        if is_read(event) and target:
            reads[call_signature(event)].append(i)
        if is_continuity(event):
            continuity[continuity_key(event)].append(i)
        if is_ci_poll(event):
            ci_polls[ci_key(event)].append(i)
        if is_repo_write(event):
            repo_writes[repo_write_key(event)].append(i)
        if is_repo_read(event):
            repo_reads[f"{tool}|{norm(event, 'repo')}|{norm(event, 'branch')}"] .append(i)
        if is_validation(event):
            validations[call_signature(event)].append(i)

        if i:
            prev = events[i - 1]
            if (
                norm(prev, "status") in RETRY_FAILURES
                and call_signature(prev) == call_signature(event)
                and not has_invalidator(event)
            ):
                # A rate-limited call retried after the provider's wait window is
                # a changed condition, not an unchanged retry.
                allowed_rate_retry = False
                if is_rate_limited(prev):
                    sp, sc = end(prev) if end(prev) is not None else start(prev), start(event)
                    try:
                        retry_after = float(prev.get("retry_after_ms", 0) or 0)
                    except (TypeError, ValueError):
                        retry_after = 0.0
                    threshold = retry_after if retry_after > 0 else rapid_rate_ms
                    if sp is not None and sc is not None and sc - sp >= threshold:
                        allowed_rate_retry = True
                if not allowed_rate_retry:
                    unchanged_retry_pairs.append((i - 1, i, call_signature(event)))

    repeated_discovery_pairs: list[tuple[int, int, str]] = []
    for key, idxs in discoveries.items():
        for a, b in zip(idxs, idxs[1:]):
            if not has_invalidator(events[b]):
                repeated_discovery_pairs.append((a, b, key))

    repeated_read_pairs: list[tuple[int, int, str]] = []
    for key, idxs in reads.items():
        for a, b in zip(idxs, idxs[1:]):
            left, right = events[a], events[b]
            if norm(left, "status") in RETRY_FAILURES:
                # A failed read produced no trustworthy cached body; retry logic
                # is reviewed separately.
                continue
            if has_invalidator(right):
                continue
            lt, rt = state_token(left), state_token(right)
            if lt and rt and lt != rt:
                continue
            if had_scope_write_between(events, a, b):
                continue
            repeated_read_pairs.append((a, b, key))

    continuity_resweep_pairs: list[tuple[int, int, str]] = []
    for key, idxs in continuity.items():
        for a, b in zip(idxs, idxs[1:]):
            left, right = events[a], events[b]
            if has_invalidator(right):
                continue
            if had_scope_write_between(events, a, b):
                continue
            lt, rt = state_token(left), state_token(right)
            if lt and rt and lt != rt:
                continue
            continuity_resweep_pairs.append((a, b, key))

    ci_poll_storms: dict[str, list[int]] = {}
    rapid_ci_pairs: list[tuple[int, int, str, float]] = []
    for key, idxs in ci_polls.items():
        repeated_same_state: list[int] = []
        last_state = None
        for idx in idxs:
            state = ci_state(events[idx])
            if state and state != last_state:
                repeated_same_state = [idx]
                last_state = state
            else:
                repeated_same_state.append(idx)
        if len(idxs) > 2:
            # If state annotations exist, only call it a storm when one state is observed >2 times.
            state_groups: defaultdict[str, list[int]] = defaultdict(list)
            for idx in idxs:
                state_groups[ci_state(events[idx]) or "<unknown>"].append(idx)
            storm_members = [members for members in state_groups.values() if len(members) > 2]
            if storm_members:
                ci_poll_storms[key] = max(storm_members, key=len)

        for a, b in zip(idxs, idxs[1:]):
            sa = end(events[a]) if end(events[a]) is not None else start(events[a])
            sb = start(events[b])
            useful_between = any(not is_ci_poll(events[j]) for j in range(a + 1, b))
            state_changed = bool(ci_state(events[a]) and ci_state(events[b]) and ci_state(events[a]) != ci_state(events[b]))
            if (
                not useful_between
                and not state_changed
                and sa is not None
                and sb is not None
                and 0 <= sb - sa < rapid_ci_ms
            ):
                rapid_ci_pairs.append((a, b, key, round(sb - sa, 3)))

    hard_route_repeat_pairs: list[tuple[int, int, str]] = []
    last_hard_failure: dict[str, int] = {}
    for i, event in enumerate(events):
        key = route_key(event)
        if has_invalidator(event):
            last_hard_failure.pop(key, None)
        if key in last_hard_failure and i != last_hard_failure[key]:
            hard_route_repeat_pairs.append((last_hard_failure[key], i, key))
        if is_hard_failure(event):
            last_hard_failure[key] = i

    rate_limit_hammer_pairs: list[tuple[int, int, str, float | None]] = []
    last_rate_failure: dict[str, int] = {}
    for i, event in enumerate(events):
        key = route_key(event)
        if has_invalidator(event):
            last_rate_failure.pop(key, None)
        if key in last_rate_failure and i != last_rate_failure[key]:
            prev_i = last_rate_failure[key]
            prev = events[prev_i]
            sp = end(prev) if end(prev) is not None else start(prev)
            sc = start(event)
            delta = None if sp is None or sc is None else sc - sp
            try:
                retry_after = float(prev.get("retry_after_ms", 0) or 0)
            except (TypeError, ValueError):
                retry_after = 0.0
            threshold = retry_after if retry_after > 0 else rapid_rate_ms
            if delta is None or (0 <= delta < threshold):
                rate_limit_hammer_pairs.append((prev_i, i, key, None if delta is None else round(delta, 3)))
        if is_rate_limited(event):
            last_rate_failure[key] = i

    fragmented_repo_writes: dict[str, list[int]] = {}
    for key, idxs in repo_writes.items():
        unintentional = [idx for idx in idxs if not truthy(events[idx], "intentional_boundary")]
        if key.strip("|") and len(unintentional) > 1:
            fragmented_repo_writes[key] = unintentional

    broad_ci_rediscovery_after_known_run: list[tuple[int, int, str]] = []
    known_run_by_scope: dict[str, tuple[int, str]] = {}
    for i, event in enumerate(events):
        scope = ci_scope(event)
        run_id = norm(event, "run_id")
        if run_id and scope:
            known_run_by_scope[scope] = (i, run_id)
        elif scope and is_ci_discovery(event) and scope in known_run_by_scope and not has_invalidator(event):
            prior_i, prior_run = known_run_by_scope[scope]
            broad_ci_rediscovery_after_known_run.append((prior_i, i, prior_run))

    overlapping_singleflight_pairs: list[tuple[int, int, str]] = []
    stateless_by_sig: defaultdict[str, list[int]] = defaultdict(list)
    for i, event in enumerate(events):
        if not is_ci_poll(event) and not is_continuity(event):
            sig = call_signature(event)
            if sig.strip("|"):
                stateless_by_sig[sig].append(i)
    for sig, idxs in stateless_by_sig.items():
        for pos, a in enumerate(idxs):
            sa, ea = start(events[a]), end(events[a])
            if sa is None or ea is None:
                continue
            for b in idxs[pos + 1:]:
                sb, eb = start(events[b]), end(events[b])
                if sb is None or eb is None:
                    continue
                if max(sa, sb) < min(ea, eb):
                    overlapping_singleflight_pairs.append((a, b, sig))

    serial_repo_read_runs: dict[str, list[int]] = {}
    for key, idxs in repo_reads.items():
        if len(idxs) < 3:
            continue
        run = []
        for idx in idxs:
            event = events[idx]
            if truthy(event, "batched"):
                if len(run) >= 3:
                    serial_repo_read_runs[f"{key}|{run[0]}"] = list(run)
                run = []
                continue
            if run:
                previous_idx = run[-1]
                previous_id = str(events[previous_idx].get("id", previous_idx))
                depends_on_previous_read = previous_id in dependency_set(event)
                if idx != previous_idx + 1 or depends_on_previous_read:
                    if len(run) >= 3:
                        serial_repo_read_runs[f"{key}|{run[0]}"] = list(run)
                    run = []
            run.append(idx)
        if len(run) >= 3:
            serial_repo_read_runs[f"{key}|{run[0]}"] = list(run)

    repeated_validation_pairs: list[tuple[int, int, str]] = []
    for key, idxs in validations.items():
        for a, b in zip(idxs, idxs[1:]):
            left, right = events[a], events[b]
            if norm(left, "status") in RETRY_FAILURES or has_invalidator(right):
                continue
            lt, rt = state_token(left), state_token(right)
            if lt and rt and lt != rt:
                continue
            if had_any_write_between(events, a, b):
                continue
            repeated_validation_pairs.append((a, b, key))

    post_write_same_state_resweeps: list[tuple[int, int, str]] = []
    latest_write_by_scope: dict[str, int] = {}
    for i, event in enumerate(events):
        scope = f"{norm(event, 'repo')}|{norm(event, 'branch')}"
        if is_repo_write(event):
            latest_write_by_scope[scope] = i
        elif is_continuity(event) and scope in latest_write_by_scope and not has_invalidator(event):
            wi = latest_write_by_scope[scope]
            write_values = {norm(events[wi], key) for key in ("sha", "head_sha", "revision", "version", "etag", "state_version") if norm(events[wi], key)}
            continuity_values = {norm(event, key) for key in ("sha", "head_sha", "revision", "version", "etag", "state_version") if norm(event, key)}
            if write_values and continuity_values and write_values.intersection(continuity_values):
                post_write_same_state_resweeps.append((wi, i, scope))

    # Conservative same-wave candidates: never group mutations, and never place
    # an event in a candidate group if it depends on any earlier member. This is
    # advisory only; governing tool/provider semantics still decide batching.
    batching_candidates: list[list[int]] = []
    current: list[int] = []
    current_ids: set[str] = set()
    ids = [str(e.get("id", i)) for i, e in enumerate(events)]
    for i, event in enumerate(events):
        deps = dependency_set(event)
        unsafe = is_any_write(event) or bool(deps & current_ids)
        if unsafe:
            if len(current) > 1:
                batching_candidates.append(current)
            current = []
            current_ids = set()
            if is_any_write(event):
                continue
        current.append(i)
        current_ids.add(ids[i])
    if len(current) > 1:
        batching_candidates.append(current)

    durations = [d for e in events if (d := duration(e)) is not None]
    starts = [s for e in events if (s := start(e)) is not None]
    ends = [x for e in events if (x := end(e)) is not None]
    timed_events = sum(1 for e in events if start(e) is not None and end(e) is not None and duration(e) is not None)
    timing_coverage = round(timed_events / len(events), 6) if events else 1.0
    cp = declared_critical_path(events)
    serial_ms = round(sum(durations), 3) if len(durations) == len(events) and events else None
    headroom = None
    if serial_ms is not None and cp["critical_path_ms"] is not None:
        headroom = round(serial_ms - float(cp["critical_path_ms"]), 3)

    acceptance_tags = sorted(set().union(*(as_str_set(e.get("satisfies")) for e in events))) if events else []
    quality_tags = sorted(set().union(*(as_str_set(e.get("quality_satisfies")) for e in events))) if events else []

    generic_flags = (
        sum(n - 1 for n in duplicate_review_signatures.values())
        + len(repeated_discovery_pairs)
        + len(repeated_read_pairs)
        + len(unchanged_retry_pairs)
        + len(repeated_validation_pairs)
    )
    specialized_flags = (
        len(continuity_resweep_pairs)
        + sum(max(0, len(v) - 2) for v in ci_poll_storms.values())
        + len(rapid_ci_pairs)
        + len(hard_route_repeat_pairs)
        + len(rate_limit_hammer_pairs)
        + sum(len(v) - 1 for v in fragmented_repo_writes.values())
        + len(broad_ci_rediscovery_after_known_run)
        + sum(max(0, len(v) - 1) for v in serial_repo_read_runs.values())
        + len(post_write_same_state_resweeps)
        + len(overlapping_singleflight_pairs)
    )

    return {
        "events": len(events),
        "acceptance_tags": acceptance_tags,
        "quality_tags": quality_tags,
        "exact_duplicate_signatures": exact_duplicates,
        "stateless_duplicate_review_signatures": duplicate_review_signatures,
        "repeated_discovery_pairs": repeated_discovery_pairs,
        "repeated_read_pairs": repeated_read_pairs,
        "continuity_resweep_pairs": continuity_resweep_pairs,
        "ci_poll_storm_targets": ci_poll_storms,
        "rapid_ci_poll_pairs": rapid_ci_pairs,
        "broad_ci_rediscovery_after_known_run": broad_ci_rediscovery_after_known_run,
        "fragmented_repo_write_groups": fragmented_repo_writes,
        "serial_repo_read_runs": serial_repo_read_runs,
        "hard_route_repeat_pairs": hard_route_repeat_pairs,
        "rate_limit_hammer_pairs": rate_limit_hammer_pairs,
        "post_write_same_state_resweeps": post_write_same_state_resweeps,
        "unchanged_retry_pairs": unchanged_retry_pairs,
        "repeated_validation_pairs": repeated_validation_pairs,
        "overlapping_singleflight_pairs": overlapping_singleflight_pairs,
        "candidate_independent_groups": batching_candidates,
        "observed_total_tool_time_ms": round(sum(durations), 3) if durations else None,
        "observed_trace_span_ms": round(max(ends) - min(starts), 3) if starts and ends else None,
        "timed_events": timed_events,
        "timing_coverage": timing_coverage,
        "declared_critical_path_ms": cp["critical_path_ms"],
        "declared_dependency_cycle": cp["cycle"],
        "unresolved_dependencies": cp["unresolved_dependencies"],
        "declared_parallelism_headroom_ms": headroom,
        "generic_review_flags": generic_flags,
        "specialized_review_flags": specialized_flags,
        "review_flags": generic_flags + specialized_flags,
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Events: {report['events']}")
    print(
        f"Review flags: {report['review_flags']} "
        f"(generic={report['generic_review_flags']}, specialized={report['specialized_review_flags']})"
    )
    if report["observed_total_tool_time_ms"] is not None:
        print(f"Observed summed tool time: {report['observed_total_tool_time_ms']:.3f} ms")
    if report["observed_trace_span_ms"] is not None:
        print(
            f"Observed trace span: {report['observed_trace_span_ms']:.3f} ms "
            f"(timing coverage={report['timing_coverage']:.1%})"
        )
    if report["declared_critical_path_ms"] is not None:
        print(f"Declared critical path: {report['declared_critical_path_ms']:.3f} ms")
        print(f"Declared parallelism headroom: {report['declared_parallelism_headroom_ms']:.3f} ms")
    if report["acceptance_tags"]:
        print(f"Acceptance tags: {len(report['acceptance_tags'])}")
    if report["quality_tags"]:
        print(f"Quality tags: {len(report['quality_tags'])}")
    for label, key in (
        ("Exact duplicate signatures", "exact_duplicate_signatures"),
        ("Stateless duplicate review signatures", "stateless_duplicate_review_signatures"),
        ("Repeated discovery pairs", "repeated_discovery_pairs"),
        ("Repeated read pairs", "repeated_read_pairs"),
        ("Continuity resweep pairs", "continuity_resweep_pairs"),
        ("CI poll storm targets", "ci_poll_storm_targets"),
        ("Rapid CI poll pairs", "rapid_ci_poll_pairs"),
        ("Broad CI rediscovery after known run", "broad_ci_rediscovery_after_known_run"),
        ("Fragmented repo write groups", "fragmented_repo_write_groups"),
        ("Serial repo read runs", "serial_repo_read_runs"),
        ("Hard-route repeat pairs", "hard_route_repeat_pairs"),
        ("Rate-limit hammer pairs", "rate_limit_hammer_pairs"),
        ("Post-write same-state resweeps", "post_write_same_state_resweeps"),
        ("Unchanged retry pairs", "unchanged_retry_pairs"),
        ("Repeated validation pairs", "repeated_validation_pairs"),
        ("Overlapping single-flight pairs", "overlapping_singleflight_pairs"),
        ("Candidate independent groups", "candidate_independent_groups"),
    ):
        print(f"{label}: {len(report[key])}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="JSON array or JSONL trace")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument(
        "--rapid-ci-ms", type=float, default=30000.0,
        help="flag unchanged CI polls closer than this many ms (default 30000)",
    )
    parser.add_argument(
        "--rapid-rate-ms", type=float, default=30000.0,
        help="flag same-route retry pressure after rate limit inside this window when Retry-After is absent",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = audit(load_events(args.trace), args.rapid_ci_ms, args.rapid_rate_ms)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
