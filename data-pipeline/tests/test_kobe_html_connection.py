"""Synthetic reservation/receipt connection only; no real worker, P1 or CAS."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import kobe_html_connection as k
from mayor_updates.city_scope import reserve_request
from mayor_updates.projection import Hold


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ('series', 'cas', 'p1', 'legacy'):
            (self.root/name).mkdir()
        self.now = datetime.fromisoformat('2026-11-23T10:00:00+09:00')
        self.pins = {}
        self.legacy = self.pin('legacy/reservation', {'url': k.URL})
        end = self.pin('terminal', {'reservation_sha256': self.legacy['sha256'],
            'termination_confirmed': True, 'approval_reference': 'synthetic-only'})
        self.legacy['termination_evidence'] = end
        self.c = {'mode':'kobe-html1-reobservation-v1', 'city':'kobe',
            'source':copy.deepcopy(k.SOURCE), 'limits':copy.deepcopy(k.LIMITS),
            'enabled':True, 'network_enabled':True,
            'series_root':str(self.root/'series'), 'cas_root':str(self.root/'cas'),
            'p1_code_root':str(self.root/'p1'), 'legacy_reservations':[self.legacy],
            'legacy_state_roots':[str(self.root/'legacy')]}
        self.c['series_identity'] = self.pin('identity', {'city':'kobe', 'url':k.URL,
            'series_root':self.c['series_root'], 'cas_root':self.c['cas_root']})
        self.a = {key:self.c[key] for key in ('city','source','series_root','cas_root','p1_code_root')}
        self.a.update(approved=True, approval_reference='synthetic-only', week='2026-11-23',
                      valid_from='2026-11-23T09:00:00+09:00', valid_until='2026-11-23T11:00:00+09:00')
        self.calls = []; self.status = 'stored_new_version'; self.mutation = None
        for p in (patch.object(k.weekly, 'assert_owner_only'),
                  patch.object(socket.socket, 'connect', side_effect=AssertionError('HTTP forbidden'))):
            p.start(); self.addCleanup(p.stop)

    def pin(self, name, data):
        p = self.root/(name+'.json'); p.write_text(json.dumps(data), encoding='utf-8')
        return {'path':str(p), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

    def acquire(self, **kw):
        self.calls.append('acquire')
        self.assertEqual(kw['limits'], k.LIMITS)
        body = b'<html>synthetic</html>'; sha = hashlib.sha256(body).hexdigest()
        original = '2026-11-15T00:00:00+00:00'
        observed = '2026-11-23T01:00:00+00:00'
        rec = dict(city_code='kobe', document_id='kobe-doc-'+hashlib.sha256(k.URL.encode()).hexdigest()[:24],
            source_url=k.URL, final_url=k.URL, fiscal_year=2026, document_type='budget_index',
            mime_type='text/html', sha256=sha, version_id=sha, snapshot_relative_path='objects/test.bin',
            retrieved_at=original if self.status=='unchanged' else observed)
        self.bridge = MagicMock(); self.bridge.store.root = self.root/'cas'
        self.bridge.hashes = {'synthetic':'pin'}
        self.bridge.record.return_value = rec, body
        self.bridge.index = {'documents':{k.URL:{'versions':[{'sha256':sha, 'record':rec}]}},
            'attempts':[{'source_url':k.URL,'sha256':sha,'observed_at':observed,
                        'outcome':'unchanged' if self.status=='unchanged' else 'new_version'}]}
        version = {**rec, 'retrieved_at':observed}
        receipt = dict(stopped=False, public_writes=0, new_get_requests=1, new_get_requests_max=1,
            receipts=[dict(source_url=k.URL, final_url=k.URL, status=self.status, version=version,
                sha256=sha, stored_bytes=len(body), readback_pass=True, new_get_requests=1, http_status=200)])
        preflight = {'sources':[k.SOURCE], 'limits':k.LIMITS, 'code_sha256':dict(self.bridge.hashes)}
        if self.mutation: self.mutation(receipt, preflight, self.bridge)
        prefix = kw['output'].relative_to(self.root)
        return {'termination_confirmed':True,
            'acquisition_receipt':self.pin(str(prefix/'acquisition_result'), receipt),
            'acquisition_preflight':self.pin(str(prefix/'preflight'), preflight)}

    def factory(self, *args, **kwargs):
        self.assertEqual(self.calls, ['acquire'])  # Fresh P1 after worker, not stale index.
        return self.bridge

    def process(self, **kw):
        self.calls.append('process')
        self.assertFalse(kw['network_enabled']); self.assertFalse(kw['publication_authorized'])
        return {'state_advanced':True, 'public_writes':0, 'network_requests':0}

    def run_case(self, acquire=None):
        cp = self.pin('contract', self.c); self.a['contract_sha256'] = cp['sha256']
        ap = self.pin('approval', self.a)
        with patch.object(k, 'P1Bridge', side_effect=self.factory), patch.object(k, 'clock', return_value=self.now):
            return k.connect(cp, ap, acquire=acquire or self.acquire, process=self.process)

    def test_new_and_same_version_handoff(self):
        result = self.run_case()
        self.assertEqual(result['state'], 'private_result_saved')
        self.assertTrue((Path(result['output'])/'reservation.json').exists())
        with self.assertRaises(Hold): self.run_case()

    def test_same_version_retains_original_time(self):
        self.status = 'unchanged'; result = self.run_case()
        audit = result['acquisition_audit']
        self.assertNotEqual(audit['original_retrieved_at'], audit['acquisition_observed_at'])

    def test_disabled_and_scope_mismatch(self):
        original = copy.deepcopy(self.c)
        for key, value in [('enabled',False),('network_enabled',False),('city','osaka')]:
            self.c = copy.deepcopy(original); self.c[key]=value
            with self.assertRaises(Hold): self.run_case()
        for key,value in [('url',k.URL+'?x=1'),('media_type','pdf'),('fiscal_year',2025)]:
            self.c=copy.deepcopy(original); self.c['source'][key]=value
            with self.assertRaises(Hold): self.run_case()
        self.assertEqual(self.calls, [])

    def test_week_approval_legacy_and_root_mismatch(self):
        original = copy.deepcopy(self.a)
        for key,value in [('week','2026-11-30'),('approved',False),('series_root',str(self.root)),
                          ('valid_until','2026-11-23T09:59:59+09:00')]:
            self.a=copy.deepcopy(original); self.a[key]=value
            with self.assertRaises(Hold): self.run_case()
        self.a=original; self.now=datetime.fromisoformat('2026-11-21T10:00:00+09:00')
        with self.assertRaises(Hold): self.run_case()
        self.now=datetime.fromisoformat('2026-11-23T10:00:00+09:00')
        (self.root/'legacy/cycles/2026-11-23').mkdir(parents=True)
        with self.assertRaises(Hold): self.run_case()
        self.assertEqual(self.calls, [])

    def test_unknown_or_failed_worker_retains_reservation(self):
        with self.assertRaises(Hold): self.run_case(lambda **kw: {'termination_confirmed':False})
        dirs=list((self.root/'series').iterdir()); self.assertEqual(len(dirs),1)
        self.assertTrue((dirs[0]/'reservation.json').exists())
        self.assertTrue((dirs[0]/'failure.json').exists())
        with self.assertRaises(Hold): self.run_case()

    def test_pins_receipt_cas_mismatch_preserves_legacy(self):
        before=Path(self.legacy['path']).read_bytes()
        self.mutation=lambda r,p,b:p['code_sha256'].update(synthetic='wrong')
        with self.assertRaises(Hold): self.run_case()
        self.assertEqual(Path(self.legacy['path']).read_bytes(),before)
        with self.assertRaises(Hold): self.run_case()

    def test_cas_version_mismatch(self):
        self.mutation=lambda r,p,b:r['receipts'][0]['version'].update(document_id='wrong')
        with self.assertRaises(Hold): self.run_case()
        self.assertNotIn('process',self.calls)

    def test_legacy_reservation_guard_unchanged(self):
        scope={'enabled':True,'network_enabled':True}
        storage={'state_root':str(self.root/'legacy')}
        reserve_request(scope,storage,k.SOURCE)
        with self.assertRaises(Hold): reserve_request(scope,storage,k.SOURCE)

    def test_interrupted_directory_and_existing_lock_rejected(self):
        (self.root/'series/unfinished').mkdir()
        with self.assertRaises(Hold): self.run_case()
        self.assertEqual(self.calls, [])
        (self.root/'series/unfinished').rmdir()  # Test fixture only.
        (self.root/'series/weekly.lock').write_text('synthetic other process')
        with self.assertRaises(Hold): self.run_case()
        self.assertTrue((self.root/'series/weekly.lock').exists())

    def test_expiry_at_pre_acquisition_check_keeps_slot(self):
        cp=self.pin('contract',self.c); self.a['contract_sha256']=cp['sha256']
        ap=self.pin('approval',self.a)
        later=datetime.fromisoformat('2026-11-23T11:00:00+09:00')
        with patch.object(k,'clock',side_effect=[self.now,self.now,later]):
            with self.assertRaises(Hold):
                k.connect(cp,ap,acquire=self.acquire,process=self.process)
        self.assertEqual(self.calls,[])
        self.assertEqual(len(list((self.root/'series').glob('*/failure.json'))),1)

    def test_process_public_write_or_unknown_network_is_not_success(self):
        self.process=lambda **kw:{'state_advanced':True,'public_writes':1}
        with self.assertRaises(Hold): self.run_case()
        self.assertEqual(list((self.root/'series').glob('*/completed.json')),[])

    def forged_observation(self, stamp):
        def mutate(r, p, b):
            r['receipts'][0]['version']['retrieved_at'] = stamp
            b.record.return_value[0]['retrieved_at'] = stamp
            b.index['attempts'][0]['observed_at'] = stamp
        self.mutation = mutate
        with self.assertRaisesRegex(Hold, 'outside this authorized'):
            self.run_case()
        self.assertNotIn('process', self.calls)
        self.assertEqual(len(list((self.root/'series').glob('*/reservation.json'))), 1)
        self.assertEqual(list((self.root/'series').glob('*/completed.json')), [])

    def test_past_receipt_cannot_be_relabelled_as_new_get(self):
        self.forged_observation('2026-11-15T01:00:00+00:00')

    def test_future_receipt_is_not_current_acquisition(self):
        self.forged_observation('2026-11-23T01:00:01+00:00')


if __name__ == '__main__': unittest.main()
