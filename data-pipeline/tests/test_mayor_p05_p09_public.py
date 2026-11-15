import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from mayor_updates.projection import budget_total,format_record_amount,sync_totals,Hold
class BudgetHistoryTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT.parent/'frontend/public/data/kyoto_mayor_tracker.json').read_text(encoding='utf-8'))
  self.p={x['id']:x for x in self.data['pledges']}
 def series(self):return copy.deepcopy(self.p['P-09']['budget_records'][1:])
 def total(self,rows):return budget_total([{'id':'TEST','budget_records':rows}])
 def test_annual_history_not_sum_of_three_amounts(self):
  self.assertEqual(self.total(self.series()),3500000000)
  self.assertEqual(self.total(self.p['P-09']['budget_records']),3500000000)
  self.assertEqual([r['fiscal_year_ad'] for r in self.p['P-09']['budget_records']],[2025,2026,2026,2026])
 def test_both_initial_and_after_selected_is_rejected(self):
  rows=self.series();rows[0]['aggregation_status']='included'
  with self.assertRaises(Hold):self.total(rows)
 def test_incorrect_sum_is_rejected(self):
  rows=self.series();rows[2]['amount_jpy']+=1
  with self.assertRaises(Hold):self.total(rows)
 def test_year_account_scope_and_evidence_must_match(self):
  for key,value in [('fiscal_year_ad',2025),('account','別会計'),('series_id','other'),('evidence_status','unverified'),('doc_source','')]:
   with self.subTest(key=key):
    rows=self.series();rows[0][key]=value
    with self.assertRaises(Hold):self.total(rows)
 def test_multiple_deltas_need_explicit_reconciliation(self):
  rows=self.series();rows.append(copy.deepcopy(rows[1]))
  with self.assertRaises(Hold):self.total(rows)
 def test_negative_delta_is_displayed_but_never_added(self):
  rows=self.series();rows[1]['amount_jpy']=-250000000;rows[2]['amount_jpy']=750000000
  self.assertEqual(self.total(rows),750000000)
  self.assertEqual(format_record_amount(rows[1]),'−2億5,000万円')
 def test_commitment_is_not_spending(self):
  row=dict(self.series()[0],amount_role='commitment',aggregation_status='excluded')
  self.assertEqual(self.total([row]),0)
  row['aggregation_status']='included'
  with self.assertRaises(Hold):self.total([row])
 def test_p05_scope_not_implicitly_combined(self):
  a,delta,legacy=self.p['P-05']['budget_records']
  self.assertEqual(a['amount_jpy'],462329000);self.assertEqual(a['amount_display'],'4億6,232万9,000円')
  self.assertNotEqual(a['series_id'],delta['series_id']);self.assertEqual(delta['aggregation_status'],'excluded')
  self.assertEqual(self.total([a,delta]),462329000)
  self.assertEqual(legacy['amount_jpy'],280000000)
 def test_aggregate_and_display_generated_together(self):
  self.assertEqual(self.data,sync_totals(copy.deepcopy(self.data)))
  self.assertEqual(self.data['summary_stats']['total_allocated_budget_raw'],9115487000)
  self.assertEqual(self.data['summary_stats']['total_allocated_budget_jpy'],'91億1,549万円')
  self.assertEqual([self.p[x]['stage_level'] for x in ['P-05','P-07','P-09']],[3,3,3])
 def test_wrong_display_is_regenerated(self):
  d=copy.deepcopy(self.data);next(p for p in d['pledges'] if p['id']=='P-09')['budget_records'][-1]['amount_display']='70億円'
  self.assertEqual(sync_totals(d),self.data)
if __name__=='__main__':unittest.main()
