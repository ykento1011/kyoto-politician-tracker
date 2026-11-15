"""One-use, representative-approved Kyoto council-index acquisition only.

Importing this module never performs HTTP. No normal scraper or update pipeline
is imported. The approval reference is an operational record, not a signature.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import http.cookiejar
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlsplit

TOP = "https://ssp.kaigiroku.net/tenant/kyoto/SpTop.html"
INDEX = "https://ssp.kaigiroku.net/dnp/search/councils/index"
REFERER = "https://ssp.kaigiroku.net/tenant/kyoto/SpMinuteBrowse.html"
POST_BODY = b"tenant_id=355&power_user=false"
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 25
INTERVAL = 1.2
LEDGER_SHA = "59215bebdf28bfca1e375faad73e7840db1f6d2ea0964a1ddd586f92534f22fc"
BASELINE_SHA = "7c705b83aedb4cddd325f3e1d4955eba40cfe6106f636723406bf8e9e76d4c98"
from kyoto_private_paths import private_storage

ARTIFACT = private_storage()
LEDGER = ARTIFACT / "new-meeting-evidence/history-ledger.json"
STORAGE = ARTIFACT / "new-meeting-evidence/council-list-trials"
LIMITS = {"http_attempts": 2, "tls_verify": True, "retries": 0, "redirects": 0,
          "response_body_bytes": MAX_BYTES, "timeout_seconds": TIMEOUT,
          "interval_seconds": INTERVAL}
ALLOWED = [("GET", TOP), ("POST", INDEX)]
COOKIE_FIELDS = ("version", "name", "value", "port", "port_specified", "domain",
                 "domain_specified", "domain_initial_dot", "path", "path_specified",
                 "secure", "expires", "discard", "comment", "comment_url", "rfc2109")


class Stop(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       indent=2) + "\n").encode("utf-8")


def safe_path(path):
    path = Path(path).absolute()
    for p in (path, *path.parents):
        if not p.exists():
            continue
        if p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 0x400:
            raise Stop("Reparse/symlink paths are not allowed")
    return path


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(json_bytes(value))
    os.replace(temporary, path)


def request_contract(method, url):
    if (method, url) not in ALLOWED:
        raise Stop("Unapproved method or exact URL")
    return POST_BODY if method == "POST" else None


def _https_once(method, url, cookies):
    """Worker: exactly one HTTPS request, no redirects/retries/proxy discovery."""
    body = request_contract(method, url)
    ctx = ssl.create_default_context()
    if not ctx.check_hostname or ctx.verify_mode != ssl.CERT_REQUIRED:
        raise Stop("TLS verification is required")
    jar = http.cookiejar.CookieJar()
    if not isinstance(cookies, list) or len(cookies) > 100:
        raise Stop("Invalid cookie state")
    for state in cookies:
        jar.set_cookie(http.cookiejar.Cookie(**state))
    req = urllib.request.Request(url, data=body, method=method)
    jar.add_cookie_header(req)  # Cookie policy only; urllib never opens a URL.
    headers = {"User-Agent": "GikaiNoMikataBot/1.0 (+https://gikai-mikata.jp; info@gikai-mikata.jp)",
               "Referer": REFERER, "X-Requested-With": "XMLHttpRequest",
               "Accept-Encoding": "identity", "Connection": "close"}
    if req.has_header("Cookie"):
        headers["Cookie"] = req.get_header("Cookie")
    if method == "POST":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = "text/html"
    connection = http.client.HTTPSConnection("ssp.kaigiroku.net", timeout=TIMEOUT, context=ctx)
    started = utc()
    response = None
    try:
        connection.request(method, urlsplit(url).path, body=body, headers=headers)
        response = connection.getresponse()
        # No follow-up request is made, including for a Location header.
        encoding = response.getheader("Content-Encoding", "identity").lower()
        length = response.getheader("Content-Length")
        transfer = response.getheader("Transfer-Encoding")
        if encoding not in ("identity", ""):
            raise Stop("Unexpected content encoding")
        if length is not None and (not length.isdigit() or int(length) > MAX_BYTES):
            raise Stop("Response size limit exceeded or invalid length")
        if transfer and (transfer.lower() != "chunked" or length is not None):
            raise Stop("Conflicting/unsupported transfer framing")
        content = response.read(MAX_BYTES)
        if ((length is not None and len(content) != int(length))
                or (length is None and len(content) == MAX_BYTES)):
            raise Stop("Incomplete or potentially oversized response")
        jar.extract_cookies(response, req)
        cookie_state = []
        for cookie in jar:
            state = {k: getattr(cookie, k) for k in COOKIE_FIELDS}
            state["rest"] = cookie._rest
            cookie_state.append(state)
        # Cookie values are returned in-memory only and never written to evidence.
        return {"started_utc": started, "completed_utc": utc(), "status": response.status,
                "content_type": response.getheader("Content-Type", ""),
                "bytes": len(content), "body_b64": base64.b64encode(content).decode("ascii"),
                "cookies": cookie_state}
    except Exception as exc:
        details = {"started_utc": started, "completed_utc": utc(),
                   "http_status": response.status if response is not None else None}
        raise Stop(type(exc).__name__ + ": " + str(exc), details) from exc
    finally:
        connection.close()


def isolated_request(method, url, cookies, trial, slot):
    """A disposable worker gives the whole communication a hard 25-second limit."""
    request_contract(method, url)
    payload = {"method": method, "url": url, "cookies": cookies,
               "trial": str(trial), "slot": slot}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=flags)
    try:
        output, error = process.communicate(json_bytes(payload), timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise Stop("Communication deadline exceeded; worker stopped without retry") from exc
    try:
        result = json.loads(output)
    except (ValueError, UnicodeError) as exc:
        raise Stop("Communication failed without a complete receipt; no retry") from exc
    if "error" in result:
        raise Stop(result["error"], result.get("details"))
    if process.returncode != 0:
        raise Stop("Communication failed; no retry")
    return result


def validate_session(body, content_type):
    if content_type.split(";")[0].strip().lower() != "text/html":
        raise Stop("Session response is not HTML")
    lower = body.lower()
    if b"<html" not in lower or b"</html>" not in lower:
        raise Stop("Incomplete session HTML")
    if any(marker in lower for marker in (b"cf-chl-", b"g-recaptcha", b"hcaptcha", b"access denied")):
        raise Stop("Challenge/access-denied response")


def parse_index(body, content_type, ledger):
    media = content_type.split(";")[0].strip().lower()
    if media not in {"application/json", "text/json", "application/javascript", "text/javascript"}:
        raise Stop("Council index content type mismatch")
    text = body.decode("utf-8-sig").strip()
    if text.startswith("jQuery"):
        match = re.fullmatch(r"jQuery[A-Za-z0-9_]*\((\{.*\})\);?", text, re.DOTALL)
        if not match:
            raise Stop("Unexpected JSONP wrapper")
        text = match[1]
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("councils"), list) or len(data["councils"]) != 1:
        raise Stop("Council index root structure mismatch")
    container = data["councils"][0]
    if not isinstance(container, dict) or not isinstance(container.get("view_years"), list):
        raise Stop("Missing view_years")
    for obj in (data, container):
        if "tenant_id" in obj and str(obj["tenant_id"]) != "355":
            raise Stop("Wrong tenant")
    known = {key.split(":")[1] for key in ledger["meetings"]}
    results, seen = [], set()
    for year_group in container["view_years"]:
        if not isinstance(year_group, dict):
            raise Stop("Invalid year-group object")
        year = str(year_group.get("view_year", ""))
        if not re.fullmatch("[0-9]{4}", year) or not isinstance(year_group.get("council_type"), list):
            raise Stop("Invalid year group")
        for kind in year_group["council_type"]:
            if not isinstance(kind, dict) or not isinstance(kind.get("councils"), list):
                raise Stop("Invalid council_type group")
            for item in kind["councils"]:
                if not isinstance(item, dict):
                    raise Stop("Invalid council item")
                ident, name = str(item.get("council_id", "")), item.get("name")
                if (not re.fullmatch("[1-9][0-9]*", ident) or ident in seen
                        or not isinstance(name, str) or not name.strip()):
                    raise Stop("Missing/duplicate council identifier or name")
                seen.add(ident)
                results.append({"council_id": ident, "name": name, "year": year,
                                "target_date": None, "schedule_id": None,
                                "status": "in_saved_history" if ident in known else "absent_from_saved_history",
                                "new_publication_verified": False})
    if not results:
        raise Stop("Empty index is not accepted as successful acquisition")
    return {"structure": {"root": "object", "councils_groups": 1,
                          "year_groups": len(container["view_years"]), "councils": len(results)},
            "councils": results,
            "date_limitation": "Only the listed year is known; exact target dates and schedule_id remain unknown",
            "history_completeness": "unknown"}


def validate_approval(path, ledger):
    approval = json.loads(safe_path(path).read_text(encoding="utf-8"))
    if (approval.get("representative_go") is not True
            or approval.get("approved_by") != "representative"
            or approval.get("scope") != "kyoto_ssp_councils_only"
            or approval.get("limits") != LIMITS
            or approval.get("requests") != [{"method": m, "url": u} for m, u in ALLOWED]
            or approval.get("post_parameters") != {"tenant_id": "355", "power_user": "false"}
            or approval.get("ledger_sha256") != LEDGER_SHA
            or approval.get("baseline_sha256") != BASELINE_SHA
            or approval.get("guard_sha256") != digest(Path(__file__).read_bytes())
            or not isinstance(approval.get("reference"), str) or not approval["reference"].strip()
            or not re.fullmatch("[a-z0-9][a-z0-9-]{0,79}", approval.get("run_id", ""))):
        raise Stop("Explicit, hash-bound representative GO for these two requests is required")
    if digest(safe_path(ledger).read_bytes()) != LEDGER_SHA:
        raise Stop("Frozen history ledger hash mismatch")
    return approval


def acquire(approval_path):
    approval = validate_approval(approval_path, LEDGER)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if ledger.get("completeness") != "unknown" or len(ledger.get("meetings", [])) != 750:
        raise Stop("Frozen 750-meeting history structure mismatch")
    safe_path(STORAGE)
    STORAGE.mkdir(parents=True, exist_ok=True)
    trial = STORAGE / approval["run_id"]
    # This durable, unique directory consumes the GO even after failure.
    trial.mkdir(exist_ok=False)
    receipt = {"status": "in_progress", "started_utc": utc(), "limits": LIMITS,
               "representative_reference": approval["reference"],
               "guard_sha256": approval["guard_sha256"], "ledger_sha256": LEDGER_SHA,
               "baseline_sha256": BASELINE_SHA, "attempts": [], "council_comparison": None,
               "normal_scraper_run": False, "gemini_calls": 0, "publication_enabled": False}
    write_json(trial / "receipt.json", receipt)
    cookies, last_finished = [], None
    try:
        for slot, (method, url) in enumerate(ALLOWED, 1):
            if len(receipt["attempts"]) >= 2:
                raise Stop("HTTP attempt budget exhausted")
            if last_finished is not None:
                time.sleep(max(0, last_finished + INTERVAL - time.monotonic()))
            attempt = {"slot": slot, "method": method, "url": url,
                       "reserved_utc": utc(), "result": "not_completed",
                       "http_status": None, "sha256": None}
            receipt["attempts"].append(attempt)
            write_json(trial / "receipt.json", receipt)
            # The worker atomically consumes this individual HTTP slot.
            (trial / f"slot-{slot}.authorized").write_bytes(json_bytes({"method": method, "url": url}))
            response = isolated_request(method, url, cookies, trial, slot)
            last_finished = time.monotonic()
            body = base64.b64decode(response["body_b64"], validate=True)
            if len(body) > MAX_BYTES or response["bytes"] != len(body):
                raise Stop("Worker response size mismatch")
            filename = "01-session.html" if slot == 1 else "02-councils.json"
            (trial / filename).write_bytes(body)
            attempt.update(result="received", started_utc=response["started_utc"],
                           completed_utc=response["completed_utc"], http_status=response["status"],
                           content_type=response["content_type"], response_bytes=len(body),
                           sha256=digest(body), raw_file=filename)
            write_json(trial / "receipt.json", receipt)
            if response["status"] != 200:
                raise Stop("Non-200 response, including redirects; stopping")
            if slot == 1:
                validate_session(body, response["content_type"])
                cookies = response["cookies"]
            else:
                comparison = parse_index(body, response["content_type"], ledger)
                write_json(trial / "council-comparison.json", comparison)
                receipt["council_comparison"] = comparison["structure"]
        if digest(LEDGER.read_bytes()) != LEDGER_SHA:
            raise Stop("Frozen ledger changed during trial")
        receipt["status"] = "council_index_acquired_only"
    except BaseException as exc:
        receipt["status"] = "stopped"
        receipt["failure"] = type(exc).__name__ + ": " + str(exc)
        if receipt["attempts"] and isinstance(exc, Stop):
            receipt["attempts"][-1].update(exc.details)
        raise
    finally:
        receipt["finished_utc"] = utc()
        receipt["http_attempt_slots_consumed"] = len(receipt["attempts"])
        write_json(trial / "receipt.json", receipt)
    return trial


def worker():
    payload = json.load(sys.stdin)
    method, url, slot = payload["method"], payload["url"], payload["slot"]
    if type(slot) is not int or slot not in (1, 2) or (method, url) != ALLOWED[slot - 1]:
        raise Stop("Invalid worker slot")
    trial = safe_path(payload["trial"])
    if trial.parent.resolve() != STORAGE.resolve() or not trial.is_dir():
        raise Stop("Worker requires an approved private trial")
    receipt = json.loads((trial / "receipt.json").read_text(encoding="utf-8"))
    auth = json.loads((trial / f"slot-{slot}.authorized").read_text(encoding="utf-8"))
    if (receipt["status"] != "in_progress" or len(receipt["attempts"]) != slot
            or receipt["guard_sha256"] != digest(Path(__file__).read_bytes())
            or auth != {"method": method, "url": url}):
        raise Stop("Worker authorization mismatch")
    # A second invocation of the same slot cannot send another HTTP request.
    with (trial / f"slot-{slot}.used").open("xb") as f:
        f.write(b"consumed")
    print(json.dumps(_https_once(method, url, payload["cookies"])))


def main():
    if sys.argv[1:] == ["--worker"]:
        try:
            worker()
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__ + ": " + str(exc),
                              "details": exc.details if isinstance(exc, Stop) else {}}))
            raise SystemExit(1)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", required=True)
    args = parser.parse_args()
    try:
        print(acquire(args.approval))
    except (Stop, OSError, ValueError, KeyError, TypeError) as exc:
        print("STOP: " + str(exc))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
