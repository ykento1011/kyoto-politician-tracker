"""Real registered Kyoto URLs; synthetic versions, no network or live CAS writes."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urljoin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import continuous as loop
from mayor_updates.projection import Hold

REPO=Path(__file__).resolve().parents[2]

class SavedBridge:
    def __init__(self, root, sources):
        self.store=SimpleNamespace(root=root,verify_integrity=lambda:None)
        self.index={'documents':{},'attempts':[]};self.bodies={}
        self.modules={'discovery':SimpleNamespace(
            parse_saved_html=lambda text:SimpleNamespace(redirect_hints=[],base_hints=[]),
            canonical_official_url=lambda url,base,**kw:urljoin(base,url))}
        for s in sources:self.save(s,'initial')
    def save(self,s,label):
        body=('<div id="mol_contents"><h2>令和'+str(s['fiscal_year']-2018)+'年度 当初予算案</h2>'
              '<p>'+label+'</p><a href="'+label+'.pdf">候補資料</a></div>').encode()
        sha=hashlib.sha256(body).hexdigest();url=s['url'];self.bodies[sha]=body
        rec=dict(city_code='kyoto',source_url=url,sha256=sha,version_id=sha,
            retrieved_at='2026-11-17T00:00:00+00:00',mime_type='text/html',source_title=s['title'])
        self.index['documents'].setdefault(url,{'versions':[]})['versions'].append({'record':rec,'sha256':sha})
        self.index['attempts'].append(dict(source_url=url,outcome='new_version',sha256=sha))
    def record(self,url,sha):
        rec=next(v['record'] for v in self.index['documents'][url]['versions'] if v['sha256']==sha)
        body=self.bodies[sha]
        if hashlib.sha256(body).hexdigest()!=sha:raise Hold('Corrupt original')
        return rec,body
    def extract(self,url,sha):return {'candidates':[]}

class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.state=self.root/'state';self.state.mkdir()
        cas=self.root/'cas';cas.mkdir()
        self.config=loop.load(REPO/'config/mayor_update_sources.json')
        self.baseline=loop.load(REPO/'frontend/public/data/kyoto_mayor_tracker.json')
        self.sources=self.config['cities']['kyoto']['monitor_sources']
        self.bridge=SavedBridge(cas,self.sources)
        for p in (patch.object(socket.socket,'connect',side_effect=AssertionError('No HTTP')),
                  patch.object(loop.weekly,'assert_owner_only')):
            p.start();self.addCleanup(p.stop)
    def run_cycle(self,day):
        return loop.cycle(self.bridge,self.config,self.baseline,[],self.state,
            city='kyoto',cycle_key='2026-11-'+str(day),base_revision='offline-fixture')
    def test_repeated_loop_keeps_good_versions_and_review_history(self):
        baseline=copy.deepcopy(self.baseline)
        first=self.run_cycle(17);self.assertTrue(first['state_advanced'])
        self.assertEqual(self.run_cycle(18)['new_review_count'],0)
        self.bridge.save(self.sources[0],'revised-index')
        self.bridge.save(self.sources[2],'revised-progress')
        changed=self.run_cycle(19);self.assertEqual(changed['new_review_count'],2)
        state=loop.load(self.state/'state.json');before=(self.state/'state.json').read_bytes()
        evidence=loop.load(self.state/'cycles/2026-11-19/evidence_review_queue.json')
        self.assertEqual(evidence['source_units'][0]['policy_id'],'P-03')
        self.assertIn('revised-progress',evidence['source_units'][0]['quote'])
        self.assertFalse(evidence['publication_authorized'])
        key=next(iter(state['seen_reviews']))
        loop.review_decision(self.state,key,'hold','TEST reviewer','政策対応は未確認')
        loop.review_decision(self.state,key,'rejected','TEST reviewer','予算議決の証拠ではない')
        self.assertEqual((self.state/'state.json').read_bytes(),before)
        self.bridge.index['attempts'].append(dict(source_url=self.sources[0]['url'],outcome='timeout'))
        failed=self.run_cycle(20);self.assertFalse(failed['state_advanced'])
        self.assertEqual((self.state/'state.json').read_bytes(),before)
        with self.assertRaises(Hold):self.run_cycle(20)
        self.bridge.index['attempts'].append(dict(source_url=self.sources[0]['url'],outcome='unchanged'))
        self.assertEqual(self.run_cycle(21)['new_review_count'],0)
        self.assertEqual(len(list((self.state/'review_events').glob('*.json'))),2)
        self.assertEqual(self.baseline,baseline)
        for path in (self.state/'cycles').glob('*/cycle_result.json'):
            result=loop.load(path);self.assertEqual(result['public_writes'],0);self.assertEqual(result['network_requests'],0)
    def test_corruption_and_unknown_source_do_not_replace_good_pointer(self):
        self.run_cycle(17);before=(self.state/'state.json').read_bytes()
        sha=next(iter(self.bridge.bodies));self.bridge.bodies[sha]=b'corrupt'
        with self.assertRaises(Hold):self.run_cycle(18)
        self.assertEqual((self.state/'state.json').read_bytes(),before)
        self.config['cities']['kyoto']['monitor_sources'][0]['url']='https://example.org/index.html'
        with self.assertRaises(Hold):self.run_cycle(19)
        self.assertFalse((self.state/'cycles/2026-11-19').exists())
    def test_no_approval_or_arbitrary_cycle(self):
        with self.assertRaises(Hold):self.run_cycle('../escape')
        self.run_cycle(17)
        key=next(iter(loop.load(self.state/'state.json')['seen_reviews']))
        with self.assertRaises(Hold):loop.review_decision(self.state,key,'approved','TEST','approve')
        with self.assertRaises(Hold):loop.review_decision(self.state,'unknown','hold','TEST','reason')

if __name__=='__main__':unittest.main()
