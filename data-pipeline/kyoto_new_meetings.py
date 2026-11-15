"""Private, offline intake for ONE reviewed new Kyoto meeting.

Never starts a scraper, analyzer, generator, Git, notification, or publisher.
Existing producers are copied unchanged into a private working directory.
"""
import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit
import uuid

from minutes_update_guard import (
    GENERATOR_BLOB, SUMMARY_NAMES, summary_records, preserve_summary_pair, _replace,
)
from kyoto_private_paths import UpdateSafetyError, _hash_file

PINNED_CODE = {
    "batch_analyze_council.py": "4c9629673c7898bd7bed5485f5b9f1b0daa76fc7",
    "generate_static_data.py": GENERATOR_BLOB,
    "build_timeline_contexts.py": "917af61bad207744da30135134452ff2efe97886",
}
MAX_MEETING_BYTES = 32 * 1024 * 1024
MAX_MEETING_ROWS = 100000


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    _hash_file(Path(path).absolute())
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def meeting_key(url, *, speech=False):
    try:
        u = urlsplit(url)
        q = parse_qs(u.query, strict_parsing=True)
        if (u.scheme != "https" or u.netloc != "ssp.kaigiroku.net"
                or u.path != "/tenant/kyoto/MinuteView.html"
                or set(q) != {"council_id", "schedule_id"}
                or any(len(v) != 1 or not re.fullmatch(r"[1-9][0-9]*", v[0]) for v in q.values())
                or (speech and not re.fullmatch(r"minute_[1-9][0-9]*", u.fragment))):
            raise ValueError()
        return "kyoto:" + q["council_id"][0] + ":" + q["schedule_id"][0]
    except (TypeError, ValueError, AttributeError) as exc:
        raise UpdateSafetyError("Indeterminate: invalid Kyoto official meeting URL") from exc


def validate_ledger(ledger):
    if (ledger.get("schema") != 1 or ledger.get("city") != "kyoto"
            or ledger.get("completeness") != "unknown"):
        raise UpdateSafetyError("Ledger must not infer official completeness")
    observed = set()
    for source in ledger.get("sources", []):
        if (not re.fullmatch("[0-9a-f]{64}", source.get("sha256", ""))
                or not source.get("coverage") or source.get("official_completeness") != "unknown"):
            raise UpdateSafetyError("Missing snapshot hash or explicit coverage")
        for m in source.get("meetings", []):
            if (not re.fullmatch(r"kyoto:[1-9][0-9]*:[1-9][0-9]*", m.get("key", ""))
                    or type(m.get("records")) is not int or m["records"] < 1
                    or date.fromisoformat(m["date_min"]) > date.fromisoformat(m["date_max"])):
                raise UpdateSafetyError("Invalid observed meeting metadata")
            observed.add(m["key"])
    keys = ledger.get("meetings", [])
    if not observed or len(keys) != len(set(keys)) or set(keys) != observed:
        raise UpdateSafetyError("Ledger index does not match its observed sources")
    return observed


def classify(key, ledger):
    known = validate_ledger(ledger)
    if not isinstance(key, str) or not re.fullmatch(r"kyoto:[1-9][0-9]*:[1-9][0-9]*", key):
        raise UpdateSafetyError("Indeterminate: invalid meeting identifier")
    return "existing" if key in known else "candidate_pending_review"


def iter_rows(path, digest):
    """Stream a saved JSON array, buffering one row; never load an old analysis dataset."""
    path = Path(path)
    # This entry accepts the SSP producer output, not the 192 MB analyzed file.
    if path.name != "kyoto_raw_statements.json":
        raise UpdateSafetyError("Only the saved SSP cache input contract is accepted")
    _hash_file(path.absolute())
    decoder = json.JSONDecoder()
    buffer, started, ended, expect_value, count = "", False, False, True, 0
    with path.open("rb") as f:
        import codecs
        utf8 = codecs.getincrementaldecoder("utf-8-sig")()
        while True:
            chunk = f.read(64 * 1024)
            digest.update(chunk)
            buffer += utf8.decode(chunk, final=not chunk)
            while True:
                buffer = buffer.lstrip()
                if not started:
                    if not buffer:
                        break
                    if buffer[0] != "[":
                        raise UpdateSafetyError("SSP input must be an array")
                    started, buffer = True, buffer[1:]
                    continue
                if ended:
                    if buffer:
                        raise UpdateSafetyError("Trailing SSP input")
                    break
                if not buffer:
                    break
                if expect_value:
                    if buffer[0] == "]":
                        if count:
                            raise UpdateSafetyError("Trailing comma")
                        ended, buffer = True, buffer[1:]
                        continue
                    try:
                        row, end = decoder.raw_decode(buffer)
                    except json.JSONDecodeError:
                        break
                    if not isinstance(row, dict):
                        raise UpdateSafetyError("Invalid SSP row")
                    yield row
                    count += 1
                    expect_value, buffer = False, buffer[end:]
                else:
                    if buffer[0] == "]":
                        ended, buffer = True, buffer[1:]
                    elif buffer[0] == ",":
                        expect_value, buffer = True, buffer[1:]
                    else:
                        raise UpdateSafetyError("Invalid SSP separator")
            if len(buffer.encode("utf-8")) > MAX_MEETING_BYTES:
                raise UpdateSafetyError("Oversized or corrupt SSP row")
            if not chunk:
                break
    if not started or not ended or buffer.strip() or not count:
        raise UpdateSafetyError("Incomplete or empty SSP input")


def inspect_cache(cache, ledger, selected=None):
    known = validate_ledger(ledger)
    if Path(cache).name != "kyoto_raw_statements.json":
        raise UpdateSafetyError("Only the saved SSP cache input contract is accepted")
    before = Path(cache).stat()
    digest, groups, seen, ids, selected_rows = hashlib.sha256(), {}, set(), set(), []
    selected_size = 0
    for row in iter_rows(cache, digest):
        key = meeting_key(row.get("official_url"), speech=True)
        c, s = key.split(":")[1:]
        seq = row.get("sequence_number")
        if (row.get("city", "kyoto") != "kyoto" or row.get("city_code", "kyoto") != "kyoto"
                or row.get("meeting_id") != f"ssp_{c}_{s}" or type(seq) is not int or seq < 1
                or urlsplit(row["official_url"]).fragment != f"minute_{seq}"
                or any(not isinstance(row.get(f), str) or not row[f].strip()
                       for f in ("speaker", "statement_text", "meeting_title", "meeting_date"))
                or row.get("source_url", row["official_url"]) != row["official_url"]):
            raise UpdateSafetyError("Indeterminate: missing/conflicting SSP identity or fields")
        date.fromisoformat(row["meeting_date"])
        ident = f"{row['meeting_id']}_{seq}"
        if row.get("id", ident) != ident or (key, seq) in seen or ident in ids:
            raise UpdateSafetyError("Indeterminate: duplicate/conflicting ID or speech position")
        seen.add((key, seq))
        ids.add(ident)
        group = groups.setdefault(key, {"key": key, "records": 0, "date": row["meeting_date"],
                                       "title": row["meeting_title"],
                                       "status": "existing" if key in known else "candidate_pending_review"})
        if (group["date"], group["title"]) != (row["meeting_date"], row["meeting_title"]):
            raise UpdateSafetyError("Conflicting meeting metadata")
        group["records"] += 1
        if key == selected:
            prepared = dict(row, id=ident, source_url=row["official_url"])
            selected_size += len(encode(prepared))
            if selected_size > MAX_MEETING_BYTES or len(selected_rows) >= MAX_MEETING_ROWS:
                raise UpdateSafetyError("Selected meeting exceeds input limits")
            selected_rows.append(prepared)
    after = Path(cache).stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise UpdateSafetyError("SSP input changed during inspection")
    return {"input_sha256": digest.hexdigest(), "ledger_sha256": sha(encode(ledger)),
            "meetings": [{k: v for k, v in g.items() if k != "title"} for g in groups.values()]}, selected_rows


def _private_root(root, public_summary):
    root, public_summary = Path(root).absolute(), Path(public_summary).absolute()
    if not root.is_dir() or root == Path(root.anchor):
        raise UpdateSafetyError("An existing private root is required")
    for part in (root, *root.parents):
        st = part.lstat()
        if (part.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400
                or (part / ".git").exists()):
            raise UpdateSafetyError("Private root cannot be a checkout or reparse path")
    repo = public_summary.parents[3]
    if root.resolve().is_relative_to(repo.resolve()) or repo.resolve().is_relative_to(root.resolve()):
        raise UpdateSafetyError("Private staging must be outside the protected repository")
    return root


@contextmanager
def private_transaction(root):
    temporary = Path(tempfile.mkdtemp(prefix=".incomplete-", dir=root))
    final = root / ("ready-" + uuid.uuid4().hex)
    try:
        yield temporary, final
        os.replace(temporary, final)
    finally:
        if temporary.exists():
            # Only remove this newly allocated, contained staging directory.
            if (temporary.resolve().parent != root.resolve()
                    or not temporary.name.startswith(".incomplete-")
                    or any(p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 0x400
                           for p in [temporary, *temporary.rglob("*")])):
                raise UpdateSafetyError("Unsafe staging cleanup path")
            shutil.rmtree(temporary)


def prepare(cache, ledger, approval, public_summary, code_dir, master_file, private_root):
    root = _private_root(private_root, public_summary)
    key = approval.get("meeting_key")
    if classify(key, ledger) != "candidate_pending_review":
        raise UpdateSafetyError("Existing meetings cannot enter new-meeting analysis")
    report, rows = inspect_cache(cache, ledger, key)
    _hash_file(Path(public_summary).absolute())
    baseline_bytes = Path(public_summary).read_bytes()
    baseline = summary_records(baseline_bytes)
    if not rows or key in {meeting_key(r["source_url"]) for r in baseline.values()}:
        raise UpdateSafetyError("No selected new meeting or meeting already published")
    decision = approval.get("decision")
    retrospective = decision == "approved_retrospective_trial"
    if retrospective:
        fixed_trial = key == "kyoto:6360:1"
        if ((fixed_trial and (len(rows) != 213 or approval.get("original_raw_sha256") !=
                    "c57bc107d835a1c794644ad2cd845cf48dfd2647ed16d42fd4d848b4bd2d3f5b"))
                or (not fixed_trial and approval.get("approved_record_count") != len(rows))
                or not re.fullmatch("[0-9a-f]{64}", approval.get("original_raw_sha256",""))
                or approval.get("official_coverage") != "unknown"
                or approval.get("new_publication_verified") is not False
                or approval.get("retrospective_trial_only") is not True
                or _hash_file(Path(approval["original_raw_path"]).absolute()) != approval["original_raw_sha256"]):
            raise UpdateSafetyError("Retrospective approval must bind the exact source, row count and unknown coverage")
    expected = {"decision": "approved_retrospective_trial" if retrospective else "confirmed_new_meeting", "input_sha256": report["input_sha256"],
                "ledger_sha256": report["ledger_sha256"], "baseline_sha256": sha(baseline_bytes)}
    if any(approval.get(k) != v for k, v in expected.items()) or any(
            not isinstance(approval.get(k), str) or not approval[k].strip()
            for k in (("review_id", "history_gap_review", "retrospective_acceptance") if retrospective
                      else ("review_id", "history_gap_review", "publication_evidence"))):
        raise UpdateSafetyError("Hash-bound PM new-publication and history-gap review required")
    start, end = date.fromisoformat(approval["period_start"]), date.fromisoformat(approval["period_end"])
    if start > end or any(not start <= date.fromisoformat(r["meeting_date"]) <= end for r in rows):
        raise UpdateSafetyError("Unapproved meeting date")
    if set(baseline) & {r["id"] for r in rows}:
        raise UpdateSafetyError("Existing public ID collision")
    source_code = {}
    for name, expected_blob in PINNED_CODE.items():
        path = Path(code_dir) / name
        _hash_file(path.absolute())
        data = path.read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        if hashlib.sha1(b"blob " + str(len(lf)).encode() + b"\0" + lf).hexdigest() != expected_blob:
            raise UpdateSafetyError("Producer code version mismatch")
        source_code[name] = data
    _hash_file(Path(master_file).absolute())
    master_bytes = Path(master_file).read_bytes()
    if approval.get("master_sha256") != sha(master_bytes):
        raise UpdateSafetyError("Approved councilor master hash required")
    master = json.loads(master_bytes.decode("utf-8-sig"))
    if not isinstance(master, list) or not master or any(
            not isinstance(p, dict) or not isinstance(p.get("name"), str) or not p["name"].strip()
            for p in master):
        raise UpdateSafetyError("Invalid existing councilor master")
    with private_transaction(root) as (stage, final):
        pipeline = stage / "data-pipeline"
        pipeline.mkdir()
        for name, data in source_code.items():
            (pipeline / name).write_bytes(data)
        (pipeline / "master").mkdir()
        (pipeline / "master/councilors_kyoto.json").write_bytes(master_bytes)
        # Same SSP payload, compatibility filename only; never the old Sagebase dataset.
        for name in ("sagebase_crawled_data.json", "kyoto_raw_statements.json"):
            (pipeline / name).write_bytes(encode(rows))
        (pipeline / "eval_checkpoint.json").write_bytes(b"{}\n")
        data_dir = stage / "frontend/public/data"
        data_dir.mkdir(parents=True)
        # Existing timeline reader expects a list; derive names from the approved master.
        (data_dir / "speaker_stats.json").write_bytes(encode([{"name": p["name"]} for p in master]))
        manifest = dict(expected, meeting_key=key, review_id=approval["review_id"],
                        trial_mode="retrospective_private" if retrospective else "new_meeting_private",
                        official_coverage=approval.get("official_coverage", "unknown"),
                        new_publication_verified=False if retrospective else None,
                        original_raw_sha256=approval.get("original_raw_sha256"),
                        prepared_rows=len(rows), baseline_records=len(baseline),
                        publication_enabled=False, execution_authorized=False,
                        input_id_policy="existing SSP meeting_id + sequence_number; no legacy ID migration",
                        files={p.relative_to(stage).as_posix(): _hash_file(p)
                               for p in stage.rglob("*") if p.is_file()
                               and p.name != "eval_checkpoint.json"})
        (stage / "manifest.json").write_bytes(encode(manifest))
        (stage / "READY.json").write_bytes(encode({"status": "prepared_only",
                                                  "manifest_sha256": sha(encode(manifest))}))
        if sha(Path(public_summary).read_bytes()) != expected["baseline_sha256"]:
            raise UpdateSafetyError("Public baseline changed during preparation")
    return final


def assemble(prepared, public_summary, private_root):
    root = _private_root(private_root, public_summary)
    prepared = Path(prepared).absolute()
    if prepared.parent.resolve() != root.resolve() or not prepared.name.startswith("ready-"):
        raise UpdateSafetyError("Prepared input must be a committed private stage")
    manifest = read_json(prepared / "manifest.json")
    ready = read_json(prepared / "READY.json")
    if ready != {"status": "prepared_only", "manifest_sha256": sha(encode(manifest))}:
        raise UpdateSafetyError("Uncommitted or modified preparation")
    for name, digest in manifest["files"].items():
        path = prepared / name
        if not path.resolve().is_relative_to(prepared.resolve()) or _hash_file(path) != digest:
            raise UpdateSafetyError("Prepared input/code changed")
    baseline_bytes = Path(public_summary).read_bytes()
    if sha(baseline_bytes) != manifest["baseline_sha256"]:
        raise UpdateSafetyError("Public baseline version changed")
    old = summary_records(baseline_bytes)
    inputs = read_json(prepared / "data-pipeline/kyoto_raw_statements.json")
    indexed = {r["id"]: r for r in inputs}
    addition = summary_records((prepared / "frontend/public/data/statements_summary.json").read_bytes())
    if set(addition) & set(old) or not set(addition) <= set(indexed):
        raise UpdateSafetyError("New summary overlaps or escapes the selected input")
    for ident, row in addition.items():
        original = indexed[ident]
        if any(row[f] != original[f] for f in ("meeting_id", "sequence_number", "source_url", "meeting_date")):
            raise UpdateSafetyError("New summary identity/source mismatch")
    mid = inputs[0]["meeting_id"]
    timeline_dir = prepared / "frontend/public/data/timelines"
    files = list(timeline_dir.iterdir()) if timeline_dir.is_dir() else []
    if len(files) != 1 or files[0].name != mid + ".json" or not files[0].is_file():
        raise UpdateSafetyError("Only the new meeting timeline may be staged")
    if (Path(public_summary).parent / "timelines" / files[0].name).exists():
        raise UpdateSafetyError("Existing timeline cannot be replaced")
    timeline_bytes = files[0].read_bytes()
    timeline = read_json(files[0])
    if not isinstance(timeline, dict) or set(timeline) != {str(r["sequence_number"]) for r in addition.values()}:
        raise UpdateSafetyError("New timeline does not cover exactly the new summary")
    raw_by_seq = {r["sequence_number"]: r for r in inputs}
    for target, context in timeline.items():
        if not isinstance(context, list) or not context:
            raise UpdateSafetyError("Empty timeline context")
        targets, sequences = [], []
        for item in context:
            seq = item.get("sequence_number")
            if (type(seq) is not int or seq not in raw_by_seq
                    or item.get("statement_text") != raw_by_seq[seq]["statement_text"].strip()
                    or item.get("speaker") != raw_by_seq[seq]["speaker"].strip()):
                raise UpdateSafetyError("Timeline context escapes input or changes text")
            sequences.append(seq)
            if item.get("is_target") is True:
                targets.append(seq)
        if targets != [int(target)]:
            raise UpdateSafetyError("Timeline target mismatch")
        if sequences != sorted(set(sequences)):
            raise UpdateSafetyError("Duplicated or unordered timeline context")
    with private_transaction(root) as (stage, final):
        data_dir = stage / "data"
        data_dir.mkdir()
        (data_dir / SUMMARY_NAMES[1]).write_bytes(baseline_bytes)
        with preserve_summary_pair(data_dir):
            merged = encode([*old.values(), *addition.values()])
            for name in SUMMARY_NAMES:
                _replace(data_dir / name, merged)
        (stage / "timeline-additions").mkdir()
        (stage / "timeline-additions" / files[0].name).write_bytes(timeline_bytes)
        (stage / "READY.json").write_bytes(encode({
            "status": "private_append_candidate", "publication_enabled": False,
            "existing_records": len(old), "added_records": len(addition),
            "baseline_sha256": sha(baseline_bytes),
            "timeline_mode": "new-meeting-overlay-only; existing timelines remain untouched",
            "meeting_key": manifest["meeting_key"],
        }))
        if sha(Path(public_summary).read_bytes()) != manifest["baseline_sha256"]:
            raise UpdateSafetyError("Public baseline changed during assembly")
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inspect", "prepare", "assemble"])
    parser.add_argument("--config", required=True, help="Explicit private local configuration JSON")
    args = parser.parse_args()
    config = read_json(args.config)
    if args.operation == "inspect":
        report, _ = inspect_cache(config["cache"], read_json(config["ledger"]))
        print(json.dumps(report, ensure_ascii=False))
    elif args.operation == "prepare":
        path = prepare(config["cache"], read_json(config["ledger"]), read_json(config["approval"]),
                       config["public_summary"], config["code_dir"], config["master_file"], config["private_root"])
        print(path)
    else:
        print(assemble(config["prepared"], config["public_summary"], config["private_root"]))


if __name__ == "__main__":
    try:
        main()
    except (UpdateSafetyError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "indeterminate", "stopped": True, "reason": str(exc)},
                         ensure_ascii=False))
        raise SystemExit(1)
