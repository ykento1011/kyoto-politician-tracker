"""Single-use council 6360 acquisition. Reuses the accepted HTTPS transport.
No acquisition on import; never invokes a scraper/analyzer/updater.
"""
import argparse
import base64
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata

import kyoto_council_list_guard as transport

Stop = transport.Stop
ROOT = transport.ARTIFACT
STORAGE = ROOT / "new-meeting-evidence/council-6360-trials"
LEDGER = transport.LEDGER
LEDGER_SHA = transport.LEDGER_SHA
TRANSPORT_SHA = "bfa292dd7577bd81eb7c1061ec563f7981ec6a349ca7b254ec85f5163ace5ff7"
SCHEDULE = "https://ssp.kaigiroku.net/dnp/search/minutes/get_schedule_all"
MINUTE = "https://ssp.kaigiroku.net/dnp/search/minutes/get_minute"
ALLOWED = [("GET", transport.TOP), ("POST", SCHEDULE), ("POST", MINUTE)]
LIMITS = dict(transport.LIMITS, http_attempts=3)
COMMON = b"tenant_id=355&power_user=false&council_id=6360"
COUNCIL = "6360"
TARGET_SCHEDULE = None
TARGET_DATE = "2026-03-12"
SCHEDULES_ONLY = False


def configure(approval):
    """Exact one-meeting policy, never a crawler-wide setting."""
    global COUNCIL, TARGET_SCHEDULE, TARGET_DATE, COMMON, SCHEDULES_ONLY
    SCHEDULES_ONLY = approval.get("scope") == "kyoto_reviewed_council_schedules"
    if approval.get("scope") in ("kyoto_one_reviewed_meeting","kyoto_reviewed_council_schedules"):
        COUNCIL = ident(approval.get("council_id"))
        TARGET_SCHEDULE = None if SCHEDULES_ONLY else ident(approval.get("schedule_id"))
        if SCHEDULES_ONLY:
            year=approval.get("council_year")
            if type(year) is not int or not 2000<=year<=2099:raise Stop("Reviewed council year required")
            TARGET_DATE=date(year,1,1).isoformat() # Year context only; no inferred meeting date.
        else:
            TARGET_DATE = date.fromisoformat(approval.get("meeting_date","")).isoformat()
        if not approval.get("candidate_review"):
            raise Stop("Missing reviewed candidate reference")
    elif approval.get("scope") == "kyoto_council_6360_one_schedule":
        COUNCIL, TARGET_SCHEDULE, TARGET_DATE = "6360", None, "2026-03-12"
    else:
        raise Stop("Unsupported meeting scope")
    COMMON = b"tenant_id=355&power_user=false&council_id=" + COUNCIL.encode("ascii")


def ident(value):
    if type(value) not in (str, int) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise Stop("Missing/invalid identifier")
    return str(value)


def decode(body, media):
    if media.split(";")[0].strip().lower() not in {
            "application/json", "text/json", "application/javascript", "text/javascript"}:
        raise Stop("Unexpected JSON media type")
    text = body.decode("utf-8-sig").strip()
    if text.startswith("jQuery"):
        match = re.fullmatch(r"jQuery[A-Za-z0-9_]*\((\{.*\})\);?", text, re.DOTALL)
        if not match:
            raise Stop("Invalid JSONP wrapper")
        text = match[1]
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise Stop("Duplicate JSON field")
            obj[key] = value
        return obj
    data = json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(Stop("Nonfinite JSON")))
    if not isinstance(data, dict):
        raise Stop("Response root is not an object")
    check_scope(data)
    for field in ("error", "errors"):
        if data.get(field):
            raise Stop("API error response")
    for field in ("has_more", "has_next", "next_page", "next"):
        if data.get(field):
            raise Stop("Pagination/continuation requires an unapproved request")
    return data


def check_scope(obj, schedule_id=None):
    for field, expected in (("tenant_id", "355"), ("council_id", COUNCIL)):
        if field in obj and ident(obj[field]) != expected:
            raise Stop("Response scope mismatch")
    if schedule_id is not None and "schedule_id" in obj and ident(obj["schedule_id"]) != schedule_id:
        raise Stop("Response schedule mismatch")


def schedule_candidates(body, media, ledger):
    data = decode(body, media)
    items = data.get("schedules_and_materials")
    if not isinstance(items, list):
        raise Stop("Missing schedule array")
    eligible, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise Stop("Invalid schedule object")
        check_scope(item)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise Stop("Missing schedule title")
        if any(word in name for word in ("目次", "資料")):
            continue
        sid = ident(item.get("schedule_id"))
        if sid in seen:
            raise Stop("Duplicate schedule identifier")
        seen.add(sid)
        norm = unicodedata.normalize("NFKC", name)
        years = re.findall(r"(20[0-9]{2})\s*年", norm)
        eras = re.findall(r"令和\s*([0-9]+)\s*年", norm)
        expected_year = date.fromisoformat(TARGET_DATE).year
        if any(y != str(expected_year) for y in years) or any(int(y)+2018 != expected_year for y in eras):
            raise Stop("Schedule year contradicts selected council")
        matches = re.findall(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", norm)
        if len(matches) != 1:
            raise Stop("Exact meeting date is not identifiable")
        month, day = map(int, matches[0])
        when = date(expected_year, month, day).isoformat()
        key = "kyoto:" + COUNCIL + ":" + sid
        eligible.append({"schedule_id": sid, "name": name, "meeting_date": when,
                         "meeting_key": key})
    return eligible


def select_schedule(body, media, ledger):
    eligible=schedule_candidates(body, media, ledger)
    if TARGET_SCHEDULE is not None:
        eligible=[s for s in eligible if s["schedule_id"]==TARGET_SCHEDULE]
    if len(eligible) != 1:
        raise Stop("Expected exactly one eligible schedule", {"eligible_schedules": len(eligible)})
    selected = eligible[0]
    if selected["meeting_date"] != TARGET_DATE:
        raise Stop("Selected date differs from reviewed candidate")
    if selected["meeting_key"] in ledger["meetings"]:
        raise Stop("Selected meeting is already in frozen history")
    return selected


def validate_minutes(body, media, selected):
    data = decode(body, media)
    check_scope(data, selected["schedule_id"])
    blocks = data.get("tenant_minutes")
    if not isinstance(blocks, list) or not blocks:
        raise Stop("Missing/empty minute blocks; not a successful meeting acquisition")
    seen = set()
    for block in blocks:
        if not isinstance(block, dict):
            raise Stop("Invalid minute block")
        check_scope(block, selected["schedule_id"])
        mid = ident(block.get("minute_id"))
        if mid in seen:
            raise Stop("Duplicate minute identifier")
        seen.add(mid)
        if any(not isinstance(block.get(k), str) for k in ("title", "body")):
            raise Stop("Minute block missing title/body")
    for field in ("total", "total_count", "minute_count", "total_minutes"):
        if field in data and (type(data[field]) is not int or data[field] != len(blocks)):
            raise Stop("Declared minute count mismatch")
    return {"meeting_key": selected["meeting_key"], "meeting_date": selected["meeting_date"],
            "raw_blocks": len(blocks), "unique_minute_ids": len(seen),
            "official_meeting_url": "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?"
                                    "council_id=" + COUNCIL + "&schedule_id=" + selected["schedule_id"],
            "transport_complete": True, "official_coverage": "unknown",
            "history_status": "absent_from_frozen_ledger",
            "new_publication_verified": False, "analysis_authorized": False,
            "source_position": "tenant_minutes[] / minute_id"}


def contract(method, url, sid=None):
    if (method, url) not in ALLOWED:
        raise Stop("Exact method/URL is outside this trial")
    if SCHEDULES_ONLY and url == MINUTE:
        raise Stop("Schedules-only scope prohibits minute acquisition")
    if url == transport.TOP:
        return None
    if url == SCHEDULE:
        return COMMON
    return COMMON + b"&schedule_id=" + ident(sid).encode("ascii")


def validate_approval(path):
    approval = json.loads(transport.safe_path(path).read_text(encoding="utf-8"))
    configure(approval)
    checks = {"pm_go": True,
              "limits": dict(LIMITS,http_attempts=2 if SCHEDULES_ONLY else 3), "ledger_sha256": LEDGER_SHA,
              "transport_sha256": TRANSPORT_SHA,
              "guard_sha256": transport.digest(Path(__file__).read_bytes())}
    if any(approval.get(k) != v for k, v in checks.items()):
        raise Stop("PM scope, limits, or code hash mismatch")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", approval.get("run_id", "")):
        raise Stop("Invalid run ID")
    if not approval.get("reference"):
        raise Stop("Missing PM reference")
    if transport.digest(LEDGER.read_bytes()) != LEDGER_SHA:
        raise Stop("Frozen ledger changed")
    if transport.digest(Path(transport.__file__).read_bytes()) != TRANSPORT_SHA:
        raise Stop("Accepted transport changed")
    return approval


def isolated_request(method, url, cookies, trial, slot, sid):
    contract(method, url, sid)
    payload = dict(method=method, url=url, cookies=cookies, trial=str(trial), slot=slot, sid=sid)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=flags)
    try:
        out, err = child.communicate(transport.json_bytes(payload), timeout=25)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()
        raise Stop("25-second communication deadline; no retry")
    try:
        result = json.loads(out)
    except (ValueError, UnicodeError):
        raise Stop("Incomplete worker result; no retry")
    if "error" in result or child.returncode:
        raise Stop(result.get("error", "Worker failed"), result.get("details"))
    return result


def acquire(path):
    approval = validate_approval(path)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if len(ledger.get("meetings", [])) != 750 or ledger.get("completeness") != "unknown":
        raise Stop("Unexpected frozen history structure")
    transport.safe_path(STORAGE).mkdir(parents=True, exist_ok=True)
    trial = STORAGE / approval["run_id"]
    trial.mkdir(exist_ok=False)  # Durable consumption of this run ID, even on failure.
    receipt = dict(status="in_progress", started_utc=transport.utc(), limits=approval["limits"],
                   meeting_scope={k:approval[k] for k in
                       ("scope","council_id","schedule_id","meeting_date","council_year","candidate_review") if k in approval},
                   guard_sha256=approval["guard_sha256"], transport_sha256=TRANSPORT_SHA,
                   ledger_sha256=LEDGER_SHA, reference=approval["reference"],
                   selected_schedule=None, attempts=[], gemini_calls=0, public_writes=False)
    transport.write_json(trial / "receipt.json", receipt)
    cookies, last, selected = [], None, None
    try:
        for slot, (method, url) in enumerate(ALLOWED[:approval["limits"]["http_attempts"]], 1):
            sid = selected["schedule_id"] if selected else None
            if last is not None:
                time.sleep(max(0, last + transport.INTERVAL - time.monotonic()))
            attempt = dict(slot=slot, method=method, url=url, reserved_utc=transport.utc())
            receipt["attempts"].append(attempt)
            transport.write_json(trial / "receipt.json", receipt)
            transport.write_json(trial / f"slot-{slot}.authorized",
                                 dict(method=method, url=url, sid=sid))
            result = isolated_request(method, url, cookies, trial, slot, sid)
            last = time.monotonic()
            body = base64.b64decode(result["body_b64"], validate=True)
            if len(body) > transport.MAX_BYTES or len(body) != result["bytes"]:
                raise Stop("Response size mismatch")
            filename = ("01-session.html", "02-schedules.json", "03-minutes.json")[slot - 1]
            (trial / filename).write_bytes(body)
            attempt.update({k: result[k] for k in ("started_utc", "completed_utc", "status", "content_type")})
            attempt.update(raw_file=filename, bytes=len(body), sha256=transport.digest(body))
            transport.write_json(trial / "receipt.json", receipt)
            if result["status"] != 200:
                raise Stop("Non-200 status; no redirect or retry")
            if slot == 1:
                transport.validate_session(body, result["content_type"])
            elif slot == 2:
                if SCHEDULES_ONLY:
                    receipt["schedule_candidates"] = [
                        dict(s,history_status="in_saved_history" if s["meeting_key"] in ledger["meetings"]
                             else "absent_from_saved_history",new_publication_verified=False)
                        for s in schedule_candidates(body,result["content_type"],ledger)]
                    if not receipt["schedule_candidates"]: raise Stop("Empty schedule list")
                else:
                    selected = select_schedule(body, result["content_type"], ledger)
                    receipt["selected_schedule"] = selected
                transport.write_json(trial / "receipt.json", receipt)
            else:
                report = validate_minutes(body, result["content_type"], selected)
                transport.write_json(trial / "meeting-receipt.json", report)
            cookies = result["cookies"]
        if transport.digest(LEDGER.read_bytes()) != LEDGER_SHA:
            raise Stop("Frozen ledger changed during trial")
        receipt["status"] = ("schedules_acquired_pending_review" if SCHEDULES_ONLY else
                             "raw_acquired_pending_offline_reconciliation")
    except BaseException as exc:
        receipt["status"] = "stopped"
        receipt["failure"] = type(exc).__name__ + ": " + str(exc)
        if isinstance(exc, Stop):
            receipt["failure_details"] = exc.details
        raise
    finally:
        receipt["finished_utc"] = transport.utc()
        receipt["http_attempt_slots_consumed"] = len(receipt["attempts"])
        transport.write_json(trial / "receipt.json", receipt)
    return trial


def worker():
    p = json.load(sys.stdin)
    slot = p["slot"]
    if type(slot) is not int or slot not in (1, 2, 3) or (p["method"], p["url"]) != ALLOWED[slot - 1]:
        raise Stop("Invalid worker slot")
    trial = transport.safe_path(p["trial"])
    if trial.parent.resolve() != STORAGE.resolve() or not trial.is_dir():
        raise Stop("Worker storage outside approved root")
    r = json.loads((trial / "receipt.json").read_text(encoding="utf-8"))
    configure(r["meeting_scope"])
    if slot > r["limits"]["http_attempts"]:
        raise Stop("Worker exceeds approved communication count")
    if transport.digest(LEDGER.read_bytes()) != LEDGER_SHA:
        raise Stop("Frozen ledger changed before communication")
    auth = json.loads((trial / f"slot-{slot}.authorized").read_text(encoding="utf-8"))
    if (r["status"] != "in_progress" or len(r["attempts"]) != slot
            or r["guard_sha256"] != transport.digest(Path(__file__).read_bytes())
            or r["transport_sha256"] != transport.digest(Path(transport.__file__).read_bytes())
            or auth != dict(method=p["method"], url=p["url"], sid=p["sid"])):
        raise Stop("Worker authorization mismatch")
    if slot == 3:
        prior = r["attempts"][1]
        raw = (trial / "02-schedules.json").read_bytes()
        if transport.digest(raw) != prior["sha256"]:
            raise Stop("Saved schedule changed")
        selected = select_schedule(raw, prior["content_type"],
                                   json.loads(LEDGER.read_text(encoding="utf-8")))
        if selected != r["selected_schedule"] or p["sid"] != selected["schedule_id"]:
            raise Stop("Unvalidated schedule")
    with (trial / f"slot-{slot}.used").open("xb") as f:
        f.write(b"consumed")
    # Only the in-memory request-body validator is specialized; accepted TLS/
    # cookie/response-size transport remains byte-for-byte unchanged on disk.
    transport.request_contract = lambda m, u: contract(m, u, p["sid"])
    print(json.dumps(transport._https_once(p["method"], p["url"], p["cookies"])))


if __name__ == "__main__":
    if sys.argv[1:] == ["--worker"]:
        try:
            worker()
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__ + ": " + str(exc),
                              "details": exc.details if isinstance(exc, Stop) else {}}))
            raise SystemExit(1)
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--approval", required=True)
        args = parser.parse_args()
        try:
            print(acquire(args.approval))
        except Exception as exc:
            print("STOP: " + type(exc).__name__ + ": " + str(exc))
            raise SystemExit(1)
