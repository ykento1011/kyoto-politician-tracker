"""Single-run connection tests. No live HTTP is issued by any test."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import acquire
from mayor_updates.engine import digest
from mayor_updates.projection import Hold,policies
from mayor_updates.monitor import request_plan

SOURCE={'id':'TEST','url':'https://www.city.kyoto.lg.jp/gyozai/page/TEST.html','title':'TEST',
        'fiscal_year':2026,'document_kind':'budget_index','max_bytes':2097152}

class AcquisitionTests(unittest.TestCase):
    def test_no_authorization_stops_before_bridge_or_network(self):
        with patch.object(acquire,'P1Bridge') as factory:
            with self.assertRaises(Hold): acquire.capture_sources('P1','CAS',[SOURCE],'.')
            factory.assert_not_called()

    def test_invalid_scope_is_rejected(self):
        for key,value in [('url','http://www.city.kyoto.lg.jp/a.html'),('url','https://example.org/a.html'),
                          ('url','https://www.city.kyoto.lg.jp/a.pdf'),('max_bytes',20*1024*1024)]:
            source={**SOURCE,key:value}
            with self.assertRaises(Hold): acquire.validate_sources([source])
        with self.assertRaises(Hold): acquire.validate_sources([SOURCE,SOURCE])

    def test_worker_needs_durable_parent_intent(self):
        with tempfile.TemporaryDirectory() as d, patch.object(acquire,'P1Bridge') as factory:
            with self.assertRaises(Hold): acquire.worker('P1','CAS',SOURCE,d)
            factory.assert_not_called()

    def test_wall_timeout_stops_without_retry(self):
        bridge=MagicMock(); bridge.hashes={}; bridge.store.read_index.return_value={'documents':{}}
        bridge.store.verify_integrity.return_value={}
        with tempfile.TemporaryDirectory() as d, patch.object(acquire,'assert_owner_only',return_value={'owner_only':True}), \
             patch.object(acquire,'P1Bridge',return_value=bridge), \
             patch.object(acquire.subprocess,'run',side_effect=subprocess.TimeoutExpired('TEST',10)) as worker:
            result=acquire.capture_sources('P1','CAS',[SOURCE],d,authorized=True)
            self.assertTrue(result['stopped']); self.assertIsNone(result['new_get_requests'])
            self.assertEqual(result['new_get_requests_max'],1); self.assertEqual(worker.call_count,1)
            self.assertEqual(worker.call_args.kwargs['timeout'],10)
            bridge.store.record_failure.assert_called_once()
            with self.assertRaises(Hold): acquire.capture_sources('P1','CAS',[SOURCE],d,authorized=True)
            self.assertEqual(worker.call_count,1)

    def test_reuse_is_zero_get_and_same_hash(self):
        body=b'<html>TEST fixture</html>'; sha=hashlib.sha256(body).hexdigest()
        rec={'sha256':sha,'version_id':sha,'retrieved_at':'2026-11-15T00:00:00Z'}
        bridge=MagicMock(); bridge.hashes={}; bridge.store.verify_integrity.return_value={}
        bridge.store.read_index.return_value={'documents':{SOURCE['url']:{'versions':[{'record':rec}]}}}
        bridge.store.snapshot_bytes.return_value=body
        with tempfile.TemporaryDirectory() as d, patch.object(acquire,'assert_owner_only',return_value={'owner_only':True}), \
             patch.object(acquire,'P1Bridge',return_value=bridge), patch.object(acquire.subprocess,'run') as worker:
            result=acquire.capture_sources('P1','CAS',[SOURCE],d,authorized=True)
            self.assertEqual(result['new_get_requests'],0); worker.assert_not_called()
            self.assertEqual(result['receipts'][0]['sha256'],sha)
            self.assertTrue(result['receipts'][0]['readback_pass'])

@unittest.skipUnless(os.environ.get('KYOTO_OPERATIONS_ROOT'),'Saved official fixtures require private operation root')
class OfficialConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mayor_updates.p1_bridge import P1Bridge
        cls.root=Path(os.environ['KYOTO_OPERATIONS_ROOT']); cls.private=cls.root.parent
        cls.load=staticmethod(lambda p:json.loads(p.read_text(encoding='utf-8-sig')))
        cls.config=cls.load(cls.root/'candidate/config/mayor_update_sources.json')
        cls.sources=cls.config['cities']['kyoto']['monitor_sources']
        cls.bridge=P1Bridge(os.environ['MAYOR_P1_CODE'],os.environ['MAYOR_PRIVATE_CAS'])
        cls.before=cls.load(cls.root/'monitor_before.json')
        cls.current=cls.load(cls.root/'trial/monitor_state.json')
        cls.baseline=cls.load(cls.private/'mayor_update_engine_20261115/demo/run_04/baseline_kyoto.json')
        cls.rules=cls.load(cls.root/'source_bound_rules.json')

    def test_actual_get_counts_cas_and_scope(self):
        result=self.load(self.root/'acquisition/acquisition_result.json')
        self.assertFalse(result['stopped']); self.assertEqual(result['new_get_requests'],2)
        self.assertEqual([r['new_get_requests'] for r in result['receipts']],[1,1,0])
        self.assertTrue(all(r['readback_pass'] for r in result['receipts']))
        self.assertTrue(all(r['stored_bytes']<=2097152 for r in result['receipts']))
        self.assertEqual(len(self.sources),3)
        self.assertFalse(self.config['schedule']['enabled'])
        self.assertTrue(all(s['interval_days']==7 for s in self.sources))
        plan=request_plan(self.config,'kyoto')
        self.assertEqual(plan['max_requests'],3); self.assertEqual(plan['max_received_bytes'],6291456)

    def test_index_urls_resolve_to_real_saved_pdf_and_year(self):
        from mayor_updates.index_adapter import saved_index
        for source in self.sources[:2]:
            version=self.bridge.index['documents'][source['url']]['versions'][-1]['sha256']
            result=saved_index(self.bridge,source,version)
            target=self.rules[0 if source['fiscal_year']==2025 else 1]['source_specs'][0]['source_url']
            self.assertIn(target,result['links'])
            for url,rows in result['links'].items():
                self.assertNotIn('/page/cmsfiles/',url)
                self.assertTrue(url.startswith('https://www.city.kyoto.lg.jp/'))
                self.assertTrue(all(r['index_sha256']==version and r['fiscal_year']==source['fiscal_year'] for r in rows))
                self.assertTrue(all(r['verification_status']=='unverified' and not r['link_content_read'] for r in rows))

    def test_supplement_month_and_initial_are_distinct(self):
        from mayor_updates.index_adapter import saved_index
        s=self.sources[0]; version=self.bridge.index['documents'][s['url']]['versions'][-1]['sha256']
        inv=saved_index(self.bridge,s,version)
        rows=[r for values in inv['links'].values() for r in values]
        self.assertEqual({r['session'] for r in rows if r['budget_round']=='supplemental'},{'5月','7月','9月'})
        self.assertTrue(any(r['budget_round']=='initial' for r in rows))
        education=[r for r in rows if r['source_url'].endswith('15_kyouiku_kouhou.pdf')][0]
        self.assertEqual(education['budget_status'],'proposal')
        self.assertEqual(education['budget_round'],'unknown') # no inferred 当初 token

    def test_foreign_or_unexpected_base_is_held(self):
        from mayor_updates.index_adapter import saved_index
        s=copy.deepcopy(self.sources[0]); version=self.bridge.index['documents'][s['url']]['versions'][-1]['sha256']
        s['resolution_base']='https://example.org/'
        with self.assertRaises(Hold): saved_index(self.bridge,s,version)

    def test_first_baseline_is_not_fabricated_historical_change(self):
        from mayor_updates.operations import monitor
        result=monitor(self.bridge,self.sources,self.before)
        self.assertEqual([e['kind'] for e in result['document_events']],['new_document','new_document','unchanged'])
        self.assertTrue(all(e.get('baseline_creation') for e in result['index_events']))
        self.assertTrue(all(e['policy_effect'] is None for e in result['index_events']))

    def test_second_identical_saved_run_creates_no_proposal(self):
        from mayor_updates.operations import run_trial
        with tempfile.TemporaryDirectory(dir=self.root/'qa') as d:
            result,packet=run_trial(self.bridge,self.config,self.baseline,self.rules,d,previous=self.current,base_revision='TEST')
            self.assertIsNone(packet)
            self.assertEqual({e['kind'] for e in result['document_events']},{'unchanged'})
            self.assertFalse((Path(d)/'review.html').exists()); self.assertFalse((Path(d)/'review_packet.json').exists())

    def test_index_sha_only_change_does_not_request_policy_review(self):
        from mayor_updates.operations import run_trial
        fixture=copy.deepcopy(self.current)
        fixture['documents'][self.sources[0]['url']]['sha256']='0'*64
        with tempfile.TemporaryDirectory(dir=self.root/'qa') as d:
            _,packet=run_trial(self.bridge,self.config,self.baseline,self.rules,d,previous=fixture,base_revision='TEST')
            self.assertIsNone(packet)
            status=self.load(Path(d)/'run_status.json')
            self.assertEqual(status['state'],'source_version_only')
            self.assertFalse((Path(d)/'review.html').exists())

    def test_failed_fetch_retains_good_state_and_no_proposal(self):
        from mayor_updates.operations import run_trial
        fixture=copy.copy(self.bridge); fixture.index=copy.deepcopy(self.bridge.index)
        fixture.index['attempts'].append({'source_url':self.sources[0]['url'],'outcome':'TEST_timeout','observed_at':'2099-01-01T00:00:00Z'})
        before=digest(self.baseline)
        with tempfile.TemporaryDirectory(dir=self.root/'qa') as d:
            result,packet=run_trial(fixture,self.config,self.baseline,self.rules,d,previous=self.current,base_revision='TEST')
            self.assertIsNone(packet); self.assertEqual(result['state']['documents'],self.current['documents'])
            self.assertEqual(digest(self.baseline),before)
            self.assertFalse((Path(d)/'candidate_tracker_PRIVATE.json').exists())

    def test_same_url_sha_change_and_link_removed_are_not_policy_removal(self):
        from mayor_updates.operations import monitor
        fixture=copy.deepcopy(self.current); url=self.sources[0]['url']
        fixture['documents'][url]['sha256']='0'*64
        fixture['indexes'][url]['https://www.city.kyoto.lg.jp/TEST_removed.pdf']=[]
        result=monitor(self.bridge,self.sources,fixture)
        self.assertEqual(result['document_events'][0]['kind'],'replacement_document')
        removed=[e for e in result['index_events'] if e['kind']=='link_removed']
        self.assertEqual(len(removed),1); self.assertIsNone(removed[0]['policy_effect'])

    def test_zero_structured_progress_preserves_quote_and_position(self):
        from mayor_updates.index_adapter import preserved_units
        s=self.sources[-1]; version=self.bridge.index['documents'][s['url']]['versions'][-1]['sha256']
        units=preserved_units(self.bridge,s,version)
        self.assertGreaterEqual(len(units),2)
        self.assertTrue(any('一時停止' in u['quote'] for u in units))
        self.assertTrue(all(u['locator']['heading'] and u['sha256']==version and not u['eligible_for_automatic_publication'] for u in units))

    def test_p03_only_and_generator_roundtrip_exact(self):
        candidate=self.load(self.root/'trial/candidate_tracker_PRIVATE.json')
        old,new=policies(self.baseline),policies(candidate)
        self.assertEqual([p for p in old if old[p]!=new[p]],['P-03'])
        for key in ('stage_level','stage_label','milestone','legislative_bill'):
            self.assertEqual(old['P-03'][key],new['P-03'][key])
        spec=importlib.util.spec_from_file_location('operations_builder',self.root/'candidate/data-pipeline/build_mayor_tracker.py')
        builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        self.assertEqual(builder.generation_output(self.root/'trial/candidate_tracker_PRIVATE.json'),candidate)
        self.assertEqual(candidate['summary_stats']['total_allocated_budget_raw'],9830158000)
        self.assertIn('全額の原典確認を済ませた総額ではありません',candidate['summary_stats']['budget_total_note'])

    def test_packet_retains_index_pdf_versions_and_no_approval(self):
        packet=self.load(self.root/'trial/review_packet.json')
        self.assertEqual(len(packet['changes']),1); self.assertEqual(len(packet['candidates']),3)
        for c in packet['candidates'][:2]:
            self.assertEqual(len(c['evidence']),2)
            self.assertTrue(any(e['mime_type']=='application/pdf' for e in c['evidence']))
            self.assertTrue(any(e['mime_type']=='text/html' for e in c['evidence']))
        self.assertFalse(packet['publication_authorized'])
        self.assertEqual(packet['verification_status'],'unverified')

if __name__=='__main__': unittest.main(verbosity=2)
