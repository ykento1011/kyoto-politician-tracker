"""Offline identity negatives and progress/KPI protection; no official GET."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mayor_updates.progress_evidence import legislative_match, validate_progress
from mayor_updates.projection import Hold

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT.parent / "frontend/public/data/kyoto_mayor_tracker.json").read_text(encoding="utf-8-sig"))
        # Synthetic source-reviewed identity for function tests, not an authenticated real bill.
        self.bill = dict(city_code="kyoto", session_year=2025, session_name="令和7年9月市会",
                         bill_number="議1", bill_title="試験用条例", result="可決",
                         source_url="https://www2.city.kyoto.lg.jp/example.html")
        self.hosts = {"www2.city.kyoto.lg.jp"}

    def match(self, b, rows):
        return legislative_match(b, rows, "kyoto", self.hosts)

    def test_complete_identity_requires_source_review(self):
        self.assertFalse(self.match(self.bill, [self.bill]))
        row = dict(self.bill, verification_status="source_checked")
        self.assertTrue(self.match(self.bill, [row]))
        self.assertFalse(self.match(self.bill, [row, row]))

    def test_every_composite_key_mismatch_fails_closed(self):
        official = dict(self.bill, verification_status="source_checked")
        for key, value in dict(city_code="kobe", session_year=2026, session_name="令和7年7月市会",
                               bill_number="議2", bill_title="別条例",
                               source_url="https://www2.city.kyoto.lg.jp/other.html",
                               result="否決").items():
            with self.subTest(key=key):
                self.assertFalse(self.match(dict(self.bill, **{key: value}), [official]))
                missing = dict(self.bill); missing.pop(key)
                self.assertFalse(self.match(missing, [official]))

    def test_bad_url_and_budget_year_are_not_identity(self):
        for url in ["http://www2.city.kyoto.lg.jp/example.html",
                    "https://example.org/example.html",
                    self.bill["source_url"] + "?year=2025"]:
            b = dict(self.bill, source_url=url)
            self.assertFalse(self.match(b, [dict(b, verification_status="source_checked")]))
        b = dict(self.bill, session_year=2026)  # upcoming fiscal year is not session year
        self.assertFalse(self.match(b, [dict(b, verification_status="source_checked")]))

    def test_real_registrations_remain_held_not_replaced(self):
        a, b = self.data["pledges"][:2]
        self.assertEqual([p["legislative_bill"]["bill_number"] for p in [a,b]], ["議88","議145"])
        votes = json.loads((ROOT.parent/"frontend/public/data/kyoto_votes_summary.json").read_text(encoding="utf-8"))
        self.assertFalse(any(v["session_name"] == a["legislative_bill"]["session_name"] and v["bill_number"] == "議88" for v in votes))
        other = [v for v in votes if v["session_name"] == b["legislative_bill"]["session_name"] and v["bill_number"] == "議145"]
        self.assertTrue(other)
        self.assertTrue(all(v["title"] != b["legislative_bill"]["bill_title"] for v in other))
        for p in [a,b]:
            self.assertFalse(self.match(p["legislative_bill"], votes))
            self.assertEqual(p["legislative_bill"]["verification_status"], "hold")
        self.assertEqual(a["milestone"]["policy_relation"], "contextual")

    def test_current_aggregate_and_budget_boundaries(self):
        self.assertTrue(validate_progress(self.data))
        a = self.data["pledges"][0]
        self.assertEqual([(r["amount_jpy"],r["policy_relation"]) for r in a["budget_records"]],
                         [(271000000,"direct"),(269000000,"contextual")])
        self.assertEqual(self.data["summary_stats"]["total_allocated_budget_raw"],9115487000)
        self.assertEqual(self.data["kpis"][0]["value"],"85.7%")
        self.assertIn("確定済み件数・公約達成率ではありません", self.data["kpis"][0]["evidence_note"])
        from mayor_updates.projection import included, format_record_amount
        legacy = sum(r["amount_jpy"] for p in self.data["pledges"] for r in p["budget_records"]
                     if "policy_relation" not in r and included(r))
        self.assertIn(format_record_amount(dict(amount_jpy=legacy, amount_role="initial")),
                      self.data["kpis"][1]["evidence_note"])

    def test_progress_promotion_or_misleading_label_rejected(self):
        for key,value in [("stage_label","予算化・実証中"),("stage_level",4)]:
            d=deepcopy(self.data);d["pledges"][0][key]=value
            with self.assertRaises(Hold):validate_progress(d)
        d=deepcopy(self.data);d["pledges"][0]["milestone"]["policy_relation"]="direct"
        with self.assertRaises(Hold):validate_progress(d)
        d=deepcopy(self.data);d["pledges"][1]["legislative_bill"]["verification_status"]="verified"
        with self.assertRaises(Hold):validate_progress(d)

    def test_stale_card_summary_kpi_or_amount_rejected(self):
        for mutate in [lambda d:d["pledges"][2].update(stage_level=2),
                       lambda d:d["summary_stats"]["stages"].update(enacted=3),
                       lambda d:d["kpis"][0].update(value="100%"),
                       lambda d:d["kpis"][0].update(subtext="14/14事業で予算措置・成立"),
                       lambda d:d["summary_stats"].update(total_allocated_budget_raw=1)]:
            d=deepcopy(self.data);mutate(d)
            with self.assertRaises(Hold):validate_progress(d)

    def test_generator_preserves_hold_and_p03_history(self):
        spec=importlib.util.spec_from_file_location("builder",ROOT/"build_mayor_tracker.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.generation_output(),self.data)
        p=self.data["pledges"][2]
        self.assertEqual(p["stage_level"],4)
        self.assertEqual(p["latest_update"]["kind"],"construction_paused")
        self.assertEqual(p["legislative_bill"]["bill_number"],"議104")

if __name__ == "__main__": unittest.main()
