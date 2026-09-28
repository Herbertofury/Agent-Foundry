#!/usr/bin/env python3
"""Compare baseline and accelerated traces without pretending structure proves quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_trace import audit, load_events  # noqa: E402


def compare(
    base: dict[str, Any], candidate: dict[str, Any], required_tags: set[str] | None = None,
    required_quality: set[str] | None = None, span_tolerance_ms: float = 0.0,
) -> dict[str, Any]:
    before_tags = set(base.get("acceptance_tags", [])) | set(required_tags or set())
    after_tags = set(candidate.get("acceptance_tags", []))
    if before_tags:
        missing = sorted(before_tags - after_tags)
        acceptance = "pass" if not missing else "fail"
    else:
        missing = []
        acceptance = "manual_review"

    before_quality = set(base.get("quality_tags", [])) | set(required_quality or set())
    after_quality = set(candidate.get("quality_tags", []))
    if before_quality:
        missing_quality = sorted(before_quality - after_quality)
        quality = "pass" if not missing_quality else "fail"
    else:
        missing_quality = []
        quality = "manual_review"

    before_cp = base.get("declared_critical_path_ms")
    after_cp = candidate.get("declared_critical_path_ms")
    if before_cp is not None and after_cp is not None:
        cp_delta = round(float(after_cp) - float(before_cp), 3)
        cp_improved = after_cp < before_cp
    else:
        cp_delta = None
        cp_improved = None

    event_delta = int(candidate["events"]) - int(base["events"])
    flag_delta = int(candidate["review_flags"]) - int(base["review_flags"])

    before_span = base.get("observed_trace_span_ms")
    after_span = candidate.get("observed_trace_span_ms")
    full_timing = float(base.get("timing_coverage", 0.0)) >= 1.0 and float(candidate.get("timing_coverage", 0.0)) >= 1.0
    if full_timing and before_span is not None and after_span is not None:
        span_delta = round(float(after_span) - float(before_span), 3)
        span_improved = span_delta < -abs(span_tolerance_ms)
        span_regressed = span_delta > abs(span_tolerance_ms)
    else:
        span_delta = None
        span_improved = None
        span_regressed = None

    # Fully observed wall-clock span outranks structural heuristics. Heuristics still
    # matter when timings are absent/equal and remain visible for manual review.
    structural_improvement = (span_improved is True) or flag_delta < 0 or (cp_improved is True)
    structural_regression = (span_regressed is True) or flag_delta > 0 or (cp_improved is False and cp_delta is not None and cp_delta > 0)

    if acceptance == "fail" or quality == "fail":
        verdict = "needs_tuning"
    elif structural_regression:
        verdict = "needs_tuning"
    elif structural_improvement:
        verdict = "pass_with_manual_quality_review" if acceptance == "manual_review" or quality == "manual_review" else "pass"
    else:
        verdict = "neutral_with_manual_quality_review" if acceptance == "manual_review" or quality == "manual_review" else "neutral"

    return {
        "acceptance_parity": acceptance,
        "missing_acceptance_tags": missing,
        "quality_parity": quality,
        "missing_quality_tags": missing_quality,
        "baseline_events": base["events"],
        "candidate_events": candidate["events"],
        "event_delta": event_delta,
        "baseline_review_flags": base["review_flags"],
        "candidate_review_flags": candidate["review_flags"],
        "review_flag_delta": flag_delta,
        "baseline_declared_critical_path_ms": before_cp,
        "candidate_declared_critical_path_ms": after_cp,
        "critical_path_delta_ms": cp_delta,
        "baseline_observed_trace_span_ms": before_span,
        "candidate_observed_trace_span_ms": after_span,
        "observed_trace_span_delta_ms": span_delta,
        "baseline_timing_coverage": base.get("timing_coverage"),
        "candidate_timing_coverage": candidate.get("timing_coverage"),
        "verdict": verdict,
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Acceptance parity: {report['acceptance_parity']}")
    print(f"Quality parity: {report['quality_parity']}")
    if report["missing_acceptance_tags"]:
        print("Missing acceptance tags: " + ", ".join(report["missing_acceptance_tags"]))
    if report["missing_quality_tags"]:
        print("Missing quality tags: " + ", ".join(report["missing_quality_tags"]))
    print(f"Events: {report['baseline_events']} -> {report['candidate_events']} ({report['event_delta']:+d})")
    print(
        f"Review flags: {report['baseline_review_flags']} -> "
        f"{report['candidate_review_flags']} ({report['review_flag_delta']:+d})"
    )
    if report["observed_trace_span_delta_ms"] is not None:
        print(
            f"Observed trace span: {report['baseline_observed_trace_span_ms']:.3f} -> "
            f"{report['candidate_observed_trace_span_ms']:.3f} ms "
            f"({report['observed_trace_span_delta_ms']:+.3f})"
        )
    if report["critical_path_delta_ms"] is not None:
        print(
            f"Declared critical path: {report['baseline_declared_critical_path_ms']:.3f} -> "
            f"{report['candidate_declared_critical_path_ms']:.3f} ms "
            f"({report['critical_path_delta_ms']:+.3f})"
        )
    print(f"Verdict: {report['verdict']}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rapid-ci-ms", type=float, default=30000.0)
    parser.add_argument("--rapid-rate-ms", type=float, default=30000.0)
    parser.add_argument(
        "--span-tolerance-ms", type=float, default=0.0,
        help="ignore observed trace-span differences within this absolute tolerance",
    )
    parser.add_argument(
        "--require", action="append", default=[], metavar="TAG",
        help="acceptance tag that the candidate must preserve; may be repeated",
    )
    parser.add_argument(
        "--require-quality", action="append", default=[], metavar="TAG",
        help="quality invariant that the candidate must preserve; may be repeated",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        base_events = load_events(args.baseline)
        cand_events = load_events(args.candidate)
        base = audit(base_events, args.rapid_ci_ms, args.rapid_rate_ms)
        candidate = audit(cand_events, args.rapid_ci_ms, args.rapid_rate_ms)
        report = compare(
            base, candidate, set(args.require), set(args.require_quality),
            span_tolerance_ms=args.span_tolerance_ms,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 1 if report["verdict"] == "needs_tuning" else 0


if __name__ == "__main__":
    raise SystemExit(main())
