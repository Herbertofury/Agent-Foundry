#!/usr/bin/env python3
"""Regression tests for Zero-Loss Chat Accelerator.

Run after editing the skill. Uses only the Python standard library.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audit_trace import audit, load_events
from compare_traces import compare
from plan_waves import plan
import watchdog
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def ev(i: str, tool: str = "x", op: str = "read", target: str = "t", **kw):
    base = {"id": i, "tool": tool, "op": op, "target": target, "status": "ok"}
    base.update(kw)
    return base


class ContractTests(unittest.TestCase):
    def test_always_on_maximum_effort_contract(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Always-on maximum-effort", text)
        self.assertIn("Maximum effort is always on; only waste is optional", text)
        self.assertIn("maximum useful effort, minimum wasted motion", text.lower())
        self.assertNotIn("For simple work, answer directly", text)
        self.assertIn("schema-overfetch guard", text.lower())

    def test_no_scope_reduction_language(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in ("never shorten solely", "never turn \"all\"", "never disable capabilities"):
            self.assertIn(phrase, text)

    def test_always_loaded_control_plane_budget(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 150)
        self.assertLessEqual(len(text.encode("utf-8")), 11000)
        self.assertIn("These references are cold-path detail", text)
        for rel in (
            "references/adaptive-routing.md",
            "references/connector-project-fastpath.md",
            "references/research-fastpath.md",
            "references/benchmark.md",
            "scripts/audit_skill_composition.py",
            "scripts/audit_skill_stalls.py",
            "references/stall-brain.md",
            "references/stall-patterns.json",
            "scripts/stall_brain.py",
            "references/watchdog.md",
            "scripts/watchdog.py",
            "references/global-memory-seed.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_anti_stall_contract(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "implementation crossing",
            "read-only circuit breaker",
            "narration as non-progress",
            "same-family search breaker",
            "stall-recovery checkpoint",
            "checkpoint-before-long-gate",
            "post-proof overlap rule",
            "resource-contention guard",
            "two unchanged status observations",
            "progress heartbeat",
            "implementation-first continuation",
            "known-fix stop barrier",
            "still-applicable domain constraint",
            "guardrail skill",
            "do not enumerate a whole skill directory",
            "runtime watchdog",
            "wait leases",
            "recovery capsule",
        ):
            self.assertIn(phrase, text)


    def test_embedded_stall_brain_contract(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Embedded Stall Brain", text)
        self.assertIn("references/stall-brain.md", text)
        self.assertIn("references/stall-patterns.json", text)
        brain = (ROOT / "references" / "stall-brain.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "skill transition resets execution state",
            "guardrail or subskill steals workflow ownership",
            "unbounded waits, socket timeouts, or retry budgets",
            "build/status ceremony displaces the usable artifact",
            "compaction/resume loses the exact next action",
            "installed skill silently rewrote itself",
        ):
            self.assertIn(phrase, brain)

        data = json.loads((ROOT / "references" / "stall-patterns.json").read_text(encoding="utf-8"))
        rules = data["rules"]
        self.assertGreaterEqual(len(rules), 40)
        self.assertEqual(len({r["id"] for r in rules}), len(rules))
        self.assertEqual(len({r["slug"] for r in rules}), len(rules))
        for rule in rules:
            for key in ("id", "slug", "scope", "failure", "required_behavior", "signals", "status"):
                self.assertIn(key, rule)
            self.assertEqual(rule["status"], "active")
            self.assertTrue(rule["signals"])



class AuditTests(unittest.TestCase):
    def run_audit(self, events):
        return audit(events, rapid_ci_ms=30000, rapid_rate_ms=30000)

    def test_repeated_read_same_version_flagged(self):
        r = self.run_audit([
            ev("a", target="file", version="1"),
            ev("b", target="file", version="1"),
        ])
        self.assertEqual(len(r["repeated_read_pairs"]), 1)

    def test_reread_after_version_change_not_flagged(self):
        r = self.run_audit([
            ev("a", target="file", version="1"),
            ev("b", target="file", version="2"),
        ])
        self.assertEqual(r["repeated_read_pairs"], [])

    def test_reread_after_write_not_flagged(self):
        r = self.run_audit([
            ev("a", target="file"),
            ev("w", op="write", target="file", category="write"),
            ev("b", target="file"),
        ])
        self.assertEqual(r["repeated_read_pairs"], [])

    def test_continuity_same_state_flagged(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="head", target="canonical state", category="continuity", repo="r", branch="main", head_sha="1"),
            ev("b", tool="GitHub", op="head", target="canonical state", category="continuity", repo="r", branch="main", head_sha="1"),
        ])
        self.assertEqual(len(r["continuity_resweep_pairs"]), 1)

    def test_continuity_after_write_not_false_positive(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="head", target="canonical state", category="continuity", repo="r", branch="main"),
            ev("w", tool="GitHub", op="commit", target="tree", category="repo_write", repo="r", branch="main"),
            ev("b", tool="GitHub", op="head", target="canonical state", category="continuity", repo="r", branch="main"),
        ])
        self.assertEqual(r["continuity_resweep_pairs"], [])

    def test_ci_state_transitions_are_legitimate(self):
        r = self.run_audit([
            ev("q", tool="GitHub", op="ci_status", target="run", category="ci_poll", run_id="9", ci_state="queued", start_ms=0, end_ms=100),
            ev("i", tool="GitHub", op="ci_status", target="run", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=500, end_ms=600),
            ev("c", tool="GitHub", op="ci_status", target="run", category="ci_poll", run_id="9", ci_state="completed", start_ms=1000, end_ms=1100),
        ])
        self.assertEqual(r["rapid_ci_poll_pairs"], [])
        self.assertEqual(r["ci_poll_storm_targets"], {})

    def test_ci_same_state_poll_storm_flagged(self):
        r = self.run_audit([
            ev("a", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=0, end_ms=100),
            ev("b", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=200, end_ms=300),
            ev("c", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=400, end_ms=500),
        ])
        self.assertTrue(r["rapid_ci_poll_pairs"])
        self.assertTrue(r["ci_poll_storm_targets"])

    def test_ci_retry_gap_measured_from_response_end(self):
        r = self.run_audit([
            ev("a", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=0, end_ms=20000),
            ev("b", category="ci_poll", run_id="9", ci_state="in_progress", start_ms=35000, end_ms=35100),
        ])
        self.assertEqual(len(r["rapid_ci_poll_pairs"]), 1, "15s idle gap should be rapid even though starts are 35s apart")

    def test_known_ci_run_then_broad_rediscovery_flagged(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="ci_status", target="run", category="ci_poll", repo="r", branch="main", run_id="42"),
            ev("b", tool="GitHub", op="list_workflow_runs", target="runs", category="ci_discovery", repo="r", branch="main"),
        ])
        self.assertEqual(len(r["broad_ci_rediscovery_after_known_run"]), 1)

    def test_no_dns_retry_flagged_and_invalidator_clears(self):
        failed = ev("a", tool="shell", op="clone", target="repo", route="runner-net", status="failed", error="DNS name resolution failed")
        r1 = self.run_audit([failed, ev("b", tool="shell", op="clone", target="repo", route="runner-net")])
        self.assertTrue(r1["hard_route_repeat_pairs"])
        r2 = self.run_audit([failed, ev("b", tool="shell", op="clone", target="repo", route="runner-net", invalidator="environment changed")])
        self.assertEqual(r2["hard_route_repeat_pairs"], [])

    def test_rate_limit_immediate_retry_flagged(self):
        r = self.run_audit([
            ev("a", op="search", route="provider", status="failed", http_status=429, retry_after_ms=30000, start_ms=0, end_ms=5000),
            ev("b", op="search", route="provider", start_ms=30000, end_ms=30100),
        ])
        self.assertTrue(r["rate_limit_hammer_pairs"], "only 25s elapsed after response; should still be pressure")

    def test_rate_limit_after_retry_window_allowed(self):
        r = self.run_audit([
            ev("a", op="search", route="provider", status="failed", http_status=429, retry_after_ms=30000, start_ms=0, end_ms=5000),
            ev("b", op="search", route="provider", start_ms=35000, end_ms=35100),
        ])
        self.assertEqual(r["rate_limit_hammer_pairs"], [])
        self.assertEqual(r["unchanged_retry_pairs"], [])

    def test_validation_repeated_same_state_flagged(self):
        r = self.run_audit([
            ev("a", op="test", target="suite", category="validation", state_version="1"),
            ev("b", op="test", target="suite", category="validation", state_version="1"),
        ])
        self.assertEqual(len(r["repeated_validation_pairs"]), 1)

    def test_validation_after_write_not_flagged(self):
        r = self.run_audit([
            ev("a", op="test", target="suite", category="validation"),
            ev("w", op="write", target="src", category="write"),
            ev("b", op="test", target="suite", category="validation"),
        ])
        self.assertEqual(r["repeated_validation_pairs"], [])
        self.assertNotIn("x|test|suite", r["stateless_duplicate_review_signatures"])

    def test_two_fragmented_repo_writes_are_reviewed(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="update_file", target="a", category="repo_write", repo="r", branch="main"),
            ev("b", tool="GitHub", op="update_file", target="b", category="repo_write", repo="r", branch="main"),
        ])
        self.assertTrue(r["fragmented_repo_write_groups"])

    def test_intentional_write_boundaries_not_flagged(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="commit", target="a", category="repo_write", repo="r", branch="main", intentional_boundary=True),
            ev("b", tool="GitHub", op="commit", target="b", category="repo_write", repo="r", branch="main", intentional_boundary=True),
        ])
        self.assertEqual(r["fragmented_repo_write_groups"], {})

    def test_three_serial_repo_reads_flagged(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="read", target="a", category="repo_read", repo="r", branch="main"),
            ev("b", tool="GitHub", op="read", target="b", category="repo_read", repo="r", branch="main"),
            ev("c", tool="GitHub", op="read", target="c", category="repo_read", repo="r", branch="main"),
        ])
        self.assertTrue(r["serial_repo_read_runs"])

    def test_dependent_serial_reads_not_flagged_as_parallelizable(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="read", target="a", category="repo_read", repo="r", branch="main"),
            ev("b", tool="GitHub", op="read", target="b", category="repo_read", repo="r", branch="main", depends_on=["a"]),
            ev("c", tool="GitHub", op="read", target="c", category="repo_read", repo="r", branch="main", depends_on=["b"]),
        ])
        self.assertEqual(r["serial_repo_read_runs"], {})

    def test_overlapping_singleflight_duplicate_flagged(self):
        r = self.run_audit([
            ev("a", tool="web", op="search", target="same", fingerprint="same", start_ms=0, end_ms=1000),
            ev("b", tool="web", op="search", target="same", fingerprint="same", start_ms=100, end_ms=900),
        ])
        self.assertTrue(r["overlapping_singleflight_pairs"])

    def test_quality_tags_collected(self):
        r = self.run_audit([
            ev("a", quality_satisfies=["maximum_effort", "full_scope"], satisfies=["deliverable"]),
        ])
        self.assertEqual(r["quality_tags"], ["full_scope", "maximum_effort"])
        self.assertEqual(r["acceptance_tags"], ["deliverable"])

    def test_search_then_fetch_same_target_not_duplicate_read(self):
        r = self.run_audit([
            ev("a", tool="web", op="search", target="topic"),
            ev("b", tool="web", op="fetch", target="topic"),
        ])
        self.assertEqual(r["repeated_read_pairs"], [])

    def test_different_discovery_ops_same_target_not_duplicate(self):
        r = self.run_audit([
            ev("a", tool="api", op="discover_schema", target="GitHub"),
            ev("b", tool="api", op="capabilities", target="GitHub"),
        ])
        self.assertEqual(r["repeated_discovery_pairs"], [])

    def test_candidate_group_respects_any_prior_dependency(self):
        r = self.run_audit([
            ev("a", op="read", target="a"),
            ev("b", op="read", target="b"),
            ev("c", op="read", target="c", depends_on=["a"]),
        ])
        self.assertNotIn([0, 1, 2], r["candidate_independent_groups"])
        self.assertIn([0, 1], r["candidate_independent_groups"])

    def test_candidate_group_excludes_mutations(self):
        r = self.run_audit([
            ev("a", op="read", target="a"),
            ev("w", op="write", target="x", category="write"),
            ev("b", op="read", target="b"),
        ])
        self.assertEqual(r["candidate_independent_groups"], [])

    def test_ci_rediscovery_without_safe_scope_not_flagged(self):
        r = self.run_audit([
            ev("a", tool="GitHub", op="ci_status", target="run", category="ci_poll", run_id="42"),
            ev("b", tool="GitHub", op="list_workflow_runs", target="runs", category="ci_discovery"),
        ])
        self.assertEqual(r["broad_ci_rediscovery_after_known_run"], [])

    def test_timing_coverage_reports_partial_trace(self):
        r = self.run_audit([
            ev("a", start_ms=0, end_ms=100),
            ev("b"),
        ])
        self.assertEqual(r["timed_events"], 1)
        self.assertEqual(r["timing_coverage"], 0.5)



class WatchdogTests(unittest.TestCase):
    def test_two_dead_waves_force_strategy_change(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "watchdog.json"
            def args(**kw):
                base = dict(state=str(state), accept=[], complete=[], canonical=[], evidence=[], hash=[], run=[], checkpoint=None, mutation=None, test=None, blocker=None, next_action="edit then targeted test", no_repeat=[], no_progress=True)
                base.update(kw)
                return type("A", (), base)()
            with mock.patch.object(watchdog, "now", return_value=100.0):
                self.assertEqual(watchdog.apply_update(args()), 0)
            with mock.patch.object(watchdog, "now", return_value=101.0):
                self.assertEqual(watchdog.apply_update(args()), 2)
            data = watchdog.load(state)
            self.assertEqual(data["watchdog"]["dead_waves"], 2)

    def test_progress_resets_dead_waves(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "watchdog.json"
            A = type("A", (), dict(state=str(state), accept=[], complete=[], canonical=[], evidence=[], hash=[], run=[], checkpoint=None, mutation=None, test=None, blocker=None, next_action="edit", no_repeat=[], no_progress=True))
            with mock.patch.object(watchdog, "now", return_value=100.0):
                watchdog.apply_update(A())
            B = type("B", (), dict(state=str(state), accept=[], complete=[], canonical=[], evidence=[], hash=[], run=[], checkpoint=None, mutation="patch-1", test=None, blocker=None, next_action="targeted test", no_repeat=[], no_progress=False))
            with mock.patch.object(watchdog, "now", return_value=101.0):
                self.assertEqual(watchdog.apply_update(B()), 0)
            self.assertEqual(watchdog.load(state)["watchdog"]["dead_waves"], 0)

    def test_wait_lease_expires_without_killing_identity(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "watchdog.json"
            start = type("S", (), dict(state=str(state), key="ci", kind="ci", identity="run-42", lease=10, status="in_progress"))
            with mock.patch.object(watchdog, "now", return_value=100.0):
                watchdog.wait_start(start())
            obs = type("O", (), dict(state=str(state), key="ci", status="in_progress", meaningful=False))
            with mock.patch.object(watchdog, "now", return_value=111.0):
                self.assertEqual(watchdog.wait_observe(obs()), 3)
            item = watchdog.load(state)["watchdog"]["waits"]["ci"]
            self.assertEqual(item["identity"], "run-42")
            self.assertFalse(item["closed"])

    def test_recovery_capsule_preserves_exact_next_action(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "watchdog.json"
            out = Path(td) / "capsule.json"
            A = type("A", (), dict(state=str(state), accept=["build"], complete=["source edit"], canonical=["repo=abc"], evidence=["log=v1"], hash=["jar=deadbeef"], run=["ci=42"], checkpoint="c1", mutation="m1", test="t1", blocker="waiting on CI", next_action="inspect exact run 42", no_repeat=["do not list runs again"], no_progress=False))
            with mock.patch.object(watchdog, "now", return_value=100.0):
                watchdog.apply_update(A())
            C = type("C", (), dict(state=str(state), output=str(out)))
            watchdog.capsule(C())
            cap = json.loads(out.read_text())
            self.assertEqual(cap["exact_next_action"], "inspect exact run 42")
            self.assertEqual(cap["runs"]["ci"], "42")
            self.assertIn("do not list runs again", cap["no_repeat"])


class CompareTests(unittest.TestCase):
    def summary(self, events):
        return audit(events, 30000, 30000)

    def test_faster_candidate_missing_acceptance_fails(self):
        base = self.summary([ev("a", satisfies=["source", "verify"], quality_satisfies=["maximum_effort"]), ev("b", op="noop")])
        cand = self.summary([ev("a", satisfies=["source"], quality_satisfies=["maximum_effort"])])
        r = compare(base, cand)
        self.assertEqual(r["acceptance_parity"], "fail")
        self.assertEqual(r["verdict"], "needs_tuning")

    def test_faster_candidate_missing_quality_fails(self):
        base = self.summary([ev("a", satisfies=["done"], quality_satisfies=["maximum_effort", "full_breadth"])])
        cand = self.summary([ev("a", satisfies=["done"], quality_satisfies=["maximum_effort"])])
        r = compare(base, cand)
        self.assertEqual(r["quality_parity"], "fail")
        self.assertIn("full_breadth", r["missing_quality_tags"])
        self.assertEqual(r["verdict"], "needs_tuning")

    def test_required_quality_guard_enforced(self):
        base = self.summary([ev("a", satisfies=["done"])])
        cand = self.summary([ev("a", satisfies=["done"])])
        r = compare(base, cand, required_quality={"maximum_effort"})
        self.assertEqual(r["quality_parity"], "fail")

    def test_full_observed_span_regression_fails_even_with_fewer_flags(self):
        base = self.summary([
            ev("a", op="noop", target="x", start_ms=0, end_ms=100),
            ev("b", op="noop", target="x", start_ms=100, end_ms=200),
        ])
        cand = self.summary([
            ev("a", op="noop", target="y", start_ms=0, end_ms=500),
        ])
        r = compare(base, cand)
        self.assertGreater(r["observed_trace_span_delta_ms"], 0)
        self.assertEqual(r["verdict"], "needs_tuning")

    def test_partial_timing_not_used_as_wall_clock_ground_truth(self):
        base = self.summary([ev("a", start_ms=0, end_ms=100), ev("b")])
        cand = self.summary([ev("a", start_ms=0, end_ms=10), ev("b")])
        r = compare(base, cand)
        self.assertIsNone(r["observed_trace_span_delta_ms"])



class PlannerTests(unittest.TestCase):
    def test_parallel_wave_and_critical_path(self):
        r = plan([
            {"id": "a", "duration_ms": 100},
            {"id": "b", "duration_ms": 200},
            {"id": "c", "depends_on": ["a", "b"], "duration_ms": 50},
        ])
        self.assertEqual(set(r["waves"][0]), {"a", "b"})
        self.assertEqual(r["critical_path_ms"], 250.0)

    def test_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            plan([
                {"id": "a", "depends_on": "b"},
                {"id": "b", "depends_on": "a"},
            ])

    def test_duplicate_fingerprints_reported(self):
        r = plan([
            {"id": "a", "fingerprint": "same"},
            {"id": "b", "fingerprint": "same"},
        ])
        self.assertEqual(r["duplicate_fingerprints"]["same"], ["a", "b"])

    def test_barrier_wave_makespan_is_reported(self):
        r = plan([
            {"id": "a", "duration_ms": 10},
            {"id": "b", "duration_ms": 100},
            {"id": "c", "depends_on": ["a"], "duration_ms": 100},
        ])
        self.assertEqual(r["critical_path_ms"], 110.0)
        self.assertEqual(r["barrier_wave_makespan_ms"], 200.0)
        self.assertEqual(r["optimized_barrier_makespan_ms"], 110.0)
        self.assertEqual(r["optimized_barrier_waves"], [["a"], ["b", "c"]])
        self.assertTrue(r["gateway_delay_risks"])

    def test_exact_barrier_scheduler_respects_exclusive_locks(self):
        r = plan([
            {"id": "a", "duration_ms": 10, "exclusive_key": "provider"},
            {"id": "b", "duration_ms": 20, "exclusive_key": "provider"},
            {"id": "c", "duration_ms": 15},
        ])
        for wave in r["optimized_barrier_waves"]:
            locked = [task for task in wave if task in {"a", "b"}]
            self.assertLessEqual(len(locked), 1)
        self.assertEqual(r["optimized_barrier_makespan_ms"], 30.0)

    def test_exact_barrier_scheduler_guard_for_large_plans(self):
        r = plan([{"id": str(i), "duration_ms": 1} for i in range(17)])
        self.assertIsNone(r["optimized_barrier_makespan_ms"])
        self.assertEqual(r["barrier_schedule_method"], "not_computed_over_16_tasks")

    def test_short_child_tail_not_reported_as_gateway_risk(self):
        r = plan([
            {"id": "a", "duration_ms": 10},
            {"id": "b", "duration_ms": 100},
            {"id": "c", "depends_on": ["a"], "duration_ms": 5},
        ])
        self.assertEqual(r["gateway_delay_risks"], [])



class ParserTests(unittest.TestCase):
    def test_json_and_jsonl(self):
        events = [ev("a"), ev("b")]
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "a.json"
            p2 = Path(td) / "b.jsonl"
            p1.write_text(json.dumps(events), encoding="utf-8")
            p2.write_text("\n".join(json.dumps(x) for x in events), encoding="utf-8")
            self.assertEqual(load_events(p1), events)
            self.assertEqual(load_events(p2), events)


if __name__ == "__main__":
    unittest.main(verbosity=2)
