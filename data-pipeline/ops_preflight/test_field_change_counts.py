"""Offline five-city field-count diagnosis and bulk stage-stop regression."""

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import preflight


def write(path, data):
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return raw


class FieldChangeCountTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.baselines = self.root / "snapshots"
        self.baselines.mkdir()
        self.private = self.root / "private_stage"
        self.private.mkdir(mode=0o700)
        os.chmod(self.private, 0o700)

    @staticmethod
    def rows(city):
        source_name = "source_url" if city == "kyoto" else "official_url"
        return [
            {
                "id": "private-fixture-1",
                "meeting_id": "offline-meeting",
                "summary": "synthetic-private-first",
                source_name: f"https://example.invalid/{city}/first",
            },
            {
                "id": "private-fixture-2",
                "meeting_id": "offline-meeting",
                "summary": "synthetic-private-second",
                source_name: f"https://example.invalid/{city}/second",
            },
        ]

    def fixture(self, city, before, after, origins):
        baseline = self.baselines / f"{city}_{preflight.FEATURE}.json"
        old_raw = write(baseline, before)
        candidate = self.root / f"{city}-candidate.json"
        write(candidate, {
            "schema_version": 1,
            "city_code": city,
            "feature": preflight.FEATURE,
            "source_status": "synthetic",
            "baseline_sha256": hashlib.sha256(old_raw).hexdigest(),
            "records": after,
            "origin_city_by_id": origins,
        })
        return baseline, candidate, old_raw

    def test_five_city_ordinary_change_is_field_counted_and_stageable(self):
        expected = {
            "new_metadata": {"field_added": 1, "field_removed": 0, "value_changed": 0},
            "summary": {"field_added": 0, "field_removed": 0, "value_changed": 1},
        }
        for city in sorted(preflight.CITIES):
            with self.subTest(city=city):
                old = self.rows(city)
                after = [dict(old[0], summary="synthetic-new-value", new_metadata=None), old[1]]
                baseline, candidate, original = self.fixture(
                    city, old, after, {"private-fixture-1": city}
                )
                report, raw, diff = preflight.inspect(city, baseline, candidate)
                self.assertEqual(report["field_change_counts"], expected)
                self.assertEqual(diff["field_change_counts"], expected)
                self.assertEqual(diff["updated"][0]["changed_fields"], ["new_metadata", "summary"])
                self.assertEqual(report["counts"], {"added": 0, "updated": 1, "deleted": 0})
                self.assertFalse(report["all_existing_rows_changed"])
                self.assertTrue(report["stage_permitted"])
                self.assertFalse(report["publish_permitted"])
                stage_id = preflight.stage(self.private, report, raw, diff)
                manifest = json.loads((self.private / stage_id / "manifest.json").read_text())
                self.assertEqual(manifest["field_change_counts"], expected)
                self.assertEqual(baseline.read_bytes(), original)
                self.assertNotIn("private-fixture-1", json.dumps(report))
                self.assertNotIn("synthetic-new-value", json.dumps(report))

    def test_all_existing_rows_changed_forces_pm_review_and_stage_stop(self):
        for city in sorted(preflight.CITIES):
            with self.subTest(city=city):
                old = self.rows(city)
                after = [dict(x, summary="synthetic-bulk-changed") for x in old]
                baseline, candidate, raw = self.fixture(
                    city, old, after, {x["id"]: city for x in old}
                )
                before_dirs = set(self.private.iterdir())
                report, candidate_raw, diff = preflight.inspect(city, baseline, candidate)
                self.assertTrue(report["all_existing_rows_changed"])
                self.assertFalse(report["stage_permitted"])
                self.assertEqual(report["review_state"], "bulk_change_requires_pm_review")
                self.assertEqual(report["counts"]["updated"], 2)
                self.assertEqual(report["field_change_counts"]["summary"]["value_changed"], 2)
                with self.assertRaisesRegex(preflight.Blocked, "Stage refused"):
                    preflight.stage(self.private, report, candidate_raw, diff)
                self.assertEqual(set(self.private.iterdir()), before_dirs)
                self.assertEqual(baseline.read_bytes(), raw)

    def test_missing_origin_emits_field_counts_but_never_ids_or_values(self):
        city = "kyoto"
        old = self.rows(city)
        after = [dict(x, summary="secret-private-statement") for x in old]
        baseline, candidate, _ = self.fixture(city, old, after, {})
        with self.assertRaises(preflight.Blocked) as exc:
            preflight.inspect(city, baseline, candidate)
        self.assertEqual(exc.exception.diagnostics["counts"]["updated"], 2)
        self.assertTrue(exc.exception.diagnostics["all_existing_rows_changed"])
        self.assertEqual(
            exc.exception.diagnostics["field_change_counts"]["summary"]["value_changed"], 2
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = preflight.main([
                "stage", "--city", city, "--baseline", str(baseline),
                "--candidate", str(candidate), "--private-root", str(self.private),
            ])
        self.assertEqual(exit_code, 2)
        output = stderr.getvalue()
        self.assertEqual(json.loads(output)["diagnostics"]["counts"]["updated"], 2)
        self.assertNotIn("private-fixture-", output)
        self.assertNotIn("secret-private-statement", output)
        self.assertEqual(list(self.private.iterdir()), [])

    def test_field_removal_is_explicitly_counted_but_still_blocked(self):
        old = self.rows("kobe")
        after = [dict(old[0]), old[1]]
        del after[0]["summary"]
        baseline, candidate, raw = self.fixture(
            "kobe", old, after, {"private-fixture-1": "kobe"}
        )
        with self.assertRaisesRegex(preflight.Blocked, "drops existing fields") as exc:
            preflight.inspect("kobe", baseline, candidate)
        self.assertEqual(
            exc.exception.diagnostics["field_change_counts"]["summary"]["field_removed"], 1
        )
        self.assertEqual(list(self.private.iterdir()), [])
        self.assertEqual(baseline.read_bytes(), raw)

    def test_true_to_one_and_absent_to_null_are_real_changes(self):
        old = self.rows("osaka")
        old[0]["score"] = True
        after = [dict(old[0], score=1, new_annotation=None), old[1]]
        baseline, candidate, _ = self.fixture(
            "osaka", old, after, {"private-fixture-1": "osaka"}
        )
        report, _, diff = preflight.inspect("osaka", baseline, candidate)
        self.assertEqual(diff["updated"][0]["changed_fields"], ["new_annotation", "score"])
        self.assertEqual(report["field_change_counts"]["score"]["value_changed"], 1)
        self.assertEqual(report["field_change_counts"]["new_annotation"]["field_added"], 1)

    def test_key_order_only_is_not_a_change(self):
        old = self.rows("nagoya")
        old[0]["meta"] = {"alpha": 1, "beta": 2}
        after = [dict(old[0], meta={"beta": 2, "alpha": 1}), dict(old[1])]
        baseline, candidate, _ = self.fixture("nagoya", old, after, {})
        report, _, diff = preflight.inspect("nagoya", baseline, candidate)
        self.assertEqual(report["counts"], {"added": 0, "updated": 0, "deleted": 0})
        self.assertEqual(report["field_change_counts"], {})
        self.assertEqual(diff["updated"], [])
        self.assertTrue(report["stage_permitted"])


if __name__ == "__main__":
    unittest.main()
