"""PDF version monitoring and future bundle tests: no live HTTP or scheduler."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import acquire,pdf_watch,weekly_bundle
from mayor_updates.engine import digest
from mayor_updates.projection import Hold
from mayor_updates.operations import load
from mayor_updates.monitor import pdf_request_plan

CONFIG=Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json'
SOURCES=load(CONFIG)['pdf_watch']['sources']
URL=SOURCES[0]['url']

def valid_pdf():
    import fitz
    with fitz.open() as doc:
        doc.new_page().insert_text((50,50),'SYNTHETIC TEST ONLY')
        return doc.tobytes()

def receipt(source,sha='b'):
    return {'source_url':source['url'],'version':{'sha256':sha*64},'sha256':sha*64,'http_status':200,'status':'unchanged'}

def baseline(): return {s['url']:{'sha256':'a'*64,'record':{'sha256':'a'*64}} for s in SOURCES}

def details(bridge,source,sha,refs):
    return {'record':{'sha256':sha,'version_id':sha},'anchor_checks':[{'status':'unconfirmed'}],'page_count':1,'bytes':100}

class PDFTests(unittest.TestCase):
    def test_separate_media_and_receive_caps(self):
        acquire.validate_sources(SOURCES,media_type='pdf')
        with self.assertRaises(Hold): acquire.validate_sources(SOURCES)
        bad=deepcopy(SOURCES); bad[1]['max_bytes']=20971520
        with self.assertRaises(Hold): acquire.validate_sources(bad,media_type='pdf')
        with self.assertRaises(Hold): acquire.validate_sources([SOURCES[0],SOURCES[0]],media_type='pdf')
        bad=deepcopy(SOURCES); bad[0]['url']='https://example.org/a.pdf'
        with self.assertRaises(Hold): acquire.validate_sources(bad,media_type='pdf')
        self.assertEqual(sum(s['max_bytes'] for s in SOURCES),25165824)

    def test_pdf_structure_validation(self):
        self.assertEqual(pdf_watch.check_pdf(valid_pdf()),1)
        for body in (b'<html>error</html>',b'%PDF-1.7\nnot a document'):
            with self.assertRaises(Hold): pdf_watch.check_pdf(body)

    def test_all_five_version_states(self):
        f=pdf_watch.compare_pdf
        self.assertEqual(f('a','a'),'unchanged'); self.assertEqual(f('a','b'),'new_saved_version')
        self.assertEqual(f(None,'a'),'initial_baseline'); self.assertEqual(f('a',None,fetch_ok=False),'fetch_failed')
        self.assertEqual(f('a','b',valid=False),'unverifiable')

    def test_changed_pdf_review_keeps_versions_policy_and_positions(self):
        with patch.object(pdf_watch,'inspect',side_effect=details):
            r=pdf_watch.reconcile(None,SOURCES,{}, {}, {'receipts':[receipt(s) for s in SOURCES],'stopped':False},baseline())
        self.assertEqual(len(r['reviews']),3)
        for row,source in zip(r['reviews'],SOURCES):
            self.assertEqual(row['policy_ids'],source['policy_ids']); self.assertEqual(row['review_pages'],source['review_pages'])
            self.assertEqual(row['before_sha256'],'a'*64); self.assertEqual(row['after_sha256'],'b'*64)
            self.assertIsNone(row['policy_effect']); self.assertFalse(row['publication_authorized'])

    def test_unchanged_and_first_baseline_have_zero_proposals(self):
        with patch.object(pdf_watch,'inspect',side_effect=details):
            for before,expected in [(baseline(),'unchanged'),({},'initial_baseline')]:
                r=pdf_watch.reconcile(None,SOURCES,{}, {}, {'receipts':[receipt(s,'a') for s in SOURCES],'stopped':False},before)
                self.assertEqual(r['counts'][expected],3); self.assertEqual(r['reviews'],[])

    def test_partial_failure_keeps_previous_pdf_state(self):
        before=baseline(); original=deepcopy(before)
        failure={'source_url':SOURCES[1]['url'],'status':'timeout','stop':True,'http_status':None}
        with patch.object(pdf_watch,'inspect',side_effect=details):
            r=pdf_watch.reconcile(None,SOURCES,{}, {}, {'receipts':[receipt(SOURCES[0]),failure],'stopped':True},before)
        self.assertTrue(r['stopped']); self.assertEqual(r['documents'],original); self.assertEqual(before,original)
        self.assertEqual(r['counts']['fetch_failed'],1); self.assertEqual(r['counts']['unverifiable'],1); self.assertEqual(r['reviews'],[])

    def test_invalid_saved_pdf_is_not_promoted(self):
        with patch.object(pdf_watch,'inspect',side_effect=Hold('invalid PDF')):
            r=pdf_watch.reconcile(None,SOURCES,{}, {}, {'receipts':[receipt(s) for s in SOURCES],'stopped':False},baseline())
        self.assertEqual(r['counts']['unverifiable'],3); self.assertEqual(r['documents'],baseline())

    def test_same_transition_is_not_proposed_twice(self):
        acq={'receipts':[receipt(s) for s in SOURCES],'stopped':False}
        with patch.object(pdf_watch,'inspect',side_effect=details):
            first=pdf_watch.reconcile(None,SOURCES,{}, {},acq,baseline())
            seen={x['review_key']:'previous_review' for x in first['reviews']}
            second=pdf_watch.reconcile(None,SOURCES,{}, {'seen_reviews':seen},acq,baseline())
        self.assertEqual(second['reviews'],[])

    def test_missing_anchor_is_unconfirmed_not_policy_change(self):
        body=valid_pdf(); sha=hashlib.sha256(body).hexdigest(); bridge=MagicMock()
        bridge.record.return_value=({'mime_type':'application/pdf','fiscal_year':2026},body)
        bridge.evidence.side_effect=Hold('Quote absent')
        result=pdf_watch.inspect(bridge,SOURCES[0],sha,[{'source_url':URL,'sha256':'a'*64,'locator':{'physical_page':22},'quote':'TEST'}])
        self.assertEqual(result['anchor_checks'][0]['status'],'unconfirmed')
        self.assertEqual(result['policy_verification'],'unchanged_by_version_watch')

    def test_bounded_pdf_capture_stops_at_failed_worker(self):
        bridge=MagicMock(); bridge.hashes={}; bridge.store.read_index.return_value={'documents':{}}; bridge.store.verify_integrity.return_value={}
        body=valid_pdf(); sha=hashlib.sha256(body).hexdigest(); bridge.store.snapshot_bytes.return_value=body
        calls=[]
        def child(cmd,**kwargs):
            calls.append(cmd); self.assertEqual(kwargs['timeout'],10)
            self.assertEqual(cmd[cmd.index('--media-type')+1],'pdf')
            folder=Path(cmd[cmd.index('--output')+1]); source=load(folder/'source.json')
            result={'status':'unchanged','source_url':source['url'],'http_status':200,'version':{'sha256':sha}}
            if len(calls)==2: result.update(status='rejected_mime',version=None)
            (folder/'worker_outcome.json').write_text(json.dumps(result))
            return SimpleNamespace(returncode=0,stderr='')
        with tempfile.TemporaryDirectory() as d,patch.object(acquire,'assert_owner_only',return_value={'owner_only':True}),patch.object(acquire,'P1Bridge',return_value=bridge),patch.object(acquire.subprocess,'run',side_effect=child):
            result=acquire.capture_sources('P1','CAS',SOURCES,d,authorized=True,refresh=True,media_type='pdf')
            self.assertTrue(result['stopped']); self.assertEqual(len(calls),2); self.assertEqual(result['new_get_requests'],2)
            self.assertEqual(load(Path(d)/'preflight.json')['limits']['max_total_received_bytes'],25165824)


class IndependentPhaseTests(unittest.TestCase):
    def config(self):
        return load(CONFIG.parent/'kyoto_additional_pdf_watch.json')

    def runtime(self, root):
        cfg=self.config(); sources=cfg['pdf_watch']['sources']
        def pinned(name,value):
            path=root/name;path.write_text(json.dumps(value),encoding='utf-8')
            return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        state=root/'phase_state';state.mkdir();cas=root/'cas';cas.mkdir()
        code=Path(pdf_watch.__file__).resolve()
        return {'state_root':str(state),'snapshot_root':str(cas),'p1_code_root':'unused',
                'network_enabled':False,'base_revision':'offline',
                'config':pinned('config.json',cfg),'baseline':pinned('baseline.json',{}),
                'bindings':pinned('bindings.json',{s['url']:[{'source_url':s['url']}] for s in sources}),
                'code_files':[{'path':str(code),'sha256':hashlib.sha256(code.read_bytes()).hexdigest()}]}

    def test_independent_six_mib_does_not_change_legacy_budget(self):
        self.assertEqual(pdf_request_plan(self.config())['max_received_bytes'],6291456)
        self.assertEqual(pdf_request_plan(load(CONFIG))['max_received_bytes'],25165824)
        bad=load(CONFIG);bad['pdf_watch']['max_total_received_bytes']=6291456
        with self.assertRaises(Hold):pdf_request_plan(bad)

    def test_phase_boundaries_fail_closed(self):
        for key,value in [('max_total_received_bytes',6291457),('max_requests_per_run',4),
                          ('tls_verify',False),('redirects',1),('retries',1),('timeout_seconds',11),
                          ('policy_ids',['KOBE-M01']),('allowed_hosts',['example.org']),('phase_id','../bad')]:
            cfg=self.config();cfg['pdf_watch'][key]=value
            with self.subTest(key=key),self.assertRaises(Hold):pdf_request_plan(cfg)
        for key,value in [('max_bytes',2097153),('policy_ids',['P-03']),('url','https://www.city.kobe.lg.jp/a.pdf')]:
            cfg=self.config();cfg['pdf_watch']['sources'][0][key]=value
            with self.subTest(key=key),self.assertRaises(Hold):pdf_request_plan(cfg)

    def test_offline_missing_original_never_falls_back_to_network(self):
        with tempfile.TemporaryDirectory() as d,patch.object(pdf_watch,'assert_owner_only'),patch('mayor_updates.weekly.assert_owner_only'):
            runtime=self.runtime(Path(d));bridge=MagicMock();bridge.index={'documents':{}}
            with patch.object(pdf_watch,'P1Bridge',return_value=bridge),patch.object(pdf_watch,'capture_sources') as capture:
                with self.assertRaisesRegex(Hold,'network fallback is forbidden'):pdf_watch.run(runtime,reuse_saved=True)
                capture.assert_not_called()
            self.assertFalse((Path(runtime['state_root'])/'state.json').exists())

    def test_independent_phase_cannot_adopt_live_state_or_different_scope(self):
        with tempfile.TemporaryDirectory() as d,patch.object(pdf_watch,'assert_owner_only'),patch('mayor_updates.weekly.assert_owner_only'):
            runtime=self.runtime(Path(d));state=Path(runtime['state_root'])
            (state/'state.json').write_text('{"sentinel":"live"}')
            with self.assertRaisesRegex(Hold,'fresh isolated state'):pdf_watch.validate_runtime(runtime,reuse_saved=True)
            self.assertEqual((state/'state.json').read_text(),'{"sentinel":"live"}')
        with tempfile.TemporaryDirectory() as d,patch.object(pdf_watch,'assert_owner_only'),patch('mayor_updates.weekly.assert_owner_only'):
            runtime=self.runtime(Path(d));pdf_watch.validate_runtime(runtime,reuse_saved=True)
            path=Path(runtime['config']['path']);cfg=load(path);cfg['pdf_watch']['phase_id']='different_phase'
            path.write_text(json.dumps(cfg));runtime['config']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(Hold,'binding mismatch'):pdf_watch.validate_runtime(runtime,reuse_saved=True)

    def test_new_phase_stays_disabled_and_old_policy_guard_remains(self):
        with tempfile.TemporaryDirectory() as d,patch.object(pdf_watch,'assert_owner_only'),patch('mayor_updates.weekly.assert_owner_only'):
            runtime=self.runtime(Path(d))
            with self.assertRaisesRegex(Hold,'not activated'):pdf_watch.validate_runtime(runtime,reuse_saved=False)
            cfg=load(CONFIG);cfg['pdf_watch']['sources'][0]['policy_ids']=['P-07']
            path=Path(runtime['config']['path']);path.write_text(json.dumps(cfg));runtime['config']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(Hold,'policy/page'):pdf_watch.validate_runtime(runtime,reuse_saved=True)

class BundleTests(unittest.TestCase):
    def gate(self, root, *, due='2026-11-15T11:00:00+09:00'):
        xml=f'''<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
        <RegistrationInfo><URI>\\GikaiMikata-Kyoto-Mayor-Weekly</URI></RegistrationInfo>
        <Principals><Principal><LogonType>InteractiveToken</LogonType></Principal></Principals>
        <Settings><AllowStartOnDemand>false</AllowStartOnDemand></Settings>
        <Triggers><TimeTrigger id="proof"><StartBoundary>{due}</StartBoundary></TimeTrigger>
        <CalendarTrigger><StartBoundary>2026-11-16T09:00:00+09:00</StartBoundary></CalendarTrigger></Triggers></Task>'''
        observation={'task_name':'GikaiMikata-Kyoto-Mayor-Weekly','registered_at':'2026-11-15T10:50:00+09:00',
                     'last_run':due,'last_result':0,'state':'Ready','checked_at':'2026-11-15T11:02:00+09:00'}
        evidence={}
        for name,text in [('task_before',xml),('task_after',xml),('observation',json.dumps(observation))]:
            path=root/name; path.write_text(text,encoding='utf-8'); evidence[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return {'state':'scheduled_run_verified','task_name':'GikaiMikata-Kyoto-Mayor-Weekly','task_last_result':0,
                'scheduled_for':due,'trigger_id':'proof','started_at':due,'finished_at':'2026-11-15T11:01:00+09:00',
                'html_get_requests':3,'public_writes':0,'cas_integrity_pass':True,'state_consistent':True,
                'scheduler_evidence':evidence}

    def test_early_scheduled_proof_and_future_or_missed_run(self):
        with tempfile.TemporaryDirectory() as d,patch.object(weekly_bundle.weekly,'assert_owner_only'):
            gate=self.gate(Path(d))
            weekly_bundle.verify_autorun(gate,datetime.fromisoformat('2026-11-15T12:00:00+09:00'))
            with self.assertRaises(Hold): weekly_bundle.verify_autorun(gate,datetime.fromisoformat('2026-11-15T10:00:00+09:00'))
            gate['state']='scheduled_run_not_met'
            with self.assertRaises(Hold): weekly_bundle.verify_autorun(gate,datetime.fromisoformat('2026-11-15T12:00:00+09:00'))

    def test_missing_or_inconsistent_run_proof_stops(self):
        with tempfile.TemporaryDirectory() as d,patch.object(weekly_bundle.weekly,'assert_owner_only'):
            gate=self.gate(Path(d)); now=datetime.fromisoformat('2026-11-15T12:00:00+09:00')
            for field,value in [('scheduler_evidence',{}),('task_name','another-task'),('trigger_id','wrong'),
                    ('scheduled_for','2026-11-15T10:59:00+09:00'),('task_last_result',1),('public_writes',1),
                    ('cas_integrity_pass',False),('state_consistent',False),('html_get_requests',0),
                    ('started_at','2026-11-15T11:04:00+09:00')]:
                with self.subTest(field=field),self.assertRaises(Hold):
                    weekly_bundle.verify_autorun({**gate,field:value},now)

    def test_manual_start_changed_task_and_unpinned_evidence_stop(self):
        with tempfile.TemporaryDirectory() as d,patch.object(weekly_bundle.weekly,'assert_owner_only'):
            root=Path(d); now=datetime.fromisoformat('2026-11-15T12:00:00+09:00')
            for mode in ('manual_allowed','changed_task','tampered_hash','wrong_task','failed_result'):
                gate=self.gate(root)
                if mode=='failed_result':
                    spec=gate['scheduler_evidence']['observation']; path=Path(spec['path'])
                    obj=json.loads(path.read_text()); obj['last_result']=1; path.write_text(json.dumps(obj))
                    spec['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                else:
                    for name in ('task_before','task_after') if mode in ('manual_allowed','wrong_task') else ('task_after',):
                        spec=gate['scheduler_evidence'][name]; path=Path(spec['path']); text=path.read_text()
                        text=text.replace('false','true') if mode!='wrong_task' else text.replace('GikaiMikata','Other')
                        path.write_text(text)
                        if mode!='tampered_hash': spec['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                with self.subTest(mode=mode),self.assertRaises(Hold): weekly_bundle.verify_autorun(gate,now)

    def test_combined_limits_and_separate_states(self):
        a={'state_root':'HTML','snapshot_root':'CAS','baseline':{'sha256':'a'}}
        b={**a,'state_root':'PDF'}; config=load(CONFIG); plan=pdf_request_plan(config)
        weekly_bundle.validate_combined(a,b,config,plan)
        with self.assertRaises(Hold): weekly_bundle.validate_combined(a,a,config,plan)
        with self.assertRaises(Hold): weekly_bundle.validate_combined(a,b,config,{**plan,'max_received_bytes':31457280})

    def test_pdf_failure_keeps_successful_html_history_and_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); history=root/'html_state.json'; history.write_text('before')
            def html(_): history.write_text('success'); return {'state_advanced':True,'new_get_requests':3}
            with patch.object(weekly_bundle.weekly,'run',side_effect=html) as h,patch.object(weekly_bundle.pdf_watch,'run',side_effect=Hold('PDF timeout')) as p:
                with self.assertRaises(Hold): weekly_bundle.execute(root,{}, {},day='2026-11-16')
                self.assertEqual(history.read_text(),'success')
                with self.assertRaises(Hold): weekly_bundle.execute(root,{}, {},day='2026-11-16')
                self.assertEqual(h.call_count,1); self.assertEqual(p.call_count,1)
                self.assertTrue(load(root/'runs/2026-11-16/failure.json')['html_success_retained'])

    def test_html_failure_does_not_start_pdf(self):
        with tempfile.TemporaryDirectory() as d,patch.object(weekly_bundle.weekly,'run',return_value={'state_advanced':False}),patch.object(weekly_bundle.pdf_watch,'run') as pdf:
            with self.assertRaises(Hold): weekly_bundle.execute(Path(d),{}, {},day='2026-11-16')
            pdf.assert_not_called()

if __name__=='__main__': unittest.main()
