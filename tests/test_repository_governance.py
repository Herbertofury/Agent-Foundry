import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import repository_governance as governance

INSTALLER = ROOT / "skills/project-brain-orchestrator/scripts/install_agents_bundle.py"


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


class RepositoryGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.target = self.base / "consumer"
        self.source.mkdir()
        self.target.mkdir()
        for name in governance.POLICY_FILES:
            dest = self.source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        (self.source / "registry").mkdir()
        self.manifest()
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)

    def manifest(self, version="1.0.0"):
        governance.atomic_json(self.source / governance.MANIFEST, governance.release(self.source, version))

    def adopted(self):
        actions = governance.apply(self.source, self.target)
        self.assertTrue(all(x["action"] == "noop" for x in actions))

    def test_plan_is_read_only_and_preserves_local_instructions(self):
        root = self.target / "AGENTS.md"
        root.write_text("# Local\nKeep product commands and privacy restrictions.\n", encoding="utf-8")
        nested = self.target / "src/AGENTS.md"
        nested.parent.mkdir()
        nested.write_text("# Subsystem\nKeep local invariants.\n", encoding="utf-8")
        before = files(self.target)
        actions = governance.plan(self.source, self.target)[2]
        self.assertEqual(files(self.target), before)
        self.assertIn("review", {x["action"] for x in actions})
        actions = governance.apply(self.source, self.target)
        self.assertEqual(root.read_bytes(), before["AGENTS.md"])
        self.assertEqual(nested.read_bytes(), before["src/AGENTS.md"])
        self.assertIn("review", {x["action"] for x in actions})
        root.write_text(root.read_text(encoding="utf-8") + "Read `.agents/foundry/AGENTS-adapter.md`.\n", encoding="utf-8")
        self.assertTrue(all(x["action"] == "noop" for x in governance.plan(self.source, self.target)[2]))

    def test_adoption_records_clean_commit_and_numbered_invariants(self):
        self.adopted()
        lock = governance.load_json(self.target / governance.LOCK, {})
        self.assertRegex(lock["sourceCommit"], r"^[a-f0-9]{40}$")
        self.assertFalse(lock["sourceWorkingTreeDirty"])
        self.assertEqual(governance.checked_release(self.source)["invariantIds"], list(range(1, 19)))
        self.assertLess((self.target / "AGENTS.md").stat().st_size, 3000)

    def test_versioned_update_preserves_custom_root(self):
        self.adopted()
        root = self.target / "AGENTS.md"
        root.write_text(root.read_text(encoding="utf-8") + "\nKeep my local build command.\n", encoding="utf-8")
        before = root.read_bytes()
        policy = self.source / "MODERNIZATION_STANDARD.md"
        policy.write_text(policy.read_text(encoding="utf-8") + "\nNew shared detail.\n", encoding="utf-8")
        self.manifest("1.0.1")
        self.adopted()
        self.assertEqual(root.read_bytes(), before)
        self.assertEqual(governance.load_json(self.target / governance.LOCK, {})["version"], "1.0.1")

    def test_edited_or_removed_managed_policy_stops_entire_apply(self):
        self.adopted()
        edited = self.target / governance.SNAPSHOT / "PRODUCT_INVARIANTS.md"
        edited.write_text("# My customization\n", encoding="utf-8")
        before = files(self.target)
        with self.assertRaisesRegex(ValueError, "no files changed"):
            governance.apply(self.source, self.target)
        self.assertEqual(files(self.target), before)
        edited.unlink()
        before = files(self.target)
        with self.assertRaisesRegex(ValueError, "no files changed"):
            governance.apply(self.source, self.target)
        self.assertEqual(files(self.target), before)

    def test_unmanaged_destination_is_not_adopted_or_overwritten(self):
        path = self.target / governance.SNAPSHOT / "RUNTIME_PROOF.md"
        path.parent.mkdir(parents=True)
        path.write_text("User-owned policy\n", encoding="utf-8")
        before = files(self.target)
        with self.assertRaises(ValueError):
            governance.apply(self.source, self.target)
        self.assertEqual(files(self.target), before)

    def test_stale_source_manifest_and_same_version_change_fail(self):
        path = self.source / "RUNTIME_PROOF.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nChanged rule.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "canonical policy drift"):
            governance.plan(self.source, self.target)
        result = subprocess.run([sys.executable, str(ROOT / "tools/repository_governance.py"),
                                 "manifest", "--repo", str(self.source), "--version", "1.0.0"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("newer version", result.stderr)
        self.assertEqual(files(self.target), {})

    def test_line_endings_do_not_create_false_drift(self):
        self.adopted()
        path = self.target / governance.SNAPSHOT / "RUNTIME_PROOF.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(all(x["action"] == "noop" for x in governance.plan(self.source, self.target)[2]))

    def test_root_override_requires_review_and_remains_unchanged(self):
        self.adopted()
        path = self.target / "AGENTS.override.md"
        path.write_text("# Local override\nKeep this policy.\n", encoding="utf-8")
        before = path.read_bytes()
        actions = governance.apply(self.source, self.target)
        self.assertTrue(any(x["action"] == "review" and x["path"] == "AGENTS.override.md" for x in actions))
        self.assertEqual(path.read_bytes(), before)

    def test_manifest_order_is_independent_of_path_platform(self):
        import source_manifest
        path = self.base / "sample-skill"
        (path / "assets").mkdir(parents=True)
        (path / "README.md").write_text("Readme", encoding="utf-8")
        (path / "assets/a.txt").write_text("Asset", encoding="utf-8")
        record = source_manifest.skill_record(path)
        self.assertEqual([x["path"] for x in record["files"]], ["README.md", "assets/a.txt"])

    def test_linked_snapshot_directory_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.target / ".agents").mkdir()
        try:
            (self.target / governance.SNAPSHOT).symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "linked destination"):
            governance.plan(self.source, self.target)
        self.assertEqual(files(outside), {})

    def test_installer_defaults_to_thin_policy_and_dry_run_writes_nothing(self):
        def run(*args):
            return subprocess.run([sys.executable, str(INSTALLER), str(self.target), *args],
                                  capture_output=True, text=True)
        self.assertEqual(run("--dry-run").returncode, 0)
        self.assertEqual(files(self.target), {})
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess((self.target / "AGENTS.md").stat().st_size, 3000)
        self.assertFalse((self.target / ".agents/tools").exists())
        before = files(self.target)
        self.assertNotEqual(run("--mode", "hybrid", "--legacy-chat-contract").returncode, 0)
        self.assertEqual(files(self.target), before)


if __name__ == "__main__":
    unittest.main()
