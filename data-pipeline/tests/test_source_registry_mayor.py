"""Offline source discovery/registration using synthetic saved index versions."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_continuous_mayor as fixtures
from mayor_updates import source_registry as sr
from mayor_updates.projection import Hold


class RegistryTests(unittest.TestCase):
    def setUp(self):
        fixtures.ContinuousTests.setUp(self)
        self.source = self.sources[1]
        self.ledger = sr.Registry(self.state,self.bridge,'kyoto')
        self.url = 'https://www.city.kyoto.lg.jp/gyozai/test.pdf'

    def save(self, links):
        html = '<div id="mol_contents"><h2>令和7年度 当初予算案</h2>'+''.join(
            '<a href="'+url+'">'+title+'</a>' for url,title in links)+'</div>'
        body = html.encode(); sha = hashlib.sha256(body).hexdigest()
        rec = dict(city_code='kyoto',source_url=self.source['url'],sha256=sha,
            final_url=self.source['url'],fiscal_year=2025,
            version_id=sha,retrieved_at='2026-11-17T00:00:00+00:00',mime_type='text/html',source_title='索引')
        self.bridge.bodies[sha] = body
        self.bridge.index['documents'][self.source['url']]['versions'].append({'record':rec,'sha256':sha})
        return sha

    def scan(self, links):
        sha = self.save(links)
        return self.ledger.apply({'operation':'scan','source':self.source,'index_sha256':sha})

    def row(self):
        return self.ledger.apply({'operation':'report'})['sources'][0]

    def request(self, op, **kw):
        r = self.row()
        return dict(operation=op,candidate_id=r['candidate_id'],revision=r['revision'],
            index_sha256=r['index_sha256'],reviewer='TEST reviewer',reason='source registration only',**kw)

    def test_discovery_dedup_changes_removal_and_stale_approval(self):
        self.assertEqual(self.scan([(self.url,'予算案')])['changes'],1)
        first = self.row(); history = [p.read_bytes() for p in sorted(self.state.glob('event-*'))]
        self.assertEqual(self.scan([(self.url,'予算案')])['new_events'],0)
        approve = self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04'])
        self.ledger.apply(approve)
        proposal = self.ledger.apply(self.request('proposal'))
        self.assertFalse(proposal['enabled']); self.assertFalse(proposal['network_enabled'])
        self.assertEqual(proposal['source']['url'],self.url)
        self.assertEqual(self.ledger.apply(approve)['new_events'],0)
        self.scan([(self.url,'改訂予算案'),(self.url,'別掲載位置')])
        self.assertEqual(self.row()['candidate_id'],first['candidate_id'])
        self.assertEqual(len(self.row()['locators']),2)
        with self.assertRaises(Hold): self.ledger.apply(approve)
        with self.assertRaises(Hold): self.ledger.apply(self.request('proposal'))
        self.scan([])
        self.assertFalse(self.row()['active'])
        self.scan([(self.url,'予算案')])
        self.assertEqual(self.row()['registration_status'],'pending')
        self.assertEqual(history[0],sorted(self.state.glob('event-*'))[0].read_bytes())

    def test_hold_reject_and_foreign_policy_do_not_allow_acquisition(self):
        self.scan([(self.url,'予算案')])
        for decision in ('hold','reject'):
            self.ledger.apply(self.request('decision',decision=decision,policy_ids=['P-04']))
            self.assertEqual(self.row()['registration_status'],decision)
            with self.assertRaises(Hold): self.ledger.apply(self.request('proposal'))
        self.assertEqual(self.ledger.apply(self.request('decision',decision='hold',policy_ids=['P-04']))['new_events'],1)
        before = list(self.state.glob('event-*'))
        for values in [dict(decision='approve_for_source_registration',policy_ids=['KOBE-M01']),
                       dict(decision='publish',policy_ids=['P-04'])]:
            with self.assertRaises(Hold): self.ledger.apply(self.request('decision',**values))
        self.assertEqual(before,list(self.state.glob('event-*')))

    def test_bad_url_year_anchor_and_index_sha_hold_without_changing_history(self):
        self.scan([(self.url,'予算案')]); before = {p.name:p.read_bytes() for p in self.state.glob('event-*')}
        for url in ('http://www.city.kyoto.lg.jp/a.pdf','https://evil.example/a.pdf'):
            with self.assertRaises(Hold): self.scan([(url,'予算案')])
        with self.assertRaises(Hold):sr.pdf_url('kyoto',self.url+'?x=1')
        wrong = copy.deepcopy(self.source); wrong['fiscal_year']=2024
        with self.assertRaises(Hold): self.ledger.apply(dict(operation='scan',source=wrong,index_sha256='0'*64))
        with self.assertRaises((Hold,StopIteration)): self.ledger.apply(dict(operation='scan',source=self.source,index_sha256='0'*64))
        version=self.save([(self.url,'予算案')]); real=sr.saved_index
        bad=real(self.bridge,self.source,version);bad['links'][self.url][0]['locator']['anchor_ordinal']=0
        with patch.object(sr,'saved_index',return_value=bad):
            with self.assertRaises(Hold): self.ledger.apply(dict(operation='scan',source=self.source,index_sha256=version))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})

    def receipt_spec(self):
        body=b'%PDF-synthetic';sha=hashlib.sha256(body).hexdigest();at='2026-11-17T00:00:00+00:00'
        rec=dict(city_code='kyoto',source_url=self.url,final_url=self.url,sha256=sha,
            document_id='kyoto-doc-fixture',version_id=sha,snapshot_relative_path='objects/fixture',
            fiscal_year=2025,mime_type='application/pdf',document_type='other_official',
            retrieved_at=at,source_title='Test budget proposal')
        self.bridge.index['documents'][self.url]={'versions':[{'sha256':sha,'record':rec}]}
        self.bridge.index['attempts'].append(dict(source_url=self.url,sha256=sha,outcome='new_version',observed_at=at))
        self.bridge.bodies[sha]=body;self.bridge.hashes={'fixture':'pin'}
        source=dict(url=self.url,fiscal_year=2025,media_type='pdf',document_kind='other_official',policy_ids=['P-04'],max_bytes=2097152)
        pre=dict(sources=[source],code_sha256=self.bridge.hashes,limits=dict(get_per_url=1,tls_verify=True,redirects=0,retries=0,wall_timeout_seconds=10))
        receipt=dict(stopped=False,public_writes=0,receipts=[dict(source_url=self.url,version=rec,sha256=sha,
            stored_bytes=len(body),readback_pass=True,new_get_requests=1,http_status=200,final_url=self.url,status='stored_new_version')])
        spec=dict(city='kyoto',source=source,policy_ids=['P-04'])
        for key,value in [('acquisition_preflight',pre),('acquisition_receipt',receipt)]:
            path=self.root/(key+'.json');path.write_text(json.dumps(value))
            spec[key]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return spec

    def test_receipt_cas_link_and_corruption_keep_good_history(self):
        self.scan([(self.url,'予算案')]);spec=self.receipt_spec()
        req=self.request('evidence',receipt_spec=spec)
        self.ledger.apply(req)
        row=self.row();self.assertEqual(row['document_id'],'kyoto-doc-fixture')
        self.assertEqual(row['evidence_status'],'政策との対応確認待ち')
        self.assertEqual(self.ledger.apply(req)['new_events'],0)
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        sha=row['original_sha256'];self.bridge.bodies[sha]=b'corrupt'
        with self.assertRaises(Hold):self.ledger.apply(req)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})

    def test_all_policies_reported_without_inferred_achievement(self):
        self.scan([(self.url,'予算案')]);report=self.ledger.apply({'operation':'report'})
        self.assertEqual(len(report['policies']),14)
        self.assertTrue(all(not p['candidate_ids'] for p in report['policies']))
        self.assertEqual(report['network_requests'],0);self.assertEqual(report['public_writes'],0)
        self.assertFalse(report['sources'][0]['publication_authorized'])

    def test_corrupt_history_and_failed_append_do_not_erase_previous(self):
        self.scan([(self.url,'予算案')]);before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        with patch.object(sr,'durable_record',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.ledger.apply(self.request('decision',decision='hold'))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})
        path=next(self.state.glob('event-*'));path.write_text(path.read_text().replace('link_added','link_removed'))
        with self.assertRaises(Hold):self.ledger.apply({'operation':'report'})

    def test_failed_latest_index_and_old_version_preserve_registry(self):
        self.scan([(self.url,'予算案')]);old=self.row()['index_sha256']
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        new=self.save([(self.url,'新版')])
        with self.assertRaises(Hold):self.ledger.apply(dict(operation='scan',source=self.source,index_sha256=old))
        self.bridge.index['attempts'].append(dict(source_url=self.source['url'],outcome='timeout'))
        with self.assertRaises(Hold):self.ledger.apply(dict(operation='scan',source=self.source,index_sha256=new))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})

    def test_missing_literal_quote_never_attaches_or_certifies(self):
        self.scan([(self.url,'予算案')]);spec=self.receipt_spec()
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        self.bridge.evidence=lambda _: (_ for _ in ()).throw(Hold('Quote absent'))
        note=dict(policy_id='P-04',subject='保育料',fact_type='budget_proposal',
                  locator={'physical_page':1},quote='not present')
        with self.assertRaises(Hold):self.ledger.apply(self.request('evidence',receipt_spec=spec,notes=[note]))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})


if __name__=='__main__':unittest.main()
