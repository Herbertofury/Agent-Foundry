#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import os
import json
import pathlib
import subprocess
import sys
import tempfile

from northpoint_execution import atomic_json, contained_file, run_logged, sha256_file

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "northpoint_production_driver.py"


def last_json(text: str) -> dict:
    for line in reversed([row.strip() for row in text.splitlines() if row.strip()]):
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError("production driver returned no JSON receipt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Northpoint production conversion against a real mod source tree.")
    parser.add_argument("--project", type=pathlib.Path, required=True)
    parser.add_argument("--minecraft", required=True)
    parser.add_argument("--loader", required=True)
    parser.add_argument("--java", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--workspace", type=pathlib.Path, help="New empty durable run directory (never deleted)")
    parser.add_argument("--java-path", help="Exact JDK java executable; javac must be beside it")
    parser.add_argument("--expect-source-minecraft")
    parser.add_argument("--expect-rewrite", action="append", default=[])
    parser.add_argument("--expect-preserved-property", action="append", default=[])
    parser.add_argument("--expect-preserved-build-block", action="append", default=[])
    args = parser.parse_args()

    project = args.project.resolve()
    if not project.is_dir():
        raise SystemExit(f"project does not exist: {project}")

    if args.workspace:
        root = args.workspace.resolve()
        if root == project or root.is_relative_to(project):
            raise SystemExit("smoke workspace must be outside the source project")
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise SystemExit(f"workspace must be empty; existing evidence was preserved: {root}")
    else:
        parent = pathlib.Path(os.environ.get("NORTHPOINT_SMOKE_ROOT", str(pathlib.Path.cwd() / ".northpoint" / "public-mod-smoke")))
        parent.mkdir(parents=True, exist_ok=True)
        root = pathlib.Path(tempfile.mkdtemp(prefix="run-", dir=parent)).resolve()
    print(f"Northpoint durable workspace: {root}", flush=True)
    with contextlib.nullcontext(root):
        work = root / "work"
        output = root / "output"
        cell = root / "cell.json"
        cell.write_text(
            json.dumps(
                {
                    "id": f"mc-{args.minecraft}-{args.loader}",
                    "minecraft": args.minecraft,
                    "loader": args.loader,
                    "java": args.java,
                    "java_path": args.java_path or "",
                    "support_state": "stable",
                    "primary": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cp = run_logged(
            [
                sys.executable,
                str(DRIVER),
                "--cell-json",
                str(cell),
                "--project",
                str(project),
                "--work",
                str(work),
                "--output",
                str(output),
                "--timeout",
                str(args.timeout),
            ],
            directory=root,
            name="driver",
            timeout=args.timeout + 60,
        )
        atomic_json(root / "execution.json", {"returncode": cp.returncode, "workspace": str(root),
                                              "project": str(project), "minecraft": args.minecraft, "loader": args.loader})
        if cp.returncode != 0:
            raise AssertionError(f"driver exited {cp.returncode}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}")
        receipt = last_json(cp.stdout)
        atomic_json(root / "receipt.json", receipt)
        if receipt.get("state") not in {"passed", "runtime-unverified"}:
            raise AssertionError(json.dumps(receipt, indent=2))
        artifact = receipt.get("artifact")
        if not artifact:
            raise AssertionError(f"verified/candidate receipt has no artifact: {receipt}")
        artifact_path = contained_file(output, str(artifact))
        if not artifact_path.is_file() or artifact_path.stat().st_size <= 0:
            raise AssertionError(f"artifact is missing or empty: {artifact_path}")
        evidence = receipt.get("evidence") or []
        if not any(str(row).startswith("metadata:") for row in evidence):
            raise AssertionError(f"loader metadata was not verified: {evidence}")

        conversion = receipt.get("conversion")
        if args.expect_source_minecraft:
            if not isinstance(conversion, dict):
                raise AssertionError(f"expected a source-to-target conversion receipt: {receipt}")
            source = conversion.get("source") or {}
            target = conversion.get("target") or {}
            if str(source.get("minecraft")) != str(args.expect_source_minecraft):
                raise AssertionError(f"conversion source mismatch: {source}")
            if str(target.get("minecraft")) != str(args.minecraft):
                raise AssertionError(f"conversion target mismatch: {target}")
            if conversion.get("source_unchanged") is not True:
                raise AssertionError(f"source immutability was not proven: {conversion}")
            applied = set(map(str, conversion.get("applied_rule_ids") or []))
            missing_rules = [rule for rule in args.expect_rewrite if rule not in applied]
            if missing_rules:
                raise AssertionError(f"expected conversion rewrites were not applied: {missing_rules}; got={sorted(applied)}")
            preserved_properties = set(map(str, conversion.get("preserved_gradle_properties") or []))
            missing_properties = [key for key in args.expect_preserved_property if key not in preserved_properties]
            if missing_properties:
                raise AssertionError(
                    f"expected Gradle properties were not preserved: {missing_properties}; got={sorted(preserved_properties)}"
                )
            preserved_blocks = conversion.get("preserved_gradle_blocks") or {}
            missing_blocks = [name for name in args.expect_preserved_build_block if int(preserved_blocks.get(name) or 0) <= 0]
            if missing_blocks:
                raise AssertionError(
                    f"expected Gradle build blocks were not preserved: {missing_blocks}; got={preserved_blocks}"
                )
        summary = {
            "status": "PASS", "state": receipt["state"],
            "artifact": artifact_path.name, "artifact_path": str(artifact_path),
            "sha256": sha256_file(artifact_path), "size": artifact_path.stat().st_size,
            "workspace": str(root), "evidence_count": len(evidence),
            "converted_from": (conversion.get("source") or {}).get("minecraft") if isinstance(conversion, dict) else None,
            "conversion_rules": conversion.get("applied_rule_ids") if isinstance(conversion, dict) else [],
        }
        atomic_json(root / "summary.json", summary)
        (root / "SHA256SUMS.txt").write_text(f"{summary['sha256']}  output/{artifact_path.name}\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
    print("Northpoint public mod production smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
