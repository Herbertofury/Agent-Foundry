import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/living_ecology.py"
REGISTRY = ROOT / "assets/memory/FEATURE-FOUNDRY-LIVING-ECOLOGY.seed.json"


class LivingEcologyTests(unittest.TestCase):
    def cmd(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            text=True,
            capture_output=True,
        )
        if ok and result.returncode:
            self.fail(result.stdout + result.stderr)
        return result

    def test_registry_validates_and_renders(self):
        self.cmd("validate")
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "living-ecology.md"
            self.cmd("render", "--output", output)
            text = output.read_text(encoding="utf-8")
            for phrase in (
                "Intent-aware anticipation",
                "Ecology Director",
                "Full World Traversal",
                "Content Age Patina",
                "Ecology Authoring Studio",
                "Performance capability ladder",
                "Potato-class",
            ):
                self.assertIn(phrase, text)

    def test_transition_depth_ladder_is_complete_and_interruptible(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        levels = data["transition_depth_ladder"]
        self.assertEqual([item["level"] for item in levels], list(range(6)))
        self.assertEqual(
            [item["id"] for item in levels],
            [
                "instant-focus",
                "ambient-echo",
                "local-material-journey",
                "shared-element-continuity",
                "workspace-recomposition",
                "full-world-traversal",
            ],
        )
        self.assertTrue(all(item["interruptible"] for item in levels))
        self.assertIn("Grass waves", levels[1]["example"])

    def test_performance_tiers_preserve_full_feature_and_data_parity(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        perf = data["performance_capability_ladder"]
        self.assertEqual(
            [item["id"] for item in perf["tiers"]],
            ["efficient", "balanced", "high", "ultra", "cinematic-lab"],
        )
        corpus = json.dumps(perf, ensure_ascii=False).lower()
        for phrase in (
            "viewport culling",
            "quantity caps",
            "remove features",
            "task-result correctness",
            "all objects remain selectable",
            "webgpu",
            "hysteresis",
        ):
            self.assertIn(phrase, corpus)

    def test_patina_channels_are_separate_and_reversible(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        memory = data["persistent_world_memory"]
        self.assertEqual(
            [item["id"] for item in memory["channels"]],
            ["chronological-patina", "interaction-patina", "authored-memory"],
        )
        corpus = json.dumps(memory, ensure_ascii=False).lower()
        for phrase in ("last played", "last updated", "frequently handled", "pristine reference", "reset"):
            self.assertIn(phrase, corpus)

    def test_authoring_studio_is_broad_and_runtime_connected(self):
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        studio = data["ecology_authoring_studio"]
        ids = {item["id"] for item in studio["tool_families"]}
        for item_id in (
            "transition-choreographer",
            "interaction-recorder",
            "material-laboratory",
            "ecology-graph",
            "spatial-audio-lab",
            "device-and-tier-simulator",
            "causal-debugger",
            "optimization-compiler",
            "authoring-version-control",
            "extension-sdk",
        ):
            self.assertIn(item_id, ids)
        self.assertGreaterEqual(len(ids), 10)
        self.assertTrue(any(test["id"] == "authoring-to-runtime" for test in data["acceptance_tests"]))

    def test_validator_rejects_feature_loss_guardrail_removal(self):
        with tempfile.TemporaryDirectory() as td:
            data = json.loads(REGISTRY.read_text(encoding="utf-8"))
            data["performance_capability_ladder"]["hard_guardrails"] = []
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps(data), encoding="utf-8")
            result = self.cmd("validate", "--registry", bad, ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing guardrail concept", result.stdout)


if __name__ == "__main__":
    unittest.main()
