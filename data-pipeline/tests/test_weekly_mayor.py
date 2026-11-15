"""Weekly persistence/review tests use synthetic data and never issue HTTP."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import weekly, operations
from mayor_updates.projection import Hold
from mayor_updates.monitor import pdf_request_plan
from test_mayor_updates import base, budget, URL

class WeeklyTests(unittest.TestCase):
    def test_lock_blocks_parallel_and_stale_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with weekly.single_run(root):
                with self.assertRaises(Hold):
                    with weekly.single_run(root): pass
            self.assertFalse((root/'weekly.lock').exists())
            (root/'weekly.lock').write_text('interrupted')
            with self.assertRaises(Hold):
                with weekly.single_run(root): pass
            self.assertEqual((root/'weekly.lock').read_text(),'interrupted')

    def test_failure_does_not_advance_good_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); prior={'monitor':{'old':'good'},'seen_reviews':{'known':'old-review'}}
            weekly.atomic_json(root/'state.json',prior)
            before=(root/'state.json').read_bytes()
            self.assertFalse(weekly.commit_success(root,root,prior,{'new':'bad'}, {'state':'stopped_no_public_change'}))
            self.assertEqual((root/'state.json').read_bytes(),before)

    def test_atomic_failure_keeps_monitor_and_review_ledger_together(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); prior={'monitor':{'old':'good'},'seen_reviews':{}}
            weekly.atomic_json(root/'state.json',prior)
            with patch.object(weekly.os,'replace',side_effect=OSError('TEST storage failure')):
                with self.assertRaises(OSError): weekly.commit_success(root,root,prior,{'new':'good'},
                    {'state':'review_pending','new_reviews':{'key':'review_packet.json'}})
            self.assertEqual(weekly.load(root/'state.json'),prior)
            self.assertEqual(list(root.glob('*.tmp')),[])

    def test_success_persists_pending_review_across_unchanged_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); prior={'monitor':{},'seen_reviews':{}}
            self.assertTrue(weekly.commit_success(root,root,prior,{'sha':'new'},
                {'state':'review_pending','new_reviews':{'key':'review_packet.json'}}))
            saved=weekly.load(root/'state.json')
            self.assertEqual(saved['seen_reviews']['key'],str(root/'review_packet.json'))
            weekly.commit_success(root,root,saved,{'sha':'new'},{'state':'unchanged'})
            self.assertEqual(weekly.load(root/'state.json')['seen_reviews'],saved['seen_reviews'])

    def test_repeated_evidence_does_not_emit_same_policy_review(self):
        result={'document_events':[], 'index_events':[{'kind':'link_changed','source_url':URL}],
                'holds':[],'fallback_units':[], 'state':{'documents':{},'indexes':{}}}
        bridge=MagicMock(); bridge.map_rule.return_value=budget()
        config={'cities':{'kyoto':{'monitor_sources':[]}}}
        rules=[{'policy_id':'P-03','source_specs':[{'source_url':URL}]}]
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, patch.object(operations,'monitor',return_value=result):
            _,packet=operations.run_trial(bridge,config,base(),rules,a,base_revision='fixture')
            self.assertIsNotNone(packet)
            seen=weekly.load(Path(a)/'run_status.json')['new_reviews']
            bridge.map_rule.return_value=copy.deepcopy(budget())
            bridge.map_rule.return_value['evidence'][0]['retrieved_at']='2026-11-16T00:00:00Z'
            _,packet=operations.run_trial(bridge,config,base(),rules,b,base_revision='fixture',seen_reviews=seen)
            self.assertIsNone(packet)
            self.assertFalse((Path(b)/'review_packet.json').exists())
            self.assertFalse((Path(b)/'review.html').exists())
            self.assertFalse((Path(b)/'candidate_tracker_PRIVATE.json').exists())

    def test_source_queue_deduplicates_but_changed_sha_is_new(self):
        result={'document_events':[], 'index_events':[{'kind':'link_added','source_url':URL}],
                'holds':[], 'fallback_units':[], 'state':{'documents':{'index':{'sha256':'a'*64}},'indexes':{}}}
        config={'cities':{'kyoto':{'monitor_sources':[]}}}
        with tempfile.TemporaryDirectory() as d, patch.object(operations,'monitor',return_value=result):
            root=Path(d); seen={}
            for i,sha in enumerate(['a','a','b']):
                result['state']['documents']['index']['sha256']=sha*64
                out=root/str(i); out.mkdir()
                operations.run_trial(None,config,base(),[],out,base_revision='fixture',seen_reviews=seen)
                new=weekly.load(out/'run_status.json')['new_reviews']
                self.assertEqual(bool(new),i!=1); seen.update(new)

    def test_pdf_registry_cannot_enable_html_runner_or_expand_limit(self):
        config=weekly.load(Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json')
        self.assertEqual(len(weekly.validate_plan(config)),3)
        self.assertEqual(sum(s['max_bytes'] for s in config['cities']['kyoto']['monitor_sources']),6291456)
        self.assertEqual(len(config['pdf_watch']['sources']),3)
        self.assertEqual(sum(s['max_bytes'] for s in config['pdf_watch']['sources']),25165824)
        self.assertFalse(config['schedule']['enabled'])
        plan=pdf_request_plan(config)
        self.assertFalse(plan['execution_enabled']); self.assertEqual(plan['max_received_bytes'],25165824)
        excessive=copy.deepcopy(config); excessive['pdf_watch']['sources'][1]['max_bytes']=20971520
        with self.assertRaises(Hold): pdf_request_plan(excessive)
        foreign=copy.deepcopy(config); foreign['pdf_watch']['sources'][0]['url']='https://example.org/a.pdf'
        with self.assertRaises(Hold): pdf_request_plan(foreign)
        config['pdf_watch']['enabled']=True
        with self.assertRaises(Hold): weekly.validate_plan(config)
        config['pdf_watch']['enabled']=False
        config['communication']['retries']=1
        with self.assertRaises(Hold): weekly.validate_plan(config)

    def test_disabled_live_entry_stops_before_acquisition(self):
        config=weekly.load(Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cfg=root/'config.json'; cfg.write_text(json.dumps(config))
            code=Path(weekly.__file__).resolve()
            runtime={'state_root':str(root),'snapshot_root':str(root),'network_enabled':False,
                     'config':{'path':str(cfg)},'baseline':{'path':str(cfg)},'rules':{'path':str(cfg)},
                     'code_files':[{'path':str(code)}]}
            with patch.object(weekly,'assert_owner_only'), \
                 patch.object(weekly,'pinned_input',side_effect=lambda spec:Path(spec['path'])), \
                 patch.object(weekly,'capture_sources') as capture:
                with self.assertRaises(Hold): weekly.run(runtime)
                capture.assert_not_called()
                self.assertFalse((root/'runs').exists())

    def test_modified_local_input_is_not_silently_used(self):
        with tempfile.TemporaryDirectory() as d, patch.object(weekly,'assert_owner_only'):
            p=Path(d)/'rules.json'; p.write_text('changed')
            with self.assertRaises(Hold): weekly.pinned_input({'path':str(p),'sha256':'0'*64})

    def test_zero_candidate_has_no_review_html(self):
        with tempfile.TemporaryDirectory() as d:
            weekly.review_index(Path(d),{'state':'unchanged','new_reviews':{}})
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_entry_failure_retains_previous_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); prior={'monitor':{},'seen_reviews':{}}
            weekly.atomic_json(root/'state.json',prior)
            with patch.object(weekly,'validate_runtime',return_value=(root,{},{})), \
                 patch.object(weekly,'P1Bridge',side_effect=ValueError('TEST corrupt CAS')):
                with self.assertRaises(ValueError): weekly.run({'p1_code_root':'TEST','snapshot_root':'TEST'},reuse_saved=True)
            self.assertEqual(weekly.load(root/'state.json'),prior)
            self.assertEqual(len(list((root/'runs').glob('*/failure.json'))),1)
            self.assertFalse((root/'weekly.lock').exists())

if __name__=='__main__': unittest.main()
