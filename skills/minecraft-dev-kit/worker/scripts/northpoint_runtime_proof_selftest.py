#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "northpoint_job_runner.py"
DRIVER = ROOT / "scripts" / "northpoint_production_driver.py"


def write(root: pathlib.Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(cmd: list[str]) -> tuple[int, dict]:
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            return cp.returncode, value
    raise AssertionError(f"runner returned no JSON receipt\n{cp.stdout}\n{cp.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="northpoint-runtime-proof-") as td:
        root = pathlib.Path(td)
        project = root / "project"
        state = root / "state"
        write(project, "src/main/java/example/Proof.java", "package example; public final class Proof { public static int value(){ return 42; } }\n")
        write(
            project,
            "src/main/resources/fabric.mod.json",
            json.dumps(
                {
                    "schemaVersion": 1,
                    "id": "runtimeproof",
                    "version": "1.0.0",
                    "name": "Runtime Proof",
                    "environment": "*",
                },
                indent=2,
            )
            + "\n",
        )
        cell_id = "mc-1.21.1-fabric"
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_root": str(project),
                    "primary_cell": cell_id,
                    "cells": [
                        {
                            "id": cell_id,
                            "minecraft": "1.21.1",
                            "loader": "fabric",
                            "java": 21,
                            "support_state": "stable",
                            "primary": True,
                        }
                    ],
                    "config": {"zero_loss": True},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cmd = [
            sys.executable,
            str(RUNNER),
            "--manifest",
            str(manifest),
            "--driver",
            str(DRIVER),
            "--state-dir",
            str(state),
            "--timeout",
            "120",
        ]
        first_code, first = run(cmd)
        assert first_code == 2, (first_code, first)
        assert first["status"] == "FAILED_PRIMARY", first
        matrix = json.loads((state / "release" / "release-matrix.json").read_text(encoding="utf-8"))
        row = next(row for row in matrix["cells"] if row["cell_id"] == cell_id)
        assert row["state"] == "runtime-unverified", row
        artifact = row["artifact"]
        assert artifact["sha256"] and artifact["file"], artifact
        candidate = state / "release" / artifact["file"]
        assert candidate.is_file() and candidate.stat().st_size > 0, candidate

        proofs = root / "runtime-proofs.json"
        proofs.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "proofs": [
                        {
                            "cell_id": cell_id,
                            "artifact_sha256": artifact["sha256"],
                            "passed": True,
                            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "evidence": ["fixture-native-runtime:PASS"],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        second_code, second = run(cmd + ["--runtime-proofs", str(proofs)])
        assert second_code == 0, (second_code, second)
        assert second["status"] == "PASS", second
        assert second["run"]["built"] == [], second
        assert second["run"]["reused"] == [cell_id], second
        assert second["run"]["runtime_promoted"] == [cell_id], second
        final_matrix = json.loads((state / "release" / "release-matrix.json").read_text(encoding="utf-8"))
        final_row = next(row for row in final_matrix["cells"] if row["cell_id"] == cell_id)
        assert final_row["state"] == "passed", final_row
        assert final_row["artifact"]["sha256"] == artifact["sha256"], final_row

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "candidate_sha256": artifact["sha256"],
                    "first": first["run"],
                    "promotion": second["run"],
                },
                indent=2,
            )
        )
    print("Northpoint external runtime proof self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
