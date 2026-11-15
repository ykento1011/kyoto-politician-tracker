import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'data-pipeline'))
from mayor_updates.projection import budget_total, included, format_record_amount

class KobeM01Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'frontend/public/data/kobe_mayor_tracker.json').read_text(encoding='utf-8'))
        self.policy = next(p for p in self.data['pledges'] if p['id'] == 'KOBE-M01')

    def test_unconfirmed_registration_is_preserved_and_excluded(self):
        r = self.policy['budget_records'][0]
        self.assertEqual(r['amount_display'], '14億2,000万円')
        self.assertEqual(r['policy_relation'], 'unconfirmed')
        self.assertEqual(r['evidence_status'], 'unverified')
        self.assertEqual(r['funding_verification_status'], 'unverified')
        self.assertFalse(included(r))
        self.assertEqual(budget_total([self.policy]), 0)
        self.assertEqual(r['doc_url'], 'https://www.city.kobe.lg.jp/documents/48584/2026yosannogaiyou.pdf')
        self.assertEqual([x['amount'] for x in r['funding_sources']], ['8億5,000万円', '5億7,000万円'])
        self.assertEqual(self.policy['stage_level'], 4)
        self.assertIn('原典未確認', r['budget_note'])
        self.assertIn('対応も未照合', r['budget_note'])

    def test_camera_source_is_separate_exact_proposal_and_excluded(self):
        self.assertEqual(len(self.policy['budget_records']), 2)
        r = self.policy['budget_records'][1]
        self.assertEqual(r['amount_jpy'], 621021000)
        self.assertEqual(r['amount_display'], format_record_amount(r))
        self.assertEqual(r['amount_display'], '6億2,102万1,000円')
        self.assertEqual(r['policy_relation'], 'direct')
        self.assertEqual(r['evidence_status'], 'source_checked')
        self.assertEqual(r['budget_status'], 'proposal')
        self.assertEqual(r['fiscal_year'], '令和8年度当初予算（案）')
        self.assertIn('印刷p.22／PDF22ページ', r['doc_source'])
        self.assertTrue(r['doc_url'].endswith('/2026yosannannnopoint.pdf'))
        self.assertIn('重複可能性が未確認', r['budget_note'])
        self.assertFalse(r.get('funding_sources'))
        self.assertFalse(included(r))
        self.assertEqual(budget_total([self.policy]), 0)

    def test_kpi_is_a_record_count_not_an_unverified_budget_sum(self):
        kpi = next(k for k in self.data['kpis'] if k['label'] == '掲載答弁記録')
        self.assertEqual(kpi['value'], str(sum(len(p.get('debate_statements', [])) for p in self.data['pledges'])) + '件')
        self.assertFalse(any(k['label'] == '関連予算総額' for k in self.data['kpis']))

    def test_generator_preserves_reviewed_budget_and_source_in_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pipeline = root / 'data-pipeline'; pipeline.mkdir()
            shutil.copyfile(ROOT / 'data-pipeline/build_kobe_mayor_tracker.py', pipeline / 'build_kobe_mayor_tracker.py')
            package = pipeline / 'mayor_updates'; package.mkdir()
            for name in ['__init__.py', 'projection.py']:
                shutil.copyfile(ROOT / 'data-pipeline/mayor_updates' / name, package / name)
            data_dir = root / 'frontend/public/data'; data_dir.mkdir(parents=True)
            target = data_dir / 'kobe_mayor_tracker.json'
            target.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')
            subprocess.run([sys.executable, '-B', str(pipeline / 'build_kobe_mayor_tracker.py')], check=True, capture_output=True, encoding='utf-8')
            generated = json.loads(target.read_text(encoding='utf-8'))
            policy = next(p for p in generated['pledges'] if p['id'] == 'KOBE-M01')
            self.assertEqual(policy['budget_records'], self.policy['budget_records'])
            self.assertEqual(policy['stage_level'], self.policy['stage_level'])
            kpi = next(k for k in generated['kpis'] if k['label'] == '掲載答弁記録')
            self.assertEqual(kpi['value'], '0件')
            self.assertFalse(included(policy['budget_records'][0]))
            target.unlink()
            subprocess.run([sys.executable, '-B', str(pipeline / 'build_kobe_mayor_tracker.py')], check=True, capture_output=True, encoding='utf-8')
            fresh = next(p for p in json.loads(target.read_text(encoding='utf-8'))['pledges'] if p['id'] == 'KOBE-M01')
            self.assertEqual(fresh['budget_records'][1], self.policy['budget_records'][1])
            self.assertEqual(budget_total([fresh]), 0)

if __name__ == '__main__': unittest.main()
