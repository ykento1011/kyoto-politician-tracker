"""Worker/IPC synthetic WinAPI and real nonsecret temporary-file protocol only."""
import ctypes as c
from dataclasses import asdict, replace
from hashlib import sha256
import json
import importlib.util
import marshal
import ntpath
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import worker_ipc as m
from mayor_updates import native_launch as n
from mayor_updates.launch_contract import FixedLaunch
from mayor_updates.projection import Hold
from mayor_updates.stage2_flow import plan_bytes,simulate_stage2,commit_flow_success
from mayor_updates.stage2_guard import supervise
from test_native_launch_mayor import MockNative
from test_native_root_mayor import RootFixture


class World:
    now=0.0
    mode='ok'
    signalled=False
    finished=False
    exit_code=0
    def __init__(self):self.instances=[];self.bodies={};self.root=None
    def clock(self):return self.now
    def factory(self,spec,*,deadline,clock):
        api=FakeAPI(spec,deadline=deadline,clock=clock,world=self)
        self.instances.append(api)
        return api


class FakeAPI(m.WorkerWindowsAPI,MockNative):
    simulation_only=True
    def __init__(self,spec,*,deadline,clock,world):
        super().__init__(spec,deadline=deadline,clock=clock)
        self.world=world;self.parent=not world.instances
    def _actor(self,process_handle=None):
        if self.world.mode=='wrong_sid':return 'S-1-5-21-11-22-33-9999'
        return self.spec.actor_sid
    def _event_acl(self,handle):
        if self.world.mode=='event_acl':raise Hold('synthetic bad event ACL')
    def assert_private_directory(self,path):
        self.world.root=Path(path)
        if self.world.mode=='directory_acl':raise Hold('synthetic bad private ACL')
    def lock_code(self,path,expected_sha,*,limit=m.MAX_REQUEST,allow_empty=False):
        if path in self.world.bodies:body=self.world.bodies[path]
        else:body=Path(path).read_bytes()
        if self.world.mode=='code_sha' and path in self.world.bodies:body+=b'changed'
        if len(body)>limit or (not body and not allow_empty):raise Hold('Synthetic bound')
        if expected_sha is not None and sha256(body).hexdigest()!=expected_sha:raise Hold('Synthetic PIN differs')
        return body
    def _fn(self,dll,name,result,types):
        base=MockNative._fn(self,dll,name,result,types)
        def call(*a):
            if name in ('ConvertStringSecurityDescriptorToSecurityDescriptorW','CreateEventW','GetLastError',
                        'SetLastError','OpenEventW','SetEvent','GetCurrentProcessId','LocalFree'):
                self.calls.append((name,a))
                if name=='ConvertStringSecurityDescriptorToSecurityDescriptorW':a[2]._obj.value=2;return 1
                if name in ('CreateEventW','OpenEventW'):return 55
                if name=='GetLastError':return 183 if self.world.mode=='event_collision' else (5 if self.world.mode=='event_status' else 0)
                if name=='GetCurrentProcessId':return 123
                if name=='SetEvent':
                    self.world.signalled=True
                    if self.world.mode in ('no_report','termination_unknown'):return 1
                    try:m.worker_entry(str(self.world.root/'request.json'),api_factory=self.world.factory,
                        simulation=True,clock=self.world.clock)
                    except Exception:self.world.exit_code=1
                    report=self.world.root/'report.json'
                    if report.exists():
                        data=json.loads(report.read_bytes())
                        if self.world.mode in ('nonce','run_id','plan_sha256','request_sha256','worker_pid','flag_type'):
                            key={'flag_type':'image_verified'}.get(self.world.mode,self.world.mode)
                            data[key]=1 if self.world.mode=='flag_type' else ('f'*64 if key!='worker_pid' else 999)
                            report.write_text(json.dumps(data))
                        if self.world.mode=='oversize':report.write_bytes(b' '* (m.MAX_REPORT+1))
                        if self.world.mode=='duplicate_key':report.write_bytes(b'{"run_id":"x","run_id":"y"}')
                    if self.world.mode=='report_late':self.world.now=11
                    if self.world.mode=='exit_failure':self.world.exit_code=1
                    self.world.finished=True;self.ended=True
                    return 1
                return 1
            if name=='WaitForSingleObject' and a[0]==55:
                self.calls.append((name,a));return 0 if self.world.signalled else 258
            if self.parent and name=='WaitForSingleObject':
                self.calls.append((name,a))
                if not self.world.finished:
                    self.world.now+=a[1]/1000;return 258
                return 0
            if self.parent and name=='GetExitCodeProcess':
                self.calls.append((name,a));a[1]._obj.value=self.world.exit_code;return 1
            if self.world.mode=='assign_failure' and name=='AssignProcessToJobObject':
                self.calls.append((name,a));return 0
            value=base(*a)
            if self.parent and name=='CreateProcessW' and self.world.mode=='late_create':self.world.now=11
            if self.parent and name in ('TerminateProcess','TerminateJobObject'):
                self.world.finished=self.world.mode!='termination_unknown'
            return value
        return call


class WorkerTests(unittest.TestCase):
    def setUp(self):
        for target in ('subprocess.Popen','socket.socket.connect','socket.getaddrinfo'):
            p=patch(target,side_effect=AssertionError('Real process/network forbidden'));p.start();self.addCleanup(p.stop)
        p=patch.object(c,'WinDLL',create=True,side_effect=AssertionError('Actual native library load forbidden'))
        p.start();self.addCleanup(p.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ipc=self.root/'ipc';self.ipc.mkdir()
        self.journal=self.root/'journal';self.journal.mkdir()
        self.world=World();self.code_root=r'C:\fixed'
        self.pins={}
        for relative in m.CODE_FILES:
            body=b'' if relative.endswith('__init__.py') else relative.encode()
            self.world.bodies[ntpath.join(self.code_root,*relative.split('/'))]=body
            self.pins[relative]=sha256(body).hexdigest()
        self.leaf=FixedLaunch(r'C:\fixture\pwsh.exe',('-NoProfile','-NonInteractive','-Command','exit 0'),
            sha256(b'synthetic native image').hexdigest(),'b'*64,'S-1-5-21-11-22-33-1004')
        self.worker=replace(self.leaf,executable=r'C:\fixture\python.exe',arguments=(
            '-I','-S','-B',r'C:\fixed\scripts\Stage2Worker.py','--stage2-worker','{request}'))
        self.manifest={'spec':asdict(self.worker),'code_root':self.code_root,'code_pins':self.pins}
        self.body=plan_bytes(self.leaf,'a'*32,'b'*64,worker_manifest=self.manifest)
        self.digest=sha256(self.body).hexdigest()
    def provision(self,**kwargs):
        args=dict(code_root=self.code_root,code_pins=self.pins,run_id='a'*32,plan_sha256=self.digest,
            plan_body=self.body,deadline=10,api_factory=self.world.factory,simulation=True,clock=self.world.clock)
        args.update(kwargs)
        return m.provision_worker(self.ipc,self.worker,self.leaf,**args)
    def execute(self):
        port=self.provision()
        return port,supervise(self.journal,'a'*32,self.digest,port,simulation=True,clock=self.world.clock)
    def test_dormant_suspended_exact_actor_job_and_event(self):
        port=self.provision();api=self.world.instances[0]
        self.assertFalse(self.world.signalled)
        self.assertFalse((self.ipc/'report.json').exists())
        request=next(a for name,a in api.calls if name=='CreateProcessW')
        self.assertEqual(request[0],self.worker.executable)
        self.assertFalse(request[4]);self.assertTrue(request[5]&4)
        self.assertEqual(api.job_policy(port.job),(True,2,False))
        self.assertEqual(api.job_members(port.job),(port.process,))
        event=next(a for name,a in api.calls if name=='CreateEventW')
        saved=json.loads((self.ipc/'request.json').read_bytes())
        self.assertEqual(event[3],saved['event_name']);self.assertFalse(event[2])
        self.assertFalse(m.WORKER_EXECUTION_ENABLED);self.assertFalse(n.NATIVE_EXECUTION_ENABLED)
    def test_full_worker_start_leaf_report_and_cleanup(self):
        port,result=self.execute()
        self.assertEqual(result['state'],'awaiting_manual_restore')
        self.assertTrue(port.closed);self.assertTrue(self.world.signalled)
        self.assertEqual(len([a for api in self.world.instances for name,a in api.calls if name=='CreateProcessW']),2)
        self.assertTrue((self.ipc/'worker_started.json').exists())
        report=json.loads((self.ipc/'report.json').read_bytes())
        self.assertEqual(report['request_sha256'],sha256((self.ipc/'request.json').read_bytes()).hexdigest())
        with self.assertRaises(Hold):port.report_reader()
        with self.assertRaises(Hold):port.start_verification()
    def test_integrates_existing_stage2_flow_and_fixed_manifest(self):
        root=self.root/'flow';root.mkdir()
        script=Path(__file__).resolve().parents[2]/'scripts/Restore-Stage2Firewall.ps1'
        script_sha=sha256(script.read_bytes()).hexdigest()
        body=plan_bytes(self.leaf,'a'*32,script_sha,worker_manifest=self.manifest)
        result=simulate_stage2(root,self.leaf,FakeAPI(self.leaf,deadline=10,clock=self.world.clock,world=self.world),
            run_id='a'*32,expected_plan_sha256=sha256(body).hexdigest(),restore_script=script,
            expected_restore_sha256=script_sha,worker_spec=self.worker,code_root=self.code_root,code_pins=self.pins,
            worker_api_factory=self.world.factory,simulation=True,clock=self.world.clock)
        self.assertFalse(commit_flow_success(root,result)['restoration_authorized'])
    def test_live_and_bad_configuration_before_any_api(self):
        for values in ({'simulation':False},{'deadline':True},{'deadline':float('nan')},
                {'code_pins':{}},{'plan_sha256':'c'*64}):
            with self.subTest(values=values),self.assertRaises(Hold):self.provision(**values)
        self.assertFalse(self.world.instances)
    def test_report_identity_size_types_and_deadline_fail_closed(self):
        for mode in ('nonce','run_id','plan_sha256','request_sha256','worker_pid','flag_type',
                     'oversize','duplicate_key','report_late','exit_failure','no_report'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                self.ipc=Path(t)/'ipc';self.ipc.mkdir();self.journal=Path(t)/'journal';self.journal.mkdir()
                bodies=self.world.bodies;self.world=World();self.world.bodies=bodies;self.world.mode=mode
                with self.assertRaises(Hold):self.execute()
                self.assertTrue((self.journal/'HOLD.json').exists())
                self.assertFalse((self.journal/'supervisor_success.json').exists())
    def test_provisioning_failure_stop_and_persistent_hold(self):
        for mode in ('wrong_sid','directory_acl','code_sha','event_collision','event_status','event_acl','assign_failure','late_create'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                self.ipc=Path(t);bodies=self.world.bodies;self.world=World();self.world.bodies=bodies;self.world.mode=mode
                with self.assertRaises(Hold):self.provision()
                self.assertTrue((self.ipc/'HOLD.json').exists())
                self.assertTrue((self.ipc/'failure_cleanup.json').exists())
                if mode in ('assign_failure','late_create'):
                    calls=[name for name,a in self.world.instances[0].calls]
                    self.assertIn('TerminateProcess',calls);self.assertNotIn('ResumeThread',calls)
    def test_no_job_ownership_no_start_signal(self):
        port=self.provision();port.api.jobs.clear()
        with self.assertRaises(Hold):port.start_verification()
        self.assertFalse(self.world.signalled)
        self.assertFalse(port.kill_and_confirm(timeout_seconds=1))
    def test_worker_request_replay_never_starts_second_leaf(self):
        self.execute();count=len(self.world.instances)
        with self.assertRaises(Hold):m.worker_entry(str(self.ipc/'request.json'),
            api_factory=self.world.factory,simulation=True,clock=self.world.clock)
        self.assertEqual(len(self.world.instances),count)
    def test_request_reservation_not_removed_or_reused(self):
        self.provision();before=(self.ipc/'request.json').read_bytes()
        with self.assertRaises(Hold):self.provision()
        self.assertEqual((self.ipc/'request.json').read_bytes(),before)
        self.assertEqual(len(self.world.instances),1)
    def test_unconfirmed_stop_is_durable_hold_and_never_success(self):
        self.world.mode='termination_unknown'
        with self.assertRaises(Hold):self.execute()
        outcome=json.loads((self.journal/'failure_cleanup.json').read_bytes())
        self.assertFalse(outcome['termination_confirmed'])
        self.assertTrue((self.journal/'HOLD.json').exists())
        self.assertFalse((self.journal/'supervisor_success.json').exists())
    def test_native_entry_and_bootstrap_cannot_activate(self):
        with self.assertRaises(Hold):self.provision(api_factory=m.WorkerWindowsAPI)
        with self.assertRaises(Hold):m.worker_entry('unused')
        import runpy
        script=Path(__file__).resolve().parents[2]/'scripts/Stage2Worker.py'
        module=runpy.run_path(str(script))
        self.assertFalse(module['LIVE_BOOTSTRAP_ENABLED'])
        with self.assertRaises(SystemExit):module['main']()
        from mayor_updates import stage2_flow,stage2_guard
        self.assertFalse(stage2_guard.LIVE_SUPERVISION_ENABLED)
        self.assertFalse(stage2_flow.LIVE_FLOW_ENABLED)
        with self.assertRaises(Hold):stage2_flow.run_native_stage2(self.root,self.leaf,
            run_id='a'*32,expected_plan_sha256=self.digest,restore_script='unused',expected_restore_sha256='b'*64,
            worker_spec=self.worker,code_root=self.code_root,code_pins=self.pins)
    def test_kernel_event_acl_exact_owner_and_protection(self):
        for owner,aces,protected,passes in ((self.leaf.actor_sid,[(0,0,0x10000000,self.leaf.actor_sid)],True,True),
                ('S-1-5-18',[(0,0,0x10000000,self.leaf.actor_sid)],True,False),
                (self.leaf.actor_sid,[(0,0,0x10000000,'S-1-1-0')],True,False),
                (self.leaf.actor_sid,[(0,0,0x10000000,self.leaf.actor_sid)],False,False)):
            fixture=RootFixture(owner=owner,aces=aces,protected=protected)
            api=m.WorkerWindowsAPI(self.worker,deadline=10,clock=self.world.clock)
            with patch.object(api,'_fn',side_effect=fixture.factory),patch.object(api,'_sid',side_effect=lambda p:fixture.sids[p]):
                if passes:api._event_acl(10)
                else:
                    with self.assertRaises(Hold):api._event_acl(10)

    def test_bootstrap_ignores_conflicting_unchecked_bytecode_and_unlisted_modules(self):
        import runpy
        script=Path(__file__).resolve().parents[2]/'scripts/Stage2Worker.py'
        loader_class=runpy.run_path(str(script))['PinnedPackage']
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);package=root/'data-pipeline/mayor_updates';package.mkdir(parents=True)
            pins={}
            for relative in m.CODE_FILES:
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
                body=b"value='pinned source'\n" if relative.endswith('worker_ipc.py') else b''
                path.write_bytes(body);pins[relative]=sha256(body).hexdigest()
            source=package/'worker_ipc.py'
            cache=Path(importlib.util.cache_from_source(str(source)));cache.parent.mkdir(exist_ok=True)
            # PEP 552 unchecked-hash cache with different executable content.
            cache.write_bytes(importlib.util.MAGIC_NUMBER+(1).to_bytes(4,'little')+b'0'*8+
                marshal.dumps(compile("value='UNPINNED bytecode'",str(source),'exec')))
            loader=loader_class(root,pins)
            spec=loader.find_spec('mayor_updates.worker_ipc')
            module=importlib.util.module_from_spec(spec);loader.exec_module(module)
            self.assertEqual(module.value,'pinned source')
            with self.assertRaises(ImportError):loader.find_spec('mayor_updates.unapproved')
            source.write_bytes(b"value='changed source'")
            with self.assertRaises(ImportError):loader.exec_module(module)

if __name__=='__main__':unittest.main()
