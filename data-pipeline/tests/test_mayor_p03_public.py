"""Portable public-data checks: no private paths, originals, P1 install or network."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mayor_updates.projection import included,format_amount
class P03PublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT.parent/'frontend/public/data/kyoto_mayor_tracker.json'
        cls.data=json.loads(cls.path.read_text(encoding='utf-8-sig'))
        cls.policy=next(p for p in cls.data['pledges'] if p['id']=='P-03')
    def test_two_annual_records_and_reference_exclusion(self):
        records=self.policy['budget_records']
        self.assertEqual([r['amount_jpy'] for r in records],[124000000,190000000])
        self.assertEqual([r['policy_relation'] for r in records],['unconfirmed','contextual'])
        self.assertEqual(sum(r['amount_jpy'] for r in records if included(r)),0)
        self.assertIn('未確認',records[0]['fiscal_year'])
        self.assertEqual(records[1]['fiscal_year'],'令和8年度当初予算（案）')
        self.assertEqual(records[1]['amount_display'],'約1億9,000万円')
    def test_separate_pdf_sources_and_page(self):
        a,b=self.policy['budget_records']
        self.assertTrue(a['doc_url'].endswith('/13_kouhou_kyoiku.pdf'))
        self.assertTrue(b['doc_url'].endswith('/15_kyouiku_kouhou.pdf'))
        self.assertIn('印刷p.188',b['doc_source'])
        self.assertIn('物理16',b['doc_source'])
        self.assertTrue(all(r.get('funding_verification_status')=='unverified' for r in (a,b)))
    def test_history_and_latest_are_separate(self):
        self.assertEqual(self.policy['stage_level'],4)
        self.assertIn('契約',self.policy['milestone']['title'])
        self.assertEqual(self.policy['legislative_bill']['result'],'可決')
        event=self.policy['latest_update']
        self.assertEqual(event['announced_at'],'2026-11-05'); self.assertIsNone(event['event_date'])
        self.assertEqual(event['kind'],'construction_paused')
        self.assertTrue(event['source_url'].endswith('/0000347372.html'))
    def test_total_and_caveat_agree(self):
        stats=self.data['summary_stats']
        self.assertEqual(stats['total_allocated_budget_raw'],sum(r['amount_jpy'] for p in self.data['pledges'] for r in p['budget_records'] if included(r)))
        self.assertEqual(stats['total_allocated_budget_jpy'],format_amount(stats['total_allocated_budget_raw']))
        kpi=next(k for k in self.data['kpis'] if k['label']=='関連予算措置総額')
        self.assertEqual(kpi['value'],stats['total_allocated_budget_jpy'])
        self.assertIn('全額の原典確認を済ませた総額ではありません',stats['budget_total_note'])
    def test_generator_does_not_roll_back_any_policy_or_metadata(self):
        spec=importlib.util.spec_from_file_location('public_builder',ROOT/'build_mayor_tracker.py')
        builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        self.assertEqual(builder.generation_output(self.path),self.data)

if __name__=='__main__': unittest.main()
