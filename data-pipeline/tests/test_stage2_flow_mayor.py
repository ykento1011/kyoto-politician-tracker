"""Integrated synthetic launch/job/deadline/HOLD/offline-handoff; no real OS."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates.launch_contract import FixedLaunch, ImageEvidence
from mayor_updates.projection import Hold
from mayor_updates import stage2_flow as flow
from mayor_updates.stage2_guard import restore_evidence
from test_launch_contract_mayor import FakeWinAPI
from test_native_launch_mayor import MockNative


class BudgetFake(FakeWinAPI):
    def wait(self, process, **kw):
        self.wait_budget = kw['timeout_seconds']
        if self.failure == 'wait': raise TimeoutError('synthetic hung process')
        self.running = True
        return self.exit_code


class FlowTests(unittest.TestCase):
    def setUp(self):
        for target in ('subprocess.Popen', 'socket.socket.connect', 'socket.getaddrinfo'):
            p = patch(target, side_effect=AssertionError('Real process/network forbidden'))
            p.start(); self.addCleanup(p.stop)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'scratch'; self.root.mkdir()
        self.script = Path(__file__).resolve().parents[2]/'scripts/Restore-Stage2Firewall.ps1'
        self.script_sha = sha256(self.script.read_bytes()).hexdigest()
        self.spec = FixedLaunch(r'C:\fixture\pwsh.exe', ('-NoProfile', '-NonInteractive', '-Command', 'exit 0'),
            sha256(b'synthetic image').hexdigest(), 'b'*64, 'S-1-5-21-1004')
        evidence = ImageEvidence(self.spec.executable, 'volume:file1', b'synthetic image', 'b'*64,
            True, self.spec.actor_sid, self.spec.actor_sid, True, True, True, 1, True)
        self.api = BudgetFake(evidence)
        self.now = 0.0

    def run_flow(self, **kw):
        args = dict(run_id='a'*32, restore_script=self.script,
            expected_restore_sha256=self.script_sha,
            expected_plan_sha256=sha256(flow.plan_bytes(self.spec, 'a'*32, self.script_sha)).hexdigest(),
            simulation=True, clock=lambda:self.now)
        args.update(kw)
        return flow.simulate_stage2(self.root, self.spec, self.api, **args)

    def test_single_launch_job_journal_plan_and_manual_handoff(self):
        result = self.run_flow()
        self.assertEqual((self.api.creations, self.api.resumes, self.api.closed), (1,1,1))
        self.assertLessEqual(self.api.wait_budget, 8)
        self.assertFalse(result['real_execution_authorized'])
        self.assertFalse(result['restoration_authorized'])
        self.assertEqual(result['operator_acknowledgement'], 'NOT_PROVIDED')
        self.assertFalse((self.root/'journal/operator_release.json').exists())
        self.assertEqual(result['plan_sha256'], sha256((self.root/'plan.json').read_bytes()).hexdigest())
        self.assertEqual(result['plan_sha256'], result['proposal_sha256'])
        plan = json.loads((self.root/'plan.json').read_bytes())
        self.assertEqual(plan['fixed_launch']['executable'], self.spec.executable)
        self.assertEqual([r['direction'] for r in plan['added_rules']], ['Inbound','Outbound'])
        with self.assertRaises(Hold):restore_evidence(self.root/'journal','a'*32,result['plan_sha256'])
        flow.commit_flow_success(self.root,result)
        self.assertFalse(restore_evidence(self.root/'journal','a'*32,result['plan_sha256'])['restoration_authorized'])

    def test_live_gate_and_native_adapter_rejected_before_writes(self):
        with self.assertRaises(Hold): self.run_flow(simulation=False)
        self.api.simulation_only=False
        with self.assertRaises(Hold): self.run_flow()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.api.creations,0)

    def test_disabled_native_api_composes_using_only_mock_winapi(self):
        self.spec=replace(self.spec,image_sha256=sha256(b'synthetic native image').hexdigest())
        self.api=MockNative(self.spec)
        self.run_flow()
        calls=[name for name,args in self.api.calls]
        self.assertEqual(calls.count('CreateProcessW'),1)
        self.assertEqual(calls.count('ResumeThread'),1)
        self.assertIn('AssignProcessToJobObject',calls)
        waits=[args[1] for name,args in self.api.calls if name=='WaitForSingleObject']
        self.assertTrue(waits)
        self.assertLessEqual(max(waits),8000)

    def test_native_wait_rejects_unbounded_or_invalid_budget(self):
        from mayor_updates.native_launch import SuspendedProcess
        api=MockNative(self.spec)
        for value in (11,True,0,-1,float('nan'),float('inf'),'8'):
            with self.subTest(value=value),self.assertRaises(Hold):
                api.wait(SuspendedProcess(1,2,3),timeout_seconds=value)
        self.assertFalse(api.calls)

    def test_plan_script_or_fixed_argument_change_blocks_before_launch(self):
        for values in ({'expected_plan_sha256':'c'*64}, {'expected_restore_sha256':'c'*64}):
            with self.subTest(values=values), self.assertRaises(Hold): self.run_flow(**values)
        old_digest=sha256(flow.plan_bytes(self.spec,'a'*32,self.script_sha)).hexdigest()
        self.spec=replace(self.spec, arguments=('unapproved',))
        with self.assertRaises(Hold): self.run_flow(expected_plan_sha256=old_digest)
        self.assertEqual(self.api.creations,0)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_process_failure_latches_hold_and_never_creates_release(self):
        self.api.failure='wait'; self.api.termination_confirmed=False
        with self.assertRaises(Hold): self.run_flow()
        self.assertTrue((self.root/'HOLD.json').exists())
        self.assertTrue((self.root/'journal/HOLD.json').exists())
        self.assertFalse((self.root/'restore_request.json').exists())
        self.assertFalse((self.root/'journal/supervisor_success.json').exists())
        self.assertEqual(self.api.terminations,1)

    def test_budget_includes_preflight_launch_and_final_handoff(self):
        original = flow._record
        def late(root,name,value):
            original(root,name,value)
            if name=='restore_request.json': self.now=11
        with patch.object(flow,'_record',side_effect=late),self.assertRaises(Hold):self.run_flow()
        self.assertTrue((self.root/'journal/HOLD.json').exists())
        with self.assertRaises(Hold):restore_evidence(self.root/'journal','a'*32,
            sha256((self.root/'plan.json').read_bytes()).hexdigest())

    def test_hung_verification_preserves_hold_cleanup_and_no_resume(self):
        original=self.api.inspect_file
        def late(image):
            self.now=9
            return original(image)
        self.api.inspect_file=late
        with self.assertRaises(Hold):self.run_flow()
        self.assertEqual(self.api.resumes,0)
        self.assertTrue((self.root/'journal/HOLD.json').exists())

    def test_late_handoff_and_failed_hold_storage_cannot_commit_success(self):
        original=flow._record
        def late(root,name,value):
            if name=='HOLD.json':raise OSError('synthetic full disk')
            original(root,name,value)
            if name=='restore_request.json':self.now=11
        with patch.object(flow,'_record',side_effect=late),self.assertRaises(Hold):self.run_flow()
        self.assertFalse((self.root/'journal/supervisor_success.json').exists())
        with self.assertRaises(Hold):restore_evidence(self.root/'journal','a'*32,
            sha256((self.root/'plan.json').read_bytes()).hexdigest())

    def test_repeat_and_existing_journal_never_overwritten(self):
        self.run_flow()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(Hold):self.run_flow()
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(self.api.creations,1)

    def test_signature_job_and_child_identity_fail_closed(self):
        for mode in ('signature','job','image'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                self.root=Path(t)
                evidence=ImageEvidence(self.spec.executable, 'volume:file1', b'synthetic image', 'b'*64,
                    True, self.spec.actor_sid, self.spec.actor_sid, True, True, True, 1, True)
                self.api=BudgetFake(evidence)
                if mode=='signature':self.api.evidence=replace(self.api.evidence,signature_valid=False)
                elif mode=='job':self.api.policy=(True,2,False)
                else:self.api.observed=replace(self.api.evidence,file_id='replaced')
                with self.assertRaises(Hold):self.run_flow()
                self.assertEqual(self.api.resumes,0)
                self.assertTrue((self.root/'HOLD.json').exists())


if __name__=='__main__':unittest.main()
