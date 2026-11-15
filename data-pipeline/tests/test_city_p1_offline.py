"""Run against the approved P1 CODE ONLY; real originals are not fixtures.
Set MAYOR_P1_APPROVED_ROOT to its data-pipeline directory. All HTTP is fake.
"""
import copy,hashlib,json,os,socket,sys,tempfile,unittest
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates.p1_city_upgrade import prepare_copy
from mayor_updates.p1_bridge import P1Bridge
from mayor_updates import acquire
from mayor_updates.city_scope import signature
from mayor_updates.projection import Hold
from test_city_scope import profile,binding
class FakeTransport:
 def __init__(self,response):self.response=response;self.calls=[]
 def request(self,url,**kwargs):self.calls.append((url,kwargs));return self.response
@unittest.skipUnless(os.environ.get('MAYOR_P1_APPROVED_ROOT'),'Requires immutable P1 code; no originals')
class P1CityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);cls.code=cls.root/'code'
  cls.public_hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).resolve().parents[2]/'frontend/public/data').glob('*_mayor_tracker.json')}
  cls.before=hashlib.sha256((Path(os.environ['MAYOR_P1_APPROVED_ROOT'])/'budget/fetch.py').read_bytes()).hexdigest()
  prepare_copy(os.environ['MAYOR_P1_APPROVED_ROOT'],cls.code,include_nagoya_host=getattr(cls,'nagoya_host',False))
  cls.bridge=P1Bridge(cls.code,cls.root/'bootstrap',city_capable=True)
  from budget.fetch import SourceFetcher,HTTPResponse
  from budget.documents import DiscoveredDocument
  from budget.snapshots import SnapshotStore
  cls.Fetcher=SourceFetcher;cls.Response=HTTPResponse;cls.Doc=DiscoveredDocument;cls.Store=SnapshotStore
  cls.network=patch.object(socket.socket,'connect',side_effect=AssertionError('No network in offline tests'));cls.network.start()
 @classmethod
 def tearDownClass(cls):
  cls.network.stop()
  assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in cls.public_hashes.items())
  assert cls.before==hashlib.sha256((Path(os.environ['MAYOR_P1_APPROVED_ROOT'])/'budget/fetch.py').read_bytes()).hexdigest()
  for name in list(sys.modules):
   if name=='budget' or name.startswith('budget.'):del sys.modules[name]
  cls.temp.cleanup()
 def store(self):
  p=Path(tempfile.mkdtemp(dir=self.root));return self.Store(p)
 def doc(self,url,medium='html'):
  return self.Doc(url,'fixture','令和8年度',2026,medium,'budget_index' if medium=='html' else 'other_official','unknown',None,url,url,None,None,'discovered_unverified',())
 def transport(self,body=b'<html>fixture</html>',status=200,tls=True,mime='text/html'):
  return FakeTransport(self.Response(status,{'Content-Type':mime},body,tls))
 def fetcher(self,store,transport,city='kobe'):
  return self.Fetcher(store,transport=transport,allowed_hosts=frozenset({'www.city.'+city+'.lg.jp'}),max_bytes=2097151,max_redirects=0,timeout_seconds=10,city_code=city)
 def test_kyoto_default_matches_existing_identity(self):
  url='https://www.city.kyoto.lg.jp/test.html';store=self.store();transport=self.transport()
  r=self.Fetcher(store,transport=transport,max_redirects=0).fetch_discovered(self.doc(url))
  rec=store.read_index()['documents'][url]['versions'][0]['record']
  self.assertEqual(rec['document_id'],'kyoto-doc-'+hashlib.sha256(url.encode()).hexdigest()[:24]);self.assertEqual(rec['city_code'],'kyoto')
  self.assertEqual(r.http_status,200)
 def test_all_six_existing_kyoto_sources_keep_identity(self):
  config=json.loads((Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json').read_text())
  sources=config['cities']['kyoto']['monitor_sources']+config['pdf_watch']['sources']
  store=self.store()
  for source in sources:
   medium=source.get('media_type','html');body=b'<html>fixture</html>' if medium=='html' else b'%PDF-1.7\nfixture'
   doc=replace(self.doc(source['url'],medium),fiscal_year_ad=source['fiscal_year'],fiscal_year='令和'+str(source['fiscal_year']-2018)+'年度',document_kind=source['document_kind'])
   fetch=self.Fetcher(store,transport=self.transport(body=body,mime='text/html' if medium=='html' else 'application/pdf'),allowed_hosts=frozenset({'www.city.kyoto.lg.jp'}),max_bytes=source['max_bytes']-1,max_redirects=0,timeout_seconds=10)
   fetch.fetch_discovered(doc);rec=store.read_index()['documents'][source['url']]['versions'][0]['record']
   self.assertEqual(rec['city_code'],'kyoto');self.assertEqual(rec['document_id'],'kyoto-doc-'+hashlib.sha256(source['url'].encode()).hexdigest()[:24]);self.assertEqual(rec['fiscal_year'],source['fiscal_year'])
 def test_neutral_document_keeps_kyoto_adapter_compatibility(self):
  from budget.adapters.kyoto import DiscoveredDocument
  self.assertIs(DiscoveredDocument,self.Doc)
 def test_kobe_html_and_pdf_saved_under_kobe(self):
  for source in profile()['sources']:
   medium=source['media_type'];body=b'<html>fixture</html>' if medium=='html' else b'%PDF-1.7\nfixture'
   store=self.store();r=self.fetcher(store,self.transport(body=body,mime='text/html' if medium=='html' else 'application/pdf')).fetch_discovered(self.doc(source['url'],medium))
   rec=store.read_index()['documents'][source['url']]['versions'][0]['record']
   self.assertEqual(rec['city_code'],'kobe');self.assertTrue(rec['document_id'].startswith('kobe-doc-'))
   self.assertEqual(rec['document_type'],'budget_index' if medium=='html' else 'other_official');self.assertEqual(rec['fiscal_year'],2026);self.assertEqual(rec['sha256'],hashlib.sha256(body).hexdigest());self.assertIsNotNone(r.version)
 def test_kyoto_url_rejected_by_kobe_before_http(self):
  t=self.transport();r=self.fetcher(self.store(),t).fetch_discovered(self.doc('https://www.city.kyoto.lg.jp/a.html'))
  self.assertEqual(r.status,'unsafe_url');self.assertEqual(t.calls,[])
 def test_city_host_identity_mismatch_rejected(self):
  with self.assertRaises(ValueError):self.Fetcher(self.store(),transport=self.transport(),city_code='kobe')
 def test_kobe_cannot_use_existing_kyoto_cas(self):
  store=self.store();self.fetcher(store,self.transport(),'kyoto').fetch_discovered(self.doc('https://www.city.kyoto.lg.jp/a.html'))
  before=copy.deepcopy(store.read_index());t=self.transport()
  with self.assertRaises(ValueError):self.fetcher(store,t,'kobe')
  self.assertEqual(t.calls,[]);self.assertEqual(store.read_index(),before)
 def test_duplicate_version_has_one_saved_object(self):
  store=self.store();f=self.fetcher(store,self.transport());doc=self.doc(profile()['sources'][0]['url'])
  first=f.fetch_discovered(doc);second=f.fetch_discovered(doc)
  self.assertTrue(first.version.new_version);self.assertFalse(second.version.new_version)
  self.assertEqual(len(store.read_index()['documents'][doc.url]['versions']),1)
  self.assertEqual(store.snapshot_bytes(first.version.version_id),b'<html>fixture</html>')
 def test_abnormal_response_preserves_good_version(self):
  for status,tls,mime,body in [(503,True,'text/html',b'<html>x</html>'),(302,True,'text/html',b'<html>x</html>'),(200,False,'text/html',b'<html>x</html>'),(200,True,'application/json',b'{}')]:
   with self.subTest(status=status,tls=tls,mime=mime):
    store=self.store();doc=self.doc(profile()['sources'][0]['url']);self.fetcher(store,self.transport()).fetch_discovered(doc)
    before=copy.deepcopy(store.read_index()['documents']);t=self.transport(body,status,tls,mime)
    r=self.fetcher(store,t).fetch_discovered(doc)
    self.assertIsNone(r.version);self.assertEqual(len(t.calls),1);self.assertEqual(store.read_index()['documents'],before)
 def test_city_worker_uses_existing_p1_with_scope_and_receipt(self):
  s=profile();s.update(enabled=True,network_enabled=True);source=s['sources'][0]
  with tempfile.TemporaryDirectory(dir=self.root) as t:
   cas,out,storage=binding(Path(t),s)
   marker={'source_url':source['url'],'media_type':'html','scope_sha256':signature(s)}
   (out/'single_get_started.json').write_text(json.dumps(marker))
   tr=self.transport()
   with patch.object(acquire,'assert_owner_only',return_value={}),patch('budget.fetch.UrllibTransport',return_value=tr):
    acquire.worker(self.code,cas,source,out,scope=s,storage=storage)
   result=json.loads((out/'worker_outcome.json').read_text());self.assertEqual(result['http_status'],200)
   self.assertTrue(result['version']['document_id'].startswith('kobe-doc-'));self.assertEqual(len(tr.calls),1)
   with self.assertRaises(Hold):acquire.worker(self.code,cas,source,out,scope=s,storage=storage)
 def test_parent_reuse_and_wrong_year_stop_without_request(self):
  s=profile();source=s['sources'][0]
  with tempfile.TemporaryDirectory(dir=self.root) as t:
   cas,out,storage=binding(Path(t),s);store=self.Store(cas)
   self.fetcher(store,self.transport()).fetch_discovered(self.doc(source['url']))
   with patch.object(acquire,'assert_owner_only',return_value={}),patch.object(acquire.subprocess,'run') as process:
    r=acquire.capture_sources(self.code,cas,[source],out,scope=s,storage=storage,authorized=True)
    process.assert_not_called();self.assertEqual(r['new_get_requests'],0);self.assertEqual(r['public_writes'],0)
   s['sources'][0]['fiscal_year']=2025
   b=Path(t)/'city_binding.json';v=json.loads(b.read_text());v['scope_sha256']=signature(s);b.write_text(json.dumps(v))
   storage['binding_sha256']=hashlib.sha256(b.read_bytes()).hexdigest();out2=out.parent/'run2';out2.mkdir()
   with patch.object(acquire,'assert_owner_only',return_value={}),patch.object(acquire.subprocess,'run') as process:
    with self.assertRaises(Hold):acquire.capture_sources(self.code,cas,[source],out2,scope=s,storage=storage,authorized=True)
    process.assert_not_called()
 def test_size_and_timeout_failures_keep_saved_document(self):
  from budget.fetch import OversizeResponse
  for error in (OversizeResponse('fixture cap'),TimeoutError('fixture timeout')):
   store=self.store();doc=self.doc(profile()['sources'][0]['url']);self.fetcher(store,self.transport()).fetch_discovered(doc)
   before=copy.deepcopy(store.read_index()['documents']);tr=self.transport()
   with patch.object(tr,'request',side_effect=error) as request:
    r=self.fetcher(store,tr).fetch_discovered(doc)
   self.assertIsNone(r.version);self.assertEqual(request.call_count,1);self.assertEqual(store.read_index()['documents'],before)
 def test_wrong_patch_pin_rejected(self):
  with self.assertRaises(Hold):P1Bridge(self.code,self.root/'never',city_capable=False)
class NagoyaP1Tests(P1CityTests):
 # Re-run city isolation/legacy Kyoto contracts against the new optional copy.
 nagoya_host=True
 def nagoya_fetcher(self,store,transport):
  return self.Fetcher(store,transport=transport,city_code='nagoya',allowed_hosts=frozenset({'www.city.nagoya.jp'}),max_bytes=2097151,max_redirects=0,timeout_seconds=10)
 def test_nagoya_document_identity_and_readback(self):
  url='https://www.city.nagoya.jp/tax.html';store=self.store();tr=self.transport()
  result=self.nagoya_fetcher(store,tr).fetch_discovered(self.doc(url))
  rec=store.read_index()['documents'][url]['versions'][0]['record']
  self.assertEqual(rec['city_code'],'nagoya');self.assertEqual(rec['document_id'],'nagoya-doc-'+hashlib.sha256(url.encode()).hexdigest()[:24])
  self.assertEqual(result.http_status,200);self.assertEqual(store.snapshot_bytes(rec['sha256']),b'<html>fixture</html>')
  self.assertEqual(len(tr.calls),1)
 def test_nagoya_wrong_host_and_foreign_cas_rejected(self):
  tr=self.transport()
  for host in ['www.city.nagoya.lg.jp','www.city.kyoto.lg.jp','www.city.nagoya.jp.evil.example']:
   with self.subTest(host=host),self.assertRaises(ValueError):
    self.Fetcher(self.store(),transport=tr,city_code='nagoya',allowed_hosts=frozenset({host}))
  store=self.store();self.fetcher(store,self.transport(),'kyoto').fetch_discovered(self.doc('https://www.city.kyoto.lg.jp/a.html'))
  before=copy.deepcopy(store.read_index())
  with self.assertRaises(ValueError):self.nagoya_fetcher(store,tr)
  self.assertEqual(tr.calls,[]);self.assertEqual(store.read_index(),before)
 def test_nagoya_worker_scope_end_to_end(self):
  s=profile();s.update(city_code='nagoya',policy_ids=['nagoya_p2'],allowed_hosts=['www.city.nagoya.jp'],enabled=True,network_enabled=True)
  s['sources']=[dict(s['sources'][0],url='https://www.city.nagoya.jp/tax.html',policy_ids=['nagoya_p2'])];source=s['sources'][0]
  with tempfile.TemporaryDirectory(dir=self.root) as t:
   cas,out,storage=binding(Path(t),s)
   (out/'single_get_started.json').write_text(json.dumps({'source_url':source['url'],'media_type':'html','scope_sha256':signature(s)}))
   tr=self.transport()
   with patch.object(acquire,'assert_owner_only',return_value={}),patch('budget.fetch.UrllibTransport',return_value=tr):
    acquire.worker(self.code,cas,source,out,scope=s,storage=storage)
   result=json.loads((out/'worker_outcome.json').read_text());self.assertEqual(result['http_status'],200)
   self.assertTrue(result['version']['document_id'].startswith('nagoya-doc-'));self.assertEqual(len(tr.calls),1)
if __name__=='__main__':unittest.main()
