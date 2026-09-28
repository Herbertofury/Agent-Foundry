#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).with_name("northpoint_compose.py")


def write(root: pathlib.Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


with tempfile.TemporaryDirectory(prefix="northpoint-compose-config-") as td:
    root = pathlib.Path(td)
    project = root / "project"
    output = root / "composed"
    project.mkdir()
    cfg = {
        "schema_version": 1,
        "mod_id": "configproof",
        "build": {
            "mode": "javac",
            "source_roots": ["src/main/java"],
            "compile_only_source_roots": ["qa-api/java"],
            "resource_roots": ["src/main/resources"],
        },
        "runtime": {"required": True, "scope": "both"},
    }
    write(project, "northpoint.project.json", json.dumps(cfg, indent=2) + "\n")
    write(project, "overlays/common/src/main/java/example/Main.java", "package example; public class Main {}\n")
    write(project, "overlays/common/qa-api/java/example/Api.java", "package example; public interface Api {}\n")
    cell_path = root / "cell.json"
    cell_path.write_text(
        json.dumps(
            {
                "id": "mc-1.21.1-fabric",
                "minecraft": "1.21.1",
                "loader": "fabric",
                "java": 21,
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project",
            str(project),
            "--cell-json",
            str(cell_path),
            "--output",
            str(output),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    composed_cfg = json.loads((output / "northpoint.project.json").read_text(encoding="utf-8"))
    assert composed_cfg["mod_id"] == "configproof", composed_cfg
    assert composed_cfg["build"]["compile_only_source_roots"] == ["qa-api/java"], composed_cfg
    assert composed_cfg["runtime"]["scope"] == "both", composed_cfg
    manifest = json.loads((output / ".northpoint-compose.json").read_text(encoding="utf-8"))
    assert manifest["files"]["northpoint.project.json"]["origin"] == "config:root", manifest

print("Northpoint compose config self-test: PASS")
