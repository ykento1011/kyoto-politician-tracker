"""Offline-only bounded runner. Transport is synthetic; no live HTTP adapter."""
import copy
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import nagoya_article_review as review
from nagoya_roster_evidence import source_position
h = review.history
FIXED = (
    "https://www.city.nagoya.jp/shikai/about/1030778/1030799.html",
    "https://www.city.nagoya.jp/shikai/about/1030633/index.html",
    "https://www.city.nagoya.jp/shikai/about/1030778/1030796.html",
    "https://www.city.nagoya.jp/shikai/about/1030778/1030797.html",
    "https://www.city.nagoya.jp/shikai/about/1030778/1030798.html",
    "https://www.city.nagoya.jp/shikai/kouhou/1030998/index.html",
    "https://www.city.nagoya.jp/shikai/kouhou/1031662/index.html",
)
MIB = 1024 * 1024
LIMITS = dict(requests=8, total_bytes=8*MIB, response_bytes=2*MIB,
              timeout_seconds=10, tls_verify=True, redirects=0, retries=0)
INDEXES = set(FIXED[-2:])

class SyntheticTransport:
    """Explicit fixtures only. Every response is simulated, never observed HTTP."""
    def __init__(self, responses):
        self.responses = copy.deepcopy(responses)
        self.calls = []
    def get(self, url, constraints):
        self.calls.append(dict(url=url, constraints=copy.deepcopy(constraints)))
        return self.responses.pop(url)

def initial():
    return dict(review.empty(), frontier={}, pages={}, runs=[])

def code_sha():
    return h.digest(Path(__file__).read_bytes())

def dependency_shas():
    return {m.__name__: h.digest(Path(m.__file__).read_bytes()) for m in
            (review, h, __import__("nagoya_roster_evidence"))}

def _document_id(url):
    parts = re.findall(r"[0-9]+", url.split("/shikai/", 1)[1])
    if not parts:
        raise ValueError("Document ID absent")
    return parts[-1]

def validate_contract(contract, originals, root):
    if (contract.get("mode") != "offline-synthetic"
            or any(contract.get(k) is not False for k in
                   ("network_enabled", "publication_enabled", "scheduler_enabled"))
            or contract.get("limits") != LIMITS or contract.get("code_sha256") != code_sha()
            or contract.get("dependency_shas") != dependency_shas()
            or contract.get("storage") != str(root)):
        raise ValueError("Offline scope/code/storage/limits mismatch")
    if not contract.get("review_owner") or not contract.get("recovery_owner"):
        raise ValueError("Named operational responsibilities required")
    targets = contract.get("targets", [])
    urls = [t["url"] for t in targets]
    if not targets or len(urls) > 8 or len(set(urls)) != len(urls):
        raise ValueError("Unique bounded request plan required")
    if len([url for url in urls if url not in FIXED]) > 1:
        raise ValueError("At most one pre-approved detail")
    for t in targets:
        url = review.official(t["url"])
        if (t.get("document_id") != _document_id(url) or t.get("approved") is not True
                or not t.get("approval_reference") or t.get("layout_accepted") is not True
                or t.get("kind") not in ("index", "page", "article")
                or (url in INDEXES and t["kind"] != "index")
                or (url in FIXED and url not in INDEXES and t["kind"] != "page")):
            raise ValueError("URL/document/permission/layout mismatch")
        binding = t["source_binding"]
        raw, receipt = originals[binding["url"]]
        ev, nodes = review.original(raw, receipt)
        if ev["sha256"] != binding["sha256"] or ev["url"] != binding["url"]:
            raise ValueError("Accepted source SHA mismatch")
        if url in FIXED:
            if binding["url"] != url:
                raise ValueError("Fixed source baseline belongs to another page")
        else:
            if t["kind"] not in ("index", "article"):
                raise ValueError("Detail must be an article or historical index")
            pos = binding["position"]
            h.position(ev, pos)
            links = [n for n in nodes if n.path() == pos["dom"] and n.tag == "a"]
            if (len(links) != 1 or links[0].attrs.get("href") != binding["href"]
                    or urljoin(ev["url"], binding["href"]) != url):
                raise ValueError("Detail lacks exact saved official href")

def _body(response, used):
    if (response.get("status") != 200 or response.get("location") is not None
            or response.get("tls_verified") is not True
            or response.get("redirects") != 0 or response.get("retries") != 0
            or response.get("elapsed_seconds", 11) < 0
            or response.get("elapsed_seconds", 11) > 10
            or response.get("content_type", "").split(";")[0].strip() != "text/html"):
        raise ValueError("HTTP/TLS/redirect/retry/deadline/type failure")
    length = response.get("content_length")
    if length is not None and (type(length) is not int or not 0 < length <= 2*MIB):
        raise ValueError("Invalid/oversized content length")
    body = bytearray()
    for chunk in response["chunks"]:
        if type(chunk) is not bytes:
            raise ValueError("Non-byte transport body")
        if len(body)+len(chunk) > 2*MIB:
            raise ValueError("Per-response limit exceeded")
        if used+len(body)+len(chunk) > 8*MIB:
            raise ValueError("Independent total-body limit exceeded")
        body.extend(chunk)
    if not body or (length is not None and len(body) != length):
        raise ValueError("Empty/incomplete response")
    if b"</html>" not in body.lower():
        raise ValueError("Incomplete HTML")
    return bytes(body)

def _snapshot(ev, nodes):
    positions = []
    for n in nodes:
        cursor = n
        while cursor is not None and cursor.attrs.get("id") != "reference":
            cursor = cursor.parent
        if cursor is not None:
            continue
        if n.tag in ("h1", "h2", "h3", "p", "li", "td", "a") and n.text().strip():
            positions.append(dict(source_position(n), tag=n.tag,
                                  href=n.attrs.get("href")))
    semantic = h.digest(h.encode([(p["tag"], p["literal"], p["href"]) for p in positions]))
    return dict(semantic_sha256=semantic, positions=positions)

def _ingest(state, raw, receipt, target, candidates, registry):
    url = receipt["url"]
    if target["kind"] == "index":
        out, count = review.inspect_index(state, raw, receipt)
        version = next(v for v in out["versions"] if v["version_id"] == out["heads"][url])
        listed = version["payload"]
        for item in out["frontier"].values():
            if url in item["index_urls"]:
                item["currently_listed"][url] = item["url"] in listed
        for link in listed.values():
            entry = out["frontier"].setdefault(link["url"], dict(url=link["url"],
                first_seen=receipt["completed_utc"], last_seen=receipt["completed_utc"],
                last_visited=None, processed_shas=[], index_urls=[],
                currently_listed={}, source_positions={}, fetch_authorized=False))
            entry["last_seen"] = receipt["completed_utc"]
            if url not in entry["index_urls"]:
                entry["index_urls"].append(url)
            entry["currently_listed"][url] = True
            entry["source_positions"][url] = dict(source_sha256=receipt["sha256"],
                                                  position=link["position"])
    elif candidates is not None:
        out, count = review.inspect_article(state, raw, receipt, candidates, registry)
    else:
        ev, nodes = review.original(raw, receipt)
        snapshot = _snapshot(ev, nodes)
        before = state["pages"].get(url)
        entries = [] if before and before == snapshot["semantic_sha256"] else [
            dict(kind="document_review", change="baseline-only" if before is None else "content_changed",
                 positions=snapshot["positions"], event_interpretation="pending",
                 fetch_authorized=False)]
        out, count = review._append(state, ev, "page_snapshot", snapshot, entries)
        out["pages"][url] = snapshot["semantic_sha256"]
    return out, count

def backlog(state, as_of):
    now = h.observed(as_of)
    items = []
    for row in state["frontier"].values():
        since = row["last_visited"] or row["first_seen"]
        days = (now-h.observed(since)).total_seconds()/86400
        if days < 0:
            raise ValueError("Backlog clock precedes observation")
        items.append(dict(copy.deepcopy(row), days_waiting=int(days),
                          unvisited=row["last_visited"] is None))
    # Oldest first; planning only, never acquisition authorization.
    return sorted(items, key=lambda x: (-x["days_waiting"], x["url"]))

def review_backlog(state, as_of):
    """Human-review worklist; accepted_for_projection still never writes facts."""
    now = h.observed(as_of)
    latest = {r["queue_id"]: r for r in state["reviews"]}
    rows = []
    for entry in state["queue"]:
        decision = latest.get(entry["queue_id"], {}).get("decision", "pending")
        if decision in ("rejected", "accepted_for_projection"):
            continue
        age = (now-h.observed(entry["observed_at"])).total_seconds()/86400
        if age < 0:
            raise ValueError("Review clock precedes observation")
        rows.append(dict(queue_id=entry["queue_id"], source_url=entry["source_url"],
                         decision=decision, days_waiting=int(age)))
    return sorted(rows, key=lambda x: (-x["days_waiting"], x["queue_id"]))

def run_offline(root, state, expected_head, contract, originals, transport,
                run_id, observed_at, candidates=None, registry=None):
    """One staged transaction, only fixture transport; never updates old histories."""
    root = review._private(root)
    if type(transport) is not SyntheticTransport:
        raise ValueError("No live/custom transport permitted in this implementation")
    h.observed(observed_at)
    validate_contract(contract, originals, root)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("Invalid one-use run ID")
    root.mkdir(parents=True, exist_ok=True)
    head = root/"article-review-head.json"
    review._private(head)
    current = json.loads(head.read_bytes())["sha256"] if head.exists() else None
    if current != expected_head:
        raise ValueError("Stale operational head")
    if current:
        prior = root/"article-review-cas"/(current+".json")
        review._private(prior)
        if h.digest(prior.read_bytes()) != current or h.encode(state) != prior.read_bytes():
            raise ValueError("Caller state differs from committed CAS")
    elif state != initial():
        raise ValueError("Initial normal state required")
    if state["runs"] and h.observed(observed_at) < h.observed(state["runs"][-1]["observed_at"]):
        raise ValueError("Observation clock moved backwards")
    runs = root/"runner-receipts"
    review._private(runs)
    runs.mkdir(exist_ok=True)
    rp = runs/(run_id+".json")
    review._private(rp)
    log = dict(run_id=run_id, simulated=True, status="reserved",
               observed_at=observed_at, contract_sha256=h.digest(h.encode(contract)),
               code_sha256=code_sha(), attempts=[], received_bytes=0,
               previous_head=expected_head)
    with rp.open("x") as f:
        json.dump(log, f)  # One-use reservation, including failed/uncertain runs.
    def record():
        temp = rp.with_suffix(".tmp")
        review._private(temp)
        with temp.open("x") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        review.os.replace(temp, rp)
    out = copy.deepcopy(state)
    try:
        for target in contract["targets"]:
            url = target["url"]
            if len(log["attempts"]) >= 8 or log["received_bytes"]+2*MIB > 8*MIB:
                raise ValueError("Request count or independent total reservation exceeded")
            attempt = dict(url=url, method="GET", status="reserved",
                           document_id=target["document_id"], simulated=True)
            log["attempts"].append(attempt)
            record()
            started = time.monotonic()
            response = transport.get(url, copy.deepcopy(LIMITS))
            chunks = response.get("chunks", [])
            attempt.update(http_status=response.get("status"),
                observed_body_bytes=sum(map(len, chunks)) if isinstance(chunks, list)
                    and all(type(c) is bytes for c in chunks) else None)
            record()
            if time.monotonic()-started > 10:
                raise ValueError("10-second response deadline exceeded")
            raw = _body(response, log["received_bytes"])
            log["received_bytes"] += len(raw)
            receipt = dict(attempt, status="success", http_status=200,
                           bytes=len(raw), sha256=h.digest(raw),
                           completed_utc=observed_at, content_type="text/html")
            ev, nodes = review.original(raw, receipt)
            ids = [n.text() for n in nodes if n.attrs.get("class") == "idnumber"]
            if not any("ページID"+target["document_id"] in value for value in ids):
                raise ValueError("Document ID/structure mismatch")
            cas = root/"runner-raw-cas"
            review._private(cas)
            cas.mkdir(exist_ok=True)
            dest = cas/receipt["sha256"]
            review._private(dest)
            if not dest.exists():
                with dest.open("xb") as f:
                    f.write(raw)
            if dest.read_bytes() != raw:
                raise ValueError("Original CAS readback mismatch")
            attempt.update(receipt, cas_sha256=receipt["sha256"])
            out, count = _ingest(out, raw, receipt, target,
                                 (candidates or {}).get(url), registry or {})
            row = out["frontier"].setdefault(url, dict(url=url, first_seen=observed_at,
                last_seen=observed_at, last_visited=None, processed_shas=[],
                index_urls=[], currently_listed={}, source_positions={}, fetch_authorized=False))
            row["last_visited"] = observed_at
            if receipt["sha256"] not in row["processed_shas"]:
                row["processed_shas"].append(receipt["sha256"])
            attempt["new_reviews"] = count
            record()
        log["status"] = "prepared"
        record()
        out["runs"].append(copy.deepcopy(log))
        # Validate durable audit before publishing the single normal-state pointer.
        if json.loads(rp.read_text()) != log:
            raise ValueError("Run receipt readback failed")
        new_head = review.save_queue(root, out, expected_head)
    except Exception as exc:
        log.update(status="failed", error=type(exc).__name__+": "+str(exc))
        log["accepted_body_bytes"] = log["received_bytes"]
        measured = [a.get("observed_body_bytes") for a in log["attempts"]]
        log["received_bytes"] = sum(measured) if all(type(n) is int for n in measured) else None
        try:
            record()
        except OSError:
            pass  # Reserved/incomplete evidence remains; never retry automatically.
        raise
    return out, new_head
