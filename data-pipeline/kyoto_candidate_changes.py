"""Offline identity recheck policy. This module never authorizes or performs HTTP."""
import hashlib, json, re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import kyoto_meeting_identity as identity
from datetime import date

INDEX_URL = "https://ssp.kaigiroku.net/dnp/search/councils/index"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_index(path):
    # Match the accepted acquisition parser's JSONP grammar. Keep its pinned
    # transport code, raw bytes and receipts unchanged; never evaluate script.
    text = Path(path).read_bytes().decode("utf-8-sig").strip()
    if text.startswith("jQuery"):
        match = re.fullmatch(r"jQuery[A-Za-z0-9_]*\((\{.*\})\);?", text, re.DOTALL)
        if not match:
            raise ValueError("Unexpected JSONP wrapper")
        text = match[1]
    return json.loads(text)

def candidate_key(row):
    # Private observation key, never an SSP/public statement ID.
    if row.get("committee"):
        day = row.get("meeting_date") or "date-unknown@" + row["source_position"]
        return "activity:" + day + ":" + row["committee"] + ":" + str(row["session_number"])
    cid = str(row.get("council_id", ""))
    if not re.fullmatch(r"[1-9][0-9]*", cid):
        raise ValueError("Council candidate requires an existing official identifier")
    return "council:" + cid

def validated_index(evidence):
    path = Path(evidence["path"])
    digest = sha(path)
    if digest != evidence["sha256"] or sha(evidence["receipt_path"]) != evidence["receipt_sha256"]:
        raise ValueError("Index/receipt SHA mismatch")
    receipt = read(evidence["receipt_path"])
    if receipt.get("status") != "council_index_acquired_only":
        raise ValueError("Successful saved council-index receipt required")
    matches = [x for x in receipt["attempts"] if x.get("method") == "POST"
               and x.get("url") == INDEX_URL and x.get("http_status") == 200
               and x.get("sha256") == digest
               and x.get("response_bytes") == path.stat().st_size
               and (Path(evidence["receipt_path"]).parent / x.get("raw_file", "")).resolve() == path.resolve()]
    if len(matches) != 1:
        raise ValueError("Index must be bound to one official successful response")
    catalog(read_index(path))  # Reject malformed/duplicate identifiers.
    return digest

def new_reference(record, evidence):
    """A new official reference allows offline review, not identity certification."""
    if evidence is None:
        return False
    if evidence.get("candidate_key") != record["candidate_key"]:
        raise ValueError("Reference belongs to a different candidate")
    if evidence.get("kind") not in ("official_identifier_reference", "official_direct_mapping"):
        raise ValueError("Activity dates and recordings are not SSP identity evidence")
    parsed = urlparse(evidence.get("source_url", ""))
    if (parsed.scheme != "https" or parsed.hostname not in ("www2.city.kyoto.lg.jp", "ssp.kaigiroku.net")
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("Official HTTPS reference required")
    if parsed.hostname == "ssp.kaigiroku.net" and not parsed.path.startswith("/tenant/kyoto/"):
        raise ValueError("Wrong tenant reference")
    if parsed.hostname == "www2.city.kyoto.lg.jp" and not parsed.path.startswith("/shikai/"):
        raise ValueError("Wrong official source scope")
    actual = sha(evidence["path"])
    if actual != evidence.get("sha256"):
        raise ValueError("Reference SHA mismatch")
    literal = evidence.get("literal")
    if not isinstance(literal, str) or not literal or not evidence.get("source_position"):
        raise ValueError("Saved source position and literal required")
    text = Path(evidence["path"]).read_text(encoding=evidence.get("encoding", "utf-8-sig"))
    if literal not in text:
        raise ValueError("Reference literal absent from original")
    cid, sid = str(evidence.get("council_id", "")), str(evidence.get("schedule_id", ""))
    if not all(re.fullmatch(r"[1-9][0-9]*", x) for x in (cid, sid)):
        raise ValueError("Both identifiers required for reference review")
    if evidence["kind"] == "official_identifier_reference":
        u = urlparse(literal)
        q = parse_qs(u.query)
        if (u.scheme != "https" or u.hostname != "ssp.kaigiroku.net"
                or not u.path.startswith("/tenant/kyoto/")
                or q.get("council_id") != [cid] or q.get("schedule_id") != [sid]):
            raise ValueError("Literal must be an exact Kyoto SSP identifier link")
    elif not evidence.get("review_reference") or not evidence.get("reviewer"):
        raise ValueError("Direct mapping requires an explicit review record")
    return actual not in record.get("checked_reference_sha256", [])

def decision(record, index_sha, reference=None):
    result = dict(allowed=False, action="skip_duplicate_lookup",
                  reason="same_index_no_new_identity_evidence", network_authorized=False)
    if not re.fullmatch(r"[0-9a-f]{64}", index_sha):
        raise ValueError("Validated index SHA required")
    if record is None:
        return dict(result, allowed=True, action="offline_identity_review", reason="not_previously_checked")
    if record.get("manual_resume_only"):
        return dict(result, action="retain_existing_hold", reason="separate_PM_review_required")
    changed = index_sha not in record["checked_index_sha256"]
    fresh_reference = new_reference(record, reference)
    if changed or fresh_reference:
        return dict(result, allowed=True, action="offline_identity_review",
                    reason="new_index" if changed else "new_official_identifier_evidence")
    return result


def catalog(raw):
    result = {}
    for year in raw["councils"][0]["view_years"]:
        for kind in year["council_type"]:
            for item in kind["councils"]:
                cid = str(item["council_id"])
                if cid in result or not re.fullmatch(r"[1-9][0-9]*", cid):
                    raise ValueError("Duplicate/invalid council identifier")
                result[cid] = dict(council_id=cid, year=int(year["view_year"]),
                    source_kind="meeting" if kind["council_type_name1"]=="全会議" else "materials",
                    name=item["name"])
    if not result:
        raise ValueError("Empty official index is not a successful observation")
    return result

def related(row, item):
    if row.get("council_id") is not None:
        return str(row["council_id"]) == item["council_id"]
    when = row.get("meeting_date")
    if not when:
        return False
    day = date.fromisoformat(when)
    m = re.fullmatch(r"令和(\d+)年(\d+)月(.+)\(第(\d+)回\)", identity.norm(item["name"]))
    return bool(m and item["year"]==day.year and
        (int(m[1])+2018,int(m[2]),m[3],int(m[4])) ==
        (day.year,day.month,identity.norm(row.get("committee")),row.get("session_number")))

def reevaluate(previous_evidence, current_evidence, candidates, records, mappings=None):
    """Changed index -> related candidates only. Mapping never certifies a body."""
    oldsha, newsha = validated_index(previous_evidence), validated_index(current_evidence)
    old, new = catalog(read_index(previous_evidence["path"])), catalog(read_index(current_evidence["path"]))
    changed = {k for k in old.keys() | new.keys() if old.get(k) != new.get(k)}
    mappings = mappings or {}
    out, seen = [], set()
    for row in candidates:
        key = candidate_key(row)
        if key in seen:
            raise ValueError("Duplicate candidate observation")
        seen.add(key)
        entry = dict(candidate_key=key, index_sha256=newsha, identifiers_confirmed=False,
                     publication="unknown", network_authorized=False)
        if row.get("source_kind") == "materials":
            out.append(dict(entry, state="excluded_materials")); continue
        day = row.get("meeting_date")
        if day is None:
            out.append(dict(entry, state="held_date_unknown")); continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise ValueError("Invalid official date")
        if date.fromisoformat(day) < date.fromisoformat(identity.TERM_START):
            out.append(dict(entry, state="excluded_before_term")); continue
        if row.get("official_date_confirmed") is not True:
            out.append(dict(entry, state="held_date_unverified")); continue
        items = [x for x in new.values() if related(row,x)]
        if row.get("source_kind") == "materials" or items and all(x["source_kind"]=="materials" for x in items):
            out.append(dict(entry, state="excluded_materials")); continue
        record = records.get(key) or dict(candidate_key=key,checked_index_sha256=[],checked_reference_sha256=[])
        mapping = mappings.get(key)
        ref = mapping["reference"] if mapping else None
        verdict = decision(record,newsha,ref)
        relevant = any(related(row,x) for k in changed for x in (old.get(k),new.get(k)) if x)
        if not verdict["allowed"] or (oldsha != newsha and not relevant and mapping is None):
            out.append(dict(entry,state="skip",reason=verdict["reason"] if not verdict["allowed"] else "unrelated_index_change")); continue
        # A new official mapping is reviewed, never inferred from activity/video or nearby IDs.
        if mapping:
            t = identity.target(mapping["target"])
            if (t["meeting_date"]!=day or identity.norm(t["committee"])!=identity.norm(row.get("committee"))
                    or t["round"]!=row.get("session_number")
                    or ref.get("council_id")!=t["council_id"] or ref.get("schedule_id")!=t["schedule_id"]):
                raise ValueError("Official mapping conflicts with candidate")
            matches=[x for x in items if x["council_id"]==t["council_id"] and identity.norm(x["name"])==identity.norm(t["formal_name"])]
            if len(matches)!=1 or matches[0]["source_kind"]!="meeting":
                raise ValueError("Mapping not corroborated by official index")
            out.append(dict(entry,state="identity_review_candidate",target=t))
        else:
            out.append(dict(entry,state="held_schedule_unknown",related_council_ids=[x["council_id"] for x in items]))
    return dict(previous_index_sha256=oldsha,current_index_sha256=newsha,
                changed_council_ids=sorted(changed),candidates=out,network_authorized=False)
