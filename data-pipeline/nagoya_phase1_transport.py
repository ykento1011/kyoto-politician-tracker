"""Disabled Nagoya Phase 1 live transport; offline harness uses fake connections only.

No CLI can enable the network. Real authority/ACL/P1 verification is a future gate.
"""
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import time

enabled = False
network_enabled = False
HOST = "ssp.kaigiroku.net"
TOP = "/tenant/nagoya/SpTop.html"
INDEX = "/dnp/search/councils/index"
BODY = "tenant_id=207&power_user=false"
REFERER = "https://ssp.kaigiroku.net/tenant/nagoya/SpMinuteBrowse.html"
REQUESTS = (("GET", TOP, ""), ("POST", INDEX, BODY))
PER_RESPONSE = 2 * 1024 * 1024
TOTAL = 4 * 1024 * 1024
SCOPE = "nagoya-ssp-phase1"


class Hold(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def acquire_live(authority=None):
    # Deliberately no Boolean/config toggle can turn this into an active client.
    raise Hold("Network disabled: real source approval/P1/ACL/actor/binding/reservation gate unimplemented")


def _live_connection(context):
    acquire_live()
    # Unreachable until a separately reviewed real authority gate is supplied.
    # http.client has no automatic redirects/retry/proxy discovery.
    return http.client.HTTPSConnection(HOST, timeout=25, context=context)


class StreamTransport:
    """One-shot HTTP streaming implementation; default connection factory refuses live.

    Production must not accept an injected connection. Injection is used exclusively
    by the fake harness; no caller-supplied host/path/body/headers are sent.
    """
    def __init__(self, connection_factory=None):
        if connection_factory is not None and connection_factory is not FakeConnection:
            raise Hold("Only the built-in fake transport may be injected")
        self.factory = connection_factory
        self.used = set()
        self.cookies = []
        self.total = 0
        self.last_finish = None
        self.failed = False

    def request(self, slot, sink, fixture=None):
        if self.factory is None:
            acquire_live()
        if self.failed or slot != len(self.used) + 1 or slot not in (1, 2) or slot in self.used:
            raise Hold("Wrong order or duplicate attempt")
        if slot == 1 and self.cookies:
            raise Hold("Session must start with an empty cookie jar")
        if self.last_finish is not None:
            time.sleep(max(0, 1.2 - (time.monotonic() - self.last_finish)))
        self.used.add(slot)  # failures permanently consume this instance's attempt
        self.failed = True  # only a fully received response clears terminal HOLD
        method, path, body = REQUESTS[slot-1]
        context = ssl.create_default_context()
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise Hold("TLS certificate/hostname verification required")
        headers = {"Referer": REFERER, "X-Requested-With": "XMLHttpRequest",
                   "Accept-Encoding": "identity",
                   "User-Agent": "GikaiNoMikataBot/1.0 (+https://gikai-mikata.jp; info@gikai-mikata.jp)"}
        if method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.cookies:
            headers["Cookie"] = "; ".join(self.cookies)
        connection = (_live_connection(context) if self.factory is None else
                      self.factory(HOST, timeout=25, context=context, fixture=fixture))
        try:
            connection.request(method, path, body=body.encode(), headers=headers)
            response = connection.getresponse()
            if response.status != 200 or response.getheader("Location") or response.getheader("WWW-Authenticate"):
                raise Hold("HTTP redirect/auth/error; no follow-up or retry")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise Hold("Compressed responses unsupported; do not bypass byte limits")
            length = response.getheader("Content-Length")
            if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) > PER_RESPONSE):
                raise Hold("Invalid/excess Content-Length")
            if length is not None and int(length) > TOTAL-self.total:
                raise Hold("Aggregate Content-Length exceeds remaining budget")
            written = 0
            while True:
                remaining = min(PER_RESPONSE-written, TOTAL-self.total)
                chunk = response.read(min(65536, remaining+1))
                if not chunk:
                    break
                if len(chunk) > remaining:
                    raise Hold("Streaming response/aggregate byte limit")
                if sink.write(chunk) != len(chunk):
                    raise Hold("Incomplete temporary write")
                written += len(chunk)
                self.total += len(chunk)
            if not written or (length is not None and written != int(length)):
                raise Hold("Empty/truncated response")
            # Conservative cookie policy: unknown attributes/paths are HOLD, never copied.
            cookies = []
            for key, value in response.getheaders():
                if key.lower() != "set-cookie":
                    continue
                if len(value) > 4096 or len(cookies) >= 20:
                    raise Hold("Cookie capacity")
                parts = [part.strip() for part in value.split(";")]
                if not re.fullmatch(r"[A-Za-z0-9_-]+=[A-Za-z0-9._~-]+", parts[0]):
                    raise Hold("Unknown session cookie")
                attrs = {p.lower() for p in parts[1:]}
                allowed = {"secure", "httponly", "path=/", "samesite=lax", "samesite=strict", "domain="+HOST}
                if "secure" not in attrs or "path=/" not in attrs or not attrs <= allowed:
                    raise Hold("Unknown/foreign cookie attributes")
                cookies.append(parts[0])
            if cookies:
                self.cookies = cookies
            self.failed = False
            return {"status": 200, "bytes": written, "content_type": response.getheader("Content-Type", ""),
                    "method": method, "url": "https://"+HOST+path}
        finally:
            connection.close()
            self.last_finish = time.monotonic()


class FakeConnection:
    """Deterministic fake: never resolves DNS, opens sockets, or spawns HTTP tools."""
    def __init__(self, host, timeout, context, fixture):
        if host != HOST or timeout != 25 or not context.check_hostname:
            raise Hold("Wrong transport contract")
        self.fixture = fixture
        self.sent = None

    def request(self, method, path, body, headers):
        self.sent = (method, path, body, headers)
        if self.fixture.get("fail"):
            raise Hold("Synthetic connection failure")

    def getresponse(self):
        return FakeResponse(self.fixture)

    def close(self):
        pass


class FakeResponse:
    def __init__(self, fixture):
        self.status = fixture.get("status", 200)
        self.headers = fixture.get("headers", [])
        self.body = io.BytesIO(fixture["body"].encode())

    def getheader(self, name, default=None):
        values = [v for k, v in self.headers if k.lower() == name.lower()]
        if len(values) > 1:
            raise Hold("Duplicate response header")
        return values[0] if values else default

    def getheaders(self):
        return self.headers

    def read(self, size):
        return self.body.read(size)


def inspect_body(raw, slot, media):
    text = raw.decode("utf-8-sig").strip()
    if slot == 1:
        if media.split(";", 1)[0] != "text/html" or "<html" not in text.lower() or re.search(r"password|<form", text, re.I):
            raise Hold("Unexpected session/authentication HTML")
        return
    if media.split(";", 1)[0] not in ("application/json", "text/javascript", "application/javascript"):
        raise Hold("Unexpected index media")
    if text.startswith("jQuery"):
        match = re.fullmatch(r"jQuery[0-9]+_[0-9]+\((\{.*\})\);?", text, re.S)
        if not match:
            raise Hold("Unknown JSONP")
        text = match[1]
    data = json.loads(text)
    if str(data.get("tenant_id", "207")) != "207":
        raise Hold("Wrong tenant")
    rows = data.get("councils")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0].get("view_years"), list) or not rows[0]["view_years"]:
        raise Hold("Unknown index structure")


def exclusive(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def stage_fake(root, contract, fixtures):
    """Internal worker. Requires a synthetic-only root; no real authority accepted."""
    root = Path(root)
    if not root.is_absolute() or not root.is_dir():
        raise Hold("Absolute existing fixture root required")
    for part in (root, *root.parents):
        if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400 or (part/".git").exists():
            raise Hold("Checkout/reparse boundary")
    for part in root.rglob("*"):
        if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise Hold("Reparse state")
    if (root/"OFFLINE-ONLY").read_text() != SCOPE:
        raise Hold("Synthetic root marker missing")
    required = {"source", "p1", "acl", "actor", "binding", "reservation_authority"}
    if (contract.get("synthetic") is not True or contract.get("scope") != SCOPE
            or contract.get("enabled") is not False or contract.get("network_enabled") is not False
            or contract.get("pin") != digest(Path(__file__).read_bytes())
            or any(contract.get(k) != "fixture-only" for k in required)):
        raise Hold("Missing fixture authority; real authority is unsupported")
    run = contract.get("run_id", "")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", run) or len(fixtures) != 2:
        raise Hold("Invalid run/fixtures")
    lock = root/"LOCK"
    exclusive(lock, b"synthetic")
    try:
        trial = root/run
        trial.mkdir()  # irreversible under normal runner; no cleanup/retry function
        head = root/"HEAD"
        if head.exists():
            old = json.loads(head.read_bytes())
            for key in old["sha256"]:
                if not re.fullmatch(r"[0-9a-f]{64}", key) or digest((root/"cas"/key).read_bytes()) != key:
                    raise Hold("Previous CAS mismatch")
        (root/"cas").mkdir(exist_ok=True)
        receipt = {"synthetic": True, "run": run, "scope": SCOPE, "attempts": [], "status": "HOLD"}
        keys = []
        try:
            # One phase child owns state. Each request is supervised in a read-only
            # response child; it has no filesystem path or reservation capability.
            total = 0
            cookies = []
            for slot in (1, 2):
                if slot == 2:
                    time.sleep(1.2)
                exclusive(trial/f"attempt-{slot}.used", encode({"slot": slot, "scope": SCOPE}))
                receipt["attempts"].append({"slot": slot, "status": "unknown"})
                payload = {"slot": slot, "fixture": fixtures[slot-1], "cookies": cookies, "total": total}
                result = supervise("--fake-response", payload, 25, 3*1024*1024)
                import base64
                raw = base64.b64decode(result.pop("body"), validate=True)
                total += len(raw)
                if len(raw) > PER_RESPONSE or total > TOTAL:
                    raise Hold("Worker output capacity")
                cookies = result.pop("cookies")  # secret values excluded from receipt/CAS
                inspect_body(raw, slot, result["content_type"])
                key = digest(raw)
                target = root/"cas"/key
                if not target.exists():
                    exclusive(target, raw)
                if target.read_bytes() != raw:
                    raise Hold("CAS readback mismatch")
                keys.append(key)
                receipt["attempts"][-1].update(result, sha256=key)
            receipt["status"] = "synthetic_prepared_not_committed"
            exclusive(trial/"receipt.json", encode(receipt))
            exclusive(trial/"next-head", encode({"synthetic": True, "run": run, "sha256": keys}))
            os.replace(trial/"next-head", head)
            return receipt
        except Exception:
            if not (trial/"receipt.json").exists():
                exclusive(trial/"receipt.json", encode(receipt))
            raise
    finally:
        lock.unlink()


def supervise(mode, payload, seconds, bound):
    if mode == "--fake-response":
        # Fixed fake worker output is bounded before sending; Cookie never spooled.
        fixture = payload.get("fixture", {})
        if (type(fixture.get("body")) is not str or len(fixture["body"].encode()) > PER_RESPONSE+1
                or len(encode({k:v for k,v in fixture.items() if k != "body"})) > 16384
                or len(encode(payload.get("cookies", []))) > 16384):
            raise Hold("Fake worker envelope capacity")
        try:
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), mode], input=encode(payload),
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=seconds, check=True)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
            raise Hold("Worker failed/unknown; no retry") from exc
        if len(result.stdout) > bound:
            raise Hold("Worker envelope capacity")
        return json.loads(result.stdout)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), mode], input=encode(payload),
                           stdout=output, stderr=errors, timeout=seconds, check=True)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
            raise Hold("Worker failed/unknown; no retry") from exc
        output.seek(0)
        raw = output.read(bound+1)
        if len(raw) > bound:
            raise Hold("Worker envelope capacity")
        return json.loads(raw)


def run_fake(root, contract, fixtures):
    if type(fixtures) is not list or len(fixtures) != 2:
        raise Hold("Exactly two fake responses")
    for item in fixtures:
        if type(item.get("body")) is not str or len(item["body"].encode()) > PER_RESPONSE+1 or len(encode({k:v for k,v in item.items() if k != "body"})) > 16384:
            raise Hold("Fixture envelope capacity")
    if len(encode(contract)) > 16384:
        raise Hold("Contract capacity")
    return supervise("--fake-phase", {"root": str(root), "contract": contract, "fixtures": fixtures}, 60, 65536)


if __name__ == "__main__":
    if sys.argv[1:] not in (["--fake-phase"], ["--fake-response"]):
        acquire_live()
    raw = sys.stdin.buffer.read(26*1024*1024+1)
    if len(raw) > 26*1024*1024:
        raise Hold("Input capacity")
    payload = json.loads(raw)
    if sys.argv[1] == "--fake-phase":
        result = stage_fake(**payload)
    else:
        import base64
        transport = StreamTransport(FakeConnection)
        slot = payload["slot"]
        if slot == 2:
            transport.used = {1}
            transport.cookies = payload["cookies"]
            transport.total = payload["total"]
        sink = io.BytesIO()  # at most remaining 4MiB/2MiB; never writes raw temp files
        result = transport.request(slot, sink, payload["fixture"])
        result.update(body=base64.b64encode(sink.getvalue()).decode(), cookies=transport.cookies)
    sys.stdout.buffer.write(encode(result))
