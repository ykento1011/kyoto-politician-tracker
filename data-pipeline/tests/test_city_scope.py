"""City boundary tests; network and live private state are never used."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates.city_scope import validate_scope,validate_storage,signature,reserve_request
from mayor_updates.acquire import validate_sources
from mayor_updates.projection import Hold
ROOT=Path(__file__).resolve().parents[2]
def profile():return json.loads((ROOT/'config/kobe_m01_trial.json').read_text(encoding='utf-8'))
def binding(root,scope):
 cas=root/'cas';state=root/'state';out=state/'run'
 cas.mkdir();state.mkdir();out.mkdir()
 b={'city_code':scope['city_code'],'scope_sha256':signature(scope),'snapshot_root':str(cas),'state_root':str(state)}
 f=root/'city_binding.json';f.write_text(json.dumps(b),encoding='utf-8')
 return cas,out,{'private_root':str(root),'state_root':str(state),'binding_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
class ScopeTests(unittest.TestCase):
 def test_disabled_exact_two_url_profile(self):
  s=profile();self.assertEqual(validate_scope(s),'kobe');self.assertFalse(s['network_enabled'])
  for medium in ('html','pdf'):validate_sources([r for r in s['sources'] if r['media_type']==medium],media_type=medium,scope=s)
 def test_other_city_policy_rejected(self):
  for location in ('scope','source'):
   s=profile()
   if location=='scope':s['policy_ids']=['P-01']
   else:s['sources'][0]['policy_ids']=['P-01']
   with self.assertRaises(Hold):validate_scope(s)
 def test_wrong_host_year_kind_size_or_source_rejected(self):
  for key,value in [('url','https://www.city.kyoto.lg.jp/a.html'),('fiscal_year',2025),('document_kind','other_official'),('max_bytes',2097153)]:
   s=profile();row={**s['sources'][0],key:value}
   with self.subTest(key=key),self.assertRaises(Hold):validate_sources([row],scope=s)
 def test_private_cas_and_state_bound_to_city(self):
  s=profile()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);cas,out,b=binding(root,s);validate_storage(s,b,cas,out)
   for wrong in [root/'kyoto_cas',Path(t).parent]:
    with self.assertRaises(Hold):validate_storage(s,b,wrong,out)
   s['city_code']='kyoto'
   with self.assertRaises(Hold):validate_storage(s,b,cas,out)
 def test_tampered_binding_rejected(self):
  s=profile()
  with tempfile.TemporaryDirectory() as t:
   cas,out,b=binding(Path(t),s);(Path(t)/'city_binding.json').write_text('{}')
   with self.assertRaises(Hold):validate_storage(s,b,cas,out)
 def test_disabled_network_and_persistent_single_attempt(self):
  s=profile()
  with tempfile.TemporaryDirectory() as t:
   cas,out,b=binding(Path(t),s)
   with self.assertRaises(Hold):reserve_request(s,b,s['sources'][0])
   s.update(enabled=True,network_enabled=True)
   reserve_request(s,b,s['sources'][0])
   with self.assertRaises(Hold):reserve_request(s,b,s['sources'][0])
 def test_legacy_kyoto_selection_unchanged(self):
  cfg=json.loads((ROOT/'config/mayor_update_sources.json').read_text())
  validate_sources(cfg['cities']['kyoto']['monitor_sources'])
  validate_sources(cfg['pdf_watch']['sources'],media_type='pdf')
if __name__=='__main__':unittest.main()
