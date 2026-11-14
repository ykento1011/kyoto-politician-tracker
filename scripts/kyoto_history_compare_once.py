"""One-shot GitHub historical saved-file comparison; never acquires live sources.

The caller extracts two pinned existing Git blobs into owner-only RUNNER_TEMP.
Only aggregate counts and fail-closed inspection status leave this process.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# Path is repository/scripts/kyoto_history_compare_once.py in CI.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline" / "ops_preflight"))
import preflight  # noqa: E402

SAVED_NAME = "kyoto_statements_summary.json"
OLD_GIT_BLOB = "438089e5e408296a9df8814dfec63d7040982cbb"
CURRENT_GIT_BLOB = "89fe9c738ca24c910554b8d8667c79a641873158"


def check_temp_input(path: Path, runner_temp: Path) -> None:
    if path.name != SAVED_NAME or path.is_symlink() or not path.is_file():
        raise preflight.Blocked("BAD_INPUT_PATH")
    if runner_temp not in path.resolve().parents:
        raise preflight.Blocked("INPUT_NOT_IN_RUNNER_TEMP")


def git_blob_hash(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def read_saved(path: Path, expected_blob: str) -> tuple[dict[str, dict], bytes]:
    data, raw = preflight._read_json(path)
    if git_blob_hash(raw) != expected_blob:
        raise preflight.Blocked("PINNED_GIT_BLOB_MISMATCH")
    indexed = preflight._index_records(data, strict_source=False)
    return indexed, raw


def run(older: Path, current: Path) -> None:
    temp_value = os.environ.get("RUNNER_TEMP")
    if not temp_value:
        raise preflight.Blocked("MISSING_RUNNER_TEMP")
    runner_temp = Path(temp_value).resolve(strict=True)
    check_temp_input(older, runner_temp)
    check_temp_input(current, runner_temp)

    old_index, old_raw = read_saved(older, OLD_GIT_BLOB)
    new_index, current_raw = read_saved(current, CURRENT_GIT_BLOB)
    old_ids, new_ids = set(old_index), set(new_index)
    added = new_ids - old_ids
    deleted = old_ids - new_ids
    common = old_ids & new_ids
    updated = {record_id for record_id in common if (
        preflight._fingerprint(old_index[record_id])
        != preflight._fingerprint(new_index[record_id])
    )}
    unchanged = len(common) - len(updated)
    lost_field_rows = sum(
        not (set(old_index[record_id]) <= set(new_index[record_id]))
        for record_id in updated
    )

    # Do not fabricate origin_city_by_id: it is deliberately EMPTY. Even a
    # public historical record is not independent origin proof for a new input.
    envelope = {
        "schema_version": 1,
        "city_code": "kyoto",
        "feature": preflight.FEATURE,
        "source_status": "saved_unverified",
        "baseline_sha256": hashlib.sha256(old_raw).hexdigest(),
        "records": list(new_index.values()),
        "origin_city_by_id": {},
    }
    candidate_bytes = json.dumps(
        envelope, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(candidate_bytes) > preflight.MAX_FILE_BYTES:
        raise preflight.Blocked("CANDIDATE_TOO_LARGE")

    candidate_path = older.parent.parent / "unverified_candidate.json"
    if runner_temp not in candidate_path.resolve().parents:
        raise preflight.Blocked("CANDIDATE_PATH_NOT_TEMP")
    preflight._write_exclusive(candidate_path, candidate_bytes)

    blocked = False
    block_code = "NONE"
    try:
        _, _, _ = preflight.inspect("kyoto", older, candidate_path)
    except preflight.Blocked as exc:
        blocked = True
        known_reasons = {
            "Changed/new record origin declarations are incomplete or extraneous": "NO_INDEPENDENT_ORIGIN_DECLARATIONS",
            "Deletion detected: PM must resolve before any stage": "DELETIONS_NOT_ALLOWED",
            "Changed record drops existing fields": "EXISTING_FIELD_LOSS",
            "Cross-city candidate record detected": "CROSS_CITY_TAG",
            "Candidate record lacks source_url or official_url": "MISSING_SOURCE_URL",
        }
        block_code = known_reasons.get(str(exc), "OTHER_SAFE_REJECTION")

    if (added or updated or deleted) and not blocked:
        raise preflight.Blocked("UNSAFE_PREFLIGHT_ACCEPTED_REAL_HISTORICAL_DELTA")

    # No individual text, record ID, URLs or rows are ever logged.
    for name, value in (
        ("COMPARE_STATUS", "OK"),
        ("DIRECTION", "2026-10-30_old_to_2026-11-14_main"),
        ("OLD_BLOB_VERIFIED", OLD_GIT_BLOB),
        ("CURRENT_BLOB_VERIFIED", CURRENT_GIT_BLOB),
        ("OLD_SHA256", hashlib.sha256(old_raw).hexdigest()),
        ("CURRENT_SHA256", hashlib.sha256(current_raw).hexdigest()),
        ("OLD_RECORD_COUNT", len(old_index)),
        ("CURRENT_RECORD_COUNT", len(new_index)),
        ("ADDED", len(added)),
        ("UPDATED", len(updated)),
        ("DELETED", len(deleted)),
        ("UNCHANGED", unchanged),
        ("FIELD_LOSS_ROW_COUNT", lost_field_rows),
        ("PREFLIGHT_INSPECT_BLOCKED", str(blocked).lower()),
        ("PREFLIGHT_BLOCK_CODE", block_code),
        ("STAGE_EXECUTED", "false"),
        ("SOURCE_AUTHENTICITY", "unverified"),
    ):
        print(f"{name}={value}")


def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise preflight.Blocked("NEED_TWO_INPUT_FILES")
        run(Path(sys.argv[1]), Path(sys.argv[2]))
    except (preflight.Blocked, OSError, ValueError, TypeError):
        # Sanitized error: never print input data or path even on failure.
        print("COMPARE_STATUS=STOP_INVALID_OR_UNAVAILABLE_HISTORY")
        return 2
    except Exception:
        print("COMPARE_STATUS=STOP_UNEXPECTED_ERROR")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
