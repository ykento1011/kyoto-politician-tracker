"""Synthetic Kyoto saved-input handoff tests; never access live producers."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kyoto_saved_adapter as adapter
import preflight


def save(path: Path, obj: object) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return raw


class KyotoSavedAdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.baseline_dir = self.root / "baseline"
        self.saved_dir = self.root / "saved"
        self.baseline_dir.mkdir()
        self.saved_dir.mkdir()
        self.baseline = self.baseline_dir / adapter.SAVED_NAME
        self.saved = self.saved_dir / adapter.SAVED_NAME
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        os.chmod(self.private, 0o700)
        self.row = {
            "id": "k-1", "meeting_id": "saved-meeting", "summary": "original",
            "source_url": "https://example.invalid/kyoto/k-1",
        }
        self.baseline_bytes = save(self.baseline, [self.row])
        self.saved_bytes = save(self.saved, [self.row])

    def assert_empty_private(self):
        self.assertEqual(list(self.private.iterdir()), [])

    def test_unchanged_saved_series_is_private_and_unverified(self):
        candidate, report, changes, saved_sha = adapter.prepare(
            self.baseline, self.saved, self.private
        )
        self.assertEqual(report["counts"], {"added": 0, "updated": 0, "deleted": 0})
        self.assertEqual(report["source_status"], "saved_unverified")
        self.assertEqual(report["source_authenticity"], "unverified")
        self.assertFalse(report["publish_permitted"])
        self.assertEqual(saved_sha, hashlib.sha256(self.saved_bytes).hexdigest())
        self.assertEqual(changes["unchanged_count"], 1)
        self.assertEqual(candidate.parent.parent, self.private)
        self.assertEqual(list(candidate.parent.iterdir()), [candidate])
        self.assertFalse((candidate.parent / "validated.json").exists())
        self.assertEqual(json.loads(candidate.read_text())["records"], [self.row])
        self.assertEqual(self.baseline.read_bytes(), self.baseline_bytes)
        self.assertEqual(self.saved.read_bytes(), self.saved_bytes)
        again, _, _, _ = adapter.prepare(self.baseline, self.saved, self.private)
        self.assertNotEqual(candidate, again)
        self.assertEqual(candidate.read_bytes(), (candidate.parent / "candidate.json").read_bytes())

    def test_changed_saved_requires_explicit_per_id_origin(self):
        edited = dict(self.row, summary="saved revision")
        save(self.saved, [edited])
        with self.assertRaises(preflight.Blocked):
            adapter.prepare(self.baseline, self.saved, self.private)
        self.assert_empty_private()

        declaration_file = self.root / "origin.json"
        save(declaration_file, {"k-1": "kyoto"})
        candidate, report, changes, _ = adapter.prepare(
            self.baseline, self.saved, self.private, declaration_file
        )
        self.assertEqual(report["counts"]["updated"], 1)
        self.assertEqual(changes["updated"][0]["changed_fields"], ["summary"])
        self.assertEqual(json.loads(candidate.read_text())["origin_city_by_id"], {"k-1": "kyoto"})
        self.assertEqual(report["source_authenticity"], "unverified")
        self.assertFalse(report["publish_permitted"])
        self.assertEqual(self.baseline.read_bytes(), self.baseline_bytes)

    def test_fail_closed_for_loss_cross_city_and_missing_origin(self):
        cases = [
            ([], None),
            ([{"id": "k-1", "source_url": "https://example.invalid/kyoto/k-1"}], None),
            ([dict(self.row, source_url="")], {"k-1": "kyoto"}),
            ([dict(self.row, city_code="osaka")], {"k-1": "kyoto"}),
            ([{"id": "k-1", "meeting_id": "saved-meeting", "summary": "original", "official_url": "https://example.invalid/osaka/k-1"}], None),
            ([dict(self.row, summary="edited")], {"k-1": "osaka"}),
            ([dict(self.row, summary="edited"), dict(self.row, summary="duplicate")], {"k-1": "kyoto"}),
        ]
        for i, (rows, origins) in enumerate(cases):
            with self.subTest(case=i):
                save(self.saved, rows)
                declaration = None
                if origins is not None:
                    declaration = self.root / "origins.json"
                    save(declaration, origins)
                with self.assertRaises(preflight.Blocked):
                    adapter.prepare(self.baseline, self.saved, self.private, declaration)
                self.assert_empty_private()
                self.assertEqual(self.baseline.read_bytes(), self.baseline_bytes)

    def test_stale_baseline_and_bad_roots_are_rejected(self):
        original_inspect = preflight.inspect

        def make_stale(city, baseline, candidate):
            save(baseline, [dict(self.row, summary="concurrent edit")])
            return original_inspect(city, baseline, candidate)

        with patch.object(preflight, "inspect", side_effect=make_stale):
            with self.assertRaises(preflight.Blocked):
                adapter.prepare(self.baseline, self.saved, self.private)
        self.assert_empty_private()
        with self.assertRaises(preflight.Blocked):
            adapter.prepare(self.baseline, self.saved, preflight.PROJECT_ROOT)
        wrong_name = self.saved_dir / "osaka_statements_summary.json"
        save(wrong_name, [self.row])
        with self.assertRaises(preflight.Blocked):
            adapter.prepare(self.baseline, wrong_name, self.private)
        self.assert_empty_private()

    def test_added_saved_row_with_declared_origin_is_review_only(self):
        new_row = dict(self.row, id="k-2", source_url="https://example.invalid/kyoto/k-2")
        save(self.saved, [self.row, new_row])
        declarations = self.root / "origins.json"
        save(declarations, {"k-2": "kyoto"})
        candidate, report, diff, _ = adapter.prepare(
            self.baseline, self.saved, self.private, declarations
        )
        self.assertEqual(report["counts"], {"added": 1, "updated": 0, "deleted": 0})
        self.assertEqual(diff["added"], ["k-2"])
        self.assertFalse(report["publish_permitted"])
        self.assertFalse((candidate.parent / "validated.json").exists())

    def test_interrupted_candidate_write_keeps_old_candidate(self):
        old, _, _, _ = adapter.prepare(self.baseline, self.saved, self.private)
        old_bytes = old.read_bytes()
        original_write = preflight._write_exclusive

        def fail_after_write(path, contents):
            original_write(path, contents)
            raise OSError("injected write interruption")

        with patch.object(preflight, "_write_exclusive", side_effect=fail_after_write):
            with self.assertRaises(OSError):
                adapter.prepare(self.baseline, self.saved, self.private)
        self.assertEqual(list(self.private.iterdir()), [old.parent])
        self.assertEqual(old.read_bytes(), old_bytes)

    def test_committed_saved_kyoto_array_handoff_read_only(self):
        # CI checkout holds the existing published snapshot; no new source is fetched.
        saved = preflight.PROJECT_ROOT / "frontend" / "public" / "data" / adapter.SAVED_NAME
        if not saved.is_file():
            self.skipTest("public snapshot not present in isolated local test checkout")
        old_bytes = saved.read_bytes()
        candidate, report, diff, saved_sha = adapter.prepare(
            saved, saved, self.private
        )
        self.assertGreater(report["baseline_count"], 0)
        self.assertEqual(report["counts"], {"added": 0, "updated": 0, "deleted": 0})
        self.assertEqual(diff["unchanged_count"], report["baseline_count"])
        self.assertEqual(saved_sha, hashlib.sha256(old_bytes).hexdigest())
        self.assertEqual(saved.read_bytes(), old_bytes)
        self.assertTrue(candidate.is_file())
        self.assertFalse(report["publish_permitted"])

    def test_bad_origin_declaration_and_invalid_json_are_rejected(self):
        origin_file = self.root / "origin.json"
        save(origin_file, ["k-1"])
        with self.assertRaises(preflight.Blocked):
            adapter.prepare(self.baseline, self.saved, self.private, origin_file)
        origin_file.write_text('{"k-1": NaN}', encoding="utf-8")
        with self.assertRaises(preflight.Blocked):
            adapter.prepare(self.baseline, self.saved, self.private, origin_file)
        self.assert_empty_private()


if __name__ == "__main__":
    unittest.main()
