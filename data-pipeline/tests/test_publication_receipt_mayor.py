"""Synthetic observations only: CLI -> real approval/receipt/private writer."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_mayor_updates import base, progress, run, approval

PIPELINE = Path(__file__).resolve().parents[1]


class PublicationReceiptCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'private'
        self.out.mkdir()
        packet, published = run([progress()])
        for name, value in dict(baseline=base(), packet=packet,
                                approval=approval(packet), published=published).items():
            (self.root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
        self.options = dict(baseline=str(self.root/'baseline.json'),
            packet=str(self.root/'packet.json'), approval=str(self.root/'approval.json'),
            published_data=str(self.root/'published.json'), commit='a'*40,
            deployed_url='https://example.test/observed.json',
            published_at='2026-11-21T10:00:00+09:00', output=str(self.out))

    def invoke(self, **overrides):
        options = self.options | overrides
        command = [sys.executable, '-B', '-m', 'mayor_updates', 'publication-receipt']
        for name, value in options.items():
            if value is not None:
                command += ['--'+name.replace('_', '-'), value]
        return subprocess.run(command, cwd=PIPELINE, capture_output=True, text=True,
                              encoding='utf-8', timeout=10)

    def reject(self, **overrides):
        result = self.invoke(**overrides)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.out/'publication_receipt_PRIVATE.json').exists())

    def test_real_cli_chain_and_exact_input_hashes(self):
        before = {p: p.read_bytes() for p in self.root.glob('*.json')}
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.out/'publication_receipt_PRIVATE.json').read_text())
        self.assertEqual(receipt['commit'], 'a'*40)
        self.assertEqual(receipt['published_at'], self.options['published_at'])
        for name, spec in receipt['observation_inputs'].items():
            self.assertEqual(spec['sha256'], hashlib.sha256(Path(self.options[name]).read_bytes()).hexdigest())
        self.assertIn('not independently verified', receipt['verification_scope'])
        self.assertEqual(before, {p:p.read_bytes() for p in before})
        self.assertEqual(len(list(self.out.iterdir())), 1)

    def test_approval_mismatch(self):
        p = self.root/'approval.json'; value=json.loads(p.read_text()); value['packet_id']='wrong'
        p.write_text(json.dumps(value)); self.reject()

    def test_baseline_mismatch(self):
        p=self.root/'baseline.json'; value=json.loads(p.read_text()); value['extra']='changed'
        p.write_text(json.dumps(value)); self.reject()

    def test_public_data_mismatch(self):
        (self.root/'published.json').write_text(json.dumps(base())); self.reject()

    def test_metadata_and_missing_inputs(self):
        cases=[{'commit':'abc'}, {'commit':None}, {'deployed_url':'https://'},
               {'deployed_url':'http://example.test'}, {'deployed_url':'https://u:p@example.test'},
               {'deployed_url':'https://example.test:bad'},
               {'published_at':'2026-11-21T10:00:00'}, {'published_at':'not-a-date'},
               {'published_at':None}, {'published_data':None}, {'approval':None},
               {'published_data':self.options['baseline']}]
        for case in cases:
            with self.subTest(case=case): self.reject(**case)

    def test_malformed_json(self):
        (self.root/'published.json').write_text('{'); self.reject()

    def test_duplicate_output_is_not_overwritten(self):
        p=self.out/'publication_receipt_PRIVATE.json'; p.write_text('existing receipt')
        result=self.invoke(); self.assertNotEqual(result.returncode,0)
        self.assertEqual(p.read_text(),'existing receipt')

    def test_actual_save_failure_is_not_success(self):
        output=self.root/'not-a-directory'; output.write_text('preserved')
        self.reject(output=str(output))
        self.assertEqual(output.read_text(),'preserved')


if __name__ == '__main__':
    unittest.main()
