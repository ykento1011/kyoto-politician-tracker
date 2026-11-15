"""Narrow offline-checkable boundaries for the legacy Kyoto minutes path.

No acquisition, generator, Git or network operation occurs on import.
Callbacks are supplied by run_update; tests use synthetic fixtures only.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from kyoto_private_paths import UpdateSafetyError, _hash_file

GENERATOR_BLOB = "3b361296ead93c092e60acfa453b7de4a4074e22"
SUMMARY_NAMES = ("statements_summary.json", "kyoto_statements_summary.json")
FIELDS = {
    "id", "meeting_id", "sequence_number", "meeting_title", "meeting_date",
    "speaker", "category", "summary", "scoring_reasoning", "statement_snippet",
    "statement_text", "evidence_score", "solution_score", "local_focus_score",
    "constructive_score", "source_url",
}


def require_fetch_script(script):
    if not Path(script).is_file():
        raise UpdateSafetyError("Kyoto acquisition is unconnected: fetch_sagebase.py is missing")
    _hash_file(Path(script).absolute())


def raw_snapshot(path):
    path = Path(path)
    _hash_file(path.absolute())
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise UpdateSafetyError("Missing/empty minutes array")
    records = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("city", "kyoto") != "kyoto":
            raise UpdateSafetyError("Invalid row or other city")
        mid, seq = row.get("meeting_id"), row.get("sequence_number")
        if (not isinstance(mid, str) or not mid.strip()
                or type(seq) is not int or seq < 0
                or not isinstance(row.get("statement_text"), str)):
            raise UpdateSafetyError("Invalid existing meeting/sequence/text contract")
        key = (mid, seq)
        if key in records:
            raise UpdateSafetyError("Duplicate minutes key")
        records[key] = hashlib.sha256(json.dumps(
            row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False).encode("utf-8")).hexdigest()
    # Keys are comparison keys only. No public ID is minted.
    digest = hashlib.sha256(json.dumps(
        [(m, s, records[(m, s)]) for m, s in sorted(records)],
        separators=(",", ":")).encode()).hexdigest()
    return digest, records


def refresh_minutes(fetch, path, accepted_digest):
    before_digest, before = raw_snapshot(path)
    # An externally refreshed cache must not be mistaken for a completed update.
    if not isinstance(accepted_digest, str) or not re.fullmatch("[0-9a-f]{64}", accepted_digest):
        raise UpdateSafetyError("PM-accepted last successful input fingerprint is required")
    if before_digest != accepted_digest:
        raise UpdateSafetyError("Cache differs from last accepted successful input")
    # Cache existence never bypasses the acquisition callback.
    fetch()
    after_digest, after = raw_snapshot(path)
    if before_digest == after_digest:
        return False, before, after_digest
    changed = {k for k in before.keys() & after.keys() if before[k] != after[k]}
    removed = before.keys() - after.keys()
    existing_meetings = {k[0] for k in before}
    continued = {k for k in after.keys() - before.keys() if k[0] in existing_meetings}
    if changed or removed or continued:
        # The existing Gemini checkpoint is keyed only by meeting/sequence.
        # Reusing it for corrected/continued threads would retain stale analysis.
        raise UpdateSafetyError("Correction/deletion/continued meeting detected; checkpoint review required")
    return True, before, after_digest


def summary_records(data):
    rows = json.loads(data.decode("utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise UpdateSafetyError("Empty/invalid summary")
    records, keys = {}, set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise UpdateSafetyError("Summary must preserve the 16-field contract")
        ident = row["id"]
        key = (row["meeting_id"], row["sequence_number"])
        if (not isinstance(ident, str) or not ident
                or not isinstance(key[0], str) or not key[0]
                or type(key[1]) is not int or key[1] < 0
                or ident in records or key in keys):
            raise UpdateSafetyError("Missing/duplicate summary ID or key")
        keys.add(key)
        records[ident] = row
    return records


def _replace(path, data):
    # Same-directory replacement; never truncate the live alias first.
    fd, name = tempfile.mkstemp(prefix=".minutes-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def preserve_summary_pair(data_dir):
    paths = [Path(data_dir) / n for n in SUMMARY_NAMES]
    original = {}
    for path in paths:
        if path.exists():
            _hash_file(path.absolute())
            original[path] = path.read_bytes()
            summary_records(original[path])
        else:
            original[path] = None
    canonical = original[paths[1]]
    if canonical is None:
        raise UpdateSafetyError("Existing Kyoto canonical summary is required")
    if original[paths[0]] is not None and summary_records(original[paths[0]]) != summary_records(canonical):
        raise UpdateSafetyError("Existing Kyoto aliases diverge; do not choose one automatically")
    baseline = summary_records(canonical)
    try:
        yield baseline
        validate_summary_pair(data_dir, baseline)
    except BaseException:
        for path, data in original.items():
            if data is None:
                if path.exists():
                    path.unlink()
            elif not path.exists() or path.read_bytes() != data:
                _replace(path, data)
        raise


def validate_summary_pair(data_dir, baseline):
    paths = [Path(data_dir) / n for n in SUMMARY_NAMES]
    if not paths[1].is_file():
        raise UpdateSafetyError("Kyoto canonical summary was removed")
    current = [summary_records(p.read_bytes()) for p in paths if p.exists()]
    if any(not baseline.keys() <= rows.keys() for rows in current):
        raise UpdateSafetyError("Existing Kyoto summary records were removed")
    for rows in current:
        for ident, old in baseline.items():
            new = rows[ident]
            if (old["meeting_id"], old["sequence_number"], old["source_url"]) != (
                    new["meeting_id"], new["sequence_number"], new["source_url"]):
                raise UpdateSafetyError("Downstream changed an existing ID/source mapping")
    if len(current) == 2 and current[0] != current[1]:
        raise UpdateSafetyError("Kyoto aliases diverged downstream")


def generate_and_handoff(script, analyzed, data_dir, scratch, run, baseline):
    script, analyzed, data_dir = Path(script), Path(analyzed), Path(data_dir)
    root = script.resolve().parent.parent
    if not scratch:
        raise UpdateSafetyError("A private scratch outside the checkout is required")
    scratch = Path(scratch).absolute()
    if not scratch.is_dir() or scratch.resolve().is_relative_to(root):
        raise UpdateSafetyError("Scratch must be an existing private directory outside the checkout")
    # Reject junctions/symlinks without opening unrelated data.
    for part in (scratch, *scratch.parents):
        if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise UpdateSafetyError("Reparse scratch is not supported")
    _hash_file(script.absolute())
    source = script.read_bytes()
    normalized = source.replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob " + str(len(normalized)).encode() + b"\0" + normalized).hexdigest()
    if blob != GENERATOR_BLOB:
        raise UpdateSafetyError("Fixed generator hash mismatch")
    input_hash = _hash_file(analyzed.absolute())
    # Retain a private staging directory on failure for diagnosis. No bulk cleanup.
    stage = Path(tempfile.mkdtemp(prefix="kyoto-summary-", dir=scratch))
    pipeline = stage / "data-pipeline"
    pipeline.mkdir()
    staged_script = pipeline / script.name
    staged_script.write_bytes(source)
    staged_input = pipeline / analyzed.name
    shutil.copyfile(analyzed, staged_input)
    if _hash_file(staged_input) != input_hash or _hash_file(analyzed.absolute()) != input_hash:
        raise UpdateSafetyError("Analysis input changed during staging")
    run(str(staged_script))
    candidate = stage / "frontend/public/data/statements_summary.json"
    _hash_file(candidate)
    payload = candidate.read_bytes()
    records = summary_records(payload)
    if not baseline.keys() <= records.keys():
        raise UpdateSafetyError("Candidate loses existing Kyoto IDs")
    for ident, old in baseline.items():
        new = records[ident]
        if (old["meeting_id"], old["sequence_number"], old["source_url"]) != (
                new["meeting_id"], new["sequence_number"], new["source_url"]):
            raise UpdateSafetyError("Existing Kyoto ID/source mapping changed")
    # Caller holds preserve_summary_pair across generation, sync and timeline.
    for name in SUMMARY_NAMES:
        _replace(data_dir / name, payload)
    return records


def check_kyoto_timeline_source(base_dir, crawled):
    # The existing timeline builder prefers SSP cache over Sagebase. Do not mix IDs.
    alternative = Path(base_dir) / "kyoto_raw_statements.json"
    if alternative.exists() and raw_snapshot(alternative) != raw_snapshot(crawled):
        raise UpdateSafetyError("Kyoto SSP/Sagebase timeline input is not identical")
