import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from mayor_updates.projection import included,sync_totals,Hold
class P07Tests(unittest.TestCase):
 def test_evidence_and_aggregate_are_independent(self):
  data=json.loads((ROOT.parent/'frontend/public/data/kyoto_mayor_tracker.json').read_text(encoding='utf-8-sig'))
  p=next(x for x in data['pledges'] if x['id']=='P-07');r=p['budget_records']
  self.assertEqual(p['stage_level'],3);self.assertEqual([x['amount_jpy'] for x in r],[715000000,99000000,25000000,0,244000000])
  self.assertEqual(r[0]['policy_relation'],'unconfirmed');self.assertEqual(r[1]['policy_relation'],'direct')
  self.assertTrue(all(not included(x) for x in r));self.assertTrue(all(x['funding_verification_status']=='unverified' for x in r))
  self.assertEqual(data,sync_totals(json.loads(json.dumps(data))))
  self.assertEqual(data['summary_stats']['total_allocated_budget_raw'],9115158000)
 def test_unknown_aggregation_rejected(self):
  with self.assertRaises(Hold):included({'aggregation_status':'typo','amount_jpy':1})
if __name__=='__main__':unittest.main()
