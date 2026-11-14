"""Offline, fail-closed preflight for five-city statement-summary candidates.

This tool does not fetch sources, run legacy producers, modify published JSON,
perform git operations, or publish. Machine validation is NOT source verification
or permission to deploy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

CITIES = frozenset({"kyoto", "osaka", "kobe", "nagoya", "yokohama"})
FEATURE = "statements_summary"
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 100_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Blocked(ValueError):
    """Candidate cannot proceed to private stage."""


def _read_json(path: Path) -> tuple[object, bytes]:
    # A single byte snapshot is checked and subsequently staged, never reloaded.
    if path.is_symlink() or not path.is_file():
        raise Blocked("Input is missing, linked, or not a regular file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise Blocked("Input is too large")
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise Blocked("Input is too large")
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise Blocked("Invalid UTF-8 JSON") from exc
    return value, raw


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _check_record(record: object, *, strict_source: bool) -> str:
    if not isinstance(record, dict):
        raise Blocked("Record is not an object")
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise Blocked("Record id must be a nonempty string")
    if strict_source:
        url = record.get("source_url")
        if not isinstance(url, str):
            raise Blocked("Candidate record lacks source_url")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise Blocked("Candidate record source_url is not HTTP(S)")
    return record_id


def _index_records(records: object, *, strict_source: bool) -> dict[str, dict]:
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise Blocked("Expected a bounded array of records")
    result: dict[str, dict] = {}
    for record in records:
        record_id = _check_record(record, strict_source=strict_source)
        if record_id in result:
            raise Blocked("Duplicate record id")
        result[record_id] = record
    return result


def _fingerprint(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha(raw)


def inspect(city: str, baseline: Path, candidate: Path) -> tuple[dict, bytes, dict]:
    """Read-only validation; returns report, original candidate bytes, and payload."""
    if city not in CITIES:
        raise Blocked("Unknown city")
    if baseline.name != f"{city}_{FEATURE}.json":
        raise Blocked("Baseline file name does not match city feature contract")

    original, baseline_bytes = _read_json(baseline)
    envelope, candidate_bytes = _read_json(candidate)
    base_index = _index_records(original, strict_source=False)
    if not isinstance(envelope, dict):
        raise Blocked("Candidate must be an explicitly city-scoped envelope")
    if envelope.get("schema_version") != 1 or envelope.get("city_code") != city:
        raise Blocked("Candidate schema or city mismatch")
    if envelope.get("feature") != FEATURE:
        raise Blocked("Candidate feature mismatch")
    if envelope.get("baseline_sha256") != _sha(baseline_bytes):
        raise Blocked("Stale or incorrect baseline revision")
    if envelope.get("source_status") not in {"synthetic", "saved_unverified"}:
        raise Blocked("Only synthetic or previously saved unverified inputs are in scope")

    candidate_index = _index_records(envelope.get("records"), strict_source=True)
    declared_origins = envelope.get("origin_city_by_id")
    if not isinstance(declared_origins, dict):
        raise Blocked("Missing record origin-city declarations")

    deleted = sorted(base_index.keys() - candidate_index.keys())
    added = sorted(candidate_index.keys() - base_index.keys())
    updated = sorted(
        key for key in (base_index.keys() & candidate_index.keys())
        if _fingerprint(base_index[key]) != _fingerprint(candidate_index[key])
    )
    # Existing records must retain their previous keys, preventing silent field loss.
    for key in updated:
        if not base_index[key].keys() <= candidate_index[key].keys():
            raise Blocked("Changed record drops existing fields")
    for key, record in candidate_index.items():
        if "city_code" in record and record["city_code"] != city:
            raise Blocked("Embedded record belongs to a different city")

    # Each new or changed row needs an explicit per-record city declaration.
    # This declaration is only a structural check, NOT independent origin proof.
    touched = set(added) | set(updated)
    if set(declared_origins.keys()) != touched:
        raise Blocked("Changed/new record origin declarations are incomplete or extraneous")
    if any(declared_origins[key] != city for key in touched):
        raise Blocked("Cross-city candidate record detected")
    if deleted:
        raise Blocked("Deletion detected: PM must resolve before any stage")

    # Record-level changes are reviewable; they are never auto-publishable.
    changes = {
        "added": added,
        "updated": [
            {"id": key,
             "changed_fields": sorted(
                 field for field in base_index[key].keys() | candidate_index[key].keys()
                 if base_index[key].get(field) != candidate_index[key].get(field)
             )}
            for key in updated
        ],
        "deleted": [],
        "unchanged_count": len(candidate_index) - len(added) - len(updated),
    }
    report = {
        "city_code": city,
        "feature": FEATURE,
        "baseline_sha256": _sha(baseline_bytes),
        "candidate_sha256": _sha(candidate_bytes),
        "baseline_count": len(base_index),
        "candidate_count": len(candidate_index),
        "counts": {"added": len(added), "updated": len(updated), "deleted": 0},
        "source_status": envelope["source_status"],
        "source_authenticity": "unverified",
        "review_state": "pending_pm_review",
        "publish_permitted": False,
    }
    return report, candidate_bytes, changes


def _check_private_root(private_root: Path) -> Path:
    # Refuse symlinks/junctions along the path, before creating any files.
    root = private_root.absolute()
    for node in (root, *root.parents):
        try:
            info = node.lstat()
        except OSError as exc:
            raise Blocked("Private stage root is missing") from exc
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise Blocked("Private stage root traverses a link or reparse point")
    if not root.is_dir():
        raise Blocked("Private stage root must already exist")
    resolved = root.resolve()
    if resolved == PROJECT_ROOT or PROJECT_ROOT in resolved.parents:
        raise Blocked("Private stage must be outside the repository")
    if os.name != "nt" and root.stat().st_mode & 0o077:
        raise Blocked("Private stage root must be owner-only (mode 0700)")
    return resolved


def _write_exclusive(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def stage(private_root: Path, report: dict, candidate_bytes: bytes, changes: dict) -> str:
    """Non-overwriting private stage; a failed stage never gets a validated marker."""
    root = _check_private_root(private_root)
    stage_id = f"{report['city_code']}-{uuid.uuid4().hex}"
    folder = root / stage_id
    folder.mkdir(mode=0o700, exist_ok=False)
    # Marker MUST be last. Partial folders remain unvalidated and unpublishable.
    _write_exclusive(folder / "candidate.json", candidate_bytes)
    diff_bytes = json.dumps(changes, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    _write_exclusive(folder / "diff.json", diff_bytes)
    manifest = dict(report)
    manifest["stage_id"] = stage_id
    manifest["diff_sha256"] = _sha(diff_bytes)
    _write_exclusive(folder / "manifest.json", json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8"))
    _write_exclusive(folder / "validated.json", json.dumps({
        "stage_id": stage_id, "state": "machine_validated_pending_pm_review",
        "publish_permitted": False,
    }, sort_keys=True).encode("utf-8"))
    return stage_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline five-city candidate inspect/private-stage")
    parser.add_argument("mode", choices=("inspect", "stage"))
    parser.add_argument("--city", required=True, choices=sorted(CITIES))
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--private-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "stage" and args.private_root is None:
            raise Blocked("Private stage root is required")
        # Check the private destination even before reading inputs in stage mode.
        if args.mode == "stage":
            _check_private_root(args.private_root)
        report, raw, changes = inspect(args.city, args.baseline, args.candidate)
        if args.mode == "stage":
            report["stage_id"] = stage(args.private_root, report, raw, changes)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (Blocked, OSError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
