"""Offline article discovery and review queue. No acquisition, facts or scheduler."""
import copy
import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import member_history as history
from nagoya_roster_evidence import Tree, source_position

def empty():
    return dict(schema=1, versions=[], heads={}, queue=[], reviews=[])

def official(url):
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != "www.city.nagoya.jp" or p.username
            or p.password or p.port not in (None, 443) or p.fragment
            or not p.path.startswith("/shikai/") or p.query):
        raise ValueError("Exact official council URL required")
    return url

def original(raw, receipt):
    ev = history.evidence(raw, receipt)
    official(ev["url"])
    nodes = Tree(raw).article_nodes()
    if len([n for n in nodes if n.tag == "h1"]) != 1:
        raise ValueError("Article heading missing")
    return ev, nodes

def version_id(ev):
    return history.digest(history.encode([ev["url"], ev["sha256"]]))

def _append(state, ev, kind, payload, entries):
    vid = version_id(ev)
    previous = next((v for v in state["versions"] if v["version_id"] == vid), None)
    binding = history.digest(history.encode([kind, payload]))
    if previous:
        if previous["binding_sha256"] != binding:
            raise ValueError("Same original cannot change its candidate interpretation")
        return copy.deepcopy(state), 0
    out = copy.deepcopy(state)
    out["versions"].append(dict(version_id=vid, kind=kind, source_url=ev["url"],
        source_sha256=ev["sha256"], observed_at=ev["observed_at"],
        binding_sha256=binding, payload=copy.deepcopy(payload)))
    out["heads"][ev["url"]] = vid
    for entry in entries:
        row = dict(entry, version_id=vid, source_url=ev["url"],
                   source_sha256=ev["sha256"], observed_at=ev["observed_at"],
                   status="hold")
        row["queue_id"] = history.digest(history.encode(row))
        out["queue"].append(row)
    return out, len(entries)

def inspect_index(state, raw, receipt):
    ev, nodes = original(raw, receipt)
    links = {}
    for n in nodes:
        if n.tag != "a" or not n.attrs.get("href"):
            continue
        url = urljoin(ev["url"], n.attrs["href"])
        if url == ev["url"]:
            continue
        try:
            official(url)
        except ValueError:
            continue
        row = dict(url=url, label=n.text().strip(), position=source_position(n))
        if url in links and links[url]["label"] != row["label"]:
            raise ValueError("Ambiguous duplicate article link")
        links.setdefault(url, row)
    if not links:
        raise ValueError("Empty/unrecognized index; preserve prior state")
    previous = next((v for v in state["versions"]
                     if v["version_id"] == state["heads"].get(ev["url"])), None)
    old = previous["payload"] if previous else {}
    entries = []
    for url in sorted(old.keys() | links.keys()):
        a, b = old.get(url), links.get(url)
        if a and b and a["label"] == b["label"]:
            continue  # Template/DOM shifts alone are not article changes.
        entries.append(dict(kind="index_link", target_url=url,
            change="baseline-only" if previous is None else
                   "added" if a is None else "removed" if b is None else "label_changed",
            before=a, after=b, fetch_authorized=False))
    # Bind semantic links, not volatile DOM offsets, for duplicate raw receipts.
    return _append(state, ev, "index", links, entries)

def _candidate(state, ev, candidate):
    c = copy.deepcopy(candidate)
    if c.get("source_url") != ev["url"] or c.get("source_sha256") != ev["sha256"]:
        raise ValueError("Candidate/source binding mismatch")
    history.position(ev, c["position"])
    if c.get("domain") not in history.DOMAINS:
        raise ValueError("Unknown event domain")
    domain, action, scope = c["domain"], c.get("action"), c.get("scope")
    if domain == "group":
        if scope != "city_council" or action not in ("leave", "join") or not c.get("title"):
            raise ValueError("Group relationship event required")
    elif domain == "role":
        if scope in (None, "", "city_council") or action not in ("held", "ended") or not c.get("title"):
            raise ValueError("Role change must remain separate from membership")
    elif domain == "membership":
        if scope != "city_council" or action not in history.END_REASONS | history.START_REASONS:
            raise ValueError("Explicit council membership event required")
    elif not c.get("title"):
        raise ValueError("Alias literal required")
    pid = c.get("person_id_candidate")
    if pid is not None and pid not in {p["person_id"] for p in state["persons"]}:
        raise ValueError("Unknown ID; no implicit onboarding or alias merge")
    date = c.get("effective_on")
    if date is not None:
        history.day(date)
        if not c.get("date_literal") or c["date_literal"] not in c["position"]["literal"]:
            raise ValueError("Date must have an original literal; human checks its meaning")
    c["identity_status"] = "pending_independent_review"
    c["hold_reasons"] = ["identity_and_meaning_review_required", "coverage_review_required"]
    if pid is None:
        c["hold_reasons"].append("identity_unresolved")
    if date is None:
        c["hold_reasons"].append("effective_date_unknown")
    return c

def inspect_article(state, raw, receipt, candidates, registry):
    ev, nodes = original(raw, receipt)
    checked = [_candidate(registry, ev, c) for c in candidates]
    ids = [c["candidate_id"] for c in checked]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate event ID in one article")
    entries = [dict(kind="article_event", candidate=c) for c in checked]
    if not entries:
        entries = [dict(kind="article_no_event", position=source_position(
            next(n for n in nodes if n.tag == "h1")),
            note="No supplied change evidence; does not prove absence of changes")]
    return _append(state, ev, "article", checked, entries)

def record_review(state, queue_id, review):
    """Record a human decision, never turn it into a member-history fact."""
    matches = [x for x in state["queue"] if x["queue_id"] == queue_id]
    if len(matches) != 1:
        raise ValueError("Unknown queue ID")
    row = matches[0]
    if (review.get("source_sha256") != row["source_sha256"]
            or not review.get("reviewer") or not review.get("review_reference")
            or not review.get("reason")):
        raise ValueError("Hash-bound named review required")
    history.observed(review["reviewed_at"])
    if review.get("decision") not in ("hold", "rejected", "accepted_for_projection"):
        raise ValueError("Explicit review decision required")
    if review["decision"] == "accepted_for_projection":
        c = row.get("candidate", {})
        if (not c.get("person_id_candidate") or not c.get("effective_on")
                or review.get("person_id") != c["person_id_candidate"]
                or review.get("identity_confirmed") is not True
                or review.get("meaning_confirmed") is not True):
            raise ValueError("Identity, meaning and dated event must be confirmed")
        start, end = history.day(review["effective_on"]), history.day(review["confirmed_through"])
        if (review["effective_on"] != c["effective_on"] or start > end
                or end > history.observed(row["observed_at"]).date()):
            raise ValueError("Bounded reviewed coverage required")
    stored = dict(copy.deepcopy(review), queue_id=queue_id)
    stored["review_id"] = history.digest(history.encode(stored))
    out = copy.deepcopy(state)
    if not any(x["review_id"] == stored["review_id"] for x in out["reviews"]):
        out["reviews"].append(stored)
    return out

def _private(root):
    root = Path(root).absolute()
    for p in (root, *root.parents):
        if p.exists() and (p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Reparse storage rejected")
        if (p / ".git").exists():
            raise ValueError("Repository/public storage rejected")
    return root

def save_queue(root, state, expected_head=None):
    """Own CAS/head, deliberately separate from member-history head."""
    root = _private(root)
    root.mkdir(parents=True, exist_ok=True)
    head = root / "article-review-head.json"
    for p in (head, root / "article-review-cas", root / "article-review.lock"):
        _private(p)
    with (root / "article-review.lock").open("x") as lock:
        try:
            current = json.loads(head.read_bytes())["sha256"] if head.exists() else None
            if current != expected_head:
                raise ValueError("Queue head changed")
            if current:
                prior = root / "article-review-cas" / (current + ".json")
                _private(prior)
                body = prior.read_bytes()
                if history.digest(body) != current:
                    raise ValueError("Prior CAS corrupted")
                old = json.loads(body)
                for k in ("schema",):
                    if state[k] != old[k]:
                        raise ValueError("Queue schema changed")
                for k in ("versions", "queue", "reviews"):
                    if state[k][:len(old[k])] != old[k]:
                        raise ValueError("Append-only queue violated")
            body = history.encode(state)
            digest = history.digest(body)
            folder = root / "article-review-cas"
            folder.mkdir(exist_ok=True)
            target = folder / (digest + ".json")
            _private(target)
            if not target.exists():
                with target.open("xb") as f:
                    f.write(body)
            if target.read_bytes() != body:
                raise ValueError("Queue CAS readback failed")
            temp = root / "article-review-head.tmp"
            _private(temp)
            with temp.open("xb") as f:
                f.write(history.encode(dict(sha256=digest)))
            os.replace(temp, head)
            return digest
        finally:
            lock.close()
            (root / "article-review.lock").unlink()

