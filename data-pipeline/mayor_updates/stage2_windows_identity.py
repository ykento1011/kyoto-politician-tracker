"""Read-only Windows identity + cancellable fixed DNS API, source-gated by caller.

No API resolves or loads until methods are invoked after the live source gates.
Existing NativeWindowsAdapter retains cache-only signature and ACL verification.
"""
import ctypes as c
from ctypes import wintypes as w
from hashlib import sha256
import os
from pathlib import Path
import threading

from .launch_contract import FixedLaunch, _image
from .native_launch import NativeWindowsAdapter, FILETIME, P, D, TRUSTED_INSTALLER_SID, LockedImage
from .projection import Hold
from .stage2_acceptance import require


class WindowsIdentity:
    def __init__(self, spec, peer_pins):
        self.api = NativeWindowsAdapter(spec)
        self.spec, self.peer_pins = spec, peer_pins
        self.retained = []
        self.own_verified = False
        self.system_verified = False

    def own(self):
        require(os.path.normcase(os.path.realpath(os.sys.executable)) ==
                os.path.normcase(self.spec.executable), 'Fixed controller interpreter required')
        if not self.own_verified:
            locked = self.api.lock_image(self.spec.executable, deny_write=True, deny_delete=True,
                                         inherit=False, reject_reparse=True)
            _image(self.spec, self.api.inspect_file(locked))
            self.own_verified = True  # image/ancestry remain locked until shutdown
        return self.capture(os.getpid(), elevated=False, expected=self.spec.executable,
                            expected_sha=self.spec.image_sha256)

    def capture(self, pid, *, elevated, expected, expected_sha):
        require(type(pid) is int and pid > 0, 'Peer PID')
        api = self.api
        # SYNCHRONIZE is required by the zero-time alive check below.
        handle = api._call('kernel32', 'OpenProcess', P, [D, w.BOOL, D], 0x1000 | 0x100000, False, pid)
        require(bool(handle), 'Cannot retain peer process')
        self.retained.append(handle)
        started, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        api._ok(api._call('kernel32', 'GetProcessTimes', w.BOOL,
            [P, c.POINTER(FILETIME), c.POINTER(FILETIME), c.POINTER(FILETIME), c.POINTER(FILETIME)],
            handle,c.byref(started),c.byref(exited),c.byref(kernel),c.byref(user)), 'Peer start time')
        token, count = P(), D()
        api._ok(api._call('advapi32','OpenProcessToken',w.BOOL,[P,D,c.POINTER(P)],handle,8,c.byref(token)), 'Peer token')
        try:
            level=D()
            api._ok(api._call('advapi32','GetTokenInformation',w.BOOL,[P,D,P,D,c.POINTER(D)],
                token,20,c.byref(level),c.sizeof(level),c.byref(count)), 'Peer elevation')
            require(bool(level.value) is elevated, 'Wrong elevated/non-elevated role')
            api._call('advapi32','GetTokenInformation',w.BOOL,[P,D,P,D,c.POINTER(D)],token,1,None,0,c.byref(count))
            require(8 <= count.value <= 65536, 'Token bound')
            buf=c.create_string_buffer(count.value)
            api._ok(api._call('advapi32','GetTokenInformation',w.BOOL,[P,D,P,D,c.POINTER(D)],
                token,1,buf,count.value,c.byref(count)), 'Peer token SID')
            sid=api._sid(P.from_buffer(buf).value)
        finally: api._close(token.value)
        size=D(32768);name=c.create_unicode_buffer(size.value)
        api._ok(api._call('kernel32','QueryFullProcessImageNameW',w.BOOL,[P,D,w.LPWSTR,c.POINTER(D)],
            handle,0,name,c.byref(size)), 'Actual peer image')
        require(name.value.casefold() == expected.casefold() and sid == self.spec.actor_sid,
                'Peer image/SID differs')
        require(sha256(Path(expected).read_bytes()).hexdigest() == expected_sha, 'Peer executable PIN')
        require(api._call('kernel32','WaitForSingleObject',D,[P,D],handle,0) == 258, 'Peer not alive')
        return dict(pid=pid,started=(started.high<<32)|started.low,image=name.value,sid=sid,
                    retained_process_handle=True,image_verified=True)

    def peer(self, claimed, *, elevated):
        pin=self.peer_pins['administrator']
        # System PS5.1 is globally readable, not an SID1004-owned worker image.
        # Reuse the native *ancestor* safety policy for its protected Windows
        # location; never weaken the owner-only worker executable guard.
        expected=os.path.join(os.environ.get('SystemRoot','C:\\Windows'),
                              'System32','WindowsPowerShell','v1.0','powershell.exe')
        require(pin['path'].casefold()==expected.casefold(),'Fixed system PS5.1 only')
        system=NativeWindowsAdapter(FixedLaunch(pin['path'],(),pin['sha256'],pin['signer_sha256'],
                                               TRUSTED_INSTALLER_SID))
        handles=[]
        try:
            if not self.system_verified:
                for parent in reversed(Path(expected).parents):
                    h=system._open(str(parent),directory=True);handles.append(h)
                    system._info(h);system._acl(h,parent=True)
                h=system._open(expected);handles.append(h)
                info=system._info(h);system._acl(h,parent=True)
                require(info.links==1 and sha256(system._bytes(h,info)).hexdigest()==pin['sha256'], 'PS5.1 image bytes')
                locked=LockedImage(expected,h,tuple(handles[:-1]))
                require(system._signature(locked)==pin['signer_sha256'],'PS5.1 cache-only signature')
                self.retained.extend(handles);handles=[]
                self.system_verified = True
        finally:
            for h in reversed(handles):system._close(h)
        actual=self.capture(claimed['pid'],elevated=elevated,expected=pin['path'],expected_sha=pin['sha256'])
        require(all(actual[k] == claimed[k] for k in ('pid','started','image','sid')), 'Stale/substituted peer')

    def check_path(self, path):
        # Lock the same ancestry policy used by the native worker, plus strict
        # owner-only leaf DACL. Keep locks for the whole IPC transaction.
        original=Path(path).absolute()
        path=original.resolve(strict=True)
        require(str(original).casefold()==str(path).casefold(),'Aliased IPC path')
        for parent in reversed(path.parents):
            h=self.api._open(str(parent),directory=True);self.retained.append(h)
            self.api._info(h);self.api._acl(h,parent=True)
        h=self.api._open(str(path),directory=path.is_dir());self.retained.append(h)
        self.api._info(h);self.api._acl(h,parent=False)

    def device_to_dos(self, value):
        require(value.casefold().startswith('\\device\\'), 'Expected NT application path')
        matches=[]
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            buf=c.create_unicode_buffer(32768)
            n=self.api._call('kernel32','QueryDosDeviceW',D,[w.LPCWSTR,w.LPWSTR,D],letter+':',buf,len(buf))
            if n and value.casefold().startswith(buf.value.casefold()+'\\'):
                matches.append(letter+':'+value[len(buf.value):])
        require(len(matches)==1,'Ambiguous/unmapped NT application path')
        return matches[0]


class QUERY_RESULT(c.Structure):
    _fields_=[('version',D),('status',c.c_int32),('options',c.c_uint64),('records',P),('reserved',P)]


class QUERY_REQUEST(c.Structure):
    _fields_=[('version',D),('name',w.LPCWSTR),('kind',w.WORD),('options',c.c_uint64),
              ('servers',P),('interface',D),('callback',P),('context',P)]


class FixedDnsQuery:
    """Keep callbacks/buffers alive through cancellation; never equate cancel to completion."""
    def __init__(self, api): self.api,self.pending=api,[]

    def __call__(self, query, timeout):
        from .stage2_os_adapter import require
        require(query.startswith('stage2-') and query.endswith('.example.com.') and 0<timeout<=1,
                'Fixed DNS query/deadline')
        done=threading.Event();result=QUERY_RESULT();result.version=1
        callback_type=getattr(c,'WINFUNCTYPE',c.CFUNCTYPE)(None,P,c.POINTER(QUERY_RESULT))
        def complete(context, observed): done.set()
        callback=callback_type(complete)
        request=QUERY_REQUEST();request.version=1;request.name=query;request.kind=1
        request.options=8|0x40|0x80  # BYPASS_CACHE, NO_HOSTS_FILE, NO_NETBT; no persistent cache edit
        request.callback=c.cast(callback,P)
        cancel=c.create_string_buffer(32)
        keep=(request,result,callback,cancel,done)
        self.pending.append(keep)
        status=self.api._call('dnsapi','DnsQueryEx',c.c_int32,
            [c.POINTER(QUERY_REQUEST),c.POINTER(QUERY_RESULT),P],c.byref(request),c.byref(result),cancel)
        if status!=9506:done.set()  # DNS_REQUEST_PENDING; not ERROR_IO_PENDING
        if not done.wait(timeout):
            self.api._call('dnsapi','DnsCancelQuery',c.c_int32,[P],cancel)
        # Cancellation alone is never proof of completion. If still pending the
        # object remains rooted until the on-site stop kills the controller.
        finished=done.is_set()
        if finished:
            if result.records:
                self.api._call('dnsapi','DnsRecordListFree',None,[P,c.c_int],result.records,1)
            self.pending.remove(keep)
        return dict(query_complete=finished,pending_service_requests=0 if finished else 1,
                    cached=False,external_egress=(result.status==0 if finished else None),
                    dns_status=result.status if finished else status)
