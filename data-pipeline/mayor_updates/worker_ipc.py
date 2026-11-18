"""Dormant Stage 2 worker provisioning and bounded, single-use private IPC.

No activation parameter exists. Native entry points remain behind the accepted
native source gate; this module's public composition accepts synthetic APIs only.
"""
import ctypes as c
from ctypes import wintypes as w
from dataclasses import asdict, replace
from hashlib import sha256
import json
import math
import ntpath
from pathlib import Path
import re
import secrets
import time

from .launch_contract import FixedLaunch, _spec, _image, simulate_fixed_launch, _fixed_launch
from .native_launch import NativeWindowsAdapter, LockedImage, P, D, EXTENDEDLIMIT
from .projection import Hold
from .stage2_guard import DormantWindowsWorkerPort, _record

WORKER_EXECUTION_ENABLED = False
MAX_REQUEST = 16 * 1024
MAX_REPORT = 4096
CODE_FILES = frozenset(('scripts/Stage2Worker.py', 'data-pipeline/mayor_updates/__init__.py',
    'data-pipeline/mayor_updates/worker_ipc.py', 'data-pipeline/mayor_updates/native_launch.py',
    'data-pipeline/mayor_updates/launch_contract.py', 'data-pipeline/mayor_updates/stage2_guard.py',
    'data-pipeline/mayor_updates/stage2_flow.py',
    'data-pipeline/mayor_updates/projection.py'))


def _json(body, limit):
    if type(body) is not bytes or not 0 < len(body) <= limit: raise Hold('IPC size outside fixed bound')
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise Hold('Duplicate IPC key')
            out[key] = value
        return out
    try:
        value = json.loads(body.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(Hold('Nonfinite IPC number')))
    except (ValueError, UnicodeError, RecursionError) as exc: raise Hold('Invalid IPC JSON') from exc
    if type(value) is not dict: raise Hold('IPC object required')
    return value


def _digest(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value): raise Hold('Fixed SHA/nonce required')


def _actor(spec):
    _spec(spec)
    if not re.fullmatch(r'S-1-5-21-\d+-\d+-\d+-1004', spec.actor_sid):
        raise Hold('Fixed SID1004 required')


def _mode(simulation):
    if simulation is True:return
    if simulation is not False or WORKER_EXECUTION_ENABLED is not True:
        raise Hold('Live worker execution/provisioning disabled')


def _api_mode(api, simulation):
    if getattr(api,'simulation_only',None) is not simulation:
        raise Hold('Worker adapter does not match fixed execution mode')


class SECURITY_ATTRIBUTES(c.Structure):
    _fields_ = [('length', D), ('descriptor', P), ('inherit', c.c_int32)]


class WorkerWindowsAPI(NativeWindowsAdapter):
    """Concrete APIs, all still blocked by NativeWindowsAdapter._fn by default."""

    def __init__(self, spec, *, deadline, clock=time.monotonic):
        super().__init__(spec)
        self.deadline, self.clock = deadline, clock
        self.events = set()

    def remaining(self):
        left = self.deadline-self.clock()
        if not 0 < left <= 10: raise Hold('Worker total deadline expired/invalid')
        return left

    def lock_code(self, path, expected_sha, *, limit=MAX_REQUEST, allow_empty=False):
        """Lock full ancestry and data; no signature claim for pinned Python text."""
        if (not ntpath.isabs(path) or ntpath.normpath(path) != path
                or ':' in path[2:] or path.startswith('\\\\')): raise Hold('Canonical local code/IPC path required')
        parents = []; handle = None
        try:
            parts=[]; cursor=ntpath.dirname(path)
            while cursor:
                parts.append(cursor); nxt=ntpath.dirname(cursor)
                if cursor==nxt: break
                cursor=nxt
            for cursor in reversed(parts):
                h=self._open(cursor,directory=True);parents.append(h)
                self._info(h);self._acl(h,parent=True)
            handle=self._open(path);info=self._info(handle);self._acl(handle)
            size=(info.size_high<<32)|info.size_low
            if info.attributes & 0x10 or info.links!=1 or not (0 <= size <= limit) or (size==0 and not allow_empty):
                raise Hold('Unsafe code/IPC file size/type/links')
            body=self._bytes(handle,info) if size else b''
            if expected_sha is not None and sha256(body).hexdigest()!=expected_sha:
                raise Hold('Pinned code/request SHA differs')
            locked=LockedImage(path,handle,tuple(parents));self.images.append(locked)
            return body
        except Exception:
            self._close(handle)
            for h in reversed(parents):self._close(h)
            raise

    def assert_private_directory(self, path):
        parents=[];parts=[];cursor=ntpath.dirname(path)
        while cursor:
            parts.append(cursor);nxt=ntpath.dirname(cursor)
            if cursor==nxt:break
            cursor=nxt
        try:
            for cursor in reversed(parts):
                parent=self._open(cursor,directory=True);parents.append(parent)
                self._info(parent);self._acl(parent,parent=True)
        except Exception:
            for parent in reversed(parents):self._close(parent)
            raise
        try:h=self._open(path,directory=True)
        except Exception:
            for parent in reversed(parents):self._close(parent)
            raise
        # Keep the directory locked through publication/reading of IPC files.
        self.images.append(LockedImage(path,h,tuple(parents)))
        info=self._info(h)
        if not info.attributes & 0x10:raise Hold('Private IPC directory required')
        self._acl(h)

    def create_worker_job(self):
        job=super().create_job(kill_on_close=True,active_process_limit=1,breakaway=False)
        limits=EXTENDEDLIMIT();limits.basic.flags=0x2000|8;limits.basic.active_limit=2
        self._ok(self._call('kernel32','SetInformationJobObject',w.BOOL,
            [P,c.c_int,P,D],job,9,c.byref(limits),c.sizeof(limits)),'Worker job limits')
        if self.job_policy(job)!=(True,2,False):raise Hold('Worker Job policy differs')
        return job

    def _event_acl(self, handle):
        owner=P();dacl=P();sd=P()
        status=self._call('advapi32','GetSecurityInfo',D,
            [P,D,D,c.POINTER(P),P,c.POINTER(P),P,c.POINTER(P)],
            handle,6,5,c.byref(owner),None,c.byref(dacl),None,c.byref(sd))
        if status!=0:raise Hold('Event security unavailable')
        try:
            if not owner.value or not dacl.value or self._sid(owner.value)!=self.spec.actor_sid:
                raise Hold('Event owner differs')
            control=w.WORD();revision=D()
            self._ok(self._call('advapi32','GetSecurityDescriptorControl',w.BOOL,
                [P,c.POINTER(w.WORD),c.POINTER(D)],sd,c.byref(control),c.byref(revision)),'Event DACL control')
            if not control.value&0x1000:raise Hold('Protected event DACL required')
            count=c.c_ushort.from_address(dacl.value+4).value
            if count!=1:raise Hold('Exact owner-only event ACE required')
            ace=P();self._ok(self._call('advapi32','GetAce',w.BOOL,
                [P,D,c.POINTER(P)],dacl,0,c.byref(ace)),'Event ACE')
            if (c.c_ubyte.from_address(ace.value).value!=0
                    or c.c_ubyte.from_address(ace.value+1).value!=0
                    or c.c_ushort.from_address(ace.value+2).value<12
                    or self._sid(ace.value+8)!=self.spec.actor_sid
                    or D.from_address(ace.value+4).value not in (0x10000000,0x1F0003)):
                raise Hold('Event ACL differs')
        finally:
            if sd.value:self._call('kernel32','LocalFree',P,[P],sd)

    def create_start_event(self, name):
        descriptor=P()
        sddl='O:'+self.spec.actor_sid+'D:P(A;;GA;;;'+self.spec.actor_sid+')'
        self._ok(self._call('advapi32','ConvertStringSecurityDescriptorToSecurityDescriptorW',w.BOOL,
            [w.LPCWSTR,D,c.POINTER(P),P],sddl,1,c.byref(descriptor),None),'Event descriptor')
        try:
            sa=SECURITY_ATTRIBUTES(c.sizeof(SECURITY_ATTRIBUTES),descriptor,False)
            self._call('kernel32','SetLastError',None,[D],0)
            event=self._call('kernel32','CreateEventW',P,[c.POINTER(SECURITY_ATTRIBUTES),w.BOOL,w.BOOL,w.LPCWSTR],
                c.byref(sa),True,False,name)
            error=self._call('kernel32','GetLastError',D,[])
            if not event:raise Hold('Start event creation failed')
            self.events.add(event)
            if error!=0:raise Hold('Start event already exists or creation status is unknown')
            self._event_acl(event)
            return event
        finally:
            if descriptor.value:self._call('kernel32','LocalFree',P,[P],descriptor)

    def open_start_event(self, name):
        event=self._call('kernel32','OpenEventW',P,[D,w.BOOL,w.LPCWSTR],0x120000,False,name)
        if not event:raise Hold('Fixed start event unavailable')
        self.events.add(event);self._event_acl(event)
        return event

    def wait_start_event(self, event):
        status=self._call('kernel32','WaitForSingleObject',D,[P,D],event,int(self.remaining()*1000))
        if status!=0:raise Hold('Start event not signalled within deadline')

    def worker_pid(self):return int(self._call('kernel32','GetCurrentProcessId',D,[]))

    def terminate_and_confirm(self, job, process):
        try:
            if job:self._ok(self._call('kernel32','TerminateJobObject',w.BOOL,[P,D],job,1),'Terminate worker job')
            if process:
                self._ok(self._call('kernel32','TerminateProcess',w.BOOL,[P,D],process.handle,1),'Terminate worker')
                timeout=max(0,min(10,self.deadline-self.clock()))
                if self._call('kernel32','WaitForSingleObject',D,[P,D],process.handle,int(timeout*1000))!=0:return False
            return not job or self.job_members(job)==()
        except Exception:return False

    def close_handles(self,*args):
        failures=[]
        for event in tuple(self.events):
            try:self._close(event);self.events.remove(event)
            except Exception as exc:failures.append(exc)
        try:super().close_handles(*args)
        except Exception as exc:failures.append(exc)
        if failures:raise Hold('Worker cleanup incomplete')


class OneShotReport:
    def __init__(self, api, path, request, request_sha, process, clock):
        self.api,self.path,self.request,self.request_sha=api,path,request,request_sha
        self.process,self.clock,self.consumed=process,clock,False

    def __call__(self):
        if self.consumed:raise Hold('IPC report already consumed')
        self.consumed=True
        if (Path(self.path).parent/'HOLD.json').exists():raise Hold('Worker persistent HOLD')
        left=self.request['deadline']-self.clock()
        if not 0<left<=10:raise Hold('IPC report arrived after deadline')
        if self.api.wait(self.process,timeout_seconds=left)!=0:raise Hold('Worker exit was not successful')
        body=self.api.lock_code(self.path,None,limit=MAX_REPORT)
        report=_json(body,MAX_REPORT)
        expected={'schema_version':1,'run_id':self.request['run_id'],'plan_sha256':self.request['plan_sha256'],
            'nonce':self.request['nonce'],'request_sha256':self.request_sha,'worker_pid':self.process.pid,
            'image_verified':True,'process_exited':True,'all_descendants_exited':True,'validation_complete':True}
        if (report!=expected or type(report.get('schema_version')) is not int
                or type(report.get('worker_pid')) is not int or any(type(report.get(k)) is not bool for k in
                ('image_verified','process_exited','all_descendants_exited','validation_complete'))):
            raise Hold('IPC report identity/evidence differs')
        if self.clock()>=self.request['deadline']:raise Hold('IPC validation exceeded deadline')
        return report


class ProvisionedWorker(DormantWindowsWorkerPort):
    """Owned dormant worker, its locked image/code/IPC and one-shot event/report."""
    def __init__(self, api, process, job, event, reader, before, clock, deadline):
        super().__init__(api,process,job,event,reader)
        self.before,self.clock,self.deadline=before,clock,deadline
        self.simulation_only=getattr(api,'simulation_only',False) is True

    def start_verification(self):
        if self.clock()>=self.deadline:raise Hold('Worker start deadline expired')
        observed=self.api.inspect_process_image(self.process)
        _image(self.api.spec,observed)
        if observed!=self.before:raise Hold('Dormant worker identity changed')
        super().start_verification()
        if self.clock()>=self.deadline:raise Hold('Worker start exceeded deadline')

    def kill_and_confirm(self,*,timeout_seconds):
        if self.closed:return self.termination_verified
        if self.api.processes.get(self.process.pid) is not self.process or self.job not in self.api.jobs:
            return False
        self.termination_verified=self.api.terminate_and_confirm(self.job,self.process) is True
        return self.termination_verified

    def close_handles(self,*,timeout_seconds):
        if self.closed:return True
        self.api.close_handles();self.closed=True
        return True


def provision_worker(root, worker_spec, leaf_spec, *, code_root, code_pins, run_id,
                     plan_sha256, plan_body, deadline, api_factory=WorkerWindowsAPI,
                     simulation=False, clock=time.monotonic):
    """Create/verify/contain a suspended worker, resume only into its start wait.

    A fresh exclusive IPC reservation is retained on failure; no retries or
    fallback. This entry is synthetic-only until separately reviewed activation.
    """
    _mode(simulation)
    _actor(worker_spec);_actor(leaf_spec)
    if type(code_pins) is not dict:raise Hold('Fixed code PIN object required')
    code_pins=dict(code_pins)
    if worker_spec.actor_sid!=leaf_spec.actor_sid:raise Hold('Worker/leaf SID differs')
    if not re.fullmatch('[0-9a-f]{32}',run_id):raise Hold('Fixed run ID required')
    _digest(plan_sha256)
    plan=_json(plan_body,64*1024)
    manifest={'spec':asdict(worker_spec),'code_root':code_root,'code_pins':code_pins}
    if (sha256(plan_body).hexdigest()!=plan_sha256 or plan.get('run_id')!=run_id
            or plan.get('fixed_launch')!=json.loads(json.dumps(asdict(leaf_spec)))
            or plan.get('worker')!=json.loads(json.dumps(manifest))):
        raise Hold('Worker/leaf/code configuration not bound to fixed plan')
    if set(code_pins)!=CODE_FILES:raise Hold('Exact worker code dependency PIN set required')
    for value in code_pins.values():_digest(value)
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not 0<deadline-clock()<=10:
        raise Hold('Invalid total worker deadline')
    bootstrap=ntpath.join(code_root,'scripts','Stage2Worker.py')
    if worker_spec.arguments!=('-I','-S','-B',bootstrap,'--stage2-worker','{request}'):
        raise Hold('Fixed isolated Python bootstrap arguments required')
    root=Path(root).resolve(strict=True)
    if any(root.iterdir()):raise Hold('Empty worker IPC scratch required')
    request_path=str(root/'request.json');report_path=str(root/'report.json')
    nonce=secrets.token_hex(32)
    event_name='Local\\GikaiMikata-Stage2-'+run_id+'-'+nonce
    spec=replace(worker_spec,arguments=(*worker_spec.arguments[:-1],request_path))
    api=api_factory(spec,deadline=deadline,clock=clock)
    _api_mode(api,simulation)
    process=job=event=image=None
    try:
        api.assert_private_directory(str(root))
        api.remaining()
        # Lock all bootstrap/package code and ancestors for the worker lifetime.
        for relative,digest in sorted(code_pins.items()):
            api.lock_code(ntpath.join(code_root,*relative.split('/')),digest,limit=1024*1024,allow_empty=True)
            api.remaining()
        image=api.lock_image(spec.executable,deny_write=True,deny_delete=True,inherit=False,reject_reparse=True)
        before=api.inspect_file(image);_image(spec,before);api.remaining()
        event=api.create_start_event(event_name);api.remaining()
        request={'schema_version':1,'run_id':run_id,'plan_sha256':plan_sha256,'nonce':nonce,
            'deadline':deadline,'actor_sid':spec.actor_sid,'event_name':event_name,
            'report_path':report_path,'leaf':asdict(leaf_spec),'code_root':code_root,'code_pins':code_pins}
        body=json.dumps(request,sort_keys=True).encode()
        _json(body,MAX_REQUEST)
        _record(root,'request.json',request)
        request_sha=sha256(body).hexdigest()
        if api.lock_code(request_path,request_sha,limit=MAX_REQUEST)!=body:raise Hold('IPC request readback differs')
        job=api.create_worker_job();api.remaining()
        process=api.create_process(application_name=spec.executable,arguments=spec.arguments,
            creation_flags=4,inherit_handles=False,actor_sid=spec.actor_sid)
        api.remaining()
        if not api.is_suspended(process):raise Hold('Dormant worker not suspended')
        api.assign_job(job,process)
        if api.job_policy(job)!=(True,2,False) or api.job_members(job)!=(process,):raise Hold('Worker Job membership differs')
        observed=api.inspect_process_image(process);_image(spec,observed)
        if observed!=before or api.inspect_file(image)!=before:raise Hold('Worker image changed')
        api.remaining()
        api.resume(process)  # fixed bootstrap can now only wait on the un-signalled event
        api.remaining()
        reader=OneShotReport(api,report_path,request,request_sha,process,clock)
        port=ProvisionedWorker(api,process,job,event,reader,before,clock,deadline)
        port.ownership_verified=True
        return port
    except Exception as exc:
        failure={'run_id':run_id,'plan_sha256':plan_sha256,'state':'HOLD','restore_prohibited':True,
            'reason':type(exc).__name__,'termination_confirmed':False,'cleanup_complete':False}
        try:_record(root,'HOLD.json',failure)
        except Exception:pass
        try:failure['termination_confirmed']=api.terminate_and_confirm(job,process) is True
        except Exception:pass
        try:api.close_handles();failure['cleanup_complete']=True
        except Exception:pass
        try:_record(root,'failure_cleanup.json',failure)
        except Exception:pass
        raise Hold('Worker provisioning HOLD; no retry or automatic restore') from exc


def worker_entry(request_path, *, api_factory=WorkerWindowsAPI, simulation=False, clock=time.monotonic):
    """Fixed child bootstrap implementation; live command-line entry stays disabled."""
    _mode(simulation)
    root=Path(request_path).resolve(strict=True).parent
    if str(Path(request_path))!=str(root/'request.json'):raise Hold('Fixed canonical request filename required')
    if any((root/name).exists() for name in ('worker_started.json','report.json','HOLD.json')):
        raise Hold('Worker request already consumed; no replay')
    # First parse is untrusted routing only. All bytes are independently locked
    # and re-read before any event or leaf operation can be used.
    with open(request_path,'rb') as stream:body=stream.read(MAX_REQUEST+1)
    request=_json(body,MAX_REQUEST)
    if set(request)!=set(('schema_version','run_id','plan_sha256','nonce','deadline','actor_sid',
            'event_name','report_path','leaf','code_root','code_pins')) or type(request['schema_version']) is not int or request['schema_version']!=1:
        raise Hold('Worker request schema differs')
    _digest(request['nonce']);_digest(request['plan_sha256'])
    if (type(request['deadline']) not in (int,float) or not math.isfinite(request['deadline'])
            or not 0 < request['deadline']-clock() <= 10):raise Hold('Finite remaining deadline required')
    if not re.fullmatch('[0-9a-f]{32}',request['run_id']):raise Hold('Worker run ID differs')
    leaf=dict(request['leaf']);leaf['arguments']=tuple(leaf['arguments']);leaf=FixedLaunch(**leaf)
    _actor(leaf)
    if (request['actor_sid']!=leaf.actor_sid or request['report_path']!=str(root/'report.json')
            or request['event_name']!='Local\\GikaiMikata-Stage2-'+request['run_id']+'-'+request['nonce']
            or set(request['code_pins'])!=CODE_FILES):raise Hold('Fixed worker IPC binding differs')
    api=api_factory(leaf,deadline=request['deadline'],clock=clock)
    _api_mode(api,simulation)
    event=None
    try:
        if api._actor()!=leaf.actor_sid:raise Hold('Worker actual SID differs')
        api.assert_private_directory(str(root));api.remaining()
        if api.lock_code(str(root/'request.json'),sha256(body).hexdigest(),limit=MAX_REQUEST)!=body:
            raise Hold('Worker request changed after parse')
        for relative,digest in sorted(request['code_pins'].items()):
            _digest(digest);api.lock_code(ntpath.join(request['code_root'],*relative.split('/')),digest,limit=1024*1024,allow_empty=True)
            api.remaining()
        _record(root,'worker_started.json',{'run_id':request['run_id'],'nonce':request['nonce'],
            'request_sha256':sha256(body).hexdigest(),'state':'waiting_for_fixed_start'})
        event=api.open_start_event(request['event_name']);api.wait_start_event(event);api.remaining()
        # Reuse the fixed launch and the shared remaining-time wrapper.
        from .stage2_flow import _BudgetAPI
        leaf_api=api_factory(leaf,deadline=request['deadline'],clock=clock)
        _api_mode(leaf_api,simulation)
        budget_api=_BudgetAPI(leaf_api,clock,request['deadline'],1)
        result=(simulate_fixed_launch(leaf,budget_api,simulation=True) if simulation
                else _fixed_launch(leaf,budget_api))
        api.remaining()
        if result['image_verified'] is not True or result['exit_code']!=0:raise Hold('Leaf evidence incomplete')
        report={'schema_version':1,'run_id':request['run_id'],'plan_sha256':request['plan_sha256'],
            'nonce':request['nonce'],'request_sha256':sha256(body).hexdigest(),'worker_pid':api.worker_pid(),
            'image_verified':True,'process_exited':True,'all_descendants_exited':True,'validation_complete':True}
        _json(json.dumps(report,sort_keys=True).encode(),MAX_REPORT)
        _record(root,'report.json',report)
        api.remaining()
        return report
    except Exception as exc:
        try:_record(root,'HOLD.json',{'state':'HOLD','run_id':request['run_id'],
            'restore_prohibited':True,'reason':type(exc).__name__})
        except Exception:pass
        raise Hold('Worker failed; preserve isolation') from exc
    finally:api.close_handles()
