"""Fixture-only Phase 1 regression; never import a scraper or make HTTP calls."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("phase1", Path(__file__).resolve().parents[1] /
                                            "data-pipeline/nagoya_ssp_phase1_guard.py")
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nagoya-phase1-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "OFFLINE-TEST-ONLY.json").write_bytes(g.encode({"scope": g.SCOPE, "synthetic": True}))
        self.approval = {"synthetic": True, "network_enabled": False, "scope": g.SCOPE,
                         "tenant_id": "207", "requests": copy.deepcopy(g.REQUESTS),
                         "limits": dict(g.LIMITS), "pins": g.pins(), "source_registration": "FIXTURE-source",
                         "approval_reference": "FIXTURE-GO-not-real", "principal": "fixture-owner",
                         "storage": str(self.root), "run_id": "fixture-1"}
        self.bind()
        self.fixtures = [self.response(b"<html><title>synthetic Nagoya session</title></html>", "text/html"),
                         self.response(g.encode({"councils": [{"view_years": [{"view_year": "2026",
                            "council_type": [{"councils": [{"council_id": 676, "name": "synthetic meeting"}]}]}]}]}))]
        self.addCleanup(patch.stopall)
        patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")).start()
        patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")).start()
        patch.object(g.time, "sleep").start()
        self.child_mock = patch.object(g, "child", side_effect=lambda fixture, req, seconds: g.worker(fixture, req)).start()

    def bind(self):
        self.binding = {"synthetic": True, "scope": g.SCOPE,
                        "approval_sha256": g.sha(g.encode(self.approval)), "principal": "fixture-owner",
                        "storage": str(self.root), "acl": {"owner": "fixture-owner", "owner_only": True, "simulated": True},
                        "receipt_namespace": "nagoya-ssp-phase1-synthetic"}

    def response(self, raw, media="application/json", **changes):
        value = {"body_base64": base64.b64encode(raw).decode(), "status": 200, "content_type": media,
                 "tls_verify": True, "redirects": 0, "retries": 0, "complete": True,
                 "auth_required": False, "cookies": []}
        value.update(changes)
        return value

    def run_guard(self, **kw):
        return g._stage_synthetic(self.root, self.approval, self.binding, self.fixtures,
                               principal="fixture-owner", **kw)

    def assert_preflight_hold(self):
        with self.assertRaises((g.Hold, ValueError, KeyError)):
            self.run_guard()
        self.assertFalse((self.root / "trials").exists())
        self.child_mock.assert_not_called()

    def test_fixed_order_headers_cookies_and_no_phase2(self):
        self.fixtures[0]["cookies"] = [{"name": "session", "value": "SECRET-FIXTURE",
                                         "domain": g.HOST, "path": "/", "secure": True}]
        receipt = self.run_guard()
        calls = self.child_mock.call_args_list
        self.assertEqual([c.args[1]["method"] for c in calls], ["GET", "POST"])
        self.assertEqual(calls[0].args[1]["cookies"], [])
        self.assertEqual(calls[1].args[1]["cookies"][0]["value"], "SECRET-FIXTURE")
        self.assertEqual(calls[1].args[1]["body"], "tenant_id=207&power_user=false")
        self.assertEqual(calls[1].args[1]["headers"]["Referer"], g.REFERER)
        g.time.sleep.assert_called_once_with(1.2)
        self.assertEqual(len(receipt["attempts"]), 2)
        self.assertFalse(json.loads((self.root / "HEAD").read_bytes())["responses"][1]["parsed"]["phase2_authorized"])
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"SECRET-FIXTURE", path.read_bytes())

    def test_changed_url(self):
        self.approval["requests"][0]["url"] += "?changed=1"
        self.bind()
        self.assert_preflight_hold()

    def test_kyoto_tenant_rejected(self):
        self.approval["tenant_id"] = "355"
        self.bind()
        self.assert_preflight_hold()

    def test_changed_post(self):
        self.approval["requests"][1]["body"] = "tenant_id=207&power_user=true"
        self.bind()
        self.assert_preflight_hold()

    def test_cookie_injection(self):
        with self.assertRaises(g.Hold):
            self.run_guard(initial_cookies=[{"name": "old", "value": "old"}])
        self.child_mock.assert_not_called()

    def test_acl_missing_or_nonowner(self):
        for acl in ({}, {"owner": "other", "owner_only": True, "simulated": True}):
            self.binding["acl"] = acl
            self.assert_preflight_hold()

    def test_pin_mismatch(self):
        self.approval["pins"]["guard"] = "0"*64
        self.bind()
        self.assert_preflight_hold()

    def test_missing_source_approval_binding_principal_receipt(self):
        for field in ("source_registration", "approval_reference", "principal"):
            original = self.approval.pop(field)
            self.bind()
            self.assert_preflight_hold()
            self.approval[field] = original
        self.bind()
        self.binding["receipt_namespace"] = "kyoto"
        self.assert_preflight_hold()

    def test_live_always_refused_before_any_reservation(self):
        with self.assertRaises(g.Hold):
            g.acquire_live(self.root, self.approval, self.binding)
        self.assertFalse(g.LIVE_ENABLED)
        self.assertFalse((self.root / "trials").exists())

    def test_each_response_capacity_and_empty(self):
        for raw in (b"", b"x"*(2*1024*1024+1)):
            with self.assertRaises(g.Hold):
                g.parse_response(1, raw, self.fixtures[0])

    def test_aggregate_capacity_independent(self):
        with patch.dict(g.LIMITS, total_bytes=60):
            self.approval["limits"] = dict(g.LIMITS)
            self.bind()
            with self.assertRaisesRegex(g.Hold, "Aggregate"):
                self.run_guard()
        self.assertFalse((self.root / "HEAD").exists())

    def test_redirect_retry_tls_auth_partial_and_failure_stop(self):
        for changes in ({"status": 302}, {"redirects": 1}, {"retries": 1}, {"tls_verify": False},
                        {"auth_required": True}, {"complete": False}, {"status": 503}):
            value = dict(self.fixtures[0], **changes)
            with self.assertRaises(g.Hold):
                g.parse_response(1, b"<html></html>", value)

    def test_unknown_jsonp_and_structure_hold(self):
        for raw in (b'evil({"councils":[]})', b'jQueryfoo({"councils":[]})', b'{"councils":[]}',
                    b'{"tenant_id":355,"councils":[]}'):
            with self.assertRaises((g.Hold, ValueError)):
                g.parse_response(2, raw, self.fixtures[1])
        payload = base64.b64decode(self.fixtures[1]["body_base64"])
        self.assertEqual(g.parse_response(2, b"jQuery123_456("+payload+b");", self.fixtures[1])["kind"], "index_only")

    def test_failure_keeps_last_good_and_previous_cas(self):
        self.run_guard()
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        self.approval["run_id"] = "fixture-2"
        self.bind()
        self.fixtures[1]["status"] = 503
        with self.assertRaises(g.Hold):
            self.run_guard()
        for path, raw in before.items():
            self.assertEqual((self.root / path).read_bytes(), raw)
        receipt = json.loads((self.root / "trials/fixture-2/receipt.json").read_bytes())
        self.assertEqual(receipt["status"], "HOLD")
        with self.assertRaisesRegex(g.Hold, "already reserved"):
            self.run_guard()

    def test_duplicate_attempt_refused(self):
        self.run_guard()
        self.child_mock.reset_mock()
        with self.assertRaises(g.Hold):
            self.run_guard()
        self.child_mock.assert_not_called()

    def test_worker_timeout_consumes_attempt(self):
        self.child_mock.side_effect = g.Hold("Worker timeout")
        with self.assertRaises(g.Hold):
            self.run_guard()
        self.assertTrue((self.root / "trials/fixture-1/attempt-1.used").exists())
        self.assertFalse((self.root / "trials/fixture-1/attempt-2.used").exists())
        with self.assertRaises(g.Hold):
            self.run_guard()

    def test_parent_phase_deadline(self):
        with patch.object(g.time, "monotonic", side_effect=[0, 61]):
            with self.assertRaisesRegex(g.Hold, "deadline"):
                self.run_guard()
        self.child_mock.assert_not_called()

    def test_commit_failure_keeps_normal_and_cas(self):
        self.run_guard()
        normal = (self.root / "HEAD").read_bytes()
        self.approval["run_id"] = "fixture-2"
        self.bind()
        with patch.object(g.os, "replace", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.run_guard()
        self.assertEqual((self.root / "HEAD").read_bytes(), normal)
        receipt = json.loads((self.root / "trials/fixture-2/receipt.json").read_bytes())
        self.assertEqual(receipt["status"], "synthetic_prepared")
        self.assertEqual(receipt["commit_status"], "not_asserted_by_receipt")

    def test_child_hard_timeout_uses_subprocess_timeout(self):
        # Read the original function, not the patched transport used by other tests.
        spec = importlib.util.spec_from_file_location("phase1_child", g.__file__)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 25)) as proc:
            with self.assertRaises(module.Hold):
                module.child(self.fixtures[0], g.REQUESTS[0], 25)
            self.assertEqual(proc.call_args.kwargs["timeout"], 25)
            self.assertEqual(proc.call_count, 1)

    def test_real_synthetic_child_no_network(self):
        request = dict(g.REQUESTS[0], headers={"Referer": g.REFERER, "X-Requested-With": "XMLHttpRequest"}, cookies=[])
        result = subprocess.run([sys.executable, "-B", g.__file__, "--synthetic-worker"],
                                input=g.encode({"fixture": self.fixtures[0], "request": request}),
                                capture_output=True, timeout=25, check=True)
        self.assertEqual(json.loads(result.stdout), self.fixtures[0])

    def test_outer_phase_has_hard_60s_supervisor(self):
        with patch.object(g.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 60)) as proc:
            with self.assertRaises(g.Hold):
                g.run_synthetic(self.root, self.approval, self.binding, self.fixtures, principal="fixture-owner")
            self.assertEqual(proc.call_args.kwargs["timeout"], 60)
            self.assertIn("--synthetic-phase", proc.call_args.args[0])
        self.assertFalse((self.root / "trials").exists())

    def test_oversized_envelope_rejected_before_launch(self):
        self.fixtures[0]["body_base64"] = "x"*(3*1024*1024)
        self.assert_preflight_hold()

    def test_bounded_worker_output(self):
        def oversized(*args, **kwargs):
            kwargs["stdout"].write(b"x"*101)
        with patch.object(g.subprocess, "run", side_effect=oversized):
            with self.assertRaisesRegex(g.Hold, "output capacity"):
                g.supervised("--synthetic-worker", {}, 25, 100)

    def test_complete_supervised_phase(self):
        # Actual two-child process path, with fixture-only requests and real 1.2s interval.
        result = g.run_synthetic(self.root, self.approval, self.binding, self.fixtures, principal="fixture-owner")
        self.assertEqual(result["status"], "synthetic_prepared")
        self.assertEqual(json.loads((self.root / "HEAD").read_bytes())["run_id"], "fixture-1")


if __name__ == "__main__":
    unittest.main()
