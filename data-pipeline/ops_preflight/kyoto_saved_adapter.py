"""Prepare one saved Kyoto statement series for the existing offline preflight.

No source acquisition, producer execution, public data writes, or publication.
The private candidate remains saved_unverified, even after machine inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import preflight

CITY = "kyoto"
SAVED_NAME = f"{CITY}_{preflight.FEATURE}.json"


def prepare(
    baseline: Path,
    saved: Path,
    private_root: Path,
    origin_declarations: Path | None = None,
) -> tuple[Path, dict, dict, str]:
    """Create a non-overwriting private envelope *only if* preflight accepts it.

    The source is a previously saved local array, NOT a newly verified source.
    Changed/added IDs must be declared by the caller, never invented here.
    """
    root = preflight._check_private_root(private_root)
    if baseline.name != SAVED_NAME or saved.name != SAVED_NAME:
        raise preflight.Blocked("Expected Kyoto statements-summary saved input filenames")
    baseline_records, baseline_bytes = preflight._read_json(baseline)
    saved_records, saved_bytes = preflight._read_json(saved)
    preflight._index_records(baseline_records, strict_source=False)
    preflight._index_records(saved_records, strict_source=True)
    if any("source_url" not in row for row in saved_records):
        raise preflight.Blocked("Kyoto saved series requires source_url on every row")

    origins = {}
    if origin_declarations is not None:
        origins, _ = preflight._read_json(origin_declarations)
        if not isinstance(origins, dict):
            raise preflight.Blocked("Origin declarations must be a JSON object")

    envelope = {
        "schema_version": 1,
        "city_code": CITY,
        "feature": preflight.FEATURE,
        "source_status": "saved_unverified",
        "baseline_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "records": saved_records,
        "origin_city_by_id": origins,
    }
    candidate_bytes = json.dumps(
        envelope, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(candidate_bytes) > preflight.MAX_FILE_BYTES:
        raise preflight.Blocked("Private candidate exceeds preflight input limit")

    # Reserve an exclusive owner-only subdirectory. The validated marker is
    # intentionally NOT created here; only preflight.stage can do that later.
    folder = root / f"kyoto-saved-{uuid.uuid4().hex}"
    folder.mkdir(mode=0o700, exist_ok=False)
    pending = folder / "candidate.json.pending"
    candidate = folder / "candidate.json"
    try:
        preflight._write_exclusive(pending, candidate_bytes)
        # The existing preflight re-reads the baseline. If it changed after our
        # hash calculation, the SHA check rejects this pending candidate.
        report, _, changes = preflight.inspect(CITY, baseline, pending)
        os.replace(pending, candidate)  # new private directory: no existing target
    except BaseException:
        # Failure must never leave a final candidate or a valid stage marker.
        pending.unlink(missing_ok=True)
        folder.rmdir()
        raise
    return candidate, report, changes, hashlib.sha256(saved_bytes).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline Kyoto saved statement series -> private preflight candidate"
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--saved", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--origin-declarations", type=Path)
    args = parser.parse_args(argv)
    try:
        candidate, report, changes, saved_sha = prepare(
            args.baseline, args.saved, args.private_root, args.origin_declarations
        )
        print(json.dumps({
            "status": "prepared_pending_pm_review",
            "candidate_path": str(candidate),
            "saved_sha256": saved_sha,
            "preflight": report,
            "diff": changes,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (preflight.Blocked, OSError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
