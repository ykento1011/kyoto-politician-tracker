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
    """Candidate cannot proceed; diagnostics contain only aggregate field counts."""

    def __init__(self, reason: str, *, diagnostics: dict | None = None) -> None:
        super().__init__(reason)
        self.diagnostics = diagnostics


def _reject_nonjson_constant(token: str) -> None:
    raise Blocked(f"Nonstandard JSON numeric constant: {token}")


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
        value = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_nonjson_constant)
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
        # Existing Kyoto rows use source_url; the other four published cities
        # use official_url. These are *structural* references, not proof.
        url_fields = [name for name in ("source_url", "official_url") if name in record]
        if not url_fields:
            raise Blocked("Candidate record lacks source_url or official_url")
        for field in url_fields:
            url = record[field]
            if not isinstance(url, str):
                raise Blocked(f"Candidate record {field} must be a URL")
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise Blocked(f"Candidate record {field} is not HTTP(S)")
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


def _fingerprint(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha(raw)


def _field_changes(before: dict, after: dict) -> dict[str, str]:
    """Top-level schema field -> change kind; never return a value or record ID."""
    result = {}
    for field in before.keys() | after.keys():
        if field not in before:
            result[field] = "field_added"
        elif field not in after:
            result[field] = "field_removed"
        elif _fingerprint(before[field]) != _fingerprint(after[field]):
            result[field] = "value_changed"
    return result


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

    # Count top-level field names on CHANGED existing records only; additions
    # and deletions of whole records remain in counts. Nested values are atomic.
    changed_rows = []
    field_counts: dict[str, dict[str, int]] = {}
    dropped_fields = False
    for key in updated:
        previous, current = base_index[key], candidate_index[key]
        changed = _field_changes(previous, current)
        changed_rows.append({"id": key, "changed_fields": sorted(changed)})
        if not previous.keys() <= current.keys():
            dropped_fields = True
        for field, kind in changed.items():
            counter = field_counts.setdefault(field, {
                "value_changed": 0, "field_added": 0, "field_removed": 0,
            })
            counter[kind] += 1

    # Diagnostics are safe for inspect stdout/stderr: no records, values,
    # source URLs or IDs. A change to every existing row is a deterministic
    # review trigger, not an estimated ratio or source-authenticity judgment.
    diagnostics = {
        "counts": {
            "added": len(added), "updated": len(updated), "deleted": len(deleted),
        },
        "field_change_counts": {
            name: field_counts[name] for name in sorted(field_counts)
        },
        "all_existing_rows_changed": bool(base_index) and len(updated) == len(base_index),
    }

    if dropped_fields:
        raise Blocked("Changed record drops existing fields", diagnostics=diagnostics)
    for key, record in candidate_index.items():
        if "city_code" in record and record["city_code"] != city:
            raise Blocked("Embedded record belongs to a different city", diagnostics=diagnostics)

    # A declarative origin is not independent evidence. Missing or mismatched
    # declarations continue to reject the candidate, even when the field
    # summary can be displayed read-only for PM diagnosis.
    touched = set(added) | set(updated)
    if set(declared_origins.keys()) != touched:
        raise Blocked(
            "Changed/new record origin declarations are incomplete or extraneous",
            diagnostics=diagnostics,
        )
    if any(declared_origins[key] != city for key in touched):
        raise Blocked("Cross-city candidate record detected", diagnostics=diagnostics)
    if deleted:
        raise Blocked("Deletion detected: PM must resolve before any stage", diagnostics=diagnostics)

    # Per-ID details are retained ONLY in private diff.json. Report/CLI uses
    # the aggregate field names and counts above; no value or ID is emitted.
    changes = {
        "added": added,
        "updated": changed_rows,
        "deleted": [],
        "unchanged_count": len(candidate_index) - len(added) - len(updated),
        "field_change_counts": diagnostics["field_change_counts"],
    }
    bulk_review = diagnostics["all_existing_rows_changed"]
    report = {
        "city_code": city,
        "feature": FEATURE,
        "baseline_sha256": _sha(baseline_bytes),
        "candidate_sha256": _sha(candidate_bytes),
        "baseline_count": len(base_index),
        "candidate_count": len(candidate_index),
        "counts": diagnostics["counts"],
        "field_change_counts": diagnostics["field_change_counts"],
        "all_existing_rows_changed": bulk_review,
        "stage_permitted": not bulk_review,
        "source_status": envelope["source_status"],
        "source_authenticity": "unverified",
        "review_state": "bulk_change_requires_pm_review" if bulk_review else "pending_pm_review",
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
    if (
        report.get("stage_permitted") is not True
        or report.get("review_state") != "pending_pm_review"
        or report.get("all_existing_rows_changed") is not False
    ):
        raise Blocked("Stage refused: PM must review bulk or unapproved change")
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
    # The final marker name must not exist until its bytes have been flushed
    # and synced successfully. A failed marker fsync leaves only a .pending file.
    marker_pending = folder / "validated.json.pending"
    _write_exclusive(marker_pending, json.dumps({
        "stage_id": stage_id, "state": "machine_validated_pending_pm_review",
        "publish_permitted": False,
    }, sort_keys=True).encode("utf-8"))
    os.replace(marker_pending, folder / "validated.json")
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
    except Blocked as exc:
        payload = {"status": "blocked", "reason": str(exc)}
        if exc.diagnostics is not None:
            payload["diagnostics"] = exc.diagnostics
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"status": "blocked", "reason": "Local file operation failed"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
