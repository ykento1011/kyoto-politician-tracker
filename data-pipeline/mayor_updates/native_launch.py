"""Native Windows adapter, permanently execution-disabled in this stage.

All native entry points pass through _fn. There is no activation argument,
command-line entry, DLL load at import, network API or Firewall operation.
Tests replace _fn with a synthetic API table. Future activation is a new change.
"""
import ctypes as c
from ctypes import wintypes as w
from dataclasses import dataclass
from hashlib import sha256
import ntpath
import os
import subprocess
from .launch_contract import ImageEvidence, CREATE_SUSPENDED, _spec
from .projection import Hold

P = c.c_void_p
D = c.c_uint32
Q = c.c_size_t
NATIVE_EXECUTION_ENABLED = False  # source-level gate; no public activation parameter

class FILETIME(c.Structure):
    _fields_ = [('low', D), ('high', D)]


class STARTUPINFO(c.Structure):
    _fields_ = [('cb', D), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
        ('x', D), ('y', D), ('xs', D), ('ys', D), ('xc', D), ('yc', D), ('fill', D),
        ('flags', D), ('show', w.WORD), ('reserved2size', w.WORD), ('reserved2', P),
        ('stdin', P), ('stdout', P), ('stderr', P)]


class PROCESSINFO(c.Structure):
    _fields_ = [('process', P), ('thread', P), ('pid', D), ('tid', D)]


class BASICLIMIT(c.Structure):
    _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong), ('flags', D),
        ('min_working_set', Q), ('max_working_set', Q), ('active_limit', D),
        ('affinity', Q), ('priority', D), ('scheduling', D)]


class IOCOUNTERS(c.Structure):
    _fields_ = [(n, c.c_ulonglong) for n in ('ro', 'wo', 'oo', 'rb', 'wb', 'ob')]


class EXTENDEDLIMIT(c.Structure):
    _fields_ = [('basic', BASICLIMIT), ('io', IOCOUNTERS), ('process_memory', Q),
        ('job_memory', Q), ('peak_process', Q), ('peak_job', Q)]


class FILEINFO(c.Structure):
    _fields_ = [('attributes', D), ('created', FILETIME), ('accessed', FILETIME),
        ('written', FILETIME), ('volume', D), ('size_high', D), ('size_low', D),
        ('links', D), ('index_high', D), ('index_low', D)]


class GUID(c.Structure):
    _fields_ = [('a', D), ('b', w.WORD), ('c', w.WORD), ('d', c.c_ubyte * 8)]


class TRUSTFILE(c.Structure):
    _fields_ = [('size', D), ('path', w.LPCWSTR), ('handle', P), ('subject', P)]


class TRUSTDATA(c.Structure):
    _fields_ = [('size', D), ('policy', P), ('sip', P), ('ui', D), ('revocation', D),
        ('choice', D), ('file', P), ('action', D), ('state', P), ('url', w.LPWSTR),
        ('flags', D), ('context', D), ('signature_settings', P)]


class CERTCONTEXT(c.Structure):
    _fields_ = [('encoding', D), ('encoded', P), ('length', D), ('info', P), ('store', P)]


class PROVIDERCERT_HEAD(c.Structure):
    _fields_ = [('size', D), ('cert', c.POINTER(CERTCONTEXT))]


@dataclass
class LockedImage:
    path: str
    handle: int
    parents: tuple


@dataclass(eq=False)
class SuspendedProcess:
    handle: int
    thread: int
    pid: int
    suspended: bool = True


class NativeWindowsAdapter:
    simulation_only = False

    def __init__(self, spec):
        _spec(spec)
        self.spec = spec
        self.processes = {}
        self.jobs = set()
        self.images = []

    def _fn(self, dll, name, result, args):
        if not NATIVE_EXECUTION_ENABLED or os.name != 'nt':
            raise Hold('Native execution disabled; separate Stage 2 activation review required')
        library = c.WinDLL(dll, use_last_error=True)
        fn = getattr(library, name)
        fn.restype = result; fn.argtypes = args
        return fn

    def _call(self, dll, name, result, types, *args):
        return self._fn(dll, name, result, types)(*args)

    def _ok(self, value, label):
        if not value: raise Hold('WinAPI failed: ' + label)
        return value

    def _close(self, handle):
        if handle: self._ok(self._call('kernel32', 'CloseHandle', w.BOOL, [P], handle), 'CloseHandle')

    def _sid(self, sid):
        text = P()
        self._ok(self._call('advapi32', 'ConvertSidToStringSidW', w.BOOL,
            [P, c.POINTER(P)], sid, c.byref(text)), 'ConvertSidToStringSidW')
        try: return c.wstring_at(text.value)
        finally: self._call('kernel32', 'LocalFree', P, [P], text)

    def _actor(self, process_handle=None):
        token = P()
        self._ok(self._call('advapi32', 'OpenProcessToken', w.BOOL,
            [P, D, c.POINTER(P)], P(-1) if process_handle is None else process_handle, 8, c.byref(token)), 'OpenProcessToken')
        try:
            elevation = D(); returned = D()
            self._ok(self._call('advapi32', 'GetTokenInformation', w.BOOL,
                [P, D, P, D, c.POINTER(D)], token, 20, c.byref(elevation), c.sizeof(elevation), c.byref(returned)), 'TokenElevation')
            if elevation.value != 0: raise Hold('Elevated execution refused')
            size = D()
            self._call('advapi32', 'GetTokenInformation', w.BOOL,
                [P, D, P, D, c.POINTER(D)], token, 1, None, 0, c.byref(size))
            if not 8 <= size.value <= 65536: raise Hold('Invalid token size')
            buf = c.create_string_buffer(size.value)
            self._ok(self._call('advapi32', 'GetTokenInformation', w.BOOL,
                [P, D, P, D, c.POINTER(D)], token, 1, buf, size.value, c.byref(size)), 'TokenUser')
            return self._sid(P.from_buffer(buf).value)
        finally: self._close(token.value)

    def _acl(self, handle, *, parent=False):
        owner = P(); dacl = P(); sd = P()
        status = self._call('advapi32', 'GetSecurityInfo', D,
            [P, D, D, c.POINTER(P), P, c.POINTER(P), P, c.POINTER(P)],
            handle, 1, 5, c.byref(owner), None, c.byref(dacl), None, c.byref(sd))
        if status != 0: raise Hold('GetSecurityInfo failed')
        try:
            if not owner.value or not dacl.value: raise Hold('Owner or DACL missing')
            owner_sid = self._sid(owner.value)
            count = c.c_ushort.from_address(dacl.value + 4).value
            allowed = set(); trusted = {self.spec.actor_sid, 'S-1-5-18', 'S-1-5-32-544'}
            for i in range(count):
                ace = P()
                self._ok(self._call('advapi32', 'GetAce', w.BOOL,
                    [P, D, c.POINTER(P)], dacl, i, c.byref(ace)), 'GetAce')
                kind = c.c_ubyte.from_address(ace.value).value
                flags = c.c_ubyte.from_address(ace.value + 1).value
                size = c.c_ushort.from_address(ace.value + 2).value
                if kind not in (0, 1) or size < 12: raise Hold('Unsupported ACL structure')
                if kind == 1 or flags & 8: continue  # deny or inherit-only ACE cannot grant here
                mask = D.from_address(ace.value + 4).value
                sid = self._sid(ace.value + 8)
                if parent:
                    # Delete, delete-child, write DAC/owner, generic write/all,
                    # add/overwrite data, subdirectory, EA/attributes.
                    if mask & 0x500D0156 and sid not in trusted:
                        raise Hold('Untrusted writable ancestor')
                else: allowed.add(sid)
            good = (owner_sid in trusted if parent else
                    owner_sid == self.spec.actor_sid and allowed == {self.spec.actor_sid})
            if not good: raise Hold('Owner-only executable or safe ancestor ACL required')
            return owner_sid
        finally:
            if sd.value: self._call('kernel32', 'LocalFree', P, [P], sd)

    def _open(self, path, *, directory=False):
        access = 0x20080 if directory else 0x80020000
        share = 3 if directory else 1  # no DELETE; image additionally denies WRITE
        flags = 0x00200000 | (0x02000000 if directory else 0)
        handle = self._call('kernel32', 'CreateFileW', P,
            [w.LPCWSTR, D, D, P, D, D, P], path, access, share, None, 3, flags, None)
        if handle in (None, 0, c.c_void_p(-1).value): raise Hold('Cannot lock image/ancestor')
        return handle

    def _info(self, handle):
        info = FILEINFO()
        self._ok(self._call('kernel32', 'GetFileInformationByHandle', w.BOOL,
            [P, c.POINTER(FILEINFO)], handle, c.byref(info)), 'File information')
        if info.attributes & 0x400: raise Hold('Reparse point refused')
        return info

    def lock_image(self, path, **options):
        if path != self.spec.executable or options != dict(deny_write=True, deny_delete=True,
                inherit=False, reject_reparse=True): raise Hold('Fixed image lock contract required')
        handles = []; image = None
        try:
            parts = []; parent = ntpath.dirname(path)
            while parent:
                parts.append(parent); next_parent = ntpath.dirname(parent)
                if next_parent == parent: break
                parent = next_parent
            for parent in reversed(parts):
                h = self._open(parent, directory=True); handles.append(h)
                self._info(h); self._acl(h, parent=True)
            image = self._open(path)
            self._info(image); self._acl(image)
            locked = LockedImage(path, image, tuple(handles)); self.images.append(locked)
            return locked
        except Exception:
            self._close(image)
            for h in reversed(handles): self._close(h)
            raise

    def _bytes(self, handle, info):
        length = (info.size_high << 32) | info.size_low
        if not 0 < length <= 32 * 1024 * 1024: raise Hold('Executable size outside verification limit')
        self._ok(self._call('kernel32', 'SetFilePointerEx', w.BOOL,
            [P, c.c_longlong, P, D], handle, 0, None, 0), 'Seek')
        buf = c.create_string_buffer(length); read = D()
        self._ok(self._call('kernel32', 'ReadFile', w.BOOL,
            [P, P, D, c.POINTER(D), P], handle, buf, length, c.byref(read), None), 'ReadFile')
        if read.value != length: raise Hold('Short executable read')
        return buf.raw

    def _signature(self, locked):
        # Verify the held handle using cached trust only, including chain revocation.
        action = GUID(0x00AAC56B, 0xCD44, 0x11D0,
            (c.c_ubyte * 8)(0x8C, 0xC2, 0, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))
        file = TRUSTFILE(c.sizeof(TRUSTFILE), locked.path, locked.handle, None)
        data = TRUSTDATA(); data.size = c.sizeof(data); data.ui = 2; data.revocation = 1
        data.choice = 1; data.file = c.cast(c.pointer(file), P); data.action = 1
        data.flags = 0x1000 | 0x80  # cache-only retrieval, chain revocation excluding root
        try:
            status = self._call('wintrust', 'WinVerifyTrust', c.c_int32,
                [P, c.POINTER(GUID), c.POINTER(TRUSTDATA)], P(-1), c.byref(action), c.byref(data))
            if status != 0 or not data.state: raise Hold('Offline signature/trust unavailable or invalid')
            provider = self._call('wintrust', 'WTHelperProvDataFromStateData', P, [P], data.state)
            if not provider: raise Hold('Missing trust provider')
            signer = self._call('wintrust', 'WTHelperGetProvSignerFromChain', P,
                [P, D, w.BOOL, D], provider, 0, False, 0)
            if not signer: raise Hold('Missing verified signer')
            cert_ptr = self._call('wintrust', 'WTHelperGetProvCertFromChain', P, [P, D], signer, 0)
            if not cert_ptr: raise Hold('Missing verified signer certificate')
            head = c.cast(cert_ptr, c.POINTER(PROVIDERCERT_HEAD)).contents
            if not head.cert: raise Hold('Missing signer context')
            cert = head.cert.contents
            if not cert.encoded or not 0 < cert.length <= 1024 * 1024: raise Hold('Invalid signer certificate')
            return sha256(c.string_at(cert.encoded, cert.length)).hexdigest()
        finally:
            if data.state:
                data.action = 2
                status = self._call('wintrust', 'WinVerifyTrust', c.c_int32,
                    [P, c.POINTER(GUID), c.POINTER(TRUSTDATA)], P(-1), c.byref(action), c.byref(data))
                if status != 0: raise Hold('Trust state close failed')

    def inspect_file(self, locked):
        info = self._info(locked.handle)
        if info.attributes & 0x10 or info.links != 1: raise Hold('Not a single-link regular executable')
        owner = self._acl(locked.handle)
        for parent in locked.parents: self._info(parent); self._acl(parent, parent=True)
        return ImageEvidence(locked.path, f'{info.volume}:{info.index_high}:{info.index_low}',
            self._bytes(locked.handle, info), self._signature(locked), True, owner,
            self._actor(), True, True, True, info.links, True)

    def create_job(self, **options):
        if options != dict(kill_on_close=True, active_process_limit=1, breakaway=False):
            raise Hold('Fixed job contract required')
        h = self._call('kernel32', 'CreateJobObjectW', P, [P, w.LPCWSTR], None, None)
        if not h: raise Hold('CreateJobObjectW failed')
        self.jobs.add(h)
        limits = EXTENDEDLIMIT(); limits.basic.flags = 0x2000 | 8; limits.basic.active_limit = 1
        try:
            self._ok(self._call('kernel32', 'SetInformationJobObject', w.BOOL,
                [P, c.c_int, P, D], h, 9, c.byref(limits), c.sizeof(limits)), 'Job limits')
            return h
        except Exception:
            self._close(h); self.jobs.remove(h); raise

    def job_policy(self, job):
        limits = EXTENDEDLIMIT()
        self._ok(self._call('kernel32', 'QueryInformationJobObject', w.BOOL,
            [P, c.c_int, P, D, P], job, 9, c.byref(limits), c.sizeof(limits), None), 'Query job policy')
        flags = limits.basic.flags
        return (bool(flags & 0x2000), int(limits.basic.active_limit), bool(flags & (0x800 | 0x1000)))

    def create_process(self, **request):
        expected = dict(application_name=self.spec.executable, arguments=self.spec.arguments,
            creation_flags=CREATE_SUSPENDED, inherit_handles=False, actor_sid=self.spec.actor_sid)
        if request != expected or self._actor() != self.spec.actor_sid:
            raise Hold('Fixed process request/actor required')
        # No shell/PATH search: lpApplicationName is non-null, handles not inherited.
        cmd = c.create_unicode_buffer(subprocess.list2cmdline([self.spec.executable, *self.spec.arguments]))
        startup = STARTUPINFO(); startup.cb = c.sizeof(startup); pi = PROCESSINFO()
        self._ok(self._call('kernel32', 'CreateProcessW', w.BOOL,
            [w.LPCWSTR, w.LPWSTR, P, P, w.BOOL, D, P, w.LPCWSTR,
             c.POINTER(STARTUPINFO), c.POINTER(PROCESSINFO)], self.spec.executable,
            cmd, None, None, False, CREATE_SUSPENDED | 0x08000000,
            None, ntpath.dirname(self.spec.executable), c.byref(startup), c.byref(pi)), 'CreateProcessW')
        proc = SuspendedProcess(pi.process, pi.thread, pi.pid)
        self.processes[proc.pid] = proc
        if not proc.handle or not proc.thread or not proc.pid:
            self.terminate_and_confirm(None, proc)
            raise Hold('Invalid process handles')
        return proc

    def is_suspended(self, process):
        # The flag/primary thread handle come from this adapter's own creation.
        return self.processes.get(process.pid) is process and process.suspended is True

    def assign_job(self, job, process):
        self._ok(self._call('kernel32', 'AssignProcessToJobObject', w.BOOL,
            [P, P], job, process.handle), 'Assign job')

    def job_members(self, job):
        buf = c.create_string_buffer(8 + 8 * c.sizeof(Q))
        self._ok(self._call('kernel32', 'QueryInformationJobObject', w.BOOL,
            [P, c.c_int, P, D, P], job, 3, buf, len(buf), None), 'Query job members')
        assigned, listed = (D * 2).from_buffer(buf)
        if assigned != listed or listed > 1: raise Hold('Unexpected job members')
        ids = (Q * listed).from_buffer(buf, 8)
        if any(pid not in self.processes for pid in ids): raise Hold('Unknown process in job')
        return tuple(self.processes[pid] for pid in ids)

    def inspect_process_image(self, process):
        if self._actor(process.handle) != self.spec.actor_sid: raise Hold('Child token mismatch')
        buf = c.create_unicode_buffer(32768); length = D(len(buf))
        self._ok(self._call('kernel32', 'QueryFullProcessImageNameW', w.BOOL,
            [P, D, w.LPWSTR, c.POINTER(D)], process.handle, 0, buf, c.byref(length)), 'Process image')
        if length.value == 0 or buf.value != self.spec.executable: raise Hold('Actual process path mismatch')
        # Reopen the observed path while original file and ancestors remain locked.
        image = self.lock_image(buf.value, deny_write=True, deny_delete=True, inherit=False, reject_reparse=True)
        return self.inspect_file(image)

    def resume(self, process):
        if not self.is_suspended(process): raise Hold('Process not suspended')
        count = self._call('kernel32', 'ResumeThread', D, [P], process.thread)
        if count != 1: raise Hold('Unexpected suspend count')
        process.suspended = False

    def wait(self, process, *, timeout_seconds):
        if timeout_seconds != self.spec.timeout_seconds: raise Hold('Fixed timeout required')
        status = self._call('kernel32', 'WaitForSingleObject', D, [P, D], process.handle, timeout_seconds * 1000)
        if status != 0: raise Hold('Wait failed or timed out')
        code = D()
        self._ok(self._call('kernel32', 'GetExitCodeProcess', w.BOOL,
            [P, c.POINTER(D)], process.handle, c.byref(code)), 'Exit code')
        if code.value == 259: raise Hold('Process still active')
        return int(code.value)

    def terminate_and_confirm(self, job, process):
        try:
            if job:
                self._ok(self._call('kernel32', 'TerminateJobObject', w.BOOL, [P, w.UINT], job, 1), 'Terminate job')
            # Also cover a suspended process whose assignment failed.
            if process:
                self._ok(self._call('kernel32', 'TerminateProcess', w.BOOL,
                    [P, w.UINT], process.handle, 1), 'Terminate process')
                if self._call('kernel32', 'WaitForSingleObject', D, [P, D], process.handle, 10000) != 0: return False
            return not job or not self.job_members(job)
        except Exception: return False

    def close_handles(self, *unused):
        errors = []
        for process in self.processes.values():
            for handle in (process.thread, process.handle):
                try: self._close(handle)
                except Exception as exc: errors.append(exc)
        for job in self.jobs:
            try: self._close(job)
            except Exception as exc: errors.append(exc)
        for image in reversed(self.images):
            for handle in (image.handle, *reversed(image.parents)):
                try: self._close(handle)
                except Exception as exc: errors.append(exc)
        self.processes.clear(); self.jobs.clear(); self.images.clear()
        if errors: raise Hold('Native handle close incomplete; keep OS isolation')

