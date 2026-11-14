"""Offline synthetic tests; never imports, starts, or patches legacy update code."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import preflight


def save(path: Path, data: object) -> bytes:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    return raw


class FiveCityOfflinePreflightTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.baselines = self.root / "public_snapshots"
        self.baselines.mkdir()
        self.private = self.root / "private_stage"
        self.private.mkdir(mode=0o700)
        os.chmod(self.private, 0o700)

    @staticmethod
    def row(record_id: str, city: str, summary: str = "original") -> dict:
        return {
            "id": record_id,
            "meeting_id": f"meeting-{city}",
            "meeting_date": "2026-10-01",
            "speaker": "Test Speaker",
            "summary": summary,
            "source_url": f"https://example.invalid/{city}/{record_id}",
        }

    def fixture(self, city: str, *, case: str = "update") -> tuple[Path, Path, bytes]:
        baseline = self.baselines / f"{city}_statements_summary.json"
        old_bytes = save(baseline, [self.row("r1", city)])
        new_records = [self.row("r1", city, "corrected")]
        origins = {"r1": city}
        if case == "unchanged":
            new_records = [self.row("r1", city)]
            origins = {}
        if case == "delete":
            new_records = []
            origins = {}
        if case == "broken":
            new_records = "not-a-list"
            origins = {}
        if case == "wrong-city":
            origins = {"r1": "osaka" if city != "osaka" else "kyoto"}
        if case == "missing-source":
            del new_records[0]["source_url"]
        envelope = {
            "schema_version": 1,
            "city_code": city,
            "feature": preflight.FEATURE,
            "source_status": "synthetic",
            "baseline_sha256": hashlib.sha256(old_bytes).hexdigest(),
            "records": new_records,
            "origin_city_by_id": origins,
        }
        candidate = self.root / f"{city}-{case}.json"
        save(candidate, envelope)
        return baseline, candidate, old_bytes

    def test_five_cities_update_stage_and_unchanged_inspect(self):
        for city in sorted(preflight.CITIES):
            with self.subTest(city=city):
                baseline, candidate, raw = self.fixture(city)
                report, source_raw, changes = preflight.inspect(city, baseline, candidate)
                self.assertEqual(report["counts"], {"added": 0, "updated": 1, "deleted": 0})
                self.assertFalse(report["publish_permitted"])
                self.assertEqual(changes["updated"][0]["changed_fields"], ["summary"])
                stage_id = preflight.stage(self.private, report, source_raw, changes)
                stage_dir = self.private / stage_id
                marker = json.loads((stage_dir / "validated.json").read_text())
                self.assertEqual(marker["state"], "machine_validated_pending_pm_review")
                self.assertEqual((stage_dir / "candidate.json").read_bytes(), source_raw)
                self.assertEqual(baseline.read_bytes(), raw)

                b2, c2, _ = self.fixture(city, case="unchanged")
                before = set(self.private.iterdir())
                nochange, _, diff = preflight.inspect(city, b2, c2)
                self.assertEqual(nochange["counts"], {"added": 0, "updated": 0, "deleted": 0})
                self.assertEqual(diff["unchanged_count"], 1)
                self.assertEqual(set(self.private.iterdir()), before)

    def test_five_cities_fail_closed_delete_corrupt_and_cross_city(self):
        for city in sorted(preflight.CITIES):
            for case in ("delete", "broken", "wrong-city", "missing-source"):
                with self.subTest(city=city, case=case):
                    baseline, candidate, raw = self.fixture(city, case=case)
                    before = set(self.private.iterdir())
                    with self.assertRaises(preflight.Blocked):
                        report, data, diff = preflight.inspect(city, baseline, candidate)
                        preflight.stage(self.private, report, data, diff)
                    self.assertEqual(baseline.read_bytes(), raw)
                    self.assertEqual(set(self.private.iterdir()), before)

    def test_stale_revision_duplicate_id_and_wrong_envelope_city_rejected(self):
        baseline, candidate, raw = self.fixture("kyoto")
        obj = json.loads(candidate.read_text())
        for case in ("sha", "duplicate", "city"):
            with self.subTest(case=case):
                local = json.loads(json.dumps(obj))
                if case == "sha":
                    local["baseline_sha256"] = "0" * 64
                elif case == "duplicate":
                    local["records"].append(local["records"][0])
                else:
                    local["city_code"] = "osaka"
                save(candidate, local)
                with self.assertRaises(preflight.Blocked):
                    preflight.inspect("kyoto", baseline, candidate)
                self.assertEqual(baseline.read_bytes(), raw)

    def test_partial_stage_has_no_validated_marker_and_previous_stage_survives(self):
        baseline, candidate, raw = self.fixture("kobe")
        report, data, changes = preflight.inspect("kobe", baseline, candidate)
        previous_id = preflight.stage(self.private, report, data, changes)
        previous = self.private / previous_id
        previous_files = {p.name: p.read_bytes() for p in previous.iterdir()}
        original_write = preflight._write_exclusive

        def injected_failure(path, contents):
            if path.name == "diff.json":
                raise OSError("synthetic disk error")
            return original_write(path, contents)

        with patch.object(preflight, "_write_exclusive", side_effect=injected_failure):
            with self.assertRaises(OSError):
                preflight.stage(self.private, report, data, changes)
        self.assertEqual(baseline.read_bytes(), raw)
        self.assertEqual({p.name: p.read_bytes() for p in previous.iterdir()}, previous_files)
        partials = [p for p in self.private.iterdir() if p.name != previous_id]
        self.assertEqual(len(partials), 1)
        self.assertFalse((partials[0] / "validated.json").exists())

    def test_private_root_rejects_repository_and_symlink(self):
        with self.assertRaises(preflight.Blocked):
            preflight._check_private_root(preflight.PROJECT_ROOT)
        if hasattr(os, "symlink"):
            link = self.root / "link"
            try:
                link.symlink_to(self.private, target_is_directory=True)
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(preflight.Blocked):
                preflight._check_private_root(link)

    def test_rejects_nonstandard_json_constants(self):
        baseline, candidate, raw = self.fixture("kyoto")
        original = candidate.read_text(encoding="utf-8")
        self.assertIn('"summary":"corrected"', original)
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                candidate.write_text(
                    original.replace('"summary":"corrected"', f'"summary":{constant}', 1),
                    encoding="utf-8",
                )
                with self.assertRaises(preflight.Blocked):
                    preflight.inspect("kyoto", baseline, candidate)
                self.assertEqual(baseline.read_bytes(), raw)

    def test_marker_fsync_failure_never_finalizes_validated_marker(self):
        baseline, candidate, raw = self.fixture("kyoto")
        report, data, changes = preflight.inspect("kyoto", baseline, candidate)
        original_fsync = os.fsync
        calls = 0

        def fail_on_fourth_fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 4:  # candidate, diff, manifest, pending marker
                raise OSError("simulated validated-marker fsync failure")
            return original_fsync(fd)

        with patch.object(preflight.os, "fsync", side_effect=fail_on_fourth_fsync):
            with self.assertRaises(OSError):
                preflight.stage(self.private, report, data, changes)
        self.assertEqual(calls, 4)
        self.assertEqual(baseline.read_bytes(), raw)
        partials = list(self.private.iterdir())
        self.assertEqual(len(partials), 1)
        self.assertFalse((partials[0] / "validated.json").exists())

    def test_saved_public_five_city_contract_offline_read_only(self):
        # This reads one committed statements-summary JSON per city. It does
        # not fetch sources, import producers, overwrite JSON, or stage output.
        public = preflight.PROJECT_ROOT / "frontend" / "public" / "data"
        for city in sorted(preflight.CITIES):
            with self.subTest(city=city):
                baseline = public / f"{city}_{preflight.FEATURE}.json"
                source_records, raw = preflight._read_json(baseline)
                self.assertGreater(len(raw), 0)
                self.assertLessEqual(len(raw), preflight.MAX_FILE_BYTES)
                index = preflight._index_records(source_records, strict_source=True)
                self.assertGreater(len(index), 0)
                self.assertEqual(len(index), len(source_records))
                expected_origin_key = "source_url" if city == "kyoto" else "official_url"
                self.assertTrue(
                    all(expected_origin_key in row for row in source_records),
                    f"{city}: absent saved origin URL key",
                )
                envelope = {
                    "schema_version": 1,
                    "city_code": city,
                    "feature": preflight.FEATURE,
                    "source_status": "saved_unverified",
                    "baseline_sha256": hashlib.sha256(raw).hexdigest(),
                    "records": source_records,
                    "origin_city_by_id": {},
                }
                # Candidate is a no-change private *copy*, not a fresh source.
                candidate = self.root / f"{city}-saved-candidate.json"
                save(candidate, envelope)
                report, _, changes = preflight.inspect(city, baseline, candidate)
                self.assertEqual(report["counts"], {"added": 0, "updated": 0, "deleted": 0})
                self.assertEqual(report["source_status"], "saved_unverified")
                self.assertEqual(report["source_authenticity"], "unverified")
                self.assertEqual(changes["unchanged_count"], len(source_records))
                self.assertEqual(baseline.read_bytes(), raw)
                print(
                    f"SAVED_CONTRACT city={city} records={len(source_records)} "
                    f"bytes={len(raw)} url_field={expected_origin_key} PASS"
                )



if __name__ == "__main__":
    unittest.main()
