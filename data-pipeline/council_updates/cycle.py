"""City-neutral offline observation transaction; never acquires or publishes."""
import copy
import json
import os
import re
import uuid
from datetime import datetime, date
from pathlib import Path
from kyoto_private_paths import _hash_file, UpdateSafetyError
from nagoya_article_review import _private
from .providers import config, digest, encode, ssp_snapshot

def initial(city, scope):
    config(city)
    return dict(schema=1, city=city, scope=scope, baseline=None, last_good=None,
                processed={}, reviews=[], observations=[], weeks=[])

def validate(snapshot, week):
    cfg = config(snapshot["city"])
    when = datetime.fromisoformat(snapshot["observed_at"])
    if when.tzinfo is None or not re.fullmatch(r"\d{4}-W\d{2}", week):
        raise ValueError("Explicit observation timestamp and ISO week required")
    iso = when.isocalendar()
    if week != f"{iso.year}-W{iso.week:02d}":
        raise ValueError("Week does not match observation")
    if snapshot["provider"] != cfg["provider"] or not snapshot["scope"] or not isinstance(snapshot["records"], dict):
        raise ValueError("Provider/scope/records mismatch")
    if snapshot.get("origin") not in ("synthetic", "saved-official-response"):
        raise ValueError("Unknown input origin")
    for e in snapshot["evidence"]:
        if not re.fullmatch("[0-9a-f]{64}", e["sha256"]) or not e["url"].startswith("https://"):
            raise ValueError("Explicit source SHA and HTTPS locator required")
    if not snapshot["evidence"]:
        raise ValueError("Source proof missing")
    records, excluded = {}, []
    for key, row in snapshot["records"].items():
        if (row.get("city") != snapshot["city"]
                or key != ":".join([snapshot["city"], row["council_id"], row["schedule_id"]])
                or not row.get("formal_name") or not row.get("schedule_name")
                or not row.get("source_position")):
            raise ValueError("City/meeting identity/name/position mismatch")
        day = date.fromisoformat(row["meeting_date"])
        if cfg["term_start"] and day < date.fromisoformat(cfg["term_start"]):
            excluded.append(key)
            continue
        speeches = row["statements"]
        if speeches is not None:
            if not isinstance(speeches, dict):
                raise ValueError("Invalid statement collection")
            for sid, speech in speeches.items():
                if (not re.fullmatch("[1-9][0-9]*", sid)
                        or not isinstance(speech.get("speaker_raw"), str)
                        or not isinstance(speech.get("body_html"), str)
                        or not speech.get("source_position")):
                    raise ValueError("Missing statement identity/body/provenance")
        records[key] = copy.deepcopy(row)
    return cfg, records, excluded

def cycle(state, snapshot, week):
    cfg, records, excluded = validate(snapshot, week)
    if (state["city"], state["scope"]) != (snapshot["city"], snapshot["scope"]):
        raise ValueError("Another city/scope cannot replace a baseline")
    if week in state["weeks"]:
        raise ValueError("Same-week duplicate observation rejected")
    if state["observations"] and datetime.fromisoformat(snapshot["observed_at"]) < datetime.fromisoformat(state["observations"][-1]["observed_at"]):
        raise ValueError("Observation clock moved backwards")
    version = digest(encode([snapshot["city"], snapshot["scope"],
                            [e["sha256"] for e in snapshot["evidence"]]]))
    signature = digest(encode([records, snapshot["holds"], excluded, snapshot["origin"]]))
    out = copy.deepcopy(state)
    out["weeks"].append(week)
    entries = []
    reasons = list(snapshot["holds"])
    if cfg["term_start"] is None:
        reasons.append(dict(reason="official_term_unconfirmed"))
    old = state["last_good"]
    if old is not None:
        for key in sorted(old.keys()-records.keys()):
            reasons.append(dict(reason="meeting_missing_or_deleted", meeting_key=key))
        for key in sorted(old.keys() & records.keys()):
            before, after = old[key], records[key]
            if before == after:
                continue
            metadata = [k for k in before.keys() | after.keys()
                        if k != "statements" and before.get(k) != after.get(k)]
            if metadata:
                reasons.append(dict(reason="meeting_metadata_changed", meeting_key=key, fields=metadata))
            a, b = before["statements"], after["statements"]
            if a != b:
                if a is not None and b is not None:
                    reasons.append(dict(reason="existing_statements_changed", meeting_key=key,
                        removed=sorted(a.keys()-b.keys()), added=sorted(b.keys()-a.keys()),
                        changed=sorted(k for k in a.keys() & b.keys() if a[k] != b[k])))
                else:
                    reasons.append(dict(reason="existing_meeting_correction_or_supplement", meeting_key=key))
    if version in state["processed"]:
        if state["processed"][version] != signature:
            raise ValueError("Same source version cannot change interpretation")
        status = "same-version-HOLD" if reasons else "same-version"
        # No second source review, but never call a rollback a clean observation.
    else:
        out["processed"][version] = signature
        if reasons:
            status = "HOLD"
            entries = [dict(kind="HOLD", detail=r) for r in reasons]
        elif state["baseline"] is None:
            out["baseline"] = dict(records=copy.deepcopy(records), version=version)
            out["last_good"] = records
            status = "baseline-only"
        else:
            status = "review-ready"
            entries = [dict(kind="new-meeting-candidate", meeting_key=k,
                            identity="unverified", publication_authorized=False)
                       for k in sorted(records.keys()-old.keys())]
            out["last_good"] = records  # Normal observation, not accepted facts.
        for item in entries:
            item.update(source_version=version, evidence=copy.deepcopy(snapshot["evidence"]),
                        scope=state["scope"], observed_at=snapshot["observed_at"],
                        status="hold", reason_reference="independent review required")
            item["review_id"] = digest(encode(item))
            out["reviews"].append(item)
    result = dict(week=week, observed_at=snapshot["observed_at"], status=status,
                  source_version=version, new_reviews=len(entries), excluded_term=excluded,
                  source_complete="unknown", published=False, origin=snapshot["origin"],
                  hold_reasons=copy.deepcopy(reasons), evidence=copy.deepcopy(snapshot["evidence"]))
    out["observations"].append(result)
    return out, result

def stage(root, expected_sha, snapshot, week):
    """New isolated state/journal only. Never opens original CAS for writing."""
    config(snapshot["city"])
    if not re.fullmatch(r"\d{4}-W\d{2}", week):
        raise ValueError("Invalid week path")
    root = _private(root)
    root.mkdir(parents=True, exist_ok=True)
    normal = root/"normal.json"
    marker = root/(snapshot["city"]+"-"+week+".attempt.json")
    for p in (normal, marker, root/"cycle.lock"):
        _private(p)
    with (root/"cycle.lock").open("x") as lock:
        try:
            current = _hash_file(normal.absolute()) if normal.exists() else None
            if current != expected_sha:
                raise ValueError("Last-good state changed")
            state = json.loads(normal.read_bytes()) if current else initial(snapshot["city"], snapshot["scope"])
            # Failure consumes this week's slot too. No automatic retry.
            with marker.open("x", encoding="utf-8") as f:
                json.dump(dict(week=week, status="reserved", official_HTTP=0), f)
            try:
                if "ssp_inputs" in snapshot:
                    args = snapshot["ssp_inputs"]
                    snapshot = ssp_snapshot(config(snapshot["city"]), args["index"],
                        args["schedules"], args["council_id"], snapshot["observed_at"],
                        minutes=args.get("minutes"))
                out, result = cycle(state, snapshot, week)
                data = encode(out)
                temp = root/("cycle-"+uuid.uuid4().hex+".tmp")
                with temp.open("xb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                if temp.read_bytes() != data:
                    raise ValueError("Stage readback failed")
                os.replace(temp, normal)
            except Exception as exc:
                # Original last-good/head is never truncated. Incomplete journal
                # and orphan temp are retained; PM decides restart scope.
                failed = root/(marker.name+".failure.json")
                with failed.open("x", encoding="utf-8") as f:
                    json.dump(dict(status="failed", error=type(exc).__name__+": "+str(exc),
                                   prior_normal_sha=current, official_HTTP=0), f)
                raise
            return out, result, digest(data)
        finally:
            lock.close()
            (root/"cycle.lock").unlink()
