"""Stage 2 parent deadline and append-only recovery journal. No live entry point.

The worker must already be dormant under a kill-on-close containment job before
beginning validation; start_verification signals it, not an unbounded CreateProcess.
The worker protocol is injected. No live worker factory or activation is shipped.
"""
import ctypes as c
import json
import os
import re
from pathlib import Path
import tempfile
import time
from .projection import Hold


def _record(root, name, value):
    destination = root / name
    fd, temporary = tempfile.mkstemp(prefix='.stage2-', dir=root)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True); stream.flush(); os.fsync(stream.fileno())
        if os.name == 'nt': os.rename(temp, destination)
        else: os.link(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def supervise(root, run_id, plan_sha256, worker, *, clock=time.monotonic,
              total_seconds=10, cleanup_reserve=2, simulation=False):
    """Bound all validation/work/cleanup decisions in one monotonic parent window.

    Only mock workers can run here. The separate parent kills the worker's whole
    job when a native verification API hangs, rather than trusting that worker to
    check a cooperative deadline. Real worker setup/OS binding is a separate gate.
    No Firewall restoration or automatic permission to remove rules is performed.
    """
    if simulation is not True or getattr(worker, 'simulation_only', None) is not True:
        raise Hold('Live Stage 2 supervision is disabled')
    if (type(total_seconds) is not int or not 3 <= total_seconds <= 10
            or type(cleanup_reserve) is not int or not 1 <= cleanup_reserve < total_seconds
            or not isinstance(run_id, str) or not re.fullmatch('[0-9a-f]{32}', run_id)
            or not isinstance(plan_sha256, str) or len(plan_sha256) != 64
            or any(c not in '0123456789abcdef' for c in plan_sha256)):
        raise Hold('Invalid fixed Stage 2 deadline/identity')
    root = Path(root).resolve(strict=True)
    if any(root.iterdir()): raise Hold('New empty run journal required')
    started = clock(); deadline = started + total_seconds
    base = {'schema_version':1, 'run_id':run_id, 'plan_sha256':plan_sha256,
            'auto_restore':False, 'total_seconds':total_seconds}
    # Missing success acknowledgement means restore denied, even if later writes
    # fail or the supervisor crashes. Never remove this intent on failure.
    _record(root, 'run_started.json', {**base, 'state':'restore_blocked'})
    def remaining(reserve=0):
        value = deadline - clock() - reserve
        if value <= 0: raise Hold('Stage 2 total deadline expired')
        return value
    try:
        remaining(cleanup_reserve)
        worker.start_verification()
        remaining(cleanup_reserve)
        report = worker.wait_for_result(timeout_seconds=remaining(cleanup_reserve))
        remaining(cleanup_reserve)
        if (not isinstance(report, dict) or report.get('run_id') != run_id
                or report.get('plan_sha256') != plan_sha256
                or any(report.get(k) is not True for k in (
                    'image_verified','process_exited','all_descendants_exited','validation_complete'))):
            raise Hold('Worker completion or termination not proven')
        if worker.confirm_empty_job(timeout_seconds=remaining()) is not True:
            raise Hold('Job termination unconfirmed')
        remaining()
        if worker.close_handles(timeout_seconds=remaining()) is not True:
            raise Hold('Handle cleanup unconfirmed')
        remaining()
        # Serialize/commit is still inside the same deadline. A post-write
        # overrun latches HOLD, which takes precedence over this acknowledgement.
        _record(root, 'termination_confirmed.json', {**base,
            'termination_confirmed':True, 'cleanup_complete':True, 'operator_release_required':True,
            'elapsed_seconds':clock()-started})
        remaining()
        return {**base, 'state':'awaiting_manual_restore', 'auto_restore':False,
                'elapsed_seconds':clock()-started}
    except Exception as exc:
        failure = {**base, 'state':'HOLD', 'restore_prohibited':True,
                   'reason':type(exc).__name__, 'elapsed_seconds':clock()-started}
        # Latch before potentially blocking native cleanup. If storage fails,
        # no complete success acknowledgement is sufficient to restore safely.
        try: _record(root, 'HOLD.json', failure)
        except Exception: failure['hold_record_failed']=True
        try:
            budget = max(0, deadline-clock())
            failure['termination_confirmed'] = worker.kill_and_confirm(timeout_seconds=budget) is True
        except Exception: failure['termination_confirmed']=False
        # The immutable HOLD stays even if termination later succeeds.
        raise Hold('Stage 2 HOLD; automatic restore prohibited') from exc


def restore_evidence(root, run_id, plan_sha256):
    """Conservative journal reader for the offline restore gate, no OS mutation."""
    root = Path(root)
    if (root/'HOLD.json').exists(): raise Hold('Persistent HOLD blocks restoration')
    started = json.loads((root/'run_started.json').read_text(encoding='utf-8'))
    done = json.loads((root/'termination_confirmed.json').read_text(encoding='utf-8'))
    for record in (started, done):
        if (record.get('run_id') != run_id or record.get('plan_sha256') != plan_sha256
                or record.get('auto_restore') is not False): raise Hold('Restore identity mismatch')
    if done.get('termination_confirmed') is not True or done.get('cleanup_complete') is not True:
        raise Hold('Restore termination evidence incomplete')
    if not 0 <= done['elapsed_seconds'] < done['total_seconds']:
        raise Hold('Deadline completion not proven')
    return {'operator_check_required':True, 'restoration_authorized':False, 'automatic_restore':False}



class DormantWindowsWorkerPort:
    """Concrete disabled-native IPC for a pre-created, contained verification worker.

    Provisioning that worker/job/start-event and running its fixed request is NOT
    authorized here. All APIs use the already-disabled NativeWindowsAdapter gate.
    The real port cannot pass supervise's synthetic-only guard.
    """
    simulation_only = False

    def __init__(self, api, worker_process, job, start_event, report_reader):
        self.api=api;self.process=worker_process;self.job=job;self.event=start_event
        self.report_reader=report_reader;self.started=False;self.closed=False

    def start_verification(self):
        if self.started or self.closed: raise Hold('Worker already consumed')
        # Outer containment permits only worker + one fixed leaf helper. Inner
        # helper job retains PR #104/#105's active-process limit of one.
        if self.api.job_policy(self.job)!=(True,2,False):raise Hold('Outer job containment mismatch')
        self.started=True
        self.api._ok(self.api._call('kernel32','SetEvent',c.c_int32,
            [c.c_void_p],self.event),'Start verification event')

    def _wait(self,timeout_seconds):
        if timeout_seconds<0 or timeout_seconds>10:raise Hold('Invalid remaining deadline')
        # Round down so each OS wait never asks for more than the parent budget.
        return self.api._call('kernel32','WaitForSingleObject',c.c_uint32,
            [c.c_void_p,c.c_uint32],self.process.handle,int(timeout_seconds*1000))

    def wait_for_result(self,*,timeout_seconds):
        status=self._wait(timeout_seconds)
        if status==258:return None
        if status!=0:raise Hold('Worker wait failed')
        # Reader must consume the already committed bounded private result, not
        # perform network or arbitrary work. Parent rechecks its deadline after.
        return self.report_reader()

    def confirm_empty_job(self,*,timeout_seconds):
        if self._wait(timeout_seconds)!=0:return False
        return self.api.job_members(self.job)==()

    def kill_and_confirm(self,*,timeout_seconds):
        try:
            self.api._ok(self.api._call('kernel32','TerminateJobObject',c.c_int32,
                [c.c_void_p,c.c_uint32],self.job,1),'Kill outer worker job')
            return self.confirm_empty_job(timeout_seconds=timeout_seconds)
        except Exception:return False

    def close_handles(self,*,timeout_seconds):
        if timeout_seconds<=0 or self.closed:return False
        self.api._close(self.process.thread);self.process.thread=None
        self.api._close(self.process.handle);self.process.handle=None
        self.api._close(self.event);self.event=None
        self.api._close(self.job)
        self.api.processes.pop(self.process.pid,None);self.api.jobs.discard(self.job)
        self.closed=True
        return True

