"""Fixed Kyoto two-PDF contract. Synthetic process/CAS tests, no network."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import city_scope as cs, acquire
from mayor_updates.projection import Hold
ROOT = Path(__file__).resolve().parents[2]

def profile():
    return json.loads((ROOT/'config/kyoto_p04_p14_trial.json').read_text(encoding='utf-8'))

class Wave1Tests(unittest.TestCase):
    def setUp(self):
        self.no_network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        self.no_network.start(); self.addCleanup(self.no_network.stop)
        self.acl=patch.object(acquire,'assert_owner_only',return_value={'owner_only':True})
        self.acl_mock=self.acl.start(); self.addCleanup(self.acl.stop)

    def fixture(self, root):
        # Synthetic index; production SHA remains fixed and is tested separately.
        links = ['<a href="irrelevant">x</a>'] * 119
        for _, filename, anchor in cs.KYOTO_WAVE1_DOCS:
            links[anchor-1] = '<a href="./cmsfiles/contents/0000335/335933/'+filename+'">pdf</a>'
        body = ('<div id="mol_contents">'+''.join(links)+'</div>').encode()
        sha = hashlib.sha256(body).hexdigest()
        pin = patch.object(cs, 'KYOTO_INDEX_SHA', sha); pin.start(); self.addCleanup(pin.stop)
        s = profile(); s['index_sha256'] = sha; s.update(enabled=True, network_enabled=True)
        cas = root/'cas'; state = root/'state'; out = state/'run'
        cas.mkdir(); state.mkdir(); out.mkdir()
        relative = 'objects/'+sha[:2]+'/'+sha+'.bin'
        obj = cas/relative; obj.parent.mkdir(parents=True); obj.write_bytes(body)
        rec = dict(city_code='kyoto',source_url=cs.KYOTO_INDEX_URL,final_url=cs.KYOTO_INDEX_URL,
                   sha256=sha,version_id=sha,fiscal_year=2025,mime_type='text/html',snapshot_relative_path=relative)
        index = {'documents':{cs.KYOTO_INDEX_URL:{'versions':[{'sha256':sha,'record':rec}]}}}
        (cas/'index.json').write_text(json.dumps(index),encoding='utf-8')
        (root/'city_binding.json').write_text('original binding must remain unchanged',encoding='utf-8')
        binding = dict(city_code='kyoto',scope_sha256=cs.signature(s),snapshot_root=str(cas),state_root=str(state),index_sha256=sha)
        f = root/'kyoto_p04_p14_active_binding.json'; f.write_text(json.dumps(binding),encoding='utf-8')
        storage = dict(private_root=str(root),state_root=str(state),binding_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        return s,cas,out,storage,obj,index

    def test_fixed_disabled_profile(self):
        s=profile();self.assertEqual(cs.validate_scope(s),'kyoto')
        self.assertFalse(s['enabled']);self.assertFalse(s['network_enabled'])
        self.assertEqual(cs.KYOTO_INDEX_SHA,'be45c0421b1ca127853416f420991cd8d288841fb46ce6e76f0bc601860180bd')
        acquire.validate_sources(s['sources'],media_type='pdf',scope=s)
        self.assertEqual([r['policy_ids'] for r in s['sources']],[['P-04'],['P-14']])

    def test_activation_flags_fail_closed(self):
        for enabled,network in [(True,False),(False,True),(1,True),(False,0),('true',True),(None,False)]:
            s=profile();s.update(enabled=enabled,network_enabled=network)
            with self.subTest(enabled=enabled,network=network),self.assertRaises(Hold):cs.validate_scope(s)
        s=profile();s.pop('enabled')
        with self.assertRaises(Hold):cs.validate_scope(s)

    def test_two_bindings_selected_without_overwrite_or_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);active,cas,out,storage,obj,index=self.fixture(root)
            inactive=copy.deepcopy(active);inactive.update(enabled=False,network_enabled=False)
            active_file=root/'kyoto_p04_p14_active_binding.json'
            inactive_file=root/'kyoto_p04_p14_binding.json'
            b=json.loads(active_file.read_text());b['scope_sha256']=cs.signature(inactive)
            inactive_file.write_text(json.dumps(b),encoding='utf-8')
            inactive_storage={**storage,'binding_sha256':hashlib.sha256(inactive_file.read_bytes()).hexdigest()}
            before={p.name:p.read_bytes() for p in (active_file,inactive_file,root/'city_binding.json')}
            for s,config in [(active,storage),(inactive,inactive_storage)]:
                self.acl_mock.reset_mock()
                self.assertEqual(cs.validate_storage(s,config,cas,out),out.parent)
                self.assertEqual(self.acl_mock.call_count,4)
                self.assertIn(unittest.mock.call(root/cs.wave1_binding_name(s)),self.acl_mock.call_args_list)
            with self.assertRaises(Hold):cs.validate_storage(active,inactive_storage,cas,out)
            self.assertEqual(before,{p.name:p.read_bytes() for p in (active_file,inactive_file,root/'city_binding.json')})
            active_file.unlink()
            with self.assertRaises(Hold):cs.validate_storage(active,inactive_storage,cas,out)
            inactive_file.unlink()
            with self.assertRaises(Hold):cs.validate_storage(inactive,inactive_storage,cas,out)

    def test_active_binding_rejects_scope_state_index_and_acl_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s,cas,out,storage,obj,index=self.fixture(root)
            f=root/'kyoto_p04_p14_active_binding.json';original=f.read_bytes()
            for key,value in [('scope_sha256','0'*64),('index_sha256','0'*64),('state_root',str(root/'other')),('snapshot_root',str(root/'other')),('state_root',None)]:
                b=json.loads(original);b[key]=value;f.write_text(json.dumps(b),encoding='utf-8')
                changed={**storage,'binding_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
                with self.subTest(key=key),self.assertRaises(Hold):cs.validate_storage(s,changed,cas,out)
            for raw in ['{broken','[]','{}']:
                f.write_text(raw,encoding='utf-8');changed={**storage,'binding_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
                with self.assertRaises(Hold):cs.validate_storage(s,changed,cas,out)
            f.write_bytes(original)
            other=root/'other';other.mkdir()
            with self.assertRaises(Hold):cs.validate_storage(s,{**storage,'state_root':str(other)},cas,other/'run')
            with self.assertRaises(Hold):cs.validate_storage(s,storage,other,out)
            self.acl_mock.side_effect=Hold('Not owner-only')
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,out)
            self.assertEqual(f.read_bytes(),original)

    def test_reject_changed_scope_and_source_identity(self):
        mutations=[('city_code','kobe'),('policy_ids',['P-04']),('max_requests',3),
                   ('max_total_bytes',4194305),('max_requests_by_media',{'html':1,'pdf':2}),
                   ('redirects',1),('retries',1),('tls_verify',False),('timeout_seconds',11),
                   ('index_sha256','0'*64),('profile','generic')]
        for k,v in mutations:
            s=profile();s[k]=v
            with self.subTest(key=k),self.assertRaises(Hold):cs.validate_scope(s)
        base=profile()['sources'][0]['url']
        urls=[base+'?x=1',base+'#page=1',base.replace('https:','http:'),base.replace('www.city.kyoto.lg.jp','www.city.kyoto.lg.jp:443'),base.replace('www.city.kyoto.lg.jp','user@www.city.kyoto.lg.jp'),base.replace('www.city.kyoto.lg.jp','www.city.kyoto.lg.jp.evil.example'),base.replace('07_kouhou_kowaka','other')]
        for k,v in [('url',u) for u in urls]+[('policy_ids',['P-14']),('fiscal_year',2026),('media_type','html'),('document_kind','budget_index'),('max_bytes',2097153),('document_id','wrong'),('index_anchor',118),('index_url','https://example.org/')]:
            s=profile();s['sources'][0][k]=v
            with self.subTest(key=k,value=v),self.assertRaises(Hold):cs.validate_scope(s)
        s=profile();s['sources'].reverse()
        with self.assertRaises(Hold):cs.validate_scope(s)

    def test_legacy_contract_still_rejects_two_pdfs(self):
        s=profile();s.pop('profile');s['max_requests_by_media']={'html':1,'pdf':1}
        for row in s['sources']:row.pop('index_url')
        with self.assertRaises(Hold):cs.validate_scope(s)

    def test_binding_index_readback_and_path_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s,cas,out,storage,obj,index=self.fixture(root)
            before=(root/'city_binding.json').read_bytes()
            self.assertEqual(cs.validate_storage(s,storage,cas,out),out.parent)
            self.assertEqual((root/'city_binding.json').read_bytes(),before)
            for wrong in [root/'other',out.parent]:
                with self.assertRaises(Hold):cs.validate_storage(s,storage,wrong,out)
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,root/'elsewhere')
            bad=copy.deepcopy(s);bad['network_enabled']=False
            with self.assertRaises(Hold):cs.validate_storage(bad,storage,cas,out)
            obj.write_bytes(b'corrupt')
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,out)

    def test_binding_sha_and_index_ledger_tampering(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s,cas,out,storage,obj,index=self.fixture(root)
            f=root/'kyoto_p04_p14_active_binding.json';saved=f.read_bytes();f.write_text('{}')
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,out)
            f.write_bytes(saved)
            index['documents'][cs.KYOTO_INDEX_URL]['versions'][0]['record']['city_code']='kobe'
            (cas/'index.json').write_text(json.dumps(index))
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,out)

    def test_matching_sha_with_wrong_anchor_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s,cas,out,storage,obj,index=self.fixture(root)
            body=obj.read_bytes().replace(b'07_kouhou_kowaka.pdf',b'wrong.pdf')
            sha=hashlib.sha256(body).hexdigest();relative='objects/'+sha[:2]+'/'+sha+'.bin'
            target=cas/relative;target.parent.mkdir(parents=True);target.write_bytes(body)
            v=index['documents'][cs.KYOTO_INDEX_URL]['versions'][0];v['sha256']=sha
            v['record'].update(sha256=sha,version_id=sha,snapshot_relative_path=relative)
            (cas/'index.json').write_text(json.dumps(index))
            with patch.object(cs,'KYOTO_INDEX_SHA',sha),self.assertRaises(Hold):cs.validate_wave1_index(cas)

    def test_persistent_reservation_and_disabled_scope(self):
        with tempfile.TemporaryDirectory() as t:
            s,cas,out,storage,obj,index=self.fixture(Path(t))
            disabled=copy.deepcopy(s);disabled['network_enabled']=False
            with self.assertRaises(Hold):cs.reserve_request(disabled,storage,s['sources'][0])
            cs.reserve_request(s,storage,s['sources'][0])
            with self.assertRaises(Hold):cs.reserve_request(s,storage,s['sources'][0])
            self.assertEqual(len(list(out.parent.glob('single_request_*.json'))),1)

    def test_parent_requires_both_sources_in_order(self):
        s=profile()
        with patch.object(acquire,'P1Bridge') as bridge:
            for rows in [s['sources'][1:],list(reversed(s['sources']))]:
                with self.assertRaises(Hold):acquire.capture_sources('unused','unused',rows,'unused',authorized=True,media_type='pdf',scope=s,storage={})
            bridge.assert_not_called()

    def parent_trial(self, failure=None):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s,cas,out,storage,obj,index=self.fixture(root)
            before=(cas/'index.json').read_bytes(); old_binding=(root/'city_binding.json').read_bytes()
            bridge=MagicMock();bridge.hashes={};bridge.store.read_index.return_value=index;bridge.store.verify_integrity.return_value={}
            body=b'%PDF-1.7\nsynthetic';sha=hashlib.sha256(body).hexdigest();bridge.store.snapshot_bytes.return_value=body
            if failure=='readback':bridge.store.snapshot_bytes.return_value=b'corrupt'
            seen=[]
            def process(cmd,**kwargs):
                self.assertEqual(kwargs['timeout'],10)
                source=json.loads(Path(cmd[cmd.index('--source-file')+1]).read_text(encoding='utf-8'))
                seen.append(source['url'])
                if failure=='timeout':raise subprocess.TimeoutExpired(cmd,10)
                result={'status':'rejected_mime','version':None,'http_status':200} if failure=='mime' else {'status':'stored_new_version','version':{'document_id':source['document_id'],'version_id':sha},'http_status':200}
                Path(cmd[cmd.index('--output')+1],'worker_outcome.json').write_text(json.dumps(result),encoding='utf-8')
                return subprocess.CompletedProcess(cmd,0,'','')
            with patch.object(acquire,'assert_owner_only',return_value={'owner_only':True}),patch.object(acquire,'P1Bridge',return_value=bridge),patch.object(acquire.subprocess,'run',side_effect=process):
                result=acquire.capture_sources('pinned-test-double',cas,s['sources'],out,authorized=True,media_type='pdf',scope=s,storage=storage)
            self.assertEqual(seen,[r['url'] for r in s['sources'][:1 if failure else 2]])
            self.assertEqual(result['stopped'],bool(failure));self.assertEqual(result['public_writes'],0)
            self.assertEqual((cas/'index.json').read_bytes(),before);self.assertEqual((root/'city_binding.json').read_bytes(),old_binding)
            self.assertEqual(len(list(out.parent.glob('single_request_*.json'))),1 if failure else 2)
            self.assertTrue((out/'acquisition_result.json').exists())
            if not failure:
                self.assertTrue(all(r['readback_pass'] and r['sha256']==sha for r in result['receipts']))
            with self.assertRaises(Hold):cs.reserve_request(s,storage,s['sources'][0])
    def test_parent_two_successful_readbacks(self):self.parent_trial()
    def test_first_failure_stops_and_keeps_state(self):self.parent_trial('mime')
    def test_first_timeout_stops_and_keeps_reservation(self):self.parent_trial('timeout')
    def test_first_readback_failure_stops_with_receipt(self):self.parent_trial('readback')

if __name__=='__main__':unittest.main()
