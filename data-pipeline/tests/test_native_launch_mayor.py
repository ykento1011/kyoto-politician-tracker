"""Native adapter tests: all Windows entry points are synthetic Python functions."""
import ctypes as c
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import native_launch as n
from mayor_updates.launch_contract import FixedLaunch, simulate_fixed_launch
from mayor_updates.projection import Hold


class MockNative(n.NativeWindowsAdapter):
    simulation_only = True
    def __init__(self, spec):
        super().__init__(spec); self.calls=[]; self.opened={}; self.count=10
        self.limits=None; self.ended=False; self.assigned=False; self.fail=None
        self.bad_path=False; self.changed_bytes=False; self.children=False
        self.bad_signature=False; self.bad_acl=False; self.bad_links=False
        self.body=b'synthetic native image'
    def _actor(self, process_handle=None): return self.spec.actor_sid
    def _acl(self, handle, **kw):
        if self.bad_acl: raise Hold('mock ACL failed')
        return self.spec.actor_sid
    def _signature(self, locked):
        if self.bad_signature: raise Hold('mock signature failed')
        return self.spec.signer_sha256
    def _fn(self,dll,name,result,types):
        def call(*a):
            self.calls.append((name,a))
            if self.fail==name:return 0
            if name=='CreateFileW':
                self.count+=1;self.opened[self.count]=a[0];return self.count
            if name=='GetFileInformationByHandle':
                info=a[1]._obj;info.volume=1;info.index_low=5;info.links=2 if self.bad_links else 1
                info.attributes=0 if self.opened[a[0]].endswith('.exe') else 0x10
                info.size_low=len(self.body);return 1
            if name=='SetFilePointerEx':return 1
            if name=='ReadFile':
                body=b'x'*len(self.body) if self.changed_bytes and len(self.processes) else self.body
                c.memmove(a[1],body,len(body));a[3]._obj.value=len(body);return 1
            if name=='CreateJobObjectW':return 50
            if name=='SetInformationJobObject':
                self.limits=n.EXTENDEDLIMIT.from_buffer_copy(c.string_at(a[2],a[3]));return 1
            if name=='QueryInformationJobObject':
                if a[1]==9:c.memmove(a[2],c.byref(self.limits),c.sizeof(self.limits))
                else:
                    count=0 if self.ended or not self.assigned else (2 if self.children else 1)
                    (n.D*2).from_buffer(a[2])[:]=[count,count]
                    if count:(n.Q*count).from_buffer(a[2],8)[:]=[123,999][:count]
                return 1
            if name=='CreateProcessW':
                pi=a[-1]._obj;pi.process=100;pi.thread=101;pi.pid=123;pi.tid=124;return 1
            if name=='AssignProcessToJobObject':self.assigned=True;return 1
            if name=='QueryFullProcessImageNameW':
                a[2].value=r'C:\other\pwsh.exe' if self.bad_path else self.spec.executable
                a[3]._obj.value=len(a[2].value);return 1
            if name=='ResumeThread':return 1
            if name=='WaitForSingleObject':self.ended=True;return 0
            if name=='GetExitCodeProcess':a[1]._obj.value=0;return 1
            if name in ('TerminateJobObject','TerminateProcess'):self.ended=True;return 1
            if name=='CloseHandle':return 1
            raise AssertionError('Unexpected native call '+name)
        return call


class NativeTests(unittest.TestCase):
    def setUp(self):
        for target in ('subprocess.Popen','socket.socket.connect','socket.getaddrinfo'):
            p=patch(target,side_effect=AssertionError('Real process/network forbidden'));p.start();self.addCleanup(p.stop)
        self.spec=FixedLaunch(r'C:\fixture\pwsh.exe',('-NoProfile','-NonInteractive','-Command','synthetic'),
            sha256(b'synthetic native image').hexdigest(),'b'*64,'S-1-5-21-1004')
        self.api=MockNative(self.spec)
    def launch(self):return simulate_fixed_launch(self.spec,self.api,simulation=True)
    def test_native_default_gate_never_loads_library(self):
        api=n.NativeWindowsAdapter(self.spec)
        with patch.object(c,'WinDLL',create=True) as loader:
            with self.assertRaises(Hold):api.lock_image(self.spec.executable,deny_write=True,deny_delete=True,inherit=False,reject_reparse=True)
            loader.assert_not_called()
        self.assertFalse(n.NATIVE_EXECUTION_ENABLED)
        with self.assertRaises(Hold):simulate_fixed_launch(self.spec,api,simulation=True)
    def test_complete_mocked_native_state_machine(self):
        self.assertTrue(self.launch()['image_verified'])
        create=[a for name,a in self.api.calls if name=='CreateProcessW'][0]
        self.assertEqual(create[0],self.spec.executable)
        self.assertEqual(create[5],n.CREATE_SUSPENDED|0x08000000)
        self.assertFalse(create[4]);self.assertIn('-NoProfile',create[1].value)
        names=[name for name,a in self.api.calls]
        self.assertLess(names.index('AssignProcessToJobObject'),names.index('ResumeThread'))
        self.assertLess(names.index('QueryFullProcessImageNameW'),names.index('ResumeThread'))
        self.assertFalse(self.api.processes);self.assertFalse(self.api.jobs);self.assertFalse(self.api.images)
    def test_metadata_failures_never_resume(self):
        for field in ('bad_path','changed_bytes','children','bad_signature','bad_acl','bad_links'):
            with self.subTest(field=field):
                self.api=MockNative(self.spec);setattr(self.api,field,True)
                with self.assertRaises(Hold):self.launch()
                self.assertNotIn('ResumeThread',[name for name,a in self.api.calls])
    def test_native_failure_paths(self):
        for name in ('GetFileInformationByHandle','ReadFile','CreateJobObjectW',
                'SetInformationJobObject','QueryInformationJobObject','CreateProcessW',
                'AssignProcessToJobObject','QueryFullProcessImageNameW'):
            with self.subTest(name=name):
                self.api=MockNative(self.spec);self.api.fail=name
                with self.assertRaises(Hold):self.launch()
                self.assertNotIn('ResumeThread',[name for name,a in self.api.calls])
    def test_create_request_and_actor_mismatch(self):
        with self.assertRaises(Hold):self.api.create_process(application_name='wrong')
        with patch.object(self.api,'_actor',return_value='different'):
            with self.assertRaises(Hold):self.api.create_process(application_name=self.spec.executable,
                arguments=self.spec.arguments,creation_flags=4,inherit_handles=False,actor_sid=self.spec.actor_sid)
        self.assertFalse(self.api.calls)
    def test_unknown_job_process_is_refused(self):
        self.api.assigned=True
        with self.assertRaises(Hold):self.api.job_members(50)
    def test_termination_unconfirmed_is_false(self):
        self.api.fail='TerminateProcess'
        self.assertFalse(self.api.terminate_and_confirm(None,n.SuspendedProcess(100,101,123)))
    def test_unknown_suspend_count_is_hold(self):
        proc=n.SuspendedProcess(100,101,123);self.api.processes[123]=proc
        self.api.fail='ResumeThread'
        with self.assertRaises(Hold):self.api.resume(proc)
        self.assertTrue(proc.suspended)
    def test_unsigned_or_uncached_trust_stops_and_uses_cache_only(self):
        api=n.NativeWindowsAdapter(self.spec);calls=[]
        def factory(dll,name,result,types):
            def call(*a):
                calls.append(name)
                if name=='WinVerifyTrust':
                    data=a[2]._obj
                    self.assertEqual(data.flags,0x1080);self.assertEqual(data.revocation,1)
                    self.assertEqual(c.cast(data.file,c.POINTER(n.TRUSTFILE)).contents.handle,10)
                    return -1
                raise AssertionError(name)
            return call
        with patch.object(api,'_fn',side_effect=factory):
            with self.assertRaises(Hold):api._signature(n.LockedImage(self.spec.executable,10,()))
        self.assertEqual(calls,['WinVerifyTrust'])
    def test_process_image_must_use_child_token(self):
        api=MockNative(self.spec);proc=n.SuspendedProcess(100,101,123)
        with patch.object(api,'_actor',return_value='other') as actor:
            with self.assertRaises(Hold):api.inspect_process_image(proc)
            actor.assert_called_once_with(100)
        self.assertFalse(api.calls)



class NativeObservationTests(unittest.TestCase):
    def setUp(self):
        self.spec=FixedLaunch(r'C:\fixture\pwsh.exe',(),sha256(b'image').hexdigest(),
            'b'*64,'S-1-5-21-1004')
        self.api=n.NativeWindowsAdapter(self.spec)
    def test_verified_signer_digest_and_state_closed(self):
        encoded=c.create_string_buffer(b'actual verified signer')
        cert=n.CERTCONTEXT();cert.encoded=c.cast(encoded,n.P);cert.length=len(encoded.raw)-1
        head=n.PROVIDERCERT_HEAD();head.size=c.sizeof(head);head.cert=c.pointer(cert)
        actions=[]
        def factory(dll,name,result,types):
            def call(*a):
                if name=='WinVerifyTrust':
                    data=a[2]._obj;actions.append(data.action)
                    if data.action==1:data.state=123
                    return 0
                if name=='WTHelperProvDataFromStateData':return 111
                if name=='WTHelperGetProvSignerFromChain':return 222
                if name=='WTHelperGetProvCertFromChain':return c.addressof(head)
                raise AssertionError(name)
            return call
        with patch.object(self.api,'_fn',side_effect=factory):
            digest=self.api._signature(n.LockedImage(self.spec.executable,10,()))
        self.assertEqual(digest,sha256(b'actual verified signer').hexdigest());self.assertEqual(actions,[1,2])
    def test_acl_parsing_other_allow_and_unknown_ace(self):
        acl=c.create_string_buffer(8);c.c_ushort.from_buffer(acl,4).value=1
        ace=c.create_string_buffer(24);c.c_ushort.from_buffer(ace,2).value=24
        n.D.from_buffer(ace,4).value=0x1f01ff
        def factory(dll,name,result,types):
            def call(*a):
                if name=='GetSecurityInfo':
                    a[3]._obj.value=1;a[5]._obj.value=c.addressof(acl);a[7]._obj.value=99;return 0
                if name=='GetAce':a[2]._obj.value=c.addressof(ace);return 1
                if name=='LocalFree':return 0
                raise AssertionError(name)
            return call
        with patch.object(self.api,'_fn',side_effect=factory),patch.object(self.api,'_sid',return_value=self.spec.actor_sid):
            self.assertEqual(self.api._acl(10),self.spec.actor_sid)
            c.c_ubyte.from_buffer(ace).value=9
            with self.assertRaises(Hold):self.api._acl(10)
        c.c_ubyte.from_buffer(ace).value=0
        with patch.object(self.api,'_fn',side_effect=factory),patch.object(self.api,'_sid',side_effect=[self.spec.actor_sid,'S-1-5-21-9999']):
            with self.assertRaises(Hold):self.api._acl(10)
    def test_elevated_actor_refused_and_token_closed(self):
        closed=[]
        def factory(dll,name,result,types):
            def call(*a):
                if name=='OpenProcessToken':a[2]._obj.value=100;return 1
                if name=='GetTokenInformation':
                    self.assertEqual(a[1],20);a[2]._obj.value=1;return 1
                if name=='CloseHandle':closed.append(a[0]);return 1
                raise AssertionError(name)
            return call
        with patch.object(self.api,'_fn',side_effect=factory):
            with self.assertRaisesRegex(Hold,'Elevated'):self.api._actor()
        self.assertEqual(closed,[100])


if __name__=='__main__':unittest.main()
