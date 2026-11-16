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
 def test_nagoya_exact_official_host_and_policy(self):
  s=profile();s.update(city_code='nagoya',policy_ids=['nagoya_p2'],allowed_hosts=['www.city.nagoya.jp'])
  s['sources']=[dict(s['sources'][0],url='https://www.city.nagoya.jp/tax.html',policy_ids=['nagoya_p2'])]
  self.assertEqual(validate_scope(s),'nagoya')
  for host in ['www.city.nagoya.lg.jp','www.city.kyoto.lg.jp','www.city.nagoya.jp.evil.example','www.city.nagoya.jp:443']:
   bad=copy.deepcopy(s);bad['allowed_hosts']=[host];bad['sources'][0]['url']='https://'+host+'/tax.html'
   with self.subTest(host=host),self.assertRaises(Hold):validate_scope(bad)
  bad=copy.deepcopy(s);bad['sources'][0]['policy_ids']=['OSAKA-M01']
  with self.assertRaises(Hold):validate_scope(bad)
 def test_other_cities_keep_exact_hosts(self):
  from mayor_updates.city_scope import official_host
  for city in ['kyoto','kobe','osaka','yokohama']:
   self.assertEqual(official_host(city),'www.city.'+city+'.lg.jp')
 def test_legacy_kyoto_selection_unchanged(self):
  cfg=json.loads((ROOT/'config/mayor_update_sources.json').read_text())
  validate_sources(cfg['cities']['kyoto']['monitor_sources'])
  validate_sources(cfg['pdf_watch']['sources'],media_type='pdf')
 def test_exact_yokohama_directory_html_only(self):
  from mayor_updates.city_scope import is_registered_directory_html
  url='https://www.city.yokohama.lg.jp/city-info/zaisei/'
  s=profile();s.update(city_code='yokohama',policy_ids=['YOKOHAMA-M01'],allowed_hosts=['www.city.yokohama.lg.jp'],max_requests=1)
  s['sources']=[dict(s['sources'][0],url=url,policy_ids=['YOKOHAMA-M01'])]
  self.assertTrue(is_registered_directory_html('yokohama',url,'html'))
  validate_sources(s['sources'],scope=s)
  # index.html retains the pre-existing extension path, not the new exception.
  self.assertFalse(is_registered_directory_html('yokohama',url+'index.html','html'))
  legacy=copy.deepcopy(s);legacy['sources'][0]['url']=url+'index.html';validate_scope(legacy)
  for bad_url in [url+'other/',url.rstrip('/'),url+'?q=1',url+'#x',url.replace('https:','http:'),url.replace('www.city.yokohama.lg.jp','www.city.kobe.lg.jp'),url.replace('www.city.yokohama.lg.jp','evil.example')]:
   with self.subTest(url=bad_url):
    self.assertFalse(is_registered_directory_html('yokohama',bad_url,'html'))
    bad=copy.deepcopy(s);bad['sources'][0]['url']=bad_url
    with self.assertRaises(Hold):validate_scope(bad)
  for city in ['kyoto','kobe','osaka','nagoya']:
   self.assertFalse(is_registered_directory_html(city,url,'html'))
  self.assertFalse(is_registered_directory_html('yokohama',url,'pdf'))
  for key,value in [('redirects',1),('retries',1),('tls_verify',False),('timeout_seconds',11)]:
   bad=copy.deepcopy(s);bad[key]=value
   with self.subTest(key=key),self.assertRaises(Hold):validate_scope(bad)
  bad=copy.deepcopy(s);bad['sources'][0]['max_bytes']=2097153
  with self.assertRaises(Hold):validate_scope(bad)
  row=copy.deepcopy(s['sources'][0]);row['url']=url+'index.html'
  with self.assertRaises(Hold):validate_sources([row],scope=s)
  # The Kyoto-only acquisition entry remains closed to the new URL.
  with self.assertRaises(Hold):validate_sources(s['sources'])
if __name__=='__main__':unittest.main()
