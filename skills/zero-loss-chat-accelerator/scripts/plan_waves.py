#!/usr/bin/env python3
"""Validate a large task DAG and emit dependency waves/batch opportunities.

Input is either a JSON array of task objects or {"tasks": [...]}.
Task fields:
  id (required), depends_on (optional string/list), duration_ms (optional number),
  batch_key (optional), fingerprint (optional), exclusive_key (optional).

This planner is an optional orchestration aid. It reports both a dependency-only critical-path lower bound and the barrier-wave makespan of the emitted waves, plus gateway-delay risks. Maximum-effort reasoning remains enabled whether or not the planner is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Any, Iterable


def load_tasks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("tasks")
    if not isinstance(data, list) or not all(isinstance(t, dict) for t in data):
        raise ValueError("input must be a task array or an object containing a task array")
    return data


def dep_set(task: dict[str, Any]) -> set[str]:
    value = task.get("depends_on")
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(v) for v in value}
    return {str(value)}


def partition_exclusive(layer: list[str], by_id: dict[str, dict[str, Any]]) -> list[list[str]]:
    waves: list[list[str]] = []
    locks_per_wave: list[set[str]] = []
    for task_id in layer:
        lock = str(by_id[task_id].get("exclusive_key", "")).strip()
        placed = False
        for wave, locks in zip(waves, locks_per_wave):
            if not lock or lock not in locks:
                wave.append(task_id)
                if lock:
                    locks.add(lock)
                placed = True
                break
        if not placed:
            waves.append([task_id])
            locks_per_wave.append({lock} if lock else set())
    return waves



def exact_barrier_schedule(
    ids: list[str], by_id: dict[str, dict[str, Any]], deps: dict[str, set[str]], *, max_tasks: int = 16,
) -> tuple[float, list[list[str]]] | None:
    """Find an optimal synchronous barrier-wave schedule for small timed DAGs.

    Every task in a wave starts together and descendants cannot start until the
    whole wave returns. With unlimited non-conflicting concurrency, an optimal
    wave can include every ready no-lock task below a chosen duration threshold;
    for each exclusive lock it includes one eligible task. Enumerating those
    threshold waves plus memoized completed-state masks is exact for this model.
    """
    n = len(ids)
    if n > max_tasks:
        return None
    if not all(isinstance(by_id[i].get("duration_ms"), (int, float)) and float(by_id[i]["duration_ms"]) >= 0 for i in ids):
        return None

    index = {task_id: i for i, task_id in enumerate(ids)}
    dep_masks = []
    durations = []
    locks = []
    for task_id in ids:
        mask = 0
        for dep in deps[task_id]:
            mask |= 1 << index[dep]
        dep_masks.append(mask)
        durations.append(float(by_id[task_id]["duration_ms"]))
        locks.append(str(by_id[task_id].get("exclusive_key", "")).strip())

    full = (1 << n) - 1

    @lru_cache(maxsize=None)
    def solve(done: int) -> tuple[float, tuple[tuple[int, ...], ...]]:
        if done == full:
            return 0.0, ()
        ready = [i for i in range(n) if not (done >> i) & 1 and dep_masks[i] & ~done == 0]
        if not ready:
            raise ValueError("dependency cycle detected")

        wave_masks: set[int] = set()
        for threshold in sorted({durations[i] for i in ready}):
            eligible = [i for i in ready if durations[i] <= threshold]
            base = [i for i in eligible if not locks[i]]
            groups: defaultdict[str, list[int]] = defaultdict(list)
            for i in eligible:
                if locks[i]:
                    groups[locks[i]].append(i)
            group_choices = [members for _, members in sorted(groups.items())]
            combos = product(*group_choices) if group_choices else [()]
            for chosen in combos:
                members = sorted(set(base).union(chosen))
                if not members:
                    continue
                wave_mask = 0
                for i in members:
                    wave_mask |= 1 << i
                wave_masks.add(wave_mask)

        best: tuple[float, int, tuple[tuple[int, ...], ...]] | None = None
        for wave_mask in wave_masks:
            members = tuple(i for i in range(n) if (wave_mask >> i) & 1)
            wave_cost = max(durations[i] for i in members)
            rest_cost, rest_waves = solve(done | wave_mask)
            waves = (members,) + rest_waves
            candidate = (wave_cost + rest_cost, len(waves), waves)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
        assert best is not None
        return best[0], best[2]

    cost, wave_indexes = solve(0)
    return round(cost, 3), [[ids[i] for i in wave] for wave in wave_indexes]

def plan(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(t.get("id", "")) for t in tasks]
    if any(not task_id for task_id in ids):
        raise ValueError("every task must have a non-empty id")
    duplicates = sorted([task_id for task_id, count in Counter(ids).items() if count > 1])
    if duplicates:
        raise ValueError("duplicate task ids: " + ", ".join(duplicates))

    by_id = dict(zip(ids, tasks))
    deps: dict[str, set[str]] = {}
    missing: defaultdict[str, list[str]] = defaultdict(list)
    children: defaultdict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {task_id: 0 for task_id in ids}

    for task_id, task in zip(ids, tasks):
        dset = dep_set(task)
        deps[task_id] = set()
        for dep in dset:
            if dep not in by_id:
                missing[task_id].append(dep)
            else:
                deps[task_id].add(dep)
                children[dep].add(task_id)
                indegree[task_id] += 1
    if missing:
        raise ValueError("missing dependencies: " + json.dumps(missing, sort_keys=True))

    order = {task_id: i for i, task_id in enumerate(ids)}
    q = deque([task_id for task_id in ids if indegree[task_id] == 0])
    topo_layers: list[list[str]] = []
    seen = 0
    while q:
        layer = list(q)
        q.clear()
        topo_layers.append(layer)
        for task_id in layer:
            seen += 1
            newly_ready = []
            for child in children[task_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    newly_ready.append(child)
            for child in sorted(newly_ready, key=order.get):
                q.append(child)
    if seen != len(ids):
        raise ValueError("dependency cycle detected")

    waves: list[list[str]] = []
    for layer in topo_layers:
        waves.extend(partition_exclusive(layer, by_id))

    batch_groups: list[dict[str, Any]] = []
    for wave_index, wave in enumerate(waves):
        groups: defaultdict[str, list[str]] = defaultdict(list)
        for task_id in wave:
            key = str(by_id[task_id].get("batch_key", "")).strip()
            if key:
                groups[key].append(task_id)
        for key, members in groups.items():
            if len(members) > 1:
                batch_groups.append({"wave": wave_index, "batch_key": key, "tasks": members})

    fingerprints: defaultdict[str, list[str]] = defaultdict(list)
    for task_id, task in zip(ids, tasks):
        fp = str(task.get("fingerprint", "")).strip()
        if fp:
            fingerprints[fp].append(task_id)
    duplicate_fingerprints = {fp: members for fp, members in fingerprints.items() if len(members) > 1}

    durations_ok = all(isinstance(t.get("duration_ms"), (int, float)) and float(t["duration_ms"]) >= 0 for t in tasks)
    critical_path_ms = None
    barrier_wave_makespan_ms = None
    gateway_delay_risks: list[dict[str, Any]] = []
    if durations_ok:
        longest: dict[str, float] = {}
        flat_topo = [task_id for layer in topo_layers for task_id in layer]
        for task_id in flat_topo:
            base = max((longest[d] for d in deps[task_id]), default=0.0)
            longest[task_id] = base + float(by_id[task_id]["duration_ms"])
        critical_path_ms = round(max(longest.values(), default=0.0), 3)

        # Chat/tool runtimes commonly behave as barriers: the model cannot launch
        # descendants until every call in the current same-turn wave returns.
        # Report that practical wave schedule separately from the dependency-only
        # critical-path lower bound.
        barrier_wave_makespan_ms = round(
            sum(max((float(by_id[task_id]["duration_ms"]) for task_id in wave), default=0.0) for wave in waves),
            3,
        )

        tail: dict[str, float] = {}
        for task_id in reversed(flat_topo):
            tail[task_id] = float(by_id[task_id]["duration_ms"]) + max(
                (tail[child] for child in children[task_id]), default=0.0
            )
        for wave_index, wave in enumerate(waves):
            if len(wave) < 2:
                continue
            wave_max = max(float(by_id[task_id]["duration_ms"]) for task_id in wave)
            for task_id in wave:
                own = float(by_id[task_id]["duration_ms"])
                if not children[task_id] or own >= wave_max:
                    continue
                child_tail = max((tail[child] for child in children[task_id]), default=0.0)
                barrier_delay = wave_max - own
                if child_tail > barrier_delay:
                    gateway_delay_risks.append({
                        "wave": wave_index,
                        "task": task_id,
                        "barrier_delay_ms": round(barrier_delay, 3),
                        "downstream_tail_ms": round(child_tail, 3),
                    })

    exact_schedule = exact_barrier_schedule(ids, by_id, deps) if durations_ok else None
    optimized_barrier_makespan_ms = exact_schedule[0] if exact_schedule else None
    optimized_barrier_waves = exact_schedule[1] if exact_schedule else None

    return {
        "tasks": len(tasks),
        "waves": waves,
        "batch_groups": batch_groups,
        "duplicate_fingerprints": duplicate_fingerprints,
        "critical_path_ms": critical_path_ms,
        "barrier_wave_makespan_ms": barrier_wave_makespan_ms,
        "gateway_delay_risks": gateway_delay_risks,
        "optimized_barrier_makespan_ms": optimized_barrier_makespan_ms,
        "optimized_barrier_waves": optimized_barrier_waves,
        "barrier_schedule_method": "exact" if exact_schedule else ("not_computed_over_16_tasks" if durations_ok and len(tasks) > 16 else None),
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Tasks: {report['tasks']}")
    print(f"Execution waves: {len(report['waves'])}")
    for i, wave in enumerate(report["waves"]):
        print(f"  wave {i}: " + ", ".join(wave))
    print(f"Batch opportunities: {len(report['batch_groups'])}")
    print(f"Duplicate fingerprints: {len(report['duplicate_fingerprints'])}")
    if report["critical_path_ms"] is not None:
        print(f"Dependency-only critical path: {report['critical_path_ms']:.3f} ms")
        print(f"Barrier-wave makespan: {report['barrier_wave_makespan_ms']:.3f} ms")
        print(f"Gateway delay risks: {len(report['gateway_delay_risks'])}")
        if report["optimized_barrier_makespan_ms"] is not None:
            print(f"Optimized barrier makespan: {report['optimized_barrier_makespan_ms']:.3f} ms")
            for i, wave in enumerate(report["optimized_barrier_waves"]):
                print(f"  optimized wave {i}: " + ", ".join(wave))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = plan(load_tasks(args.plan))
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
