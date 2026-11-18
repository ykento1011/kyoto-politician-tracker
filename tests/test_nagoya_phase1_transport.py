import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("transport", Path(__file__).resolve().parents[1]/
                                            "data-pipeline/nagoya_phase1_transport.py")
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nagoya-fake-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/"OFFLINE-ONLY").write_text(g.SCOPE)
        self.contract = {"synthetic": True, "scope": g.SCOPE, "enabled": False, "network_enabled": False,
                         "pin": g.digest(Path(g.__file__).read_bytes()), "run_id": "test-1"}
        self.contract.update({k: "fixture-only" for k in ("source", "p1", "acl", "actor", "binding", "reservation_authority")})
        self.fixtures = [{"body": "<html>synthetic Nagoya</html>", "headers": [["Content-Type", "text/html"]]},
                         {"body": '{"councils":[{"view_years":[{"view_year":"2026"}]}]}',
                          "headers": [["Content-Type", "application/json"]]}]
        self.addCleanup(patch.stopall)
        patch.object(socket, "create_connection", side_effect=AssertionError("No network")).start()
        patch.object(socket.socket, "connect", side_effect=AssertionError("No network")).start()
        patch.object(g.time, "sleep").start()

    def test_live_disabled_even_with_complete_fixture(self):
        with patch.object(g.http.client, "HTTPSConnection") as connection:
            with self.assertRaises(g.Hold):
                g.acquire_live(self.contract)
            with self.assertRaises(g.Hold):
                g.StreamTransport().request(1, io.BytesIO())
            connection.assert_not_called()
        self.assertFalse(g.enabled)
        self.assertFalse(g.network_enabled)

    def test_fixed_requests_tls_and_cookie_memory(self):
        seen = []
        original = g.FakeConnection.request
        def record(conn, *a, **kw):
            seen.append((a, kw))
            return original(conn, *a, **kw)
        transport = g.StreamTransport(g.FakeConnection)
        self.fixtures[0]["headers"].append(["Set-Cookie", "sid=example; Secure; HttpOnly; Path=/"])
        with patch.object(g.FakeConnection, "request", record):
            transport.request(1, io.BytesIO(), self.fixtures[0])
            transport.request(2, io.BytesIO(), self.fixtures[1])
        self.assertEqual(seen[0][0], ("GET", g.TOP))
        self.assertEqual(seen[1][0], ("POST", g.INDEX))
        self.assertEqual(seen[1][1]["body"], b"tenant_id=207&power_user=false")
        self.assertNotIn("Cookie", seen[0][1]["headers"])
        self.assertEqual(seen[1][1]["headers"]["Cookie"], "sid=example")
        self.assertEqual(seen[1][1]["headers"]["Referer"], g.REFERER)
        self.assertGreaterEqual(g.time.sleep.call_args.args[0], 0)

    def test_wrong_order_cookie_and_duplicate(self):
        t = g.StreamTransport(g.FakeConnection)
        with self.assertRaises(g.Hold): t.request(2, io.BytesIO(), self.fixtures[1])
        t.cookies = ["bad=old"]
        with self.assertRaises(g.Hold): t.request(1, io.BytesIO(), self.fixtures[0])
        t.cookies = []
        t.request(1, io.BytesIO(), self.fixtures[0])
        with self.assertRaises(g.Hold): t.request(1, io.BytesIO(), self.fixtures[0])

    def test_streaming_per_response_never_writes_excess(self):
        sink = io.BytesIO()
        fixture = {"body": "x"*(g.PER_RESPONSE+1)}
        with self.assertRaises(g.Hold):
            g.StreamTransport(g.FakeConnection).request(1, sink, fixture)
        self.assertEqual(len(sink.getvalue()), g.PER_RESPONSE)

    def test_aggregate_bound_independent(self):
        transport = g.StreamTransport(g.FakeConnection)
        transport.total = g.TOTAL-10
        sink = io.BytesIO()
        with self.assertRaises(g.Hold): transport.request(1, sink, self.fixtures[0])
        self.assertLessEqual(len(sink.getvalue()), 10)

    def test_http_errors_compression_auth_and_length(self):
        for attrs in ({"status": 302}, {"status": 401}, {"status": 503},
                      {"headers": [["Location", "/elsewhere"]]},
                      {"headers": [["WWW-Authenticate", "basic"]]},
                      {"headers": [["Content-Encoding", "gzip"]]},
                      {"headers": [["Content-Length", "99999999"]]},
                      {"headers": [["Content-Length", "100"]]},
                      {"headers": [["Set-Cookie", "sid=x; Domain=other.example; Secure"]]},
                      {"headers": [["Set-Cookie", "sid=x; Secure"]]},
                      {"headers": [["Content-Type", "text/html"], ["Content-Type", "text/html"]]}):
            with self.subTest(attrs=attrs):
                t = g.StreamTransport(g.FakeConnection)
                with self.assertRaises(g.Hold): t.request(1, io.BytesIO(), dict(self.fixtures[0], **attrs))
                with self.assertRaises(g.Hold): t.request(1, io.BytesIO(), self.fixtures[0])
                with self.assertRaises(g.Hold): t.request(2, io.BytesIO(), self.fixtures[1])

    def test_unknown_jsonp_wrong_tenant_auth_hold(self):
        for body in (b"evil({})", b"jQueryfoo({})", b'{"tenant_id":355}', b"{}"):
            with self.assertRaises((ValueError, g.Hold)):
                g.inspect_body(body, 2, "application/json")
        with self.assertRaises(g.Hold): g.inspect_body(b"<html><form>login</form></html>", 1, "text/html")

    def test_each_authority_missing_pre_reservation(self):
        for key in ("source", "p1", "acl", "actor", "binding", "reservation_authority", "pin"):
            bad = dict(self.contract)
            bad.pop(key)
            with self.assertRaises(g.Hold): g.stage_fake(self.root, bad, self.fixtures)
            self.assertFalse((self.root/"test-1").exists())

    def test_full_supervised_phase_and_last_good_on_failure(self):
        result = g.run_fake(self.root, self.contract, self.fixtures)
        self.assertEqual(result["status"], "synthetic_prepared_not_committed")
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with self.assertRaises(g.Hold): g.run_fake(self.root, self.contract, self.fixtures)
        self.contract["run_id"] = "test-2"
        self.fixtures[1]["fail"] = True
        with self.assertRaises(g.Hold): g.run_fake(self.root, self.contract, self.fixtures)
        for path, raw in before.items(): self.assertEqual((self.root/path).read_bytes(), raw)
        self.assertTrue((self.root/"test-2/attempt-2.used").exists())
        with self.assertRaises(g.Hold): g.run_fake(self.root, self.contract, self.fixtures)

    def test_hard_timeouts_and_no_retry(self):
        for mode, seconds in (("--fake-response",25),("--fake-phase",60)):
            with patch.object(g.subprocess, "run", side_effect=subprocess.TimeoutExpired("fake",seconds)) as run:
                with self.assertRaises(g.Hold): g.supervise(mode, {"fixture": self.fixtures[0]}, seconds, 100)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.kwargs["timeout"], seconds)

    def test_cookie_response_never_spooled(self):
        fixture = dict(self.fixtures[0])
        fixture["headers"] = fixture["headers"] + [["Set-Cookie", "sid=secret; Secure; Path=/"]]
        with patch.object(g.tempfile, "TemporaryFile", side_effect=AssertionError("No cookie disk spool")):
            result = g.supervise("--fake-response", {"slot": 1, "fixture": fixture, "cookies": [], "total": 0}, 25, 3*1024*1024)
        self.assertEqual(result["cookies"], ["sid=secret"])

    def test_save_failure_keeps_last_good(self):
        g.run_fake(self.root, self.contract, self.fixtures)
        old = (self.root/"HEAD").read_bytes()
        self.contract["run_id"] = "test-2"
        with patch.object(g.os, "replace", side_effect=OSError("fake disk failure")):
            with self.assertRaises(OSError): g.stage_fake(self.root, self.contract, self.fixtures)
        self.assertEqual((self.root/"HEAD").read_bytes(), old)
        self.assertEqual(json.loads((self.root/"test-2/receipt.json").read_bytes())["status"], "synthetic_prepared_not_committed")

    def test_temp_short_write_and_connection_fail_stop(self):
        with patch.object(g.FakeConnection, "getresponse", side_effect=OSError("failed")):
            t = g.StreamTransport(g.FakeConnection)
            with self.assertRaises(OSError): t.request(1, io.BytesIO(), self.fixtures[0])
            with self.assertRaises(g.Hold): t.request(1, io.BytesIO(), self.fixtures[0])
        class ShortSink:
            def write(self, data): return 0
        with self.assertRaises(g.Hold):
            g.StreamTransport(g.FakeConnection).request(1, ShortSink(), self.fixtures[0])
        t = g.StreamTransport(g.FakeConnection)
        with patch.object(g.FakeConnection, "close", side_effect=OSError("close failed")):
            with self.assertRaises(OSError): t.request(1, io.BytesIO(), self.fixtures[0])
        with self.assertRaises(g.Hold): t.request(2, io.BytesIO(), self.fixtures[1])


if __name__ == "__main__":
    unittest.main()
