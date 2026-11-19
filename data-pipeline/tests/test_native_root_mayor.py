"""C: root-only ACL policy; WinAPI and SID conversion are synthetic."""
import ctypes as c
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mayor_updates import native_launch as n
from mayor_updates.launch_contract import FixedLaunch
from mayor_updates.projection import Hold

AUTH='S-1-5-11';SYSTEM='S-1-5-18';ADMIN='S-1-5-32-544';USERS='S-1-5-32-545'
ROOT_ACES=[(0,0,4,AUTH),(0,11,0xE0010000,AUTH),
    (0,3,0x1F01FF,SYSTEM),(0,3,0x1F01FF,ADMIN),
    (0,3,0x1200A9,USERS),(0,0,0x1000A1,'S-1-15-3-1')]

class RootFixture:
    def __init__(self,path='C:\\',*,owner=n.TRUSTED_INSTALLER_SID,aces=None,protected=True):
        self.path=path;self.owner=owner;self.aces=list(ROOT_ACES if aces is None else aces)
        self.protected=protected;self.final=path;self.reparse=False;self.final_failure=False
        self.spec=FixedLaunch(r'C:\fixture\private\pwsh.exe',(),sha256(b'image').hexdigest(),'b'*64,'S-1-5-21-1004')
        self.api=n.NativeWindowsAdapter(self.spec);self.buffers=[];self.sids={1:owner};self.calls=[]
        self.acl=c.create_string_buffer(8);c.c_ushort.from_buffer(self.acl,4).value=len(self.aces)
        for kind,flags,mask,sid in self.aces:
            b=c.create_string_buffer(24);c.c_ubyte.from_buffer(b,0).value=kind;c.c_ubyte.from_buffer(b,1).value=flags
            c.c_ushort.from_buffer(b,2).value=24;n.D.from_buffer(b,4).value=mask
            self.buffers.append(b);self.sids[c.addressof(b)+8]=sid
    def factory(self,dll,name,result,types):
        def call(*a):
            self.calls.append((name,a))
            if name=='CreateFileW':return 10
            if name=='GetFileInformationByHandle':a[1]._obj.attributes=0x410 if self.reparse else 0x10;return 1
            if name=='GetFinalPathNameByHandleW':a[1].value=self.final;return 0 if self.final_failure else len(self.final)
            if name=='GetSecurityInfo':
                a[3]._obj.value=1;a[5]._obj.value=c.addressof(self.acl);a[7]._obj.value=2;return 0
            if name=='GetSecurityDescriptorControl':a[1]._obj.value=0x1000 if self.protected else 0;a[2]._obj.value=1;return 1
            if name=='GetAce':a[2]._obj.value=c.addressof(self.buffers[a[1]]);return 1
            if name in ('LocalFree','CloseHandle'):return 1
            raise AssertionError(name)
        return call
    def inspect(self,*,parent=True,register=True):
        with patch.object(self.api,'_fn',side_effect=self.factory),patch.object(self.api,'_sid',side_effect=lambda p:self.sids[p]):
            h=self.api._open(self.path,directory=True) if register else 10
            return self.api._acl(h,parent=parent)

class RootPolicyTests(unittest.TestCase):
    def test_observed_root_acl_passes_only_with_locked_root_identity(self):
        f=RootFixture();self.assertEqual(f.inspect(),n.TRUSTED_INSTALLER_SID)
        create=next(a for name,a in f.calls if name=='CreateFileW')
        self.assertEqual(create[2],3) # READ/WRITE, never DELETE sharing
        self.assertTrue(create[5]&0x00200000)
        self.assertIn('GetFinalPathNameByHandleW',[name for name,a in f.calls])
        with self.assertRaises(Hold):RootFixture().inspect(register=False)
    def test_delete_rename_replace_and_security_grants_hold(self):
        for mask in (2,0x10,0x40,0x100,0x10000,0x40000,0x80000,0x10000000,0x40000000,0x1000000):
            with self.subTest(mask=hex(mask)),self.assertRaises(Hold):
                RootFixture(aces=ROOT_ACES+[(0,0,mask,AUTH)]).inspect()
    def test_unknown_owner_inheritance_flags_or_structure_hold(self):
        for f in (RootFixture(owner='S-1-5-21-999'),RootFixture(protected=False),
                RootFixture(aces=ROOT_ACES+[(0,11,0x10000000,AUTH)]),
                RootFixture(aces=ROOT_ACES+[(0,0,4,USERS)]),
                RootFixture(aces=ROOT_ACES+[(9,0,1,AUTH)]),
                RootFixture(aces=ROOT_ACES+[(0,0x80,1,AUTH)])):
            with self.subTest(f=f),self.assertRaises(Hold):f.inspect()
    def test_root_identity_alias_reparse_query_failure_hold(self):
        for final in (r'C:\alias','D:\\','\\\\?\\D:\\'):
            f=RootFixture();f.final=final
            with self.subTest(final=final),self.assertRaises(Hold):f.inspect()
        f=RootFixture();f.reparse=True
        with self.assertRaises(Hold):f.inspect()
        f=RootFixture();f.final_failure=True
        with self.assertRaises(Hold):f.inspect()
    def test_no_exception_for_child_other_volume_or_executable(self):
        for f in (RootFixture(r'C:\Users'),RootFixture('D:\\')):
            with self.subTest(path=f.path),self.assertRaises(Hold):f.inspect()
        with self.assertRaises(Hold):RootFixture().inspect(parent=False)
        f=RootFixture();f.api.spec=FixedLaunch(r'C:\pwsh.exe',(),f.spec.image_sha256,'b'*64,f.spec.actor_sid)
        with self.assertRaises(Hold):f.inspect()
    def test_protected_direct_child_required_and_lower_guard_unchanged(self):
        safe=[(0,3,0x1F01FF,SYSTEM),(0,0,0x1200A9,USERS)]
        f=RootFixture(r'C:\Users',owner=SYSTEM,aces=safe);self.assertEqual(f.inspect(),SYSTEM)
        with self.assertRaises(Hold):RootFixture(r'C:\Users',owner=SYSTEM,aces=safe,protected=False).inspect()
        with self.assertRaises(Hold):RootFixture(r'C:\Users',owner=SYSTEM,aces=safe+[(0,0,4,AUTH)]).inspect()
        # TrustedInstaller trust must never expand beyond the root itself.
        with self.assertRaises(Hold):RootFixture(r'C:\Users\private',aces=safe).inspect()
        with self.assertRaises(Hold):RootFixture(r'C:\Users\private',owner=SYSTEM,aces=safe+[(0,0,0x10000,AUTH)]).inspect()
    def test_closed_root_handle_does_not_retain_exception(self):
        f=RootFixture();f.inspect()
        with patch.object(f.api,'_fn',side_effect=f.factory):f.api._close(10)
        with self.assertRaises(Hold):f.inspect(register=False)

if __name__=='__main__':unittest.main()

