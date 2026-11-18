"""Synthetic-only fixed PDF guard tests. No private originals or live HTTP."""
import copy
import hashlib
import json
import os
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class YokohamaPdfTests(unittest.TestCase):
    def setUp(self):
        self.real_acl = acquire.assert_owner_only
        for p in (patch.object(socket.socket, 'connect', side_effect=AssertionError('HTTP forbidden')),
                  patch.object(acquire, 'assert_owner_only', return_value={'owner_only':True})):
            mock = p.start(); self.addCleanup(p.stop)
        self.acl = mock

    def fixture(self, root, *, active=False):
        root = root.resolve(strict=True)
        cas = root/'cas'; state = root/'state'; out = state/'receipts'; code = root/'code'
        for p in (cas, state, out, code): p.mkdir(mode=0o700)
        html = ('<div id="tmp_contents"><h2>'+cs.YOKOHAMA_INDEX_HEADING+'</h2>'+''.join(
            '<a href="other'+str(n)+'.html">other</a>' for n in range(16))+
            '<a href="'+cs.YOKOHAMA_PDF_HREF+'">'+cs.YOKOHAMA_PDF_LABEL+'</a></div>').encode()
        index_sha = hashlib.sha256(html).hexdigest()
        pin = patch.object(cs, 'YOKOHAMA_INDEX_SHA', index_sha); pin.start(); self.addCleanup(pin.stop)
        files = {}
        for name in ('budget/fetch.py', 'budget/snapshots.py'):
            p = code/name; p.parent.mkdir(exist_ok=True); p.write_bytes(b'synthetic, never executed')
            files[name] = sha(p)
        p1_sha = hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        pin = patch.object(cs, 'YOKOHAMA_P1_SHA', p1_sha); pin.start(); self.addCleanup(pin.stop)
        scope = cs.yokohama_major_pdf_scope(); scope.update(enabled=active, network_enabled=active)
        relative = 'objects/'+index_sha[:2]+'/'+index_sha+'.bin'
        obj = cas/relative; obj.parent.mkdir(parents=True); obj.write_bytes(html)
        rec = dict(city_code='yokohama', source_url=cs.YOKOHAMA_INDEX_URL,
            final_url=cs.YOKOHAMA_INDEX_URL, sha256=index_sha, version_id=index_sha,
            fiscal_year=2026, mime_type='text/html', document_type='budget_index',
            snapshot_relative_path=relative,
            document_id='yokohama-doc-'+hashlib.sha256(cs.YOKOHAMA_INDEX_URL.encode()).hexdigest()[:24])
        ledger = {'documents':{cs.YOKOHAMA_INDEX_URL:{'versions':[{'sha256':index_sha,'record':rec}]}}}
        (cas/'index.json').write_text(json.dumps(ledger),encoding='utf-8')
        binding = dict(city_code='yokohama', scope_sha256=cs.signature(scope),
            snapshot_root=str(cas), state_root=str(state), p1_code_root=str(code),
            snapshot_identity=cs._directory_identity(cas), state_identity=cs._directory_identity(state),
            index_sha256=index_sha, p1_manifest_sha256=p1_sha,
            guard_code_sha256=sha(Path(cs.__file__)), acquire_code_sha256=sha(Path(acquire.__file__)))
        f = root/cs.yokohama_binding_name(scope); f.write_text(json.dumps(binding),encoding='utf-8')
        storage = dict(private_root=str(root), state_root=str(state), p1_code_root=str(code),
            p1_files=files, binding_sha256=sha(f))
        (root/'city_binding.json').write_text('{"legacy":"never overwrite"}')
        return scope, storage, cas, out, code, f, obj, ledger

    def validate(self, data):
        s, storage, cas, out, code, *_ = data
        return cs.validate_storage(s, storage, cas, out, code_root=code)

    def test_production_profile_is_exact_and_disabled(self):
        s = json.loads((ROOT/'config/yokohama_r8_major_pdf_trial.json').read_text(encoding='utf-8'))
        self.assertEqual(s, cs.yokohama_major_pdf_scope())
        self.assertEqual(cs.validate_scope(s), 'yokohama')
        self.assertFalse(s['enabled']); self.assertFalse(s['network_enabled'])
        self.assertEqual(cs.YOKOHAMA_INDEX_SHA, '872f5c8da45129bd6a3296269942880e20eeac8de6a163bb556e2bde294ae98b')
        self.assertEqual(cs.YOKOHAMA_P1_SHA, 'df02598305964e5d3bea333301ecccb93e26702db6f0a43a5fe6f8c180dd57d2')
        acquire.validate_sources(s['sources'],media_type='pdf',scope=s)
        with self.assertRaises(Hold): acquire.validate_sources(s['sources'],media_type='html',scope=s)
        with self.assertRaises(Hold): cs.reserve_request(s, {}, s['sources'][0])

    def test_transport_limits_activation_and_extra_keys_hold(self):
        mutations = dict(max_requests=2, max_total_bytes=4194304, timeout_seconds=11,
            wall_timeout_seconds=11, tls_verify=False, redirects=1, retries=1,
            follow_discovered_links=True, method='HEAD', policy_relation='confirmed',
            index_sha256='0'*64, p1_manifest_sha256='0'*64,
            max_requests_by_media={'html':1,'pdf':1}, extra='unexpected')
        for key, value in mutations.items():
            s = cs.yokohama_major_pdf_scope(); s[key] = value
            with self.subTest(key=key), self.assertRaises(Hold): cs.validate_scope(s)
        for enabled, network in [(True,False),(False,True),(1,True),(False,0),('false',False),(None,False)]:
            s=cs.yokohama_major_pdf_scope();s.update(enabled=enabled,network_enabled=network)
            with self.subTest(enabled=enabled,network=network),self.assertRaises(Hold):cs.validate_scope(s)

    def test_url_policy_document_year_media_and_index_identity_hold(self):
        base = cs.YOKOHAMA_PDF_URL
        urls = [base+'?x=1',base+'#page=1',base.replace('https:','http:'),
            base.replace('www.city.yokohama.lg.jp','user@www.city.yokohama.lg.jp'),
            base.replace('www.city.yokohama.lg.jp','www.city.yokohama.lg.jp:443'),
            base.replace('www.city.yokohama.lg.jp','www.city.yokohama.lg.jp.evil.test'),
            base.replace('www.city.yokohama.lg.jp','www.city.kobe.lg.jp'),base.replace('R8yosan-shuyou','other')]
        for key,value in [('url',u) for u in urls]+[('document_id','wrong'),('policy_ids',['P-03']),
                ('fiscal_year',2025),('media_type','html'),('max_bytes',2097153),
                ('index_anchor',18),('index_url','https://example.test/'),('title','other')]:
            s = cs.yokohama_major_pdf_scope();s['sources'][0][key] = value
            with self.subTest(key=key,value=value),self.assertRaises(Hold):cs.validate_scope(s)
        s=cs.yokohama_major_pdf_scope();s['sources']*=2
        with self.assertRaises(Hold):cs.validate_scope(s)

    def test_disabled_binding_verifies_read_only_without_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t));s,storage,cas,out,code,f,*_=data
            before={p:p.read_bytes() for p in Path(t).rglob('*') if p.is_file()}
            self.assertEqual(self.validate(data),out.parent)
            self.assertEqual(before,{p:p.read_bytes() for p in Path(t).rglob('*') if p.is_file()})
            self.assertEqual(self.acl.call_count,6)
            original=f.read_bytes();f.unlink()
            (Path(t)/'city_binding.json').write_bytes(original)
            storage['binding_sha256']=sha(Path(t)/'city_binding.json')
            with self.assertRaises(Hold):self.validate(data)

    def test_binding_scope_cas_state_code_pin_and_acl_mismatch_hold(self):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t));s,storage,cas,out,code,f,obj,ledger=data
            original=f.read_bytes()
            for key in ('city_code','scope_sha256','snapshot_root','state_root','p1_code_root',
                    'index_sha256','p1_manifest_sha256','guard_code_sha256','acquire_code_sha256',
                    'snapshot_identity','state_identity'):
                b=json.loads(original);b[key]='wrong';f.write_text(json.dumps(b))
                storage['binding_sha256']=sha(f)
                with self.subTest(key=key),self.assertRaises(Hold):self.validate(data)
            f.write_bytes(original);storage['binding_sha256']='0'*64
            with self.assertRaises(Hold):self.validate(data)
            storage['binding_sha256']=sha(f)
            for raw in ('{}','[]','broken'):
                f.write_text(raw);storage['binding_sha256']=sha(f)
                with self.assertRaises(Hold):self.validate(data)
            f.write_bytes(original);storage['binding_sha256']=sha(f)
            (code/'budget/fetch.py').write_bytes(b'changed')
            with self.assertRaises(Hold):self.validate(data)
            (code/'budget/fetch.py').write_bytes(b'synthetic, never executed')
            self.acl.side_effect=Hold('not owner-only')
            with self.assertRaises(Hold):self.validate(data)

    def test_wrong_code_argument_and_output_or_linked_paths_hold(self):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t));s,storage,cas,out,code,*_=data
            with self.assertRaises(Hold):cs.validate_storage(s,storage,cas,out)
            other=Path(t)/'other';other.mkdir()
            for snapshot,output,root in [(other,out,code),(cas,other,code),(cas,out,other)]:
                with self.assertRaises(Hold):cs.validate_storage(s,storage,snapshot,output,code_root=root)
            with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(Hold):self.validate(data)

    def test_index_missing_corrupt_other_version_and_city_hold(self):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t));s,storage,cas,out,code,f,obj,ledger=data
            original=obj.read_bytes();obj.write_bytes(b'corrupt')
            with self.assertRaises(Hold):self.validate(data)
            obj.write_bytes(original);index_file=cas/'index.json';saved=index_file.read_bytes()
            for key,value in [('city_code','kobe'),('fiscal_year',2025),('document_id','wrong'),('mime_type','application/pdf')]:
                changed=copy.deepcopy(ledger);changed['documents'][cs.YOKOHAMA_INDEX_URL]['versions'][0]['record'][key]=value
                index_file.write_text(json.dumps(changed))
                with self.subTest(key=key),self.assertRaises(Hold):self.validate(data)
            changed=copy.deepcopy(ledger);changed['documents'][cs.YOKOHAMA_INDEX_URL]['versions'].append(changed['documents'][cs.YOKOHAMA_INDEX_URL]['versions'][0])
            index_file.write_text(json.dumps(changed))
            with self.assertRaises(Hold):self.validate(data)
            index_file.write_bytes(saved);obj.unlink()
            with self.assertRaises(Hold):self.validate(data)

    def test_matching_test_sha_does_not_bypass_anchor_label_year_or_structure(self):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t));_,_,cas,_,_,_,obj,ledger=data;body=obj.read_bytes()
            variants=[body.replace(cs.YOKOHAMA_PDF_HREF.encode(),b'wrong.pdf'),
                body.replace(cs.YOKOHAMA_PDF_LABEL.encode(),b'wrong title'),
                body.replace(cs.YOKOHAMA_INDEX_HEADING.encode(),'令和７年度予算'.encode()),
                body.replace(b'<h2>',b'<a href="shift.html">shift</a><h2>'),
                body.replace(b'</div>',('<a href="'+cs.YOKOHAMA_PDF_HREF+'">duplicate</a></div>').encode()),
                body.replace(b'tmp_contents',b'unknown'),b'<base href="https://evil.test/">'+body]
            for html in variants:
                digest=hashlib.sha256(html).hexdigest();relative='objects/'+digest[:2]+'/'+digest+'.bin'
                p=cas/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(html)
                updated=copy.deepcopy(ledger);v=updated['documents'][cs.YOKOHAMA_INDEX_URL]['versions'][0]
                v['sha256']=digest;v['record'].update(sha256=digest,version_id=digest,snapshot_relative_path=relative)
                (cas/'index.json').write_text(json.dumps(updated))
                with patch.object(cs,'YOKOHAMA_INDEX_SHA',digest),self.assertRaises(Hold):cs.validate_yokohama_index(cas)

    def test_generic_and_kyoto_contracts_are_not_replaced(self):
        old=load_profile('kobe_m01_trial.json');self.assertEqual(cs.validate_scope(old),'kobe')
        old=load_profile('kyoto_p04_p14_trial.json');self.assertEqual(cs.validate_scope(old),'kyoto')
        s=cs.yokohama_major_pdf_scope();s.pop('profile')
        with self.assertRaises(Hold):cs.validate_scope(s)

    def parent_trial(self, failure=None, *, real_worker_acl=False):
        with tempfile.TemporaryDirectory() as t:
            data=self.fixture(Path(t),active=True);s,storage,cas,out,code,f,obj,index=data
            if real_worker_acl:
                f.chmod(0o600)  # Newly created synthetic binding only.
            before=(cas/'index.json').read_bytes();legacy=(Path(t)/'city_binding.json').read_bytes()
            bridge=MagicMock();bridge.hashes={};bridge.store.read_index.return_value=index;bridge.store.verify_integrity.return_value={}
            body=b'%PDF-1.7\nsynthetic';digest=hashlib.sha256(body).hexdigest();bridge.store.snapshot_bytes.return_value=body
            if failure=='readback':bridge.store.snapshot_bytes.return_value=b'corrupt'
            def process(cmd,**kwargs):
                self.assertEqual(kwargs['timeout'],10)
                if real_worker_acl:
                    run = Path(cmd[cmd.index('--output')+1])
                    self.assertEqual(run.stat().st_mode & 0o777,0o700)
                    with patch.object(acquire,'assert_owner_only',self.real_acl):
                        self.assertEqual(cs.validate_storage(s,storage,cas,run,code_root=code),out.parent)
                source=json.loads(Path(cmd[cmd.index('--source-file')+1]).read_text())
                self.assertEqual(source['url'],cs.YOKOHAMA_PDF_URL)
                if failure=='timeout':raise subprocess.TimeoutExpired(cmd,10)
                version=dict(document_id=source['document_id'],version_id=digest,city_code='yokohama',
                    source_url=source['url'],final_url=source['url'],fiscal_year=2026,
                    mime_type='application/pdf',document_type='other_official')
                if failure=='identity':version['city_code']='kobe'
                outcome=dict(status='stored_new_version',version=version,http_status=200)
                Path(cmd[cmd.index('--output')+1],'worker_outcome.json').write_text(json.dumps(outcome))
                return subprocess.CompletedProcess(cmd,0,'','')
            with patch.object(acquire,'P1Bridge',return_value=bridge),patch.object(acquire.subprocess,'run',side_effect=process) as proc:
                result=acquire.capture_sources(code,cas,s['sources'],out,authorized=True,media_type='pdf',scope=s,storage=storage)
            self.assertEqual(proc.call_count,1);self.assertEqual(result['stopped'],bool(failure))
            self.assertEqual(result['public_writes'],0)
            self.assertEqual((cas/'index.json').read_bytes(),before)
            self.assertEqual((Path(t)/'city_binding.json').read_bytes(),legacy)
            self.assertEqual(len(list(out.parent.glob('single_request_*.json'))),1)
            with self.assertRaises(Hold):cs.reserve_request(s,storage,s['sources'][0])

    def test_parent_single_pdf_readback(self):self.parent_trial()
    def test_parent_timeout_keeps_reservation(self):self.parent_trial('timeout')
    def test_parent_readback_failure_stops(self):self.parent_trial('readback')
    def test_parent_foreign_version_stops(self):self.parent_trial('identity')

    @unittest.skipIf(os.name=='nt','POSIX umask/permission regression; Windows inherits verified parent ACL')
    def test_worker_creation_with_umask_022_passes_real_owner_only_guard(self):
        prior=os.umask(0o022)
        try:self.parent_trial(real_worker_acl=True)
        finally:os.umask(prior)

    def test_refresh_is_rejected_before_p1_or_reservation(self):
        s=cs.yokohama_major_pdf_scope()
        with patch.object(acquire,'P1Bridge') as bridge,self.assertRaises(Hold):
            acquire.capture_sources('unused','unused',s['sources'],'unused',authorized=True,
                refresh=True,media_type='pdf',scope=s,storage={})
        bridge.assert_not_called()


def load_profile(name):
    return json.loads((ROOT/'config'/name).read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main()
