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

class BundleTests(unittest.TestCase):
    def gate(self):
        return {'state':'scheduled_run_verified','task_name':'GikaiMikata-Kyoto-Mayor-Weekly','task_last_result':0,
                'started_at':'2026-11-16T09:00:00+09:00','finished_at':'2026-11-16T09:01:00+09:00',
                'html_get_requests':3,'public_writes':0,'cas_integrity_pass':True,'state_consistent':True}

    def test_future_or_missed_autorun_cannot_activate_bundle(self):
        with self.assertRaises(Hold): weekly_bundle.verify_autorun(self.gate(),datetime.fromisoformat('2026-11-15T12:00:00+09:00'))
        bad=self.gate(); bad['state']='scheduled_run_not_met'
        with self.assertRaises(Hold): weekly_bundle.verify_autorun(bad,datetime.fromisoformat('2026-11-16T12:00:00+09:00'))
        weekly_bundle.verify_autorun(self.gate(),datetime.fromisoformat('2026-11-16T12:00:00+09:00'))

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
