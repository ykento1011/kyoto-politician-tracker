"""Offline, append-only member evidence and meeting-date lookup.

No HTTP, model, scheduler or public-data interface. Observations are never
effective changes. Only explicit hash-bound reviewed intervals inform speakers.
"""
import copy
import hashlib
import json
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from kyoto_private_paths import private_storage
from nagoya_roster_evidence import name_key, Tree

DOMAINS = {"membership", "group", "role", "alias"}
END_REASONS = {"resignation", "retirement", "loss_of_seat", "death", "term_end"}
START_REASONS = {"election", "by_election", "confirmed_in_office"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Explicit ISO date required")
    return date.fromisoformat(value)


def observed(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo is None:
        raise ValueError("Observation timestamp needs timezone")
    return d


def evidence(raw, receipt):
    """Reuse an existing successful receipt; never acquire or invent one."""
    u = urlsplit(receipt["url"])
    if (u.scheme != "https" or u.hostname != "www.city.nagoya.jp" or u.port not in (None, 443)
            or u.username or u.password or u.fragment or receipt.get("http_status") != 200
            or receipt.get("status") != "success" or receipt.get("method") != "GET"
            or receipt.get("bytes") != len(raw) or receipt.get("sha256") != digest(raw)):
        raise ValueError("Official source/receipt binding mismatch")
    observed(receipt["completed_utc"])
    return dict(sha256=digest(raw), url=receipt["url"], observed_at=receipt["completed_utc"],
                text=raw.decode("utf-8-sig"))


def position(ev, pos):
    # Literal and position are review evidence, not an automatic semantic verdict.
    nodes = [n for n in Tree(ev["text"].encode("utf-8")).nodes if n.path() == pos.get("dom")]
    if (len(nodes) != 1 or type(pos.get("line")) is not int or nodes[0].line != pos["line"]
            or not pos.get("literal") or name_key(pos["literal"]) not in name_key(nodes[0].text())):
        raise ValueError("Source position/literal absent")
    return copy.deepcopy(pos)


def seed_registry(persons, master_sha):
    """Caller assigns persistent local IDs once. Never derive IDs from new names."""
    if not re.fullmatch("[0-9a-f]{64}", master_sha):
        raise ValueError("Seed master SHA required")
    ids = [p["person_id"] for p in persons]
    if not persons or len(set(ids)) != len(ids) or any(not re.fullmatch(r"nagoya:[A-Za-z0-9:_-]+", i) for i in ids):
        raise ValueError("Unique explicit Nagoya person IDs required")
    if any(not p.get("seed_name") or not p.get("seed_district") for p in persons):
        raise ValueError("Seed name/district required; seed does not confirm tenure")
    return dict(schema=1, city="nagoya", seed_master_sha256=master_sha,
                persons=copy.deepcopy(persons), observations=[], reviews=[], facts=[], failures=[])


def candidate_person(state, row, when=None):
    candidates = []
    for p in state["persons"]:
        names = {name_key(p["seed_name"])}
        if when:
            slots = {f["scope"] for f in state["facts"] if f["person_id"] == p["person_id"] and f["domain"] == "alias"}
            for slot in slots:
                a = at_date(state, p["person_id"], when, "alias", slot)
                if a["status"] == "confirmed":
                    names.add(name_key(a["value"]))
        if name_key(row["name"]) in names and (row.get("district") is None or p["seed_district"] == row["district"]):
            candidates.append(p["person_id"])
    return candidates[0] if len(candidates) == 1 else None


def register_person(state, person, ev, review):
    """Explicit onboarding for a replacement/new member; no automatic name merge."""
    if (review.get("decision") != "confirmed" or not review.get("reviewer")
            or not review.get("review_reference") or review.get("source_sha256") != ev["sha256"]):
        raise ValueError("New identity requires official evidence and explicit review")
    seed_registry([person], state["seed_master_sha256"])
    if person["person_id"] in {p["person_id"] for p in state["persons"]}:
        raise ValueError("Person ID already assigned; never replace a person")
    row = copy.deepcopy(person)
    row["identity_review"] = dict(review, position=position(ev, review["position"]),
                                  observed_at=ev["observed_at"], source_url=ev["url"])
    new = copy.deepcopy(state)
    new["persons"].append(row)
    return new


def add_observation(state, ev, rows, document_date, covered_fields):
    """Unknown/missing identities become review holds, never new person IDs."""
    if day(document_date) > observed(ev["observed_at"]).date():
        raise ValueError("Future document date")
    if not rows or not {"name", "group"} <= set(covered_fields):
        raise ValueError("Missing roster/required fields")
    if any(o["source_sha256"] == ev["sha256"] for o in state["observations"]):
        return copy.deepcopy(state)  # Same original never emits another review.
    normalized = []
    for row in rows:
        pos = position(ev, row["position"])
        normalized.append(dict(person_id=candidate_person(state, row, document_date), name=row["name"],
            district=row.get("district"), group=row.get("group"), roles=row.get("roles"),
            position=pos, identity_status="candidate_only"))
    assigned = [r["person_id"] for r in normalized if r["person_id"] is not None]
    if len(set(assigned)) != len(assigned):
        raise ValueError("Duplicate person mapping; hold the snapshot")
    new = copy.deepcopy(state)
    obs = dict(source_sha256=ev["sha256"], source_url=ev["url"],
        observed_at=ev["observed_at"], document_date=document_date,
        covered_fields=sorted(covered_fields), rows=normalized)
    prior = state["observations"][-1] if state["observations"] else None
    changes = []
    if prior:
        old = {r["person_id"]: r for r in prior["rows"] if r["person_id"]}
        now = {r["person_id"]: r for r in normalized if r["person_id"]}
        for pid in sorted(old.keys() | now.keys()):
            if pid not in now or pid not in old:
                changes.append(dict(person_id=pid, field="roster_presence",
                    before=pid in old, after=pid in now, status="hold",
                    reason="presence alone does not prove resignation or election"))
                continue
            for field in set(prior["covered_fields"]) & set(covered_fields):
                if old[pid].get(field) != now[pid].get(field):
                    changes.append(dict(person_id=pid, field=field,
                        before=old[pid].get(field), after=now[pid].get(field), status="hold",
                        reason="effective date and identity require official review"))
    for row in normalized:
        if row["person_id"] is None:
            changes.append(dict(person_id=None, field="identity", name=row["name"], status="hold",
                                reason="unknown, variant or homonymous identity"))
    if changes:
        review = dict(previous_sha256=prior["source_sha256"] if prior else None,
                      source_sha256=ev["sha256"], changes=changes,
                      decision="pending", effective_on=None)
        review["review_id"] = digest(encode(review))
        if not any(x["review_id"] == review["review_id"] for x in new["reviews"]):
            new["reviews"].append(review)
    new["observations"].append(obs)
    return new


def record_failure(state, source_url, when, reason):
    observed(when)
    if not reason:
        raise ValueError("Failure reason required")
    new = copy.deepcopy(state)
    new["failures"].append(dict(source_url=source_url, observed_at=when, reason=reason))
    return new  # Prior normal observation and all accepted facts remain intact.


def add_reviewed_fact(state, ev, fact):
    """Append a human-reviewed bounded interval/event. No roster auto-promotion."""
    if fact.get("person_id") not in {p["person_id"] for p in state["persons"]}:
        raise ValueError("Unknown person; explicit registry onboarding required")
    if (fact.get("domain") not in DOMAINS or fact.get("decision") != "confirmed"
            or not fact.get("reviewer") or not fact.get("review_reference")
            or fact.get("source_sha256") != ev["sha256"]):
        raise ValueError("Explicit identity/meaning review and source SHA required")
    start, through = day(fact.get("effective_on")), day(fact.get("confirmed_through"))
    if not start <= through <= observed(ev["observed_at"]).date():
        raise ValueError("Unknown/reversed/unobserved coverage")
    if fact.get("domain") == "membership":
        if (fact.get("value") not in ("member", "not_member")
                or fact.get("scope") != "city_council"
                or fact.get("reason") not in (START_REASONS if fact["value"] == "member" else END_REASONS)):
            raise ValueError("Council membership needs explicit membership evidence")
    elif fact["domain"] == "role":
        if fact.get("scope") in (None, "", "city_council") or fact.get("value") not in ("held", "ended") or not fact.get("title"):
            raise ValueError("Role requires a distinct committee/chamber/faction/union scope")
    elif fact["domain"] == "alias":
        if not fact.get("value") or not re.fullmatch(r"name:[A-Za-z0-9_-]+", fact.get("scope", "")):
            raise ValueError("Dated alias needs a stable name slot")
    elif not fact.get("value") or fact.get("scope") != "city_council":
        raise ValueError("Alias/group assertion missing")
    stored = copy.deepcopy(fact)
    stored["position"] = position(ev, fact["position"])
    stored.update(source_url=ev["url"], observed_at=ev["observed_at"])
    stored["fact_id"] = digest(encode(stored))
    new = copy.deepcopy(state)
    if not any(x["fact_id"] == stored["fact_id"] for x in new["facts"]):
        new["facts"].append(stored)
    return new


def at_date(state, person_id, meeting_date, domain, scope="city_council", title=None):
    when = day(meeting_date)
    if person_id not in {p["person_id"] for p in state["persons"]}:
        raise ValueError("Unknown stable person ID")
    relevant = [f for f in state["facts"] if f["person_id"] == person_id and f["domain"] == domain
                and f["scope"] == scope and (domain != "role" or f["title"] == title)
                and day(f["effective_on"]) <= when]
    if not relevant:
        return dict(status="hold", reason="no_reviewed_effective_date")
    latest = max(f["effective_on"] for f in relevant)
    relevant = [f for f in relevant if f["effective_on"] == latest]
    values = {f["value"] for f in relevant}
    if len(values) != 1:
        return dict(status="hold", reason="conflicting_reviewed_evidence")
    covering = [f for f in relevant if when <= day(f["confirmed_through"])]
    if not covering:
        return dict(status="hold", reason="meeting_outside_confirmed_coverage")
    return dict(status="confirmed", value=covering[0]["value"],
                person_id=person_id, evidence_ids=sorted(f["fact_id"] for f in covering))


def resolve_speaker(state, speaker, meeting_date):
    """Name match alone is insufficient: dated alias AND dated membership required."""
    day(meeting_date)
    candidates = set()
    for p in state["persons"]:
        slots = {f["scope"] for f in state["facts"] if f["person_id"] == p["person_id"] and f["domain"] == "alias"}
        for slot in slots:
            alias = at_date(state, p["person_id"], meeting_date, "alias", slot)
            if alias["status"] == "confirmed" and name_key(alias["value"]) == name_key(speaker):
                candidates.add(p["person_id"])
    if len(candidates) != 1:
        return dict(status="hold", reason="ambiguous_or_unconfirmed_dated_alias", person_id=None)
    person_id = next(iter(candidates))
    membership = at_date(state, person_id, meeting_date, "membership")
    if membership.get("status") != "confirmed" or membership.get("value") != "member":
        return dict(status="hold", reason="membership_not_confirmed_at_meeting", person_id=person_id)
    return dict(status="matched_member", person_id=person_id,
                membership_evidence=membership["evidence_ids"],
                speech_role="unverified", agenda_boundary="unverified")


def save_private(state, expected_head=None):
    """CAS versions + compare-and-swap head; old evidence/facts cannot be rewritten."""
    root = private_storage()  # Existing no-repo/no-reparse storage guard.
    if expected_head is not None and not re.fullmatch("[0-9a-f]{64}", expected_head):
        raise ValueError("Expected CAS SHA required")
    cas = root / "member-cas"
    if cas.exists() and (cas.is_symlink() or getattr(cas.lstat(), "st_file_attributes", 0) & 0x400):
        raise ValueError("Unsafe CAS directory")
    head = root / "member-history-head.json"
    previous = None
    if head.exists():
        if head.is_symlink() or getattr(head.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Unsafe history pointer")
        previous = json.loads(head.read_text(encoding="utf-8"))
        if previous.get("sha256") != expected_head:
            raise ValueError("History head changed")
        prior_path = root / "member-cas" / (expected_head + ".json")
        if prior_path.is_symlink() or getattr(prior_path.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Unsafe prior CAS")
        raw = prior_path.read_bytes()
        if digest(raw) != expected_head:
            raise ValueError("Previous CAS corrupted")
        old = json.loads(raw)
        for k in ("schema", "city", "seed_master_sha256"):
            if state[k] != old[k]:
                raise ValueError("Stable registry cannot be replaced")
        for k in ("persons", "observations", "reviews", "facts", "failures"):
            if state[k][:len(old[k])] != old[k]:
                raise ValueError("Append-only history violated")
    elif expected_head is not None:
        raise ValueError("Missing expected history")
    data = encode(state)
    sha = digest(data)
    if previous and sha == expected_head:
        return sha
    cas.mkdir(exist_ok=True)
    target = cas / (sha + ".json")
    if target.exists():
        if target.is_symlink() or getattr(target.lstat(), "st_file_attributes", 0) & 0x400 or target.read_bytes() != data:
            raise ValueError("CAS mismatch")
    else:
        with target.open("xb") as f:
            f.write(data)
    if target.read_bytes() != data:
        raise ValueError("CAS readback failed")
    # Exclusive lock prevents concurrent stale-head writers. Failure preserves old head.
    lock = root / "member-history.lock"
    with lock.open("x") as handle:
        try:
            current = json.loads(head.read_text(encoding="utf-8"))["sha256"] if head.exists() else None
            if current != expected_head:
                raise ValueError("Concurrent history update")
            tmp = root / ("member-head-" + uuid.uuid4().hex + ".tmp")
            with tmp.open("xb") as f:
                f.write(encode(dict(sha256=sha)))
            os.replace(tmp, head)
        finally:
            handle.close()
            lock.unlink()
    return sha

