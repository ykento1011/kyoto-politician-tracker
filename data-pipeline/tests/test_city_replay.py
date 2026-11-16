"""Persistent single-series replay: no network, private fixtures only."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import operations
from mayor_updates.city_scope import official_host

class ReplayTests(unittest.TestCase):
    def fixture(self,root,city='kobe',policy='KOBE-M01'):
        state=root/'state';state.mkdir();cas=root/'cas';cas.mkdir();(cas/'index.json').write_text('{}')
        url='https://'+official_host(city)+'/test.html';body=b'<html><div id="content"><h2>Notice</h2><p>Original evidence</p></div></html>'
        sha=hashlib.sha256(body).hexdigest();docid=city+'-doc-'+hashlib.sha256(url.encode()).hexdigest()[:24]
        baseline=root/'baseline.json';baseline.write_text(json.dumps({'city_code':city,'pledges':[{'id':policy}]}))
        source={'url':url,'id':'test','media_type':'html','role':'progress','policy_ids':[policy],'policy_id':policy,'fiscal_year':2026,'selector':'#content','document_kind':'other_official'}
        spec={'city':city,'series_id':'test','policy_ids':[policy],'source':source,'sha256':sha,'document_id':docid,'state_root':str(state),'snapshot_root':str(cas),'baseline':{'path':str(baseline),'sha256':hashlib.sha256(baseline.read_bytes()).hexdigest()},'p1_code_root':'PINNED_TEST','city_capable':True,'base_revision':'test'}
        rec={'city_code':city,'document_id':docid,'sha256':sha,'version_id':sha,'fiscal_year':2026,'mime_type':'text/html','retrieved_at':'2026-11-15T00:00:00Z'}
        bridge=MagicMock();bridge.hashes={'test':'pinned'};bridge.index={'documents':{url:{'versions':[{'sha256':sha,'record':rec}]}},'attempts':[]};bridge.record.return_value=(rec,body);bridge.extract.return_value={'candidates':[]}
        return spec,bridge

    def run_replay(self,spec,bridge):
        with patch('mayor_updates.acquire.assert_owner_only'),patch('mayor_updates.weekly.assert_owner_only'),patch.object(operations,'P1Bridge',return_value=bridge),patch.object(operations,'capture_sources',side_effect=AssertionError('No acquisition allowed')):
            return operations.replay_saved(spec)

    def test_all_five_cities_initial_and_repeat(self):
        for city,pid in [('kyoto','P-03'),('kobe','KOBE-M01'),('yokohama','YOKOHAMA-M01'),('osaka','OSAKA-M01'),('nagoya','nagoya_p2')]:
            with self.subTest(city=city),tempfile.TemporaryDirectory() as d:
                spec,b=self.fixture(Path(d),city,pid);first=self.run_replay(spec,b);again=self.run_replay(spec,b)
                self.assertTrue(first['state_advanced']);self.assertEqual(first['new_review_count'],1)
                self.assertEqual(again['new_review_count'],0);self.assertEqual(again['network_requests'],0);self.assertEqual(again['public_writes'],0)

    def test_changed_version_review_and_repeat_are_persistent(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d));self.run_replay(s,b)
            rec,body=b.record.return_value;body+=b'<!-- new saved edition -->'
            sha=hashlib.sha256(body).hexdigest();rec=deepcopy(rec);rec.update(sha256=sha,version_id=sha)
            b.record.return_value=(rec,body)
            b.index['documents'][s['source']['url']]['versions'].append({'sha256':sha,'record':rec})
            stale=self.run_replay(s,b);self.assertFalse(stale['state_advanced'])
            s['sha256']=sha;changed=self.run_replay(s,b)
            self.assertTrue(changed['state_advanced']);self.assertEqual(changed['new_review_count'],1)
            self.assertEqual(changed['document_events'][0]['kind'],'replacement_document')
            again=self.run_replay(s,b);self.assertTrue(again['state_advanced']);self.assertEqual(again['new_review_count'],0)
            self.assertFalse(changed['publication_authorized'])

    def test_structured_candidates_keep_source_locations_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d))
            b.extract.return_value={'candidates':[{'project_name':'Extracted candidate'}]}
            first=self.run_replay(s,b)
            queue=json.loads((Path(first['run_dir'])/'evidence_review_queue.json').read_text())
            self.assertTrue(queue['source_units'])
            unit=queue['source_units'][0]
            self.assertEqual(unit['sha256'],s['sha256'])
            self.assertEqual(unit['quote'],'Original evidence')
            self.assertIn('locator',unit)
            self.assertFalse(queue['publication_authorized'])
            again=self.run_replay(s,b)
            self.assertEqual(again['new_review_count'],0)
            self.assertEqual(again['public_writes'],0)

    def test_legacy_kyoto_baseline_without_city_code(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d),'kyoto','P-03');p=Path(s['baseline']['path'])
            value=json.loads(p.read_text());del value['city_code']
            value['mayor_info']={'city_label':'京都市','bulletin_pdf':'https://www.city.kyoto.lg.jp/bulletin.pdf'}
            p.write_text(json.dumps(value));s['baseline']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertTrue(self.run_replay(s,b)['state_advanced'])
            good=(Path(s['state_root'])/'state.json').read_bytes()
            value['mayor_info']['city_label']='神戸市';p.write_text(json.dumps(value));s['baseline']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertFalse(self.run_replay(s,b)['state_advanced'])
            self.assertEqual((Path(s['state_root'])/'state.json').read_bytes(),good)

    def test_guard_failures_keep_good_state(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d));self.run_replay(s,b);state=Path(s['state_root'])/'state.json';good=state.read_bytes()
            for mutate in [lambda x:x.update(network_enabled=True),lambda x:x.update(city='osaka'),lambda x:x.update(sha256='0'*64),lambda x:x.update(document_id='wrong'),lambda x:x['source'].update(url='https://evil.example/a.html'),lambda x:x['source'].update(policy_id='P-01'),lambda x:x.update(series_id='different')]:
                bad=deepcopy(s);mutate(bad);r=self.run_replay(bad,b);self.assertFalse(r['state_advanced']);self.assertEqual(state.read_bytes(),good)
            b.index['documents'][s['source']['url']]['versions'][0]['record']['city_code']='osaka'
            self.assertFalse(self.run_replay(s,b)['state_advanced']);self.assertEqual(state.read_bytes(),good)

    def test_corrupt_original_and_failure_do_not_commit(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d));self.run_replay(s,b);state=Path(s['state_root'])/'state.json';good=state.read_bytes()
            b.record.side_effect=ValueError('SHA mismatch');r=self.run_replay(s,b);self.assertFalse(r['state_advanced']);self.assertEqual(state.read_bytes(),good)
            b.record.side_effect=None;b.index['attempts']=[{'source_url':s['source']['url'],'outcome':'not_found'}]
            r=self.run_replay(s,b);self.assertFalse(r['state_advanced']);self.assertEqual(state.read_bytes(),good)

    def test_live_unbound_state_and_existing_lock_are_not_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d));state=Path(s['state_root'])/'state.json';state.write_text('{"live":"sentinel"}');good=state.read_bytes()
            self.assertFalse(self.run_replay(s,b)['state_advanced']);self.assertEqual(state.read_bytes(),good)
            lock=state.parent/'weekly.lock';lock.write_text('existing')
            with self.assertRaises(ValueError):self.run_replay(s,b)
            self.assertEqual(lock.read_text(),'existing')

    def test_review_failure_keeps_previous_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            s,b=self.fixture(Path(d));self.run_replay(s,b);state=Path(s['state_root'])/'state.json';good=state.read_bytes()
            with patch('mayor_updates.weekly.review_index',side_effect=OSError('disk failure')):
                r=self.run_replay(s,b)
            self.assertFalse(r['state_advanced']);self.assertEqual(state.read_bytes(),good)

if __name__=='__main__':unittest.main()
