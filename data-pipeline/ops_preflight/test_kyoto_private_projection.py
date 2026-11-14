"""Offline synthetic tests for the Kyoto saved-analysis-to-preflight boundary.

Never import a paid producer, execute the legacy writer, fetch an origin, or
modify published JSON. All synthetic outputs go to an owner-only temp root.
"""

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kyoto_private_projection as projection
import preflight


def save(path: Path, data: object) -> bytes:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    return raw


class KyotoPrivateProjectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.readonly = self.root / "readonly"
        self.readonly.mkdir()
        self.saved_input = self.readonly / projection.ANALYSIS_NAME
        self.baseline = self.readonly / projection.OUTPUT_NAME
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        os.chmod(self.private, 0o700)

    @staticmethod
    def statement(record_id, summary, *, day="2026-11-04"):
        return {
            "id": record_id,
            "meeting_id": "test-committee",
            "sequence_number": 7 if record_id == "test-1" else 8,
            "meeting_title": "産業交通水道委員会",
            "meeting_date": day,
            "speaker": "テスト議員",
            "statement_text": "  市バスの改善提案\nを確認します。  ",
            "source_url": "https://example.invalid/kyoto/saved-synthetic",
            "analysis": {
                "is_evaluated": True,
                "category": ["交通"],
                "summary": summary,
                "reasoning": "合成の評価理由",
                "scores": {
                    "evidence": 3,
                    "solution": 4,
                    "local_focus": 2,
                    "constructive": 5,
                },
            },
        }

    def setup_versions(self, *, new_summary="新しい合成要約"):
        before = [
            self.statement("test-1", "以前の合成要約"),
            self.statement("test-2", "変更しない合成要約", day="2026-11-03"),
        ]
        after = [
            self.statement("test-1", new_summary),
            self.statement("test-2", "変更しない合成要約", day="2026-11-03"),
        ]
        baseline_bytes = save(self.baseline, projection.project_records(before))
        original_input = save(self.saved_input, after)
        return before, after, baseline_bytes, original_input

    def dir_names(self):
        return sorted(p.name for p in self.private.iterdir())

    def origin_file(self, declared=None):
        p = self.readonly / "origins.json"
        save(p, {"test-1": "kyoto"} if declared is None else declared)
        return p

    def test_projection_keeps_legacy_16_field_contract_and_sort(self):
        _, after, _, _ = self.setup_versions()
        records = projection.project_records(after[::-1])
        self.assertEqual([x["id"] for x in records], ["test-1", "test-2"])
        self.assertEqual(list(records[0]), [
            "id", "meeting_id", "sequence_number", "meeting_title",
            "meeting_date", "speaker", "category", "summary",
            "scoring_reasoning", "statement_snippet", "statement_text",
            "evidence_score", "solution_score", "local_focus_score",
            "constructive_score", "source_url",
        ])
        self.assertEqual(records[0]["speaker"], "テスト")
        self.assertEqual(records[0]["category"], "都市再生・交通インフラ")
        self.assertEqual(records[0]["statement_snippet"], "市バスの改善提案 を確認します。")
        self.assertEqual(records[0]["statement_text"], records[0]["statement_snippet"])
        self.assertEqual(
            [records[0][x] for x in (
                "evidence_score", "solution_score", "local_focus_score", "constructive_score"
            )], [3, 4, 2, 5]
        )

    def test_synthetic_private_projection_to_adapter_and_inspect(self):
        _, after, baseline_bytes, source_bytes = self.setup_versions()
        declarations = self.origin_file()
        result = projection.prepare_private_handoff(
            self.saved_input, self.baseline, self.private, declarations
        )
        self.assertEqual(result["status"], "private_candidate_pending_pm_review")
        self.assertEqual(result["projected_records"], 2)
        self.assertEqual(
            result["saved_analysis_sha256"], hashlib.sha256(source_bytes).hexdigest()
        )
        self.assertEqual(
            result["preflight"]["counts"], {"added": 0, "updated": 1, "deleted": 0}
        )
        self.assertEqual(
            result["preflight"]["field_change_counts"]["summary"]["value_changed"], 1
        )
        self.assertTrue(result["preflight"]["stage_permitted"])
        self.assertFalse(result["stage_executed"])
        self.assertFalse(result["publish_permitted"])
        self.assertEqual(result["preflight"]["source_authenticity"], "unverified")
        self.assertEqual(result["preflight"]["source_status"], "saved_unverified")
        self.assertEqual(self.baseline.read_bytes(), baseline_bytes)
        self.assertEqual(self.saved_input.read_bytes(), source_bytes)
        projected = list(self.private.glob("kyoto-projected-*/kyoto_statements_summary.json"))
        candidates = list(self.private.glob("kyoto-saved-*/candidate.json"))
        self.assertEqual(len(projected), 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(json.loads(projected[0].read_text()), projection.project_records(after))
        self.assertFalse(list(self.private.rglob("validated.json")))
        self.assertFalse(list(self.private.rglob("manifest.json")))

    def test_missing_origin_refuses_candidate_and_cleans_projection(self):
        self.setup_versions()
        with self.assertRaises(preflight.Blocked) as blocked:
            projection.prepare_private_handoff(
                self.saved_input, self.baseline, self.private
            )
        self.assertIn("origin declarations", str(blocked.exception))
        self.assertEqual(blocked.exception.diagnostics["counts"]["updated"], 1)
        self.assertEqual(self.dir_names(), [])

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = projection.main([
                "--saved-analysis", str(self.saved_input),
                "--baseline", str(self.baseline),
                "--private-root", str(self.private),
            ])
        self.assertEqual(result, 2)
        response = json.loads(stderr.getvalue())
        self.assertEqual(response["status"], "blocked")
        self.assertNotIn("test-1", stderr.getvalue())
        self.assertNotIn("新しい合成要約", stderr.getvalue())
        self.assertEqual(self.dir_names(), [])

    def test_all_record_change_is_pm_review_and_stage_stops(self):
        _, after, baseline_bytes, _ = self.setup_versions()
        after[1]["analysis"]["summary"] = "二件目も変更"
        save(self.saved_input, after)
        origins = self.origin_file({"test-1": "kyoto", "test-2": "kyoto"})
        report = projection.prepare_private_handoff(
            self.saved_input, self.baseline, self.private, origins
        )
        self.assertEqual(report["preflight"]["counts"]["updated"], 2)
        self.assertEqual(report["status"], "bulk_change_requires_pm_review")
        self.assertFalse(report["preflight"]["stage_permitted"])
        candidate = next(self.private.glob("kyoto-saved-*/candidate.json"))
        inspected, raw, changes = preflight.inspect("kyoto", self.baseline, candidate)
        before = self.dir_names()
        with self.assertRaisesRegex(preflight.Blocked, "Stage refused"):
            preflight.stage(self.private, inspected, raw, changes)
        self.assertEqual(self.dir_names(), before)
        self.assertFalse(list(self.private.rglob("validated.json")))
        self.assertEqual(self.baseline.read_bytes(), baseline_bytes)

    def test_missing_id_duplicate_id_url_or_scores_stop_before_writing(self):
        before, after, original, _ = self.setup_versions()
        examples = []
        missing_id = json.loads(json.dumps(after))
        del missing_id[0]["id"]
        examples.append(missing_id)
        duplicate = json.loads(json.dumps(after))
        duplicate[1]["id"] = duplicate[0]["id"]
        examples.append(duplicate)
        missing_url = json.loads(json.dumps(after))
        del missing_url[0]["source_url"]
        examples.append(missing_url)
        missing_score = json.loads(json.dumps(after))
        del missing_score[0]["analysis"]["scores"]["evidence"]
        examples.append(missing_score)
        wrong_city = json.loads(json.dumps(after))
        wrong_city[0]["city_code"] = "osaka"
        examples.append(wrong_city)
        for idx, example in enumerate(examples):
            with self.subTest(case=idx):
                save(self.saved_input, example)
                with self.assertRaises(preflight.Blocked):
                    projection.prepare_private_handoff(
                        self.saved_input, self.baseline, self.private
                    )
                self.assertEqual(self.dir_names(), [])
                self.assertEqual(self.baseline.read_bytes(), original)

    def test_interrupted_private_write_creates_no_candidate_or_marker(self):
        self.setup_versions()
        origins = self.origin_file()
        original = preflight._write_exclusive

        def break_after_write(path, data):
            original(path, data)
            if path.name.endswith(".pending"):
                raise OSError("injected private disk failure")

        with patch.object(preflight, "_write_exclusive", side_effect=break_after_write):
            with self.assertRaises(OSError):
                projection.prepare_private_handoff(
                    self.saved_input, self.baseline, self.private, origins
                )
        self.assertEqual(self.dir_names(), [])

    def test_unreviewed_legacy_module_version_is_rejected(self):
        self.setup_versions()
        with patch.object(projection, "EXPECTED_GENERATOR_GIT_BLOB", "0" * 40):
            with self.assertRaisesRegex(preflight.Blocked, "re-review"):
                projection.prepare_private_handoff(
                    self.saved_input, self.baseline, self.private
                )
        self.assertEqual(self.dir_names(), [])

    def test_invalid_source_json_and_private_root_are_refused(self):
        self.setup_versions()
        self.saved_input.write_text("NaN", encoding="utf-8")
        with self.assertRaises(preflight.Blocked):
            projection.prepare_private_handoff(self.saved_input, self.baseline, self.private)
        with self.assertRaises(preflight.Blocked):
            projection.prepare_private_handoff(
                self.saved_input, self.baseline, preflight.PROJECT_ROOT
            )
        self.assertEqual(self.dir_names(), [])

    def test_committed_public_kyoto_snapshot_unchanged_in_offline_flow(self):
        # CI reads a committed snapshot only as a guard; no file writes to public.
        public = preflight.PROJECT_ROOT / "frontend" / "public" / "data" / projection.OUTPUT_NAME
        if not public.exists():
            self.skipTest("full checkout not present in local synthetic test")
        before = hashlib.sha256(public.read_bytes()).hexdigest()
        self.setup_versions()
        projection.prepare_private_handoff(
            self.saved_input, self.baseline, self.private, self.origin_file()
        )
        self.assertEqual(hashlib.sha256(public.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
