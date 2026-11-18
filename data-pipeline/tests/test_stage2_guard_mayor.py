"""Communication-free Stage 2 parent deadline/journal tests."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates.stage2_guard import supervise,restore_evidence
from mayor_updates.projection import Hold

class Clock:
    now=0
    def __call__(self):return self.now

class Worker:
    simulation_only=True
    def __init__(self,clock):self.clock=clock;self.mode='ok';self.killed=0;self.budgets=[]
    def start_verification(self):self.clock.now+=0.2
    def wait_for_result(self,*,timeout_seconds):
        self.budgets.append(timeout_seconds)
        if self.mode=='hung':self.clock.now+=timeout_seconds;return None
        self.clock.now+=0.3
        result=dict(run_id='b'*32,plan_sha256='a'*64,image_verified=True,
            process_exited=True,all_descendants_exited=True,validation_complete=True)
        if self.mode=='unconfirmed':result['all_descendants_exited']=False
        return result
    def confirm_empty_job(self,*,timeout_seconds):
        self.clock.now+=0.1
        return self.mode!='job_unknown'
    def close_handles(self,*,timeout_seconds):
        self.clock.now+=11 if self.mode=='cleanup_timeout' else 0.1
        return self.mode!='cleanup_failed'
    def kill_and_confirm(self,*,timeout_seconds):
        self.killed+=1;self.budgets.append(timeout_seconds)
        return self.mode!='unconfirmed'

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.clock=Clock();self.worker=Worker(self.clock)
        for target in ('subprocess.Popen','socket.socket.connect','socket.getaddrinfo'):
            p=patch(target,side_effect=AssertionError('Real process/network forbidden'));p.start();self.addCleanup(p.stop)
    def run_guard(self):return supervise(self.root,'b'*32,'a'*64,self.worker,clock=self.clock,simulation=True)
    def test_default_live_gate_no_intent_or_process(self):
        with self.assertRaises(Hold):supervise(self.root,'b'*32,'a'*64,self.worker)
        self.assertFalse(list(self.root.iterdir()))
    def test_success_requires_manual_release_and_includes_cleanup(self):
        result=self.run_guard();self.assertEqual(result['state'],'awaiting_manual_restore')
        self.assertFalse(result['auto_restore']);self.assertGreater(result['elapsed_seconds'],0.6)
        evidence=restore_evidence(self.root,'b'*32,'a'*64)
        self.assertFalse(evidence['restoration_authorized'])
        self.assertFalse((self.root/'HOLD.json').exists())
    def test_failures_latch_hold_and_keep_intent(self):
        for mode in ('hung','unconfirmed','job_unknown','cleanup_timeout','cleanup_failed'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                self.root=Path(t);self.clock=Clock();self.worker=Worker(self.clock);self.worker.mode=mode
                with self.assertRaises(Hold):self.run_guard()
                self.assertTrue((self.root/'run_started.json').exists())
                record=json.loads((self.root/'HOLD.json').read_text())
                self.assertTrue(record['restore_prohibited']);self.assertEqual(self.worker.killed,1)
                with self.assertRaises(Hold):restore_evidence(self.root,'b'*32,'a'*64)
    def test_same_run_cannot_repeat(self):
        self.run_guard();before={p.name:p.read_bytes() for p in self.root.iterdir()}
        with self.assertRaises(Hold):self.run_guard()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
    def test_hung_native_work_uses_reserved_cleanup_budget(self):
        self.worker.mode='hung'
        with self.assertRaises(Hold):self.run_guard()
        self.assertAlmostEqual(self.worker.budgets[0],7.8)
        self.assertAlmostEqual(self.worker.budgets[1],2.0)
    def test_partial_journal_cannot_restore(self):
        (self.root/'run_started.json').write_text('{}')
        with self.assertRaises((Hold,FileNotFoundError,KeyError)):
            restore_evidence(self.root,'b'*32,'a'*64)
    def test_hold_record_storage_failure_never_authorizes_restore(self):
        self.worker.mode='unconfirmed'
        from mayor_updates import stage2_guard as module
        real=module._record
        def fail(root,name,value):
            if name=='HOLD.json':raise OSError('synthetic full disk')
            return real(root,name,value)
        with patch.object(module,'_record',side_effect=fail),self.assertRaises(Hold):self.run_guard()
        self.assertTrue((self.root/'run_started.json').exists())
        self.assertFalse((self.root/'termination_confirmed.json').exists())
    def test_journal_identity_mismatch_rejected(self):
        self.run_guard()
        with self.assertRaises(Hold):restore_evidence(self.root,'foreign','a'*64)




class WorkerPortTests(unittest.TestCase):
    def fixture(self):
        from types import SimpleNamespace
        from mayor_updates.stage2_guard import DormantWindowsWorkerPort
        process=SimpleNamespace(thread=11,handle=12,pid=13)
        calls=[]
        class API:
            processes={13:process};jobs={14}
            def job_policy(self,job):return True,2,False
            def _ok(self,value,label):
                if not value:raise Hold(label)
            def _call(self,dll,name,result,types,*args):calls.append((name,args));return 0 if name=='WaitForSingleObject' else 1
            def job_members(self,job):return ()
            def _close(self,handle):calls.append(('close',(handle,)))
        api=API();port=DormantWindowsWorkerPort(api,process,14,15,lambda:{'synthetic':True})
        return api,port,calls
    def test_event_bounded_wait_and_cleanup(self):
        api,port,calls=self.fixture();port.start_verification()
        self.assertEqual(port.wait_for_result(timeout_seconds=1.2345),{'synthetic':True})
        self.assertIn(('WaitForSingleObject',(12,1234)),calls)
        self.assertTrue(port.confirm_empty_job(timeout_seconds=1))
        self.assertTrue(port.close_handles(timeout_seconds=1));self.assertFalse(api.processes);self.assertFalse(api.jobs)
        with self.assertRaises(Hold):port.start_verification()
    def test_containment_refused_before_event(self):
        api,port,calls=self.fixture()
        with patch.object(api,'job_policy',return_value=(True,3,False)),self.assertRaises(Hold):port.start_verification()
        self.assertFalse(calls)
    def test_real_port_not_activated_by_supervisor(self):
        api,port,calls=self.fixture()
        with tempfile.TemporaryDirectory() as t,self.assertRaises(Hold):
            supervise(t,'b'*32,'a'*64,port,simulation=True)
        self.assertFalse(calls)
    def test_outer_job_kill_and_confirm(self):
        api,port,calls=self.fixture();self.assertTrue(port.kill_and_confirm(timeout_seconds=1))
        self.assertEqual(calls[0],('TerminateJobObject',(14,1)))
        with patch.object(api,'_call',return_value=0):self.assertFalse(port.kill_and_confirm(timeout_seconds=1))

if __name__=='__main__':unittest.main()
