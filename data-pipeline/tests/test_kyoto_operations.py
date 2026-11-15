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
        # The saved P-03 fixture predates the accepted shared history/rounding
        # disclaimer. Compare every other field exactly against that snapshot.
        from mayor_updates.projection import BUDGET_TOTAL_NOTE
        expected=copy.deepcopy(candidate)
        expected['summary_stats']['budget_total_note']=BUDGET_TOTAL_NOTE
        self.assertEqual(builder.generation_output(self.root/'trial/candidate_tracker_PRIVATE.json'),expected)
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




class CityReviewTests(unittest.TestCase):
    def fixture(self, city='yokohama', pid='YOKOHAMA-M01'):
        url='https://www.city.'+city+'.lg.jp/test.html'
        source={'url':url,'role':'progress','selector':'main'}
        config={'cities':{city:{'policy_ids':[pid],'monitor_sources':[source]}}}
        baseline={'pledges':[{'id':pid,'budget_records':[]}]}
        result={'document_events':[{'kind':'new_document','source_url':url,'before_sha256':None,'after_sha256':'a'*64}],
                'index_events':[],'state':{'documents':{url:{'sha256':'a'*64}},'indexes':{}},
                'holds':[],'fallback_units':[{'source_url':url,'sha256':'a'*64,'locator':{'selector':'main'},'quote':'SYNTHETIC'}]}
        bridge=MagicMock();bridge.index={'documents':{}}
        return bridge,config,baseline,result

    def test_explicit_city_review_and_same_transition_deduplication(self):
        from mayor_updates import operations
        bridge,config,baseline,result=self.fixture();before=copy.deepcopy(baseline)
        with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor',return_value=result):
            root=Path(d);first=root/'first';first.mkdir()
            _,packet=operations.run_trial(bridge,config,baseline,[],first,base_revision='test',city='yokohama',allowed=['YOKOHAMA-M01'])
            self.assertIsNone(packet);self.assertEqual(baseline,before)
            queue=operations.load(first/'evidence_review_queue.json')
            self.assertEqual(queue['city'],'yokohama');self.assertEqual(queue['policy_ids'],['YOKOHAMA-M01'])
            self.assertFalse(queue['publication_authorized']);self.assertEqual(queue['verification_status'],'unverified')
            self.assertEqual(queue['source_units'][0]['locator'],{'selector':'main'})
            seen=operations.load(first/'run_status.json')['new_reviews'];self.assertEqual(len(seen),1)
            repeat=root/'repeat';repeat.mkdir()
            operations.run_trial(bridge,config,baseline,[],repeat,base_revision='new-transport-only',city='yokohama',allowed=['YOKOHAMA-M01'],seen_reviews=seen)
            self.assertFalse((repeat/'evidence_review_queue.json').exists())
            self.assertEqual(operations.load(repeat/'run_status.json')['public_writes'],0)

    def test_unscoped_or_foreign_policy_rejected(self):
        from mayor_updates import operations
        bridge,config,baseline,result=self.fixture()
        for allowed in [None,[],['P-03']]:
            with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor') as monitor:
                with self.assertRaises(Hold):operations.run_trial(bridge,config,baseline,[],d,base_revision='test',city='yokohama',allowed=allowed)
                monitor.assert_not_called()
        bridge.index={'documents':{config['cities']['yokohama']['monitor_sources'][0]['url']:{'versions':[{'record':{'city_code':'kyoto'}}]}}}
        with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor') as monitor:
            with self.assertRaises(Hold):operations.run_trial(bridge,config,baseline,[],d,base_revision='test',city='yokohama',allowed=['YOKOHAMA-M01'])
            monitor.assert_not_called()

    def test_unchanged_and_failure_do_not_emit_review(self):
        from mayor_updates import operations
        for failed in [False,True]:
            bridge,config,baseline,result=self.fixture()
            result['document_events'][0]['kind']='document_fetch_failed' if failed else 'unchanged'
            if failed:result['holds']=[{'reason':'HTTP404'}]
            with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor',return_value=result):
                _,packet=operations.run_trial(bridge,config,baseline,[],d,base_revision='test',city='yokohama',allowed=['YOKOHAMA-M01'])
                self.assertIsNone(packet);self.assertFalse((Path(d)/'evidence_review_queue.json').exists())
                status=operations.load(Path(d)/'run_status.json');self.assertEqual(status['public_writes'],0)
                self.assertEqual(status['state'],'stopped_no_public_change' if failed else 'unchanged')

    def test_kyoto_default_identity_is_retained(self):
        from mayor_updates import operations
        bridge,config,baseline,result=self.fixture('kyoto','P-03')
        with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor',return_value=result):
            operations.run_trial(bridge,config,baseline,[],d,base_revision='test')
            queue=operations.load(Path(d)/'evidence_review_queue.json')
            self.assertEqual(queue['city'],'kyoto');self.assertEqual(queue['policy_ids'],['P-03'])


class LegacyKyotoRuleTests(unittest.TestCase):
    def fixture(self):
        from types import SimpleNamespace
        url='https://www.city.kyoto.lg.jp/test.html'
        rules=[{'policy_id':'P-03','source_specs':[{'source_url':url,'sha256':'a'*64}]}]
        bridge=SimpleNamespace(index={'documents':{url:{'versions':[{'sha256':'a'*64,'record':{'city_code':'kyoto'}}]}}})
        config={'cities':{'kyoto':{'policy_ids':['P-03'],'monitor_sources':[]}}}
        baseline={'pledges':[{'id':'P-03'}]}
        result={'document_events':[],'index_events':[],'state':{'documents':{},'indexes':{}},'holds':[],'fallback_units':[]}
        return bridge,config,baseline,rules,result

    def test_missing_city_only_in_legacy_kyoto_is_inferred_without_input_mutation(self):
        from mayor_updates import operations
        bridge,config,baseline,rules,result=self.fixture();before=copy.deepcopy(rules)
        with tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor',return_value=result):
            operations.run_trial(bridge,config,baseline,rules,d,base_revision='legacy')
            self.assertEqual(rules,before)
            self.assertEqual(operations.load(Path(d)/'run_status.json')['public_writes'],0)

    def test_missing_city_without_exact_saved_identity_or_with_explicit_city_is_rejected(self):
        from mayor_updates import operations
        for case in ['missing_version','foreign_record','foreign_host','null_city','foreign_city','no_sources']:
            bridge,config,baseline,rules,result=self.fixture()
            if case=='missing_version':rules[0]['source_specs'][0]['sha256']='b'*64
            if case=='foreign_record':next(iter(bridge.index['documents'].values()))['versions'][0]['record']['city_code']='kobe'
            if case=='foreign_host':rules[0]['source_specs'][0]['source_url']='https://www.city.kobe.lg.jp/test.html'
            if case=='null_city':rules[0]['city']=None
            if case=='foreign_city':rules[0]['city']='kobe'
            if case=='no_sources':rules[0]['source_specs']=[]
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d,patch.object(operations,'monitor') as monitor:
                with self.assertRaises(Hold):operations.run_trial(bridge,config,baseline,rules,d,base_revision='legacy')
                monitor.assert_not_called()


class PDFEvidenceFallbackTests(unittest.TestCase):
    def test_pdf_pages_are_explicit_and_evidence_is_not_a_budget_proposal(self):
        from mayor_updates.index_adapter import preserved_units
        import fitz
        with fitz.open() as doc:
            doc.new_page().insert_text((40,40),'SYNTHETIC evacuation awareness')
            body=doc.tobytes()
        bridge=MagicMock();bridge.record.return_value=({'mime_type':'application/pdf','source_title':'SYNTHETIC'},body)
        bridge.evidence.side_effect=lambda spec:{**spec,'quote_match':'exact','version_id':spec['sha256']}
        source={'url':'https://www.city.yokohama.lg.jp/test.pdf','policy_id':'YOKOHAMA-M01','review_pages':[{'physical_page':1}]}
        rows=preserved_units(bridge,source,'a'*64)
        self.assertEqual(rows[0]['kind'],'document_evidence');self.assertEqual(rows[0]['locator']['physical_page'],1)
        self.assertFalse(rows[0]['eligible_for_automatic_publication']);self.assertEqual(rows[0]['verification_status'],'unverified')
        self.assertNotIn('amount_jpy',rows[0])
        for pages in [[],[{'physical_page':0}],[{'physical_page':2}]]:
            with self.assertRaises(Hold):preserved_units(bridge,{**source,'review_pages':pages},'a'*64)





class CityIndexTests(unittest.TestCase):
    def fixture(self,city='kobe'):
        from types import SimpleNamespace
        from urllib.parse import urljoin,urlsplit
        from mayor_updates.city_scope import official_host
        host=official_host(city);url='https://'+host+'/index.html'
        body='<html><title>Index</title><div id="content"><h2>令和8年度 当初予算案</h2><a href="/a.pdf">A</a><h2>9月補正予算案</h2><a href="/b.pdf">B</a></div></html>'.encode()
        rec={'city_code':city,'mime_type':'text/html','sha256':'a'*64,'retrieved_at':'2026-11-15T00:00:00Z'}
        def canonical(raw,base,*,allowed_hosts):
            target=urljoin(base,raw)
            if urlsplit(target).hostname not in allowed_hosts:raise Hold('Foreign host')
            return target
        discovery=SimpleNamespace(parse_saved_html=lambda _:SimpleNamespace(redirect_hints=[],base_hints=[]),canonical_official_url=canonical)
        bridge=MagicMock();bridge.record.return_value=(rec,body);bridge.modules={'discovery':discovery}
        bridge.index={'documents':{url:{'versions':[{'sha256':'a'*64,'record':rec}]}},'attempts':[]};bridge.extract.return_value={'candidates':[]}
        source={'url':url,'resolution_base':url,'selector':'#content','fiscal_year':2026,'role':'index'}
        return bridge,source

    def test_kyoto_default_keeps_round_classification(self):
        from mayor_updates.index_adapter import saved_index
        bridge,s=self.fixture('kyoto');r=saved_index(bridge,s,'a'*64)
        self.assertEqual(r['counts'],{'initial':1,'supplemental':1})
        self.assertEqual(r['links']['https://www.city.kyoto.lg.jp/a.pdf'][0]['budget_status'],'proposal')

    def test_other_city_attachments_are_not_budget_classification(self):
        from mayor_updates.index_adapter import saved_index
        for city,host in [('kobe','www.city.kobe.lg.jp'),('nagoya','www.city.nagoya.jp')]:
            bridge,s=self.fixture(city);r=saved_index(bridge,s,'a'*64,city=city)
            self.assertEqual(r['counts'],{'unknown':2})
            for url,rows in r['links'].items():
                self.assertTrue(url.startswith('https://'+host+'/'))
                self.assertEqual(rows[0]['budget_status'],'unconfirmed');self.assertFalse(rows[0]['link_content_read'])
                self.assertEqual(rows[0]['document_kind'],'official_attachment')

    def test_index_identity_year_and_base_fail_closed(self):
        from mayor_updates.index_adapter import saved_index
        bridge,s=self.fixture()
        with self.assertRaises(Hold):saved_index(bridge,s,'a'*64)
        for field,value in [('fiscal_year',2025),('resolution_base','https://www.city.kyoto.lg.jp/')]:
            bad={**s,field:value}
            with self.assertRaises(Hold):saved_index(bridge,bad,'a'*64,city='kobe')

    def test_run_trial_passes_city_and_retains_index_review_dedup(self):
        from mayor_updates.operations import run_trial,load
        bridge,s=self.fixture();cfg={'cities':{'kobe':{'policy_ids':['KOBE-M01'],'monitor_sources':[s]}}}
        baseline={'pledges':[{'id':'KOBE-M01'}]}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=root/'first';first.mkdir()
            r,packet=run_trial(bridge,cfg,baseline,[],first,city='kobe',allowed=['KOBE-M01'],base_revision='test')
            self.assertIsNone(packet);self.assertFalse(r['holds']);self.assertEqual(load(first/'run_status.json')['new_reviews'],{})
            old=copy.deepcopy(r['state']);old['indexes'][s['url']]['https://www.city.kobe.lg.jp/a.pdf'][0]['title']='Old label'
            changed=root/'changed';changed.mkdir()
            run_trial(bridge,cfg,baseline,[],changed,previous=old,city='kobe',allowed=['KOBE-M01'],base_revision='test')
            status=load(changed/'run_status.json');self.assertEqual(len(status['new_reviews']),1);self.assertEqual(status['public_writes'],0)
            replay=root/'replay';replay.mkdir()
            run_trial(bridge,cfg,baseline,[],replay,previous=old,seen_reviews=status['new_reviews'],city='kobe',allowed=['KOBE-M01'],base_revision='test')
            self.assertEqual(load(replay/'run_status.json')['new_reviews'],{})

if __name__=='__main__': unittest.main(verbosity=2)
