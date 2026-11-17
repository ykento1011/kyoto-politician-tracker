"""Synthetic weekly acquisition with real registered URLs, sockets blocked."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_continuous_mayor as fixtures
from mayor_updates import periodic
from mayor_updates.projection import Hold
from types import SimpleNamespace


class LocalConnectivityTests(unittest.TestCase):
    def test_cached_profiles_only_and_fail_closed(self):
        for output, expected in [('["Internet","NoTraffic"]','online'),
                ('["LocalNetwork","NoTraffic"]','offline'), ('[]','unknown'),
                ('null','unknown'), ('["unexpected"]','unknown'), ('broken','unknown')]:
            with patch.object(periodic.os,'name','nt'), \
                 patch.object(periodic.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)) as proc:
                self.assertEqual(periodic.local_connectivity(), expected)
                command = proc.call_args.args[0]
                self.assertIn('Get-NetConnectionProfile', command[-1])
                self.assertNotIn('http', command[-1].lower())
                self.assertNotIn('Test-Connection', command[-1])
                self.assertNotIn('Resolve-DnsName', command[-1])
                self.assertEqual(proc.call_args.kwargs['timeout'], 5)
        for failure in (OSError('missing shell'), periodic.subprocess.TimeoutExpired('fixture',5)):
            with patch.object(periodic.os,'name','nt'), patch.object(periodic.subprocess,'run',side_effect=failure):
                self.assertEqual(periodic.local_connectivity(), 'unknown')
        with patch.object(periodic.os,'name','nt'), \
             patch.object(periodic.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='[]')):
            self.assertEqual(periodic.local_connectivity(), 'unknown')


class PeriodicTests(unittest.TestCase):
    def setUp(self):
        fixtures.ContinuousTests.setUp(self)
        self.bridge.store.read_index = lambda: copy.deepcopy(self.bridge.index)
        p = patch.object(periodic, 'local_connectivity', return_value='online')
        self.connection = p.start(); self.addCleanup(p.stop)

    def test_offline_unknown_then_online_and_overlapping_triggers(self):
        calls = []
        def capture(*_):
            calls.append(1)
            return {'stopped':False, 'new_get_requests':3}
        before = copy.deepcopy(self.bridge.index)
        for status in ('offline', 'unknown'):
            self.connection.return_value = status
            result = self.cycle('2026-11-23', callback=capture)
            self.assertEqual(result['state'], 'waiting_for_network')
            self.assertEqual(result['new_get_requests'], 0)
            self.assertFalse((self.state/'cycles').exists())
            self.assertFalse((self.state/'state.json').exists())
            self.assertEqual(self.bridge.index, before)
        self.connection.return_value = 'online'
        result = self.cycle('2026-11-23', callback=capture, hour=11)
        self.assertTrue(result['state_advanced'])
        with self.assertRaises(Hold): self.cycle('2026-11-23', callback=capture, hour=12)
        self.assertEqual(len(calls), 1)

    def test_sleep_next_week_does_not_backfill_and_disconnect_is_terminal(self):
        self.connection.return_value = 'offline'
        self.cycle('2026-11-23', callback=lambda *_: self.fail('offline GET'))
        self.connection.return_value = 'online'
        def disconnect(*_):
            self.connection.return_value = 'offline'
            return {'stopped':True, 'new_get_requests':1}
        result = self.cycle('2026-12-01', callback=disconnect)
        self.assertFalse(result['state_advanced'])
        self.assertFalse((self.state/'cycles/2026-11-23').exists())
        self.assertTrue((self.state/'cycles/2026-11-30/reservation.json').exists())
        self.connection.return_value = 'online'
        with self.assertRaises(Hold): self.cycle('2026-12-02', callback=lambda *_: self.fail('retry'))

    def test_waiting_keeps_previous_good_pointer_and_lock_blocks_second_trigger(self):
        capture = lambda *_: {'stopped':False, 'new_get_requests':3}
        self.cycle('2026-11-23', callback=capture)
        before = (self.state/'state.json').read_bytes()
        self.connection.return_value = 'offline'
        self.cycle('2026-11-30', callback=capture)
        self.assertEqual((self.state/'state.json').read_bytes(), before)
        with periodic.weekly.single_run(self.state):
            with self.assertRaises(Hold): self.cycle('2026-11-30', callback=capture)

    def test_acquisition_refreshes_cached_index_from_separate_store(self):
        self.cycle('2026-11-23', callback=lambda *_: {'stopped':False,'new_get_requests':3})
        stale = copy.deepcopy(self.bridge.index)
        self.bridge.save(self.sources[2], 'worker-saved-new-version')
        fresh = copy.deepcopy(self.bridge.index)
        self.bridge.index = stale
        self.bridge.store.read_index = lambda: copy.deepcopy(fresh)
        changed = self.cycle('2026-11-30', callback=lambda *_: {'stopped':False,'new_get_requests':3})
        self.assertEqual(changed['new_review_count'], 1)
        pointer = json.loads((self.state/'state.json').read_text(encoding='utf-8'))
        self.assertEqual(pointer['monitor']['documents'][self.sources[2]['url']]['sha256'],
                         fresh['documents'][self.sources[2]['url']]['versions'][-1]['sha256'])

    def test_new_directories_are_private_under_standard_umask(self):
        previous = os.umask(0o022)
        try:
            self.cycle('2026-11-23', callback=lambda *_: {'stopped':False,'new_get_requests':3})
        finally:
            os.umask(previous)
        for path in (self.state/'cycles', self.state/'outbox', self.state/'cycles/2026-11-23',
                     self.state/'cycles/2026-11-23/acquisition'):
            if os.name == 'posix':
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            else:
                self.assertTrue(path.is_dir())  # Real Windows ACL requires private integration.

    def cycle(self, day, *, callback=None, hour=9):
        return periodic.execute(self.bridge, self.config, self.baseline, [], self.state,
            now=datetime.fromisoformat(day+f'T{hour:02d}:00:00+09:00'),
            base_revision='synthetic', acquisition=callback,
            mode='approved_acquisition' if callback else 'offline')

    def test_first_unchanged_replacement_failure_recovery_and_hold(self):
        baseline = copy.deepcopy(self.baseline)
        def capture(sources, output):
            self.assertEqual(sources, self.sources)
            self.assertTrue((output.parent/'reservation.json').exists())
            return {'stopped':False, 'new_get_requests':3, 'receipts':[]}
        self.assertTrue(self.cycle('2026-11-23', callback=capture)['state_advanced'])
        self.assertEqual(self.cycle('2026-11-30', callback=capture)['new_review_count'], 0)
        self.bridge.save(self.sources[0], 'new-budget-document')
        self.bridge.save(self.sources[2], 'new-progress-announcement')
        changed = self.cycle('2026-12-07', callback=capture)
        self.assertEqual(changed['new_review_count'], 2)
        notice = json.loads((self.state/'outbox/2026-12-07.json').read_text(encoding='utf-8'))
        self.assertEqual(notice['kind'], 'review_pending')
        self.assertFalse(notice['publication_authorized'])
        self.assertEqual(notice['observations'][2]['policy_ids'], ['P-03'])
        self.assertTrue(notice['observations'][2]['sha256'])
        before = (self.state/'state.json').read_bytes()
        failed = self.cycle('2026-12-14', callback=lambda *_: {'stopped':True, 'new_get_requests':1})
        self.assertFalse(failed['state_advanced'])
        self.assertEqual((self.state/'state.json').read_bytes(), before)
        self.assertEqual(json.loads((self.state/'outbox/2026-12-14.json').read_text())['kind'], 'failure')
        self.assertEqual(self.cycle('2026-12-21', callback=capture)['new_review_count'], 0)
        key = next(iter(json.loads((self.state/'state.json').read_text())['seen_reviews']))
        periodic.continuous.review_decision(self.state, key, 'hold', 'TEST', 'Policy relationship unconfirmed')
        self.assertEqual(self.baseline, baseline)

    def test_duplicate_week_does_not_invoke_capture(self):
        calls = []
        def capture(*_):
            calls.append(1)
            return {'stopped':False, 'new_get_requests':3}
        self.cycle('2026-11-23', callback=capture)
        with self.assertRaises(Hold): self.cycle('2026-11-25', callback=capture)
        self.assertEqual(len(calls), 1)

    def test_sleep_delay_same_cycle_no_backfill_and_no_early_run(self):
        with self.assertRaises(Hold): self.cycle('2026-11-23', hour=8)
        result = self.cycle('2026-11-23', hour=11)
        self.assertEqual(result['delay_seconds'], 7200)
        self.assertFalse(result['started_after_noon'])
        late = periodic.period(datetime.fromisoformat('2026-11-24T09:00:00+09:00'))
        self.assertEqual(late['cycle_key'], '2026-11-23')
        self.assertTrue(late['started_after_noon'])
        with self.assertRaises(Hold): periodic.period(datetime(2026,11,23))

    def test_notification_failure_retains_good_state_and_reservation(self):
        self.cycle('2026-11-23')
        before = (self.state/'state.json').read_bytes()
        self.bridge.save(self.sources[2], 'changed')
        with patch.object(periodic, 'notify', side_effect=OSError('outbox unavailable')):
            with self.assertRaises(OSError): self.cycle('2026-11-30')
        self.assertEqual((self.state/'state.json').read_bytes(), before)
        self.assertTrue((self.state/'cycles/2026-11-30/outbox_failure.json').exists())
        with self.assertRaises(Hold): self.cycle('2026-11-30')

    def test_acquisition_exception_has_failure_notice_no_state_advance(self):
        with self.assertRaises(TimeoutError):
            self.cycle('2026-11-23', callback=lambda *_: (_ for _ in ()).throw(TimeoutError('child wall limit')))
        self.assertFalse((self.state/'state.json').exists())
        self.assertTrue((self.state/'outbox/2026-11-23.json').exists())
        with self.assertRaises(Hold): self.cycle('2026-11-23')

    def test_existing_state_and_changed_manifest_refused(self):
        path = self.state/'state.json'; path.write_text('{"protected":true}')
        with self.assertRaises(Hold): self.cycle('2026-11-23')
        self.assertEqual(path.read_text(), '{"protected":true}')
        self.config['cities']['kyoto']['monitor_sources'][0]['url'] = 'https://example.org/'
        with self.assertRaises(Hold): self.cycle('2026-11-23')
        self.assertFalse((self.state/'cycles').exists())

    def test_live_and_offline_state_cannot_mix(self):
        self.cycle('2026-11-23')
        with self.assertRaises(Hold):
            self.cycle('2026-11-30', callback=lambda *_: self.fail('must not capture'))

    def test_acl_failure_is_before_reservation_and_capture(self):
        with patch.object(periodic.weekly, 'assert_owner_only', side_effect=Hold('ACL mismatch')):
            with self.assertRaises(Hold):
                self.cycle('2026-11-23', callback=lambda *_: self.fail('must not capture'))
        self.assertEqual(list(self.state.iterdir()), [])

    def test_p1_pin_failure_is_before_reservation(self):
        runtime = dict(city='kyoto', periodic_enabled=True,
            code_files=[{'path':periodic.__file__}, {'path':periodic.continuous.__file__}],
            p1_code_root='fixture', snapshot_root='fixture')
        with patch.object(periodic.continuous,'configure_shell'), \
             patch.object(periodic.weekly,'validate_runtime',return_value=(self.state, {}, self.config)), \
             patch.object(periodic.weekly,'P1Bridge',side_effect=Hold('P1 PIN mismatch')):
            with self.assertRaises(Hold): periodic.run(runtime, acquire=True)
        self.assertEqual(list(self.state.iterdir()), [])

    def test_default_runtime_does_not_acquire_and_requires_activation(self):
        runtime = dict(city='kyoto', code_files=[{'path':periodic.__file__},
            {'path':periodic.continuous.__file__}], p1_code_root='fixture',
            snapshot_root='fixture', base_revision='fixture')
        paths = {'baseline':'baseline','rules':'rules'}
        real_load = periodic.load
        with patch.object(periodic.continuous,'configure_shell'), \
             patch.object(periodic.weekly,'validate_runtime',return_value=(self.state, paths, self.config)), \
             patch.object(periodic.weekly,'P1Bridge',return_value=self.bridge), \
             patch.object(periodic,'load',side_effect=lambda p: self.baseline if p=='baseline' else [] if p=='rules' else real_load(p)), \
             patch.object(periodic.weekly,'capture_sources',side_effect=AssertionError('HTTP forbidden')):
            result = periodic.run(runtime, now=datetime.fromisoformat('2026-11-23T09:00:00+09:00'))
            self.assertEqual(result['new_get_requests'], 0)
            with self.assertRaises(Hold): periodic.run(runtime, acquire=True)


if __name__ == '__main__': unittest.main()
