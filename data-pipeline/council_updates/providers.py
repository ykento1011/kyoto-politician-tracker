"""Provider decoding only. No scraper imports or network operations."""
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()
def digest(value):
    return hashlib.sha256(value).hexdigest()
def config(city):
    values = json.loads(Path(__file__).with_name("cities.json").read_text(encoding="utf-8"))
    return dict(values[city], city=city)
def decode(raw):
    text = raw.decode("utf-8-sig").strip()
    if text.startswith("jQuery"):
        m = re.fullmatch(r"jQuery[A-Za-z0-9_]*\((\{.*\})\);?", text, re.DOTALL)
        if not m:
            raise ValueError("Unrecognized JSONP; never evaluate script")
        text = m[1]
    return json.loads(text)
def positive(value):
    text = str(value)
    if not re.fullmatch("[1-9][0-9]*", text):
        raise ValueError("Explicit provider identifier required")
    return text

def source(bundle, cfg, phase):
    raw, receipt, approval = bundle["raw"], bundle["receipt"], bundle["approval"]
    if type(raw) is not bytes or not 0 < len(raw) <= 2*1024*1024:
        raise ValueError("Saved response is empty or exceeds accepted 2MiB boundary")
    url = "https://ssp.kaigiroku.net/dnp/search/" + (
        "councils/index" if phase == "index" else
        "minutes/get_schedule_all" if phase == "schedules" else "minutes/get_minute")
    limits = receipt["limits"]
    if (limits.get("tls_verify") is not True or limits.get("retries") != 0
            or limits.get("redirects") != 0
            or not re.fullmatch("[0-9a-f]{64}", receipt.get("guard_sha256", ""))
            or approval.get("guard_sha256") != receipt["guard_sha256"]):
        raise ValueError("Successful bound transport receipt required")
    if receipt.get("reference", receipt.get("representative_reference")) != approval.get("reference") or not approval.get("reference"):
        raise ValueError("Receipt/approval reference mismatch")
    if bundle.get("simulated") is not True:
        pins = cfg.get("accepted_receipt_guards", {}).get(phase, [])
        if receipt["guard_sha256"] not in pins or bundle.get("run_id") != approval.get("run_id"):
            raise ValueError("No accepted city-specific saved guard/run binding")
    if phase != "index":
        scope = receipt.get("meeting_scope", {})
        for field in ("council_id", "council_year", "scope"):
            if field not in scope or str(scope[field]) != str(approval.get(field)):
                raise ValueError("Receipt/approval meeting scope mismatch")
        if phase == "minutes" and str(scope.get("schedule_id")) != str(approval.get("schedule_id")):
            raise ValueError("Receipt/approval schedule mismatch")
    tenant = approval.get("post_parameters", {}).get("tenant_id") if phase == "index" else approval.get("tenant_id")
    # Existing Kyoto schedule approvals are tenant-specific via their guard;
    # other cities must explicitly bind tenant_id.
    if tenant is None and phase == "schedules" and cfg["city"] == "kyoto" and approval.get("scope") == "kyoto_reviewed_council_schedules":
        tenant = "355"
    if str(tenant) != cfg["tenant_id"]:
        raise ValueError("Wrong/unbound tenant")
    matches = [a for a in receipt["attempts"] if a.get("method") == "POST"
        and a.get("url") == url and a.get("http_status", a.get("status")) == 200
        and a.get("sha256") == digest(raw)
        and a.get("response_bytes", a.get("bytes")) == len(raw)]
    if len(matches) != 1:
        raise ValueError("Raw bytes must match one successful official response")
    expected = ("council_index_acquired_only",) if phase == "index" else (
        "schedules_acquired_pending_review",) if phase == "schedules" else ("body_acquired_only",)
    if receipt.get("status") not in expected:
        raise ValueError("Partial/failed acquisition is not a normal observation")
    a = matches[0]
    end = datetime.fromisoformat(a["completed_utc"])
    if end.tzinfo is None:
        raise ValueError("Acquisition timestamp must include timezone")
    return decode(raw), dict(url=url, sha256=digest(raw),
        receipt_sha256=digest(encode(receipt)), approval_sha256=digest(encode(approval)),
        acquired_at=a["completed_utc"], path=a.get("raw_file"), phase=phase,
        simulated=bundle.get("simulated") is True)

def ssp_snapshot(cfg, index, schedules, council_id, observed_at, minutes=None):
    if cfg["provider"] != "ssp":
        raise ValueError("Provider adapter not implemented; do not guess")
    cid = positive(council_id)
    catalog, ie = source(index, cfg, "index")
    schedule_data, se = source(schedules, cfg, "schedules")
    if str(schedules["approval"].get("council_id")) != cid:
        raise ValueError("Schedule response belongs to another council")
    rows = []
    seen = set()
    for ci, container in enumerate(catalog["councils"]):
        if "tenant_id" in container and str(container["tenant_id"]) != cfg["tenant_id"]:
            raise ValueError("Response tenant mismatch")
        for yi, y in enumerate(container["view_years"]):
            for ki, kind in enumerate(y["council_type"]):
                for ri, row in enumerate(kind["councils"]):
                    ident = positive(row["council_id"])
                    if ident in seen:
                        raise ValueError("Duplicate council identifier")
                    seen.add(ident)
                    if ident == cid:
                        rows.append((str(y["view_year"]), row["name"],
                            f"/councils/{ci}/view_years/{yi}/council_type/{ki}/councils/{ri}"))
    if len(rows) != 1 or not re.fullmatch("[0-9]{4}", rows[0][0]) or not rows[0][1]:
        raise ValueError("Unique named council and year required")
    year, title, index_position = rows[0]
    if str(schedules["approval"]["council_year"]) != year:
        raise ValueError("Index year and schedule approval disagree")
    if "tenant_id" in catalog and str(catalog["tenant_id"]) != cfg["tenant_id"]:
        raise ValueError("Root tenant mismatch")
    records, held, ids = {}, [], set()
    values = schedule_data["schedules_and_materials"]
    if not isinstance(values, list):
        raise ValueError("Schedule structure changed")
    for i, row in enumerate(values):
        name = row["name"]
        if not isinstance(name, str):
            raise ValueError("Schedule name missing")
        if "資料" in name or "目次" in name:
            continue
        sid = positive(row["schedule_id"])
        if sid in ids:
            raise ValueError("Duplicate schedule ID")
        ids.add(sid)
        m = re.fullmatch(r"\s*(\d{1,2})月(\d{1,2})日[－ー-].+", name)
        if not m:
            held.append(dict(reason="official_date_unknown", schedule_id=sid))
            continue
        day = date(int(year), int(m[1]), int(m[2])).isoformat()
        key = cfg["city"] + ":" + cid + ":" + sid  # Comparison key, never public/person ID.
        records[key] = dict(city=cfg["city"], council_id=cid, schedule_id=sid,
            meeting_date=day, formal_name=title, schedule_name=name, statements=None,
            index_position=index_position,
            source_position="/schedules_and_materials/" + str(i))
    if not records:
        held.append(dict(reason="no_dated_meeting_in_scope"))
    proofs = [ie, se]
    if minutes is not None:
        body, me = source(minutes, cfg, "minutes")
        ap = minutes["approval"]
        key = cfg["city"] + ":" + cid + ":" + positive(ap["schedule_id"])
        if str(ap.get("council_id")) != cid or key not in records:
            raise ValueError("Minute council/schedule mismatch")
        speeches = {}
        for i, block in enumerate(body["tenant_minutes"]):
            ident = positive(block["minute_id"])
            if ident in speeches or not isinstance(block["title"], str) or not isinstance(block["body"], str):
                raise ValueError("Duplicate/malformed original statement")
            speeches[ident] = dict(speaker_raw=block["title"], body_html=block["body"],
                                  source_position="/tenant_minutes/" + str(i), role="unverified")
        records[key]["statements"] = speeches
        proofs.append(me)
    simulated = [b.get("simulated") is True for b in (index, schedules) + ((minutes,) if minutes else ())]
    if any(simulated) and not all(simulated):
        raise ValueError("Synthetic and real evidence must remain separate")
    return dict(city=cfg["city"], provider=cfg["provider"], scope="council:"+cid,
        observed_at=observed_at, records=records, evidence=proofs,
        holds=held, completeness="unknown", origin="synthetic" if all(simulated) else "saved-official-response")

def fixture_snapshot(cfg, records, observed_at, scope="synthetic-scope"):
    """Explicit synthetic input; it can never certify official identity or facts."""
    return dict(city=cfg["city"], provider=cfg["provider"], scope=scope,
        observed_at=observed_at, records=records,
        evidence=[dict(url=cfg["minutes_top"], sha256=digest(encode(records)),
                       source_position="synthetic-fixture", simulated=True)],
        holds=[], completeness="unknown", origin="synthetic")
