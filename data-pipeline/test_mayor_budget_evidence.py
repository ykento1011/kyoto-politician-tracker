import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mayor_builder", ROOT / "data-pipeline/build_mayor_tracker.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BudgetEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "frontend/public/data/kyoto_mayor_tracker.json").read_text(encoding="utf-8"))
        self.policy = next(p for p in self.data["pledges"] if p["id"] == "P-01")

    def test_generator_preserves_reviewed_records(self):
        seed = next(p for p in builder.PLEDGES_MASTER if p["id"] == "P-01")
        self.assertEqual(seed["budget_records"], self.policy["budget_records"])

    def test_direct_total_excludes_reference_and_unknown(self):
        records = self.policy["budget_records"]
        self.assertEqual(sum(r["amount_jpy"] for r in records if builder.included_in_budget_total(r)), 271000000)
        for value in ("contextual", "unconfirmed", "unexpected", None):
            self.assertFalse(builder.included_in_budget_total({"policy_relation": value, "amount_jpy": 1}))
        self.assertTrue(builder.included_in_budget_total({"amount_jpy": 1}))

    def test_published_summary_and_dynamic_label_agree(self):
        summary = builder.calculate_summary_stats(self.data["pledges"])
        for key in ("total_allocated_budget_raw", "total_allocated_budget_jpy"):
            self.assertEqual(summary[key], self.data["summary_stats"][key])
        self.assertEqual(builder.format_budget_total(271000000), "2億7,100万円")
        self.assertEqual(builder.format_budget_total(15000), "2万円")


if __name__ == "__main__":
    unittest.main()
