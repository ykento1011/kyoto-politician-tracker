"""Exact-contract negative cases; real P1 tests use only isolated fake bytes."""
import copy
import hashlib
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates.p03_contract_scope import (
    URL, DOCUMENT_ID, LIMIT, contract_scope, validate_contract_scope,
    offline_fetch_options, validate_contract_record,
)
from mayor_updates.projection import Hold


class ContractScopeTests(unittest.TestCase):
    def test_disabled_exact_scope_and_conservative_p1_bounds(self):
        s = contract_scope()
        self.assertEqual(validate_contract_scope(s, s['source']), s['source'])
        self.assertEqual(offline_fetch_options(s, s['source']), {
            'allowed_hosts': frozenset({'www2.city.kyoto.lg.jp'}),
            'max_bytes': LIMIT - 1, 'max_redirects': 0, 'timeout_seconds': 10})
        s['source']['url'] = 'changed'
        self.assertEqual(contract_scope()['source']['url'], URL)

    def test_raw_url_variants_rejected_before_p1_normalization(self):
        for url in [URL.replace('https:', 'http:'), URL.replace('www2.', 'www.'),
                    URL.replace('kyoto', 'kobe'), URL.replace('www2.city.kyoto.lg.jp', 'example.test'),
                    URL.replace('.lg.jp/', '.lg.jp.example.test/'),
                    URL.replace('.lg.jp/', '.lg.jp:443/'), URL.replace('.lg.jp/', '.lg.jp:8443/'),
                    URL.replace('https://', 'https://user@'), URL + '?x=1', URL + '#page=1',
                    URL.replace('104.pdf', '105.pdf'), URL.replace('/R7-9/', '/R7-9/./')]:
            s = contract_scope(); s['source']['url'] = url
            with self.subTest(url=url), self.assertRaises(Hold):
                validate_contract_scope(s, s['source'])

    def test_scope_and_policy_limits_cannot_be_expanded(self):
        changes = {'city_code':'kobe', 'policy_ids':['P-01'], 'allowed_hosts':['www.city.kyoto.lg.jp'],
                   'max_requests':2, 'max_response_bytes':LIMIT+1, 'max_total_bytes':LIMIT+1,
                   'timeout_seconds':11, 'wall_timeout_seconds':11, 'tls_verify':False,
                   'redirects':1, 'retries':1, 'follow_links':True, 'enabled':True,
                   'network_enabled':True, 'public_writes':True, 'unknown':True}
        for key, value in changes.items():
            s = contract_scope(); s[key] = value
            with self.subTest(key=key), self.assertRaises(Hold):
                validate_contract_scope(s, s['source'])
        for value in [True, 1.0]:
            s = contract_scope(); s['max_requests'] = value
            with self.assertRaises(Hold): validate_contract_scope(s, s['source'])

    def test_source_identity_and_selection_exact(self):
        for key, value in {'document_id':'other', 'policy_ids':['P-01'], 'fiscal_year':2026,
                           'media_type':'html', 'document_kind':'budget_index'}.items():
            s = contract_scope(); source = copy.deepcopy(s['source']); source[key] = value
            with self.subTest(key=key), self.assertRaises(Hold): validate_contract_scope(s, source)
            s['source'] = source
            with self.assertRaises(Hold): validate_contract_scope(s, source)

    def test_legacy_guards_remain_closed(self):
        from mayor_updates.acquire import validate_sources
        from mayor_updates.city_scope import validate_scope
        s = contract_scope(); source = dict(s['source'], id='p03-contract', max_bytes=LIMIT)
        with self.assertRaises(Hold): validate_sources([source], media_type='pdf')
        old = dict(city_code='kyoto', policy_ids=['P-03'], allowed_hosts=['www2.city.kyoto.lg.jp'])
        with self.assertRaises(Hold): validate_scope(old)

    def test_record_sha_and_city_mismatch_rejected(self):
        s = contract_scope(); body = b'%PDF-1.4\nsynthetic only\n%%EOF'
        digest = hashlib.sha256(body).hexdigest()
        record = dict(source_url=URL, document_id=DOCUMENT_ID, city_code='kyoto',
                      fiscal_year=2025, mime_type='application/pdf', document_type='other_official',
                      sha256=digest, version_id=digest)
        self.assertEqual(validate_contract_record(s, s['source'], record, body), digest)
        for key, value in [('city_code','kobe'), ('fiscal_year',2026), ('document_id','other'),
                           ('source_url',URL+'#x'), ('mime_type','text/html'), ('sha256','0'*64),
                           ('version_id','0'*64)]:
            with self.subTest(key=key), self.assertRaises(Hold):
                validate_contract_record(s, s['source'], dict(record, **{key:value}), body)
        for bad in [b'', b'<html>not PDF</html>', body+b'corrupt', b'%PDF-'+b'x'*LIMIT]:
            with self.assertRaises(Hold): validate_contract_record(s, s['source'], record, bad)


@unittest.skipUnless(os.environ.get('MAYOR_P1_APPROVED_ROOT'), 'Requires pinned private P1 code; no originals')
class ContractP1Tests(unittest.TestCase):
    def setUp(self):
        from mayor_updates.p1_bridge import P1Bridge
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.bridge = P1Bridge(os.environ['MAYOR_P1_APPROVED_ROOT'], Path(self.temp.name)/'synthetic_cas')
        self.scope = contract_scope(); self.source = self.scope['source']
        self.body = b'%PDF-1.4\n% SYNTHETIC TEST ONLY\n%%EOF\n'
        # Any accidental live DNS/connect fails the test.
        for name in ['getaddrinfo', 'create_connection']:
            p = patch.object(socket, name, side_effect=AssertionError('No network'))
            p.start(); self.addCleanup(p.stop)
        p = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        p.start(); self.addCleanup(p.stop)

    def run_response(self, response):
        from budget.adapters.kyoto import DiscoveredDocument
        calls = []
        class Fixture:
            def request(inner, url, **limits):
                self.assertEqual(url, URL); self.assertEqual(calls, [])
                self.assertEqual(limits, dict(timeout_seconds=10, max_bytes=LIMIT-1))
                calls.append(url)
                if isinstance(response, Exception): raise response
                return response
        doc = DiscoveredDocument(URL, 'Historic contract candidate', '令和7年度', 2025,
                                 'pdf', 'other_official', 'unknown', None, URL, URL,
                                 None, None, 'discovered_unverified', ())
        fetcher = self.bridge.modules['fetch'].SourceFetcher(
            self.bridge.store, transport=Fixture(), **offline_fetch_options(self.scope, self.source))
        outcome = fetcher.fetch_discovered(doc)
        self.assertEqual(calls, [URL])
        return outcome

    def good(self):
        return self.bridge.modules['fetch'].HTTPResponse(200, {'Content-Type':'application/pdf'}, self.body, True)

    def test_actual_p1_exact_identity_readback_and_dedup(self):
        self.assertEqual(self.run_response(self.good()).status, 'stored_new_version')
        self.assertEqual(self.run_response(self.good()).status, 'unchanged')
        versions = self.bridge.store.read_index()['documents'][URL]['versions']
        self.assertEqual(len(versions), 1)
        record = versions[0]['record']; body = self.bridge.store.snapshot_bytes(record['sha256'])
        self.assertEqual(validate_contract_record(self.scope, self.source, record, body), record['sha256'])

    def test_abnormal_responses_preserve_last_good_version_no_retry(self):
        response = self.bridge.modules['fetch'].HTTPResponse
        self.run_response(self.good())
        before = copy.deepcopy(self.bridge.store.read_index()['documents'])
        bad = [response(n, {'Location':URL.replace('104','105')}, b'', True) for n in [301,302,303,307,308]]
        bad += [response(200, {'Content-Type':'application/pdf'}, self.body, False),
                response(404, {}, b'', True), response(429, {'Retry-After':'1'}, b'', True),
                TimeoutError(), response(200, {'Content-Type':'application/pdf'}, b'x'*LIMIT, True),
                response(200, {'Content-Type':'text/html'}, b'<html>x</html>', True)]
        for value in bad:
            with self.subTest(response=str(value)[:50]):
                self.assertIsNone(self.run_response(value).version)
                self.assertEqual(self.bridge.store.read_index()['documents'], before)
                self.assertEqual(self.bridge.store.snapshot_bytes(hashlib.sha256(self.body).hexdigest()), self.body)


if __name__ == '__main__': unittest.main()
