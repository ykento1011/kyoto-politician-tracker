"""One Kyoto saved-analysis -> private projection -> accepted offline preflight.

Only saved JSON is read. The legacy public writer and producer are NEVER
called. Every output stays in a pre-existing owner-only directory outside git.
This tool neither stages nor publishes, and asserts no source authenticity.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

import kyoto_saved_adapter
import preflight

ANALYSIS_NAME = "analyzed_kyoto_politicians_term.json"
OUTPUT_NAME = kyoto_saved_adapter.SAVED_NAME
LEGACY_PROJECTION_SOURCE = preflight.PROJECT_ROOT / "data-pipeline" / "generate_static_data.py"
# Pin the inspected pure-helper module. Re-review before importing changed code.
EXPECTED_GENERATOR_GIT_BLOB = "3b361296ead93c092e60acfa453b7de4a4074e22"
SCORE_FIELDS = ("evidence", "solution", "local_focus", "constructive")


def _legacy_helpers():
    """Load only the inspected generator's pure helpers, never generate_summary."""
    source = LEGACY_PROJECTION_SOURCE
    if source.is_symlink() or not source.is_file():
        raise preflight.Blocked("Legacy projection helper is unavailable")
    raw = source.read_bytes()
    blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if blob != EXPECTED_GENERATOR_GIT_BLOB:
        raise preflight.Blocked("Projection helper code has changed; PM re-review required")
    spec = importlib.util.spec_from_file_location("_reviewed_kyoto_projection_helpers", source)
    if spec is None or spec.loader is None:
        raise preflight.Blocked("Cannot load reviewed projection helpers")
    module = importlib.util.module_from_spec(spec)
    # No bytecode/repository write on import even without the -B CLI flag.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module.clean_speaker_name, module.refine_category


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _score(value: object) -> int:
    # No silent zero-fill or float truncation of an unreviewed evaluated row.
    if type(value) is int:
        score = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        score = int(value)
    else:
        raise preflight.Blocked("Evaluated record has missing or invalid scores")
    if not 0 <= score <= 5:
        raise preflight.Blocked("Evaluated record score is outside reviewed rubric")
    return score


def project_records(saved_analysis: object) -> list[dict]:
    """Mirror the legacy compact projection, with fail-closed missing-input guards.

    Changes from legacy on purpose: refuse implicit meeting_id+sequence_number
    ID creation, empty source/summary/text, missing scores, and invalid metadata.
    """
    if not isinstance(saved_analysis, list) or len(saved_analysis) > preflight.MAX_RECORDS:
        raise preflight.Blocked("Saved analysis must be a bounded JSON array")
    clean_speaker_name, refine_category = _legacy_helpers()
    records = []
    for statement in saved_analysis:
        if not isinstance(statement, dict):
            raise preflight.Blocked("Saved analysis contains a non-object row")
        analysis = statement.get("analysis", {})
        if not isinstance(analysis, dict):
            raise preflight.Blocked("Saved analysis has invalid analysis object")
        evaluated = analysis.get("is_evaluated", False)
        if type(evaluated) is not bool:
            raise preflight.Blocked("Analysis evaluation flag is not a boolean")
        if not evaluated:
            continue
        if "city_code" in statement and statement["city_code"] != "kyoto":
            raise preflight.Blocked("Saved analysis includes another city")

        # In the legacy public writer: id or f"{meeting_id}_{sequence_number}".
        # This private projection intentionally refuses a fabricated fallback.
        if not _nonblank(statement.get("id")):
            raise preflight.Blocked("Evaluated row has no explicit stable ID")
        if not _nonblank(statement.get("meeting_id")):
            raise preflight.Blocked("Evaluated row has no meeting ID")
        sequence = statement.get("sequence_number")
        if type(sequence) not in (int, str) or not str(sequence).strip():
            raise preflight.Blocked("Evaluated row has invalid sequence number")
        if not all(_nonblank(statement.get(k)) for k in (
            "meeting_title", "meeting_date", "speaker", "statement_text", "source_url",
        )):
            raise preflight.Blocked("Evaluated row has missing source or meeting context")
        summary = analysis.get("summary")
        if not _nonblank(summary):
            raise preflight.Blocked("Evaluated row has no reviewed summary")
        scores = analysis.get("scores")
        if not isinstance(scores, dict):
            raise preflight.Blocked("Evaluated row has no reviewed scores")
        mapped_scores = {field: _score(scores.get(field)) for field in SCORE_FIELDS}
        title = statement["meeting_title"]
        snippet = statement["statement_text"].strip()[:120].replace("\n", " ")
        category = refine_category(analysis.get("category", "政策質疑"), title, summary)

        # Same 16 public contract fields and insertion order as the reviewed
        # 2026-11-14 generate_static_data.py compact_records mapping.
        record = {
            "id": statement["id"],
            "meeting_id": statement["meeting_id"],
            "sequence_number": sequence,
            "meeting_title": title,
            "meeting_date": statement["meeting_date"],
            "speaker": clean_speaker_name(statement["speaker"]),
            "category": category,
            "summary": summary,
            "scoring_reasoning": analysis.get("reasoning", ""),
            "statement_snippet": snippet,
            "statement_text": snippet,
            "evidence_score": mapped_scores["evidence"],
            "solution_score": mapped_scores["solution"],
            "local_focus_score": mapped_scores["local_focus"],
            "constructive_score": mapped_scores["constructive"],
            "source_url": statement["source_url"],
        }
        preflight._check_record(record, strict_source=True)
        records.append(record)

    if not records:
        raise preflight.Blocked("Saved analysis has no reviewed statements")
    records.sort(key=lambda value: str(value.get("meeting_date", "")), reverse=True)
    preflight._index_records(records, strict_source=True)
    return records


def prepare_private_handoff(
    saved_analysis: Path,
    baseline: Path,
    private_root: Path,
    origin_declarations: Path | None = None,
) -> dict:
    """Produce a non-public saved copy then invoke existing Kyoto adapter/inspect.

    Returns only aggregate diagnostics; never calls preflight.stage or publishes.
    A failed candidate inspection removes the provisional private projection.
    """
    root = preflight._check_private_root(private_root)
    if saved_analysis.name != ANALYSIS_NAME or baseline.name != OUTPUT_NAME:
        raise preflight.Blocked("Saved analysis or baseline filename mismatch")
    analyzed, analysis_bytes = preflight._read_json(saved_analysis)
    compact = project_records(analyzed)
    raw = json.dumps(
        compact, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(raw) > preflight.MAX_FILE_BYTES:
        raise preflight.Blocked("Private Kyoto projection exceeds preflight limit")

    # Never write anything until source input and compact projection validate.
    folder = root / f"kyoto-projected-{uuid.uuid4().hex}"
    folder.mkdir(mode=0o700, exist_ok=False)
    pending = folder / (OUTPUT_NAME + ".pending")
    saved_copy = folder / OUTPUT_NAME
    try:
        preflight._write_exclusive(pending, raw)
        os.replace(pending, saved_copy)
        _candidate, report, _private_diff, _saved_sha = kyoto_saved_adapter.prepare(
            baseline, saved_copy, root, origin_declarations
        )
    except BaseException:
        pending.unlink(missing_ok=True)
        saved_copy.unlink(missing_ok=True)
        folder.rmdir()
        raise

    return {
        "status": (
            "bulk_change_requires_pm_review"
            if not report["stage_permitted"] else "private_candidate_pending_pm_review"
        ),
        "city_code": "kyoto",
        "projected_records": len(compact),
        "saved_analysis_sha256": hashlib.sha256(analysis_bytes).hexdigest(),
        "projection_sha256": hashlib.sha256(raw).hexdigest(),
        "preflight": report,
        "stage_executed": False,
        "publish_permitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Saved Kyoto analysis -> private-only projection + preflight.inspect"
    )
    parser.add_argument("--saved-analysis", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--origin-declarations", type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare_private_handoff(
            args.saved_analysis, args.baseline, args.private_root, args.origin_declarations
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except preflight.Blocked as exc:
        # Only fixed message categories and aggregate field counts are logged;
        # never log the saved input, record IDs, URLs or private paths.
        payload = {"status": "blocked", "reason": str(exc)}
        if exc.diagnostics is not None:
            payload["diagnostics"] = exc.diagnostics
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError):
        print(json.dumps({"status": "blocked", "reason": "Private file or data operation failed"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
