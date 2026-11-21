"""Synthetic saved records; real audit reader, classifier and private writer."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import record_audit as audit


class RecordAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.records = self.base/'records'; self.records.mkdir()
        self.output = self.base/'output'; self.output.mkdir()
        self.schedule = self.base/'schedule.json'
        self.spec = dict(approved=True, paused=False, applicable=True,
                         approval_reference='synthetic approval for this cycle only',
                         cycle_key='2026-11-16', scheduled_at='2026-11-16T09:00:00+09:00',
                         deadline='2026-11-16T12:00:00+09:00', series_id='a'*64,
                         format='continuous', city='kobe', mode='offline',
                         identity={'city':'kobe', 'manifest_sha256':'a'*64})
        self.write(self.schedule, self.spec)
        self.now = '2026-11-16T12:00:00+09:00'

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def setup_records(self, periodic=False, result=True):
        if periodic:
            self.spec.update(format='periodic', city='kyoto', identity={
                'adapter':'kyoto-weekly-v1', 'mode':'offline', 'manifest_sha256':'a'*64,
                'snapshot_root':'synthetic-cas', 'schedule':'Monday 09:00 JST'})
            self.write(self.schedule, self.spec)
        name = 'periodic_identity.json' if periodic else 'loop_identity.json'
        self.write(self.records/name, self.spec['identity'])
        cycle = self.records/'cycles'/self.spec['cycle_key']
        intent = dict(self.spec['identity'], cycle_key=self.spec['cycle_key'], network_requests=0)
        if periodic: intent['scheduled_at'] = self.spec['scheduled_at']
        self.write(cycle/('reservation.json' if periodic else 'intent.json'), intent)
        if result:
            self.write(cycle/'cycle_result.json', dict(cycle_key=self.spec['cycle_key'], state='unchanged'))
        return cycle

    def inspect(self):
        return audit.inspect(self.schedule, self.records, self.now)

    def cli(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        return subprocess.run([sys.executable, '-B', '-m', 'mayor_updates.record_audit',
            '--schedule', str(self.schedule), '--records-root', str(self.records),
            '--evaluated-at', self.now, '--output', str(self.output)],
            env=env, capture_output=True, text=True, timeout=15)

    def test_cli_real_reader_and_save_preserves_inputs(self):
        self.setup_records()
        before = {p: p.read_bytes() for p in self.base.rglob('*.json')}
        run = self.cli(); self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads((self.output/'operation_record_audit_PRIVATE.json').read_text())
        self.assertEqual(report['classification'], 'result_recorded')
        self.assertEqual(report['last_good_commit'], 'not_verified')
        self.assertEqual(report['automatic_start'], 'not_verified')
        self.assertEqual(report['publication'], 'not_verified')
        self.assertEqual(len(report['evidence_sha256']), 4)
        self.assertTrue(all(p.read_bytes() == raw for p, raw in before.items()))

    def test_periodic_real_schema(self):
        self.setup_records(periodic=True)
        self.assertEqual(self.inspect()['classification'], 'result_recorded')

    def test_deadline_boundary_and_missing_not_os_failure(self):
        self.now = '2026-11-16T11:59:59+09:00'
        self.assertEqual(self.inspect()['classification'], 'before_deadline')
        self.now = '2026-11-16T12:00:00+09:00'
        result = self.inspect()
        self.assertEqual(result['classification'], 'missing_evidence')
        self.assertEqual(result['os_start'], 'unknown')

    def test_not_expected(self):
        for field, value in [('approved', False), ('paused', True), ('applicable', False)]:
            with self.subTest(field=field):
                spec = dict(self.spec); spec[field] = value
                self.write(self.schedule, spec)
                self.assertEqual(self.inspect()['classification'], 'not_expected')

    def test_reservation_and_empty_cycle_are_incomplete(self):
        cycle = self.setup_records(result=False)
        self.assertEqual(self.inspect()['classification'], 'incomplete_evidence')
        (cycle/'intent.json').unlink()
        self.assertEqual(self.inspect()['classification'], 'incomplete_evidence')

    def test_failure_overrides_result_and_hold(self):
        cycle = self.setup_records()
        self.write(cycle/'failure.json', {'reason':'synthetic commit failure'})
        self.assertEqual(self.inspect()['classification'], 'hold_or_failure')
        (cycle/'failure.json').unlink()
        self.write(cycle/'safety_hold.json', {'state':'stopped_no_public_change', 'holds':['synthetic']})
        self.assertEqual(self.inspect()['classification'], 'hold_or_failure')

    def test_other_week_is_not_target_evidence(self):
        cycle = self.setup_records()
        cycle.rename(cycle.with_name('2026-11-09'))
        self.assertEqual(self.inspect()['classification'], 'missing_evidence')

    def test_mismatched_identity_cycle_mode(self):
        cycle = self.setup_records()
        original = json.loads((cycle/'intent.json').read_text())
        for field, value in [('city','osaka'), ('manifest_sha256','b'*64),
                             ('cycle_key','2026-11-09'), ('mode','approved_acquisition')]:
            with self.subTest(field=field):
                self.write(cycle/'intent.json', dict(original, **{field:value}))
                self.assertEqual(self.inspect()['classification'], 'invalid_evidence')

    def test_corrupt_and_unreadable(self):
        cycle = self.setup_records()
        (cycle/'cycle_result.json').write_text('{broken', encoding='utf-8')
        self.assertEqual(self.inspect()['classification'], 'invalid_evidence')
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('synthetic denied')):
            self.assertEqual(self.inspect()['classification'], 'invalid_evidence')
        self.records = self.base/'missing-root'
        self.assertEqual(self.inspect()['classification'], 'invalid_evidence')

    def test_invalid_metadata_and_orphan_result(self):
        cycle = self.setup_records()
        (cycle/'intent.json').unlink()
        self.assertEqual(self.inspect()['classification'], 'invalid_evidence')
        self.spec['deadline'] = '2026-11-16T12:00:00'
        self.write(self.schedule, self.spec)
        self.assertEqual(self.inspect()['classification'], 'invalid_evidence')

    def test_output_collision_and_save_failure(self):
        self.assertEqual(self.cli().returncode, 0)
        saved = (self.output/'operation_record_audit_PRIVATE.json').read_bytes()
        self.assertNotEqual(self.cli().returncode, 0)
        self.assertEqual((self.output/'operation_record_audit_PRIVATE.json').read_bytes(), saved)
        self.output = self.base/'not-created'
        self.assertNotEqual(self.cli().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_cannot_write_into_input(self):
        self.output = self.records
        self.assertNotEqual(self.cli().returncode, 0)
        self.assertEqual(list(self.records.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
