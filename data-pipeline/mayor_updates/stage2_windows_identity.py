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
import ntpath
import re

from .launch_contract import FixedLaunch, _image
from .native_launch import NativeWindowsAdapter, FILETIME, P, D, TRUSTED_INSTALLER_SID, LockedImage
from .projection import Hold
from .stage2_acceptance import require
from .native_launch import GUID, TRUSTDATA, PROVIDERCERT_HEAD


CRYPTSVC_SID = 'S-1-5-80-242729624-280608522-2219052887-3187409060-2225943459'


class CatalogTrust(c.Structure):
    _fields_ = [('size', D), ('version', D), ('catalog_path', w.LPCWSTR),
                ('tag', w.LPCWSTR), ('member_path', w.LPCWSTR), ('member_handle', P),
                ('hash', P), ('hash_size', D), ('context', P), ('admin', P)]


def ps51_paths(pin, windows):
    """Only a pinned, two-alias inbox PS5.1 image; never a worker exception."""
    expected = ntpath.join(windows, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    aliases = pin['aliases']
    require(pin['path'].casefold() == expected.casefold(), 'Inbox PS5.1 only')
    require(type(aliases) is list and len(aliases) == 2 and
            len({p.casefold() for p in aliases}) == 2 and
            expected.casefold() in {p.casefold() for p in aliases}, 'Exact two PS5.1 aliases')
    other = next(p for p in aliases if p.casefold() != expected.casefold())
    relative = ntpath.relpath(other, ntpath.join(windows, 'WinSxS'))
    require(re.fullmatch(r'amd64_microsoft-windows-powershell-exe_31bf3856ad364e35_[0-9.]+_none_[0-9a-f]{16}\\powershell\.exe',
                         relative, re.I) is not None, 'Fixed WinSxS PS5.1 alias')
    catroot = ntpath.join(windows, 'System32', 'CatRoot')
    catdir = ntpath.join(catroot, '{F750E6C3-38EE-11D1-85E5-00C04FC295EE}')
    catalog = pin['catalog']
    require(ntpath.dirname(catalog['path']).casefold() == catdir.casefold() and
            re.fullmatch(r'Microsoft-Windows-Client-Features-Package~31bf3856ad364e35~amd64~~[0-9.]+\.cat',
                         ntpath.basename(catalog['path']), re.I) is not None, 'Fixed Windows catalog')
    for value in (pin['sha256'], pin['signer_sha256'], catalog['sha256']):
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'PS5.1 SHA pin')
    require(re.fullmatch('[0-9A-F]{64}', catalog['member_hash']) is not None, 'Catalog member pin')
    require(type(pin['volume_serial']) is int and type(pin['file_id']) is int, 'File identity pins')
    expected_catalog_aliases = [catalog['path'], ntpath.join(windows,'WinSxS','Catalogs',catalog['sha256']+'.cat'),
                               ntpath.join(windows,'servicing','Packages',ntpath.basename(catalog['path']))]
    require(type(catalog['aliases']) is list and len(catalog['aliases']) == 3 and
            {p.casefold() for p in catalog['aliases']} == {p.casefold() for p in expected_catalog_aliases}, 'Exact catalog aliases')
    require(type(catalog['volume_serial']) is int and type(catalog['file_id']) is int, 'Catalog file identity pins')
    for path in aliases + catalog['aliases']:
        require(ntpath.normpath(path) == path and ntpath.isabs(path) and ':' not in path[2:], 'Canonical system path')
    return expected, (catroot.casefold(), catdir.casefold())


class SystemPs51Verifier(NativeWindowsAdapter):
    """Read-only inbox PS5.1 verification. Worker NativeWindowsAdapter is unchanged."""
    def __init__(self, pin, windows):
        self.pin = pin
        self.expected, self.catalog_directories = ps51_paths(pin, windows)
        super().__init__(FixedLaunch(pin['path'], (), pin['sha256'], pin['signer_sha256'], TRUSTED_INSTALLER_SID))

    def catalog_directory_acl(self, handle, path):
        # CryptSvc may maintain exactly these Windows catalog directories, not
        # the executable, its aliases, catalog leaf, IPC or arbitrary ancestors.
        require(path.casefold() in self.catalog_directories, 'Catalog ACL boundary')
        owner, dacl, sd = P(), P(), P()
        status = self._call('advapi32', 'GetSecurityInfo', D,
            [P,D,D,c.POINTER(P),P,c.POINTER(P),P,c.POINTER(P)],
            handle,1,5,c.byref(owner),None,c.byref(dacl),None,c.byref(sd))
        try:
            require(status == 0 and owner.value and dacl.value, 'Catalog descriptor')
            trusted = {TRUSTED_INSTALLER_SID, 'S-1-5-18', 'S-1-5-32-544', CRYPTSVC_SID}
            require(self._sid(owner.value) in trusted - {CRYPTSVC_SID}, 'Catalog directory owner')
            count = c.c_ushort.from_address(dacl.value + 4).value
            require(count <= 128, 'Catalog ACE bound')
            for i in range(count):
                ace = P()
                self._ok(self._call('advapi32','GetAce',w.BOOL,[P,D,c.POINTER(P)],dacl,i,c.byref(ace)), 'Catalog ACE')
                kind = c.c_ubyte.from_address(ace.value).value
                flags = c.c_ubyte.from_address(ace.value+1).value
                size = c.c_ushort.from_address(ace.value+2).value
                require(kind in (0,1) and size >= 12 and not flags & ~0x1f, 'Catalog ACE structure')
                if kind == 1 or flags & 8: continue  # no grant on this existing directory
                mask = D.from_address(ace.value+4).value
                sid = self._sid(ace.value+8)
                require(not mask & 0x500D0156 or sid in trusted, 'Untrusted catalog writer')
        finally:
            if sd.value: self._call('kernel32','LocalFree',P,[P],sd)

    def aliases(self, path, expected):
        size = D(32768); buf = c.create_unicode_buffer(size.value)
        enum = self._call('kernel32','FindFirstFileNameW',P,[w.LPCWSTR,D,c.POINTER(D),w.LPWSTR],
                          path,0,c.byref(size),buf)
        require(enum not in (None,0,c.c_void_p(-1).value), 'Hardlink enumeration')
        rows = []
        try:
            while True:
                rows.append(ntpath.splitdrive(path)[0]+buf.value)
                require(len(rows) <= len(expected), 'Unexpected system file link')
                size.value = len(buf)
                if not self._call('kernel32','FindNextFileNameW',w.BOOL,[P,c.POINTER(D),w.LPWSTR],enum,c.byref(size),buf):
                    require(c.get_last_error() == 38, 'Incomplete hardlink enumeration')
                    break
        finally:
            self._ok(self._call('kernel32','FindClose',w.BOOL,[P],enum), 'Hardlink enum close')
        require(len(rows) == len(expected) and {p.casefold() for p in rows} ==
                {p.casefold() for p in expected}, 'Hardlink set differs')
        return rows

    def verify(self):
        handles = []
        try:
            image = None
            catpin = self.pin['catalog']
            for path in self.aliases(self.expected,self.pin['aliases']) + self.aliases(catpin['path'],catpin['aliases']):
                for parent in reversed(Path(path).parents):
                    h = self._open(str(parent),directory=True); handles.append(h); self._info(h)
                    if str(parent).casefold() in self.catalog_directories:
                        self.catalog_directory_acl(h,str(parent))
                    else: self._acl(h,parent=True)
                h = self._open(path); handles.append(h)
                info = self._info(h); self._acl(h,parent=True)
                require(not info.attributes & 0x10, 'Regular PS5.1/catalog file')
                digest = sha256(self._bytes(h,info)).hexdigest()
                if path.casefold() in {p.casefold() for p in catpin['aliases']}:
                    require(info.links == 3 and info.volume == catpin['volume_serial'] and
                            ((info.index_high<<32)|info.index_low) == catpin['file_id'] and
                            digest == catpin['sha256'], 'Catalog bytes/file identity')
                else:
                    require(info.links == 2 and info.volume == self.pin['volume_serial'] and
                            (info.index_high<<32)|info.index_low == self.pin['file_id'] and
                            digest == self.pin['sha256'], 'PS5.1 bytes/file identity')
                    if path.casefold() == self.expected.casefold(): image = h
            require(image is not None, 'PS5.1 image missing')
            self.aliases(self.expected,self.pin['aliases'])
            self.aliases(catpin['path'],catpin['aliases'])
            self.verify_catalog(image)
            return handles
        except BaseException as verification_error:
            cleanup_errors = []
            for h in reversed(handles):
                try: self._close(h)
                except BaseException as error: cleanup_errors.append(error)
            if cleanup_errors:
                raise Hold('PS5.1 verification and handle cleanup failed; termination unconfirmed') from verification_error
            raise

    def verify_catalog(self, image):
        admin = P(); trust = TRUSTDATA()
        action = GUID(0x00AAC56B,0xCD44,0x11D0,(c.c_ubyte*8)(0x8C,0xC2,0,0xC0,0x4F,0xC2,0x95,0xEE))
        try:
            self._ok(self._call('wintrust','CryptCATAdminAcquireContext2',w.BOOL,
                [c.POINTER(P),P,w.LPCWSTR,P,D],c.byref(admin),None,'SHA256',None,0), 'Catalog context')
            size = D()
            self._ok(self._call('wintrust','CryptCATAdminCalcHashFromFileHandle2',w.BOOL,
                [P,P,c.POINTER(D),P,D],admin,image,c.byref(size),None,0), 'Catalog hash size')
            require(size.value == 32, 'SHA256 catalog hash only')
            buf = (c.c_ubyte*32)()
            self._ok(self._call('wintrust','CryptCATAdminCalcHashFromFileHandle2',w.BOOL,
                [P,P,c.POINTER(D),P,D],admin,image,c.byref(size),buf,0), 'Catalog member hash')
            tag = bytes(buf).hex().upper()
            require(size.value == 32 and tag == self.pin['catalog']['member_hash'], 'Catalog membership pin')
            cat = CatalogTrust(); cat.size=c.sizeof(cat); cat.catalog_path=self.pin['catalog']['path']
            cat.tag=tag; cat.member_path=self.expected; cat.member_handle=image
            cat.hash=c.cast(buf,P); cat.hash_size=32; cat.admin=admin
            trust.size=c.sizeof(trust); trust.ui=2; trust.revocation=1; trust.choice=2
            trust.file=c.cast(c.pointer(cat),P); trust.action=1; trust.flags=0x1080
            status=self._call('wintrust','WinVerifyTrust',c.c_int32,
                [P,c.POINTER(GUID),c.POINTER(TRUSTDATA)],P(-1),c.byref(action),c.byref(trust))
            require(status == 0 and trust.state, 'Strict offline catalog signature')
            provider=self._call('wintrust','WTHelperProvDataFromStateData',P,[P],trust.state)
            require(provider, 'Catalog provider')
            signer=self._call('wintrust','WTHelperGetProvSignerFromChain',P,[P,D,w.BOOL,D],provider,0,False,0)
            require(signer, 'Catalog signer')
            ptr=self._call('wintrust','WTHelperGetProvCertFromChain',P,[P,D],signer,0)
            require(ptr, 'Catalog certificate')
            head=c.cast(ptr,c.POINTER(PROVIDERCERT_HEAD)).contents
            require(head.cert, 'Catalog certificate context')
            cert=head.cert.contents
            require(cert.encoded and 0 < cert.length <= 1024*1024, 'Catalog certificate size')
            require(sha256(c.string_at(cert.encoded,cert.length)).hexdigest() == self.pin['signer_sha256'], 'Catalog signer pin')
        finally:
            try:
                if trust.state:
                    trust.action=2
                    require(self._call('wintrust','WinVerifyTrust',c.c_int32,
                        [P,c.POINTER(GUID),c.POINTER(TRUSTDATA)],P(-1),c.byref(action),c.byref(trust)) == 0, 'Catalog trust close')
            finally:
                if admin.value:
                    self._ok(self._call('wintrust','CryptCATAdminReleaseContext',w.BOOL,[P,D],admin,0), 'Catalog context close')


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
        system=SystemPs51Verifier(pin, os.environ.get('SystemRoot','C:\\Windows'))
        handles=[]
        try:
            if not self.system_verified:
                handles=system.verify()
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
