import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "skills" / "ultimate-agent-governance" / "scripts" / "performance_gate.py"
SPEC = importlib.util.spec_from_file_location("performance_gate", PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class PerformanceGateTests(unittest.TestCase):
    def base(self):
        return {
            "scenario": "browse",
            "workload_identity": "mods-1000",
            "result_identity": "same-results",
            "metrics": {"latency_ms": 100, "memory_mb": 500, "cpu_ms": 80},
        }

    def policy(self):
        return {
            "metrics": {
                "latency_ms": {"direction": "lower", "required_improvement": True},
                "memory_mb": {"direction": "lower"},
                "cpu_ms": {"direction": "lower"},
            }
        }

    def test_zero_loss_win_passes(self):
        candidate = {
            **self.base(),
            "metrics": {"latency_ms": 80, "memory_mb": 500, "cpu_ms": 75},
        }
        result = MOD.compare(self.base(), candidate, self.policy())
        self.assertTrue(result["passed"], result["errors"])

    def test_shifted_cost_regression_fails(self):
        candidate = {
            **self.base(),
            "metrics": {"latency_ms": 70, "memory_mb": 550, "cpu_ms": 75},
        }
        result = MOD.compare(self.base(), candidate, self.policy())
        self.assertFalse(result["passed"])
        self.assertTrue(any("memory_mb" in error for error in result["errors"]))

    def test_untracked_baseline_metric_fails(self):
        candidate = {
            **self.base(),
            "metrics": {"latency_ms": 80, "memory_mb": 500, "cpu_ms": 75},
        }
        policy = {
            "metrics": {
                "latency_ms": {"direction": "lower", "required_improvement": True},
                "memory_mb": {"direction": "lower"},
            }
        }
        result = MOD.compare(self.base(), candidate, policy)
        self.assertFalse(result["passed"])
        self.assertIn("cpu_ms", result["untracked_baseline_metrics"])

    def test_nonzero_regression_budget_requires_reason(self):
        candidate = {
            **self.base(),
            "metrics": {"latency_ms": 80, "memory_mb": 505, "cpu_ms": 75},
        }
        policy = self.policy()
        policy["metrics"]["memory_mb"]["max_regression_percent"] = 2
        result = MOD.compare(self.base(), candidate, policy)
        self.assertFalse(result["passed"])
        self.assertTrue(any("regression_budget_reason" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
