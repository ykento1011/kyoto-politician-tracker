"""Three-city repeat cycles; synthetic CAS, no HTTP or real reservation writes."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import test_continuous_mayor as fixtures
from mayor_updates import continuous, offline_weekly as adapter
from mayor_updates.projection import Hold


class OfflineWeeklyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = continuous.load(fixtures.REPO/'config/mayor_update_sources.json')
        for p in (patch.object(socket.socket, 'connect', side_effect=AssertionError('HTTP forbidden')),
                  patch.object(continuous.weekly, 'assert_owner_only')):
            p.start(); self.addCleanup(p.stop)

    def setup_city(self, city):
        local, sources = adapter.prepare(self.config, city)
        cas = self.root/city/'cas'; cas.mkdir(parents=True)
        state = self.root/city/'state'; state.mkdir()
        bridge = fixtures.SavedBridge(cas, [])
        baseline = continuous.load(fixtures.REPO/f'frontend/public/data/{city}_mayor_tracker.json')
        self.save(bridge, sources[0], city, 'initial')
        return bridge, sources[0], state, baseline

    def save(self, bridge, source, city, label):
        bridge.save(source, label)
        doc = bridge.index['documents'][source['url']]; rec = doc['versions'][-1]['record']
        old = rec['sha256']
        body = bridge.bodies[old].replace(b'mol_contents', source['selector'][1:].encode())
        sha = hashlib.sha256(body).hexdigest(); bridge.bodies[sha] = body
        rec.update(city_code=city, sha256=sha, version_id=sha)
        doc['versions'][-1]['sha256'] = sha
        bridge.index['attempts'][-1]['sha256'] = sha

    def run_city(self, city, data, day):
        bridge, _, state, baseline = data
        return adapter.run(bridge, self.config, baseline, state, city=city,
            now=datetime.fromisoformat(day+'T10:00:00+09:00'), base_revision='synthetic-only')

    def test_three_city_baseline_unchanged_change_and_duplicate_week(self):
        for city in ('osaka', 'yokohama', 'kobe'):
            with self.subTest(city=city):
                data = self.setup_city(city); bridge, source, state, baseline = data
                original = copy.deepcopy(baseline); config = copy.deepcopy(self.config)
                self.assertTrue(self.run_city(city, data, '2026-11-23')['state_advanced'])
                self.assertEqual(self.run_city(city, data, '2026-11-30')['new_review_count'], 0)
                self.save(bridge, source, city, 'new-document')
                changed = self.run_city(city, data, '2026-12-07')
                self.assertEqual(changed['new_review_count'], 1)
                self.assertEqual(self.run_city(city, data, '2026-12-14')['new_review_count'], 0)
                with self.assertRaises(Hold): self.run_city(city, data, '2026-12-15')
                report = continuous.load(state/'cycles/2026-12-07/city_report.json')
                self.assertEqual(report['city'], city)
                self.assertIn('HOLD', report['sources'][0]['policy_relation'])
                self.assertFalse(report['source_approval_inherited'])
                self.assertEqual(report['network_requests'], 0)
                self.assertEqual(report['public_writes'], 0)
                self.assertEqual(baseline, original); self.assertEqual(self.config, config)

    def test_failure_keeps_pointer_and_consumed_week(self):
        data = self.setup_city('osaka'); bridge, source, state, _ = data
        self.run_city('osaka', data, '2026-11-23'); before = (state/'state.json').read_bytes()
        bridge.index['attempts'].append({'source_url':source['url'], 'outcome':'timeout'})
        result = self.run_city('osaka', data, '2026-11-30')
        self.assertFalse(result['state_advanced'])
        self.assertEqual((state/'state.json').read_bytes(), before)
        with self.assertRaises(Hold): self.run_city('osaka', data, '2026-11-30')

    def test_correction_withdrawal_and_unknown_structure_hold(self):
        for city, text in [('osaka','訂正'), ('yokohama','撤回'), ('kobe','追補')]:
            data = self.setup_city(city); bridge, source, state, _ = data
            self.run_city(city, data, '2026-11-23'); before = (state/'state.json').read_bytes()
            self.save(bridge, source, city, text)
            result = self.run_city(city, data, '2026-11-30')
            self.assertFalse(result['state_advanced'])
            self.assertTrue((state/'cycles/2026-11-30/safety_hold.json').exists())
            self.assertEqual((state/'state.json').read_bytes(), before)

    def test_unknown_structure_and_corrupt_cas_keep_good_state(self):
        data = self.setup_city('kobe'); bridge, source, state, _ = data
        self.run_city('kobe', data, '2026-11-23'); before = (state/'state.json').read_bytes()
        self.save(bridge, source, 'kobe', 'revised')
        doc = bridge.index['documents'][source['url']]['versions'][-1]
        body = bridge.bodies[doc['sha256']].replace(b'tmp_contents', b'unknown_structure')
        sha = hashlib.sha256(body).hexdigest(); bridge.bodies[sha] = body
        doc['record'].update(sha256=sha, version_id=sha); doc['sha256'] = sha
        self.assertFalse(self.run_city('kobe', data, '2026-11-30')['state_advanced'])
        self.assertEqual((state/'state.json').read_bytes(), before)
        bridge.bodies[sha] = b'corrupt'
        with self.assertRaises(Hold): self.run_city('kobe', data, '2026-12-07')
        self.assertEqual((state/'state.json').read_bytes(), before)
        self.assertTrue((state/'cycles/2026-12-07/failure.json').exists())
        bridge.bodies[sha] = body
        with self.assertRaisesRegex(Hold, 'already attempted'):
            self.run_city('kobe', data, '2026-12-07')

    def test_empty_or_unreviewable_content_keeps_last_good(self):
        for city, content in [('osaka', ''), ('yokohama', '<h2>令和8年度</h2>'),
                              ('kobe', '<p>body without a heading</p>')]:
            data = self.setup_city(city); bridge, source, state, _ = data
            self.run_city(city, data, '2026-11-23'); before = (state/'state.json').read_bytes()
            body = ('<div id="'+source['selector'][1:]+'">'+content+'</div>').encode()
            sha = hashlib.sha256(body).hexdigest(); bridge.bodies[sha] = body
            doc = bridge.index['documents'][source['url']]['versions'][-1]
            doc['record'].update(sha256=sha, version_id=sha); doc['sha256'] = sha
            self.assertFalse(self.run_city(city, data, '2026-11-30')['state_advanced'])
            self.assertEqual((state/'state.json').read_bytes(), before)
            self.assertTrue((state/'cycles/2026-11-30/safety_hold.json').exists())
            with self.assertRaises(Hold): self.run_city(city, data, '2026-11-30')

    def test_non_html_mime_failure_consumes_week(self):
        data = self.setup_city('osaka'); bridge, source, state, _ = data
        self.run_city('osaka', data, '2026-11-23'); before = (state/'state.json').read_bytes()
        bridge.index['documents'][source['url']]['versions'][-1]['record']['mime_type'] = 'application/pdf'
        with self.assertRaises(Hold): self.run_city('osaka', data, '2026-11-30')
        bridge.index['documents'][source['url']]['versions'][-1]['record']['mime_type'] = 'text/html'
        with self.assertRaisesRegex(Hold, 'already attempted'): self.run_city('osaka', data, '2026-11-30')
        self.assertTrue((state/'cycles/2026-11-30/failure.json').exists())
        self.assertEqual((state/'state.json').read_bytes(), before)

    def test_osaka_later_section_change_is_preserved_and_deduplicated(self):
        data = self.setup_city('osaka'); bridge, source, state, _ = data
        self.run_city('osaka', data, '2026-11-23')
        body = b'<div id="mol_contents"><h2>Leading section</h2><p>unchanged intro</p><h2>Eligibility</h2><p>changed later section</p><ul><li>target condition</li></ul><table><tr><td>table footnote</td></tr></table></div>'
        sha = hashlib.sha256(body).hexdigest(); bridge.bodies[sha] = body
        doc = bridge.index['documents'][source['url']]['versions'][-1]
        doc['record'].update(sha256=sha, version_id=sha); doc['sha256'] = sha
        self.assertEqual(self.run_city('osaka', data, '2026-11-30')['new_review_count'], 1)
        queue = continuous.load(state/'cycles/2026-11-30/evidence_review_queue.json')
        later = [unit for unit in queue['source_units'] if unit['quote'] == 'changed later section']
        self.assertEqual(len(later), 1)
        self.assertEqual(later[0]['locator']['heading'], 'Eligibility')
        self.assertEqual(later[0]['sha256'], sha)
        self.assertTrue({'target condition', 'table footnote'} <= {unit['quote'] for unit in queue['source_units']})
        self.assertEqual(self.run_city('osaka', data, '2026-12-07')['new_review_count'], 0)

    def test_city_mixture_and_foreign_url_refused(self):
        data = self.setup_city('osaka'); bridge, source, state, _ = data
        bridge.index['documents'][source['url']]['versions'][0]['record']['city_code'] = 'kobe'
        with self.assertRaises(Hold): self.run_city('osaka', data, '2026-11-23')
        self.assertFalse((state/'state.json').exists())
        local, sources = adapter.prepare(self.config, 'osaka')
        sources = copy.deepcopy(sources); sources[0]['url'] = 'https://evil.example/x.html'
        local['cities']['osaka']['monitor_sources'] = sources
        with self.assertRaises(Hold): continuous.manifest(local, 'osaka', offline_sources=sources)

    def test_before_due_and_activation_are_rejected(self):
        data = self.setup_city('yokohama')
        with self.assertRaises(Hold):
            adapter.run(data[0], self.config, data[3], data[2], city='yokohama',
                now=datetime.fromisoformat('2026-11-23T08:59:00+09:00'), base_revision='fixture')
        local, sources = adapter.prepare(self.config, 'yokohama'); local['network_enabled'] = True
        with self.assertRaises(Hold): continuous.manifest(local, 'yokohama', offline_sources=sources)
        with patch.object(adapter, 'load', return_value={'enabled':False,'network_enabled':True}):
            with self.assertRaises(Hold): adapter.prepare(self.config, 'yokohama')

    def test_state_cannot_be_rebound_to_another_cas(self):
        data = self.setup_city('osaka'); bridge, _, state, _ = data
        self.run_city('osaka', data, '2026-11-23')
        before = (state/'state.json').read_bytes()
        other = self.root/'other-cas'; other.mkdir(); bridge.store.root = other
        with self.assertRaises(Hold): self.run_city('osaka', data, '2026-11-30')
        self.assertEqual((state/'state.json').read_bytes(), before)

    def test_fullwidth_year_is_equivalent_but_wrong_year_holds(self):
        data = self.setup_city('yokohama'); bridge, source, state, _ = data
        doc = bridge.index['documents'][source['url']]['versions'][-1]
        body = bridge.bodies[doc['sha256']]
        def replace_year(before, after):
            nonlocal body
            body = body.replace(before.encode(), after.encode())
            sha = hashlib.sha256(body).hexdigest(); bridge.bodies[sha] = body
            doc['record'].update(sha256=sha, version_id=sha); doc['sha256'] = sha
        replace_year('令和8年度', '令和８年度')
        self.assertTrue(self.run_city('yokohama', data, '2026-11-23')['state_advanced'])
        previous = (state/'state.json').read_bytes()
        replace_year('令和８年度', '令和７年度')
        self.assertFalse(self.run_city('yokohama', data, '2026-11-30')['state_advanced'])
        self.assertEqual((state/'state.json').read_bytes(), previous)


class SavedObservationClockTests(unittest.TestCase):
    setUp = OfflineWeeklyTests.setUp
    setup_city = OfflineWeeklyTests.setup_city
    save = OfflineWeeklyTests.save
    run_city = OfflineWeeklyTests.run_city

    def test_jst_calendar_days_and_invalid_dates(self):
        now = datetime.fromisoformat('2026-11-21T09:40:00+09:00')
        for stamp, expected in [('2026-11-15T04:45:58+00:00', 6),
                                ('2026-11-21T00:00:00+09:00', 0),
                                ('2026-11-20T15:00:00+00:00', 0),
                                ('2026-11-20T14:59:59+00:00', 1)]:
            with self.subTest(stamp=stamp):
                result = continuous.saved_observation_age(stamp, now)
                self.assertEqual(result['saved_observation_age_days'], expected)
                self.assertEqual(result['age_receipt_at'], stamp)
                self.assertEqual(result['age_evaluated_at'], now.isoformat())
        for stamp in (None, '', 'bad', '2026-11-15', '2026-11-15T09:00:00',
                      '2026-11-21T09:41:00+09:00'):
            with self.subTest(stamp=stamp), self.assertRaises(Hold):
                continuous.saved_observation_age(stamp, now)
        for invalid_now in (None, datetime(2026, 11, 21)):
            with self.assertRaises(Hold):
                continuous.saved_observation_age('2026-11-15T00:00:00Z', invalid_now)

    def test_real_adapter_report_uses_start_not_week_and_preserves_receipt(self):
        data = self.setup_city('kobe'); bridge, source, state, _ = data
        rec = bridge.index['documents'][source['url']]['versions'][-1]['record']
        rec['retrieved_at'] = '2026-11-15T04:45:58.963797+00:00'
        result = self.run_city('kobe', data, '2026-11-21')
        self.assertEqual(result['cycle_key'], '2026-11-16')
        self.assertTrue(result['state_advanced'])
        report = continuous.load(state/'cycles/2026-11-16/city_report.json')
        row = report['sources'][0]
        self.assertEqual(row['saved_observation_age_days'], 6)
        self.assertEqual(row['age_evaluated_at'], '2026-11-21T10:00:00+09:00')
        self.assertEqual(row['age_receipt_at'], rec['retrieved_at'])
        self.assertFalse(report['source_approval_inherited'])
        self.assertEqual(report['public_writes'], 0)
        with self.assertRaises(Hold):
            self.run_city('kobe', data, '2026-11-22')

    def test_invalid_receipt_preserves_last_good_and_consumes_week(self):
        data = self.setup_city('kobe'); bridge, source, state, _ = data
        self.run_city('kobe', data, '2026-11-23')
        before = (state/'state.json').read_bytes()
        self.save(bridge, source, 'kobe', 'new-document')
        rec = bridge.index['documents'][source['url']]['versions'][-1]['record']
        rec['retrieved_at'] = '2026-11-30T10:00:00'  # No timezone.
        with self.assertRaises(Hold):
            self.run_city('kobe', data, '2026-11-30')
        self.assertEqual((state/'state.json').read_bytes(), before)
        self.assertTrue((state/'cycles/2026-11-30/failure.json').exists())
        with self.assertRaises(Hold):
            self.run_city('kobe', data, '2026-11-30')


if __name__ == '__main__':
    unittest.main()
