from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("performance_audit", ROOT / "scripts" / "performance_audit.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

class PerformanceContractTests(unittest.TestCase):
    def test_performance_contract(self):
        report, errors = MOD.audit(ROOT)
        self.assertFalse(errors, "\n".join(errors))
        self.assertLessEqual(report["skill_bytes"], MOD.MAX_SKILL_BYTES)
        self.assertEqual(report["mandatory_reference_preload_bytes"], 0)
        self.assertTrue(report["jit_loading"])
        self.assertTrue(report["delta_continuity"])

if __name__ == "__main__":
    unittest.main()
