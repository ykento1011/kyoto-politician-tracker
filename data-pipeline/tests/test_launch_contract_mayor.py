"""Synthetic WinAPI only: no processes, network, private files or OS changes."""
from dataclasses import replace
import hashlib
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates.launch_contract import FixedLaunch, ImageEvidence, simulate_fixed_launch, CREATE_SUSPENDED
from mayor_updates.projection import Hold


class FakeWinAPI:
    simulation_only = True

    def __init__(self, evidence):
        self.evidence = evidence; self.observed = evidence; self.after = evidence
        self.resumes = 0; self.terminations = 0; self.closed = 0; self.creations = 0
        self.failure = None; self.running = False
        self.policy = (True, 1, False); self.members = ('process',)
        self.suspended = True; self.termination_confirmed = True; self.exit_code = 0

    def lock_image(self, path, **kw):
        assert kw == dict(deny_write=True, deny_delete=True, inherit=False, reject_reparse=True)
        return 'image'
    def inspect_file(self, image): return self.after if self.creations else self.evidence
    def create_job(self, **kw):
        assert kw == dict(kill_on_close=True, active_process_limit=1, breakaway=False)
        return 'job'
    def job_policy(self, job): return self.policy
    def create_process(self, **kw):
        self.creations += 1; self.request = kw
        if self.failure == 'create': raise OSError('mock API failure')
        return 'process'
    def is_suspended(self, process): return self.suspended
    def assign_job(self, job, process):
        if self.failure == 'assign': raise OSError('mock assignment failure')
    def job_members(self, job): return () if self.running else self.members
    def inspect_process_image(self, process):
        if self.failure == 'query': raise OSError('mock query failure')
        return self.observed
    def resume(self, process): self.resumes += 1
    def wait(self, process, **kw):
        assert kw == {'timeout_seconds': 10}
        if self.failure == 'wait': raise TimeoutError('mock timeout')
        self.running = True
        return self.exit_code
    def terminate_and_confirm(self, job, process):
        self.terminations += 1; return self.termination_confirmed
    def close_handles(self, *handles): self.closed += 1


class LaunchTests(unittest.TestCase):
    def setUp(self):
        for target in ('subprocess.Popen', 'socket.socket.connect', 'socket.getaddrinfo'):
            p = patch(target, side_effect=AssertionError('Real OS process/network forbidden'))
            p.start(); self.addCleanup(p.stop)
        self.spec = FixedLaunch(r'C:\fixture\pwsh.exe', ('-NoProfile', '-NonInteractive', '-Command', 'fixed synthetic ACL'),
            hashlib.sha256(b'synthetic image').hexdigest(), 'b'*64, 'S-1-5-21-1004')
        self.evidence = ImageEvidence(self.spec.executable, 'volume:file-1', b'synthetic image', 'b'*64,
            True, self.spec.actor_sid, self.spec.actor_sid, True, True, True, 1, True)
        self.api = FakeWinAPI(self.evidence)

    def run_fake(self): return simulate_fixed_launch(self.spec, self.api, simulation=True)
    def assert_pre_resume_hold(self):
        with self.assertRaises(Hold): self.run_fake()
        self.assertEqual(self.api.resumes, 0)

    def test_disabled_by_default_and_no_live_adapter(self):
        self.assertFalse(self.spec.enabled)
        with self.assertRaises(Hold): simulate_fixed_launch(self.spec, self.api)
        self.api.simulation_only = False
        self.assert_pre_resume_hold()
        self.assertEqual(self.api.creations, 0)

    def test_enabled_or_invalid_config_is_rejected(self):
        for kw in ({'enabled': True}, {'enabled': 0}, {'timeout_seconds': 11}, {'timeout_seconds': True},
                   {'arguments': ['other']}, {'arguments': ('bad\0arg',)}, {'image_sha256': 'bad'},
                   {'signer_sha256': 'bad'}, {'actor_sid': 'unknown'}):
            with self.subTest(kw=kw), self.assertRaises(Hold):
                simulate_fixed_launch(replace(self.spec, **kw), self.api, simulation=True)
        self.assertEqual(self.api.creations, 0)

    def test_noncanonical_paths_rejected(self):
        for path in ('pwsh.exe', r'\\host\share\pwsh.exe', r'\\?\C:\fixture\pwsh.exe',
                     r'C:\fixture\..\pwsh.exe', 'C:/fixture/pwsh.exe', r'C:\fixture\pwsh.exe:stream',
                     r'C:\fixture.\pwsh.exe'):
            with self.subTest(path=path), self.assertRaises(Hold):
                simulate_fixed_launch(replace(self.spec, executable=path), self.api, simulation=True)

    def test_exact_suspended_request_and_byte_verification(self):
        result = self.run_fake()
        self.assertEqual(self.api.request, dict(application_name=self.spec.executable,
            arguments=self.spec.arguments, creation_flags=CREATE_SUSPENDED,
            inherit_handles=False, actor_sid=self.spec.actor_sid))
        self.assertEqual((self.api.resumes, self.api.terminations, self.api.closed), (1, 0, 1))
        self.assertFalse(result['real_execution_authorized'])

    def test_preflight_bytes_signature_acl_links_and_lock_fail_closed(self):
        for kw in ({'body': b'changed'}, {'signer_sha256': 'c'*64}, {'signature_valid': False},
                   {'owner_sid': 'S-1-5-21-2000'}, {'actor_sid': 'S-1-5-21-2000'}, {'owner_only': False},
                   {'parents_safe': False}, {'reparse_free': False}, {'link_count': 2},
                   {'deny_write_delete': False}, {'file_id': ''}):
            with self.subTest(kw=kw):
                self.api = FakeWinAPI(replace(self.evidence, **kw)); self.assert_pre_resume_hold()
                self.assertEqual(self.api.creations, 0)

    def test_same_path_different_process_bytes_or_identity_rejected(self):
        for kw in ({'body': b'other'}, {'file_id': 'different'}, {'path': r'C:\other\pwsh.exe'},
                   {'signer_sha256': 'c'*64}, {'signature_valid': False}, {'reparse_free': False}):
            with self.subTest(kw=kw):
                self.api = FakeWinAPI(self.evidence); self.api.observed = replace(self.evidence, **kw)
                self.assert_pre_resume_hold(); self.assertEqual(self.api.terminations, 1)

    def test_replacement_under_held_handle_rejected(self):
        self.api.after = replace(self.evidence, file_id='replaced')
        self.assert_pre_resume_hold()

    def test_job_policy_and_child_escape_rejected(self):
        for policy in ((False, 1, False), (True, 2, False), (True, 1, True), (1, True, 0)):
            self.api = FakeWinAPI(self.evidence); self.api.policy = policy
            self.assert_pre_resume_hold()
        self.api = FakeWinAPI(self.evidence); self.api.members = ('process', 'unexpected-child')
        self.assert_pre_resume_hold()

    def test_null_handles_stop_without_resume(self):
        for name in ('lock_image', 'create_job', 'create_process'):
            self.api = FakeWinAPI(self.evidence)
            with patch.object(self.api, name, return_value=None): self.assert_pre_resume_hold()

    def test_api_failures_never_resume(self):
        for failure in ('create', 'assign', 'query'):
            self.api = FakeWinAPI(self.evidence); self.api.failure = failure
            self.assert_pre_resume_hold(); self.assertEqual(self.api.terminations, 1)
        self.api = FakeWinAPI(self.evidence); self.api.suspended = False
        self.assert_pre_resume_hold()

    def test_timeout_failure_and_unconfirmed_termination(self):
        self.api.failure = 'wait'
        with self.assertRaises(Hold): self.run_fake()
        self.assertEqual((self.api.resumes, self.api.terminations), (1, 1))
        self.api = FakeWinAPI(self.evidence); self.api.failure = 'query'; self.api.termination_confirmed = False
        with self.assertRaisesRegex(Hold, 'Termination unconfirmed'): self.run_fake()
        self.assertEqual(self.api.resumes, 0)


if __name__ == '__main__': unittest.main()
