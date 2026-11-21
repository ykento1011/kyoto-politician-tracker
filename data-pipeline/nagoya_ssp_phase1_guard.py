"""Nagoya SSP Phase 1 contract. ONLY synthetic workers; live access is disabled.

No scraper, HTTP client, Kyoto approval or production storage is imported.
ACL/approval fixtures exercise rejection logic, not real authority or ACL proof.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

LIVE_ENABLED = False
SCOPE = "nagoya-ssp-phase1-offline"
HOST = "ssp.kaigiroku.net"
REFERER = "https://ssp.kaigiroku.net/tenant/nagoya/SpMinuteBrowse.html"
REQUESTS = [
    {"method": "GET", "url": "https://ssp.kaigiroku.net/tenant/nagoya/SpTop.html", "body": ""},
    {"method": "POST", "url": "https://ssp.kaigiroku.net/dnp/search/councils/index",
     "body": "tenant_id=207&power_user=false"},
]
LIMITS = {"attempts": 2, "response_bytes": 2*1024*1024, "total_bytes": 4*1024*1024,
          "worker_seconds": 25, "phase_seconds": 60, "interval_seconds": 1.2,
          "tls_verify": True, "redirects": 0, "retries": 0}
MAX_ENVELOPE = 3*1024*1024


class Hold(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pins():
    return {"guard": sha(Path(__file__).read_bytes()),
            "python": sha(Path(sys.executable).read_bytes())}


def safe_root(value):
    root = Path(value)
    if not root.is_absolute() or not root.is_dir():
        raise Hold("Existing isolated fixture directory required")
    for part in (root, *root.parents):
        stat = part.lstat()
        if part.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise Hold("Reparse paths forbidden")
        if (part / ".git").exists():
            raise Hold("Storage must be outside every checkout")
    marker = root / "OFFLINE-TEST-ONLY.json"
    if json.loads(marker.read_bytes()) != {"scope": SCOPE, "synthetic": True}:
        raise Hold("Isolated synthetic fixture marker required")
    # A previously created state subtree cannot be redirected to real storage.
    for path in root.rglob("*"):
        stat = path.lstat()
        if path.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise Hold("Reparse state forbidden")
    return root.resolve()


def validate(root, approval, binding, principal, initial_cookies):
    if initial_cookies != []:
        raise Hold("Fresh empty Nagoya-only cookie jar required")
    if (approval.get("synthetic") is not True or approval.get("network_enabled") is not False
            or approval.get("scope") != SCOPE or approval.get("tenant_id") != "207"
            or approval.get("requests") != REQUESTS or approval.get("limits") != LIMITS
            or approval.get("pins") != pins() or not approval.get("source_registration")
            or not approval.get("approval_reference") or approval.get("principal") != principal
            or approval.get("storage") != str(root)):
        raise Hold("Missing or mismatched synthetic authorization/P1 pins")
    if (binding.get("synthetic") is not True or binding.get("scope") != SCOPE
            or binding.get("approval_sha256") != sha(encode(approval))
            or binding.get("principal") != principal or binding.get("storage") != str(root)
            or binding.get("acl") != {"owner": principal, "owner_only": True, "simulated": True}
            or binding.get("receipt_namespace") != "nagoya-ssp-phase1-synthetic"):
        raise Hold("Missing or mismatched binding/ACL/receipt namespace")
    run_id = approval.get("run_id", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise Hold("Explicit one-shot run ID required")


def exclusive(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def cas(root, raw):
    key = sha(raw)
    target = root / "cas" / key
    if target.exists():
        if target.read_bytes() != raw:
            raise Hold("CAS collision/corruption")
    else:
        exclusive(target, raw)
    if sha(target.read_bytes()) != key:
        raise Hold("CAS readback failed")
    return key


def parse_response(slot, raw, result):
    if (result.get("status") != 200 or result.get("tls_verify") is not True
            or result.get("redirects") != 0 or result.get("retries") != 0
            or result.get("complete") is not True or result.get("auth_required") is not False):
        raise Hold("HTTP, TLS, redirect, retry, authentication or completeness failure")
    if not 0 < len(raw) <= LIMITS["response_bytes"]:
        raise Hold("Response capacity exceeded or empty")
    text = raw.decode("utf-8-sig").strip()
    media = result.get("content_type", "").split(";", 1)[0].lower()
    if slot == 1:
        if (media != "text/html" or "<html" not in text.lower()
                or re.search(r'type\s*=\s*[\"\x27]?password|<form[^>]*(?:login|auth)', text, re.I)):
            raise Hold("Unexpected session HTML or authentication")
        return {"kind": "session_html"}
    if media not in ("application/json", "text/javascript", "application/javascript"):
        raise Hold("Unknown index media")
    if text.startswith("jQuery"):
        match = re.fullmatch(r"jQuery[0-9]+_[0-9]+\((\{.*\})\);?", text, re.S)
        if not match:
            raise Hold("Unknown JSONP; scripts never evaluated")
        text = match[1]
    data = json.loads(text)
    if not isinstance(data, dict) or str(data.get("tenant_id", "207")) != "207":
        raise Hold("Index tenant mismatch")
    councils = data.get("councils")
    if not isinstance(councils, list) or len(councils) != 1:
        raise Hold("Unknown councils structure")
    years = councils[0].get("view_years")
    if not isinstance(years, list) or not years:
        raise Hold("Missing index years")
    count = 0
    for year in years:
        if not re.fullmatch(r"[0-9]{4}", str(year.get("view_year", ""))):
            raise Hold("Missing official index year")
        groups = year.get("council_type")
        if not isinstance(groups, list):
            raise Hold("Unknown council groups")
        for group in groups:
            rows = group.get("councils")
            if not isinstance(rows, list):
                raise Hold("Unknown council rows")
            for row in rows:
                if not re.fullmatch(r"[1-9][0-9]*", str(row.get("council_id", ""))) or not row.get("name"):
                    raise Hold("Missing official council identity")
                count += 1
    return {"kind": "index_only", "council_count": count,
            "schedule_confirmed": False, "phase2_authorized": False}


def worker(fixture, request):
    """Synthetic child only: echo fixture, never open a socket or follow a link."""
    fixed = {key: request.get(key) for key in ("method", "url", "body")}
    if fixed not in REQUESTS:
        raise Hold("Request outside fixed Phase 1")
    expected = {"Referer": REFERER, "X-Requested-With": "XMLHttpRequest"}
    if fixed["method"] == "POST":
        expected["Content-Type"] = "application/x-www-form-urlencoded"
    if request.get("headers") != expected or type(request.get("cookies")) is not list:
        raise Hold("Unexpected headers/cookie container")
    if fixed["method"] == "GET" and request["cookies"]:
        raise Hold("Session must start empty")
    for cookie in request["cookies"]:
        if cookie.get("domain") != HOST or cookie.get("secure") is not True:
            raise Hold("Foreign cookie")
    return fixture


def bounded_fixture(fixture):
    if type(fixture) is not dict or type(fixture.get("body_base64")) is not str:
        raise Hold("Unknown synthetic envelope")
    # Bound encoded data before allocating decoded data or launching a worker.
    if len(fixture["body_base64"]) > 4*((LIMITS["response_bytes"]+2)//3):
        raise Hold("Encoded response capacity exceeded")
    metadata = {key: value for key, value in fixture.items() if key != "body_base64"}
    if len(encode(metadata)) > 16384:
        raise Hold("Oversized synthetic metadata")


def supervised(mode, payload, seconds, output_limit):
    # Spool to disposable fixture files, never accumulate unlimited PIPE output.
    # Only this pinned, network-free module is executable by the worker.
    try:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), mode],
                           input=encode(payload), stdout=output, stderr=error,
                           timeout=seconds, check=True)
            output.seek(0)
            raw = output.read(output_limit+1)
            if len(raw) > output_limit:
                raise Hold("Worker output capacity exceeded")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        raise Hold("Worker timeout/failure; attempt consumed, no retry") from exc
    return json.loads(raw)


def child(fixture, request, seconds):
    bounded_fixture(fixture)
    return supervised("--synthetic-worker", {"fixture": fixture, "request": request}, seconds, MAX_ENVELOPE)


def run_synthetic(storage, approval, binding, fixtures, *, principal, initial_cookies=None):
    """External 60s supervisor encompasses validation, stage and disk I/O.

    On forced termination a lock/attempt may remain unknown; never retry that run.
    Nested response workers cannot access stage state and have their own 25s cap.
    """
    if type(fixtures) is not list or len(fixtures) != 2:
        raise Hold("Exactly two synthetic responses required")
    for fixture in fixtures:
        bounded_fixture(fixture)
    metadata = {"storage": str(storage), "approval": approval, "binding": binding,
                "principal": principal, "initial_cookies": initial_cookies}
    if len(encode(metadata)) > 32768:
        raise Hold("Oversized phase contract")
    return supervised("--synthetic-phase", dict(metadata, fixtures=fixtures), 60, 65536)


def _stage_synthetic(storage, approval, binding, fixtures, *, principal, initial_cookies=None):
    """Internal phase worker; all checks still enforced, fixtures only."""
    start = time.monotonic()
    root = safe_root(storage)
    validate(root, approval, binding, principal, [] if initial_cookies is None else initial_cookies)
    if type(fixtures) is not list or len(fixtures) != 2:
        raise Hold("Exactly two synthetic responses required")
    for fixture in fixtures:
        bounded_fixture(fixture)
    lock = root / "phase1.lock"
    try:
        exclusive(lock, b"synthetic-only")
    except FileExistsError as exc:
        raise Hold("Concurrent or interrupted run; manual review required") from exc
    try:
        return _run(root, approval, fixtures, start)
    finally:
        lock.unlink()


def _run(root, approval, fixtures, start):
    deadline = start + LIMITS["phase_seconds"]
    run_id = approval["run_id"]
    # Before reserving any attempt, verify previous immutable state/CAS readback.
    head = root / "HEAD"
    previous = head.read_bytes() if head.exists() else None
    if previous:
        normal = json.loads(previous)
        for entry in normal["responses"]:
            if sha((root / "cas" / entry["sha256"]).read_bytes()) != entry["sha256"]:
                raise Hold("Previous normal CAS corrupted")
    (root / "cas").mkdir(exist_ok=True)
    trials = root / "trials"
    trials.mkdir(exist_ok=True)
    trial = trials / run_id
    try:
        trial.mkdir()  # Permanent one-shot reservation, even after unknown/failure.
    except FileExistsError as exc:
        raise Hold("Run already reserved; never retry") from exc
    receipt = {"synthetic": True, "scope": SCOPE, "run_id": run_id,
               "approval_sha256": sha(encode(approval)), "pins": approval["pins"],
               "limits": LIMITS, "attempts": [], "status": "HOLD"}
    cookies, total, responses = [], 0, []
    try:
        for slot, (fixed, fixture) in enumerate(zip(REQUESTS, fixtures), 1):
            if slot > 1:
                time.sleep(LIMITS["interval_seconds"])
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Hold("Phase wall-clock deadline")
            request = dict(fixed, headers={"Referer": REFERER, "X-Requested-With": "XMLHttpRequest"},
                           cookies=cookies)
            if slot == 2:
                request["headers"]["Content-Type"] = "application/x-www-form-urlencoded"
            # Child sees an immutable fixed endpoint request, no transport injection.
            exclusive(trial / f"attempt-{slot}.used", encode({"slot": slot, "request": fixed}))
            attempt = {"slot": slot, "method": fixed["method"], "url": fixed["url"], "result": "unknown"}
            receipt["attempts"].append(attempt)
            attempt["reserved_utc"] = datetime.now(timezone.utc).isoformat()
            result = child(fixture, request, min(25, remaining))
            if time.monotonic() >= deadline:
                raise Hold("Phase wall-clock deadline")
            raw = base64.b64decode(result["body_base64"], validate=True)
            total += len(raw)
            if total > LIMITS["total_bytes"]:
                raise Hold("Aggregate capacity exceeded")
            parsed = parse_response(slot, raw, result)
            received_cookies = result.get("cookies", [])
            if (type(received_cookies) is not list or any(
                    set(c) != {"name", "value", "domain", "path", "secure"}
                    or c["domain"] != HOST or c["path"] != "/" or c["secure"] is not True
                    for c in received_cookies)):
                raise Hold("Foreign/unknown cookie state")
            cookies = received_cookies or cookies  # memory only; never in receipt/CAS
            key = cas(root, raw)
            attempt.update(result="received", response_bytes=len(raw), sha256=key, http_status=200,
                           completed_utc=datetime.now(timezone.utc).isoformat())
            responses.append({"sha256": key, "parsed": parsed})
        normal = {"synthetic": True, "scope": SCOPE, "run_id": run_id, "responses": responses}
        if time.monotonic() >= deadline:
            raise Hold("Phase deadline before commit")
        receipt.update(status="synthetic_prepared", commit_status="not_asserted_by_receipt", response_bytes=total)
        exclusive(trial / "receipt.json", encode(receipt))
        exclusive(trial / "next-head.json", encode(normal))
        os.replace(trial / "next-head.json", head)
        return receipt
    except Exception:
        # Failed/unknown run remains spent, previous HEAD is never replaced.
        if not (trial / "receipt.json").exists():
            exclusive(trial / "receipt.json", encode(receipt))
        raise


def acquire_live(*args, **kwargs):
    raise Hold("Live disabled: no accepted Nagoya ACL/source/P1/binding/receipt authority; no reservation made")


if __name__ == "__main__":
    mode = sys.argv[1:]
    if mode not in (["--synthetic-worker"], ["--synthetic-phase"]):
        acquire_live()
    maximum = 2*MAX_ENVELOPE+65536
    raw = sys.stdin.buffer.read(maximum+1)
    if len(raw) > maximum:
        raise Hold("Worker input capacity exceeded")
    payload = json.loads(raw)
    if mode == ["--synthetic-worker"]:
        bounded_fixture(payload["fixture"])
        result = worker(payload["fixture"], payload["request"])
    else:
        result = _stage_synthetic(**payload)
    sys.stdout.buffer.write(encode(result))
