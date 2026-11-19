"""PS5.1-only boundary; native calls/network/processes are replaced, never enabled."""
import copy
import ctypes as c
from hashlib import sha256
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import stage2_windows_identity as m
from mayor_updates.native_launch import CERTCONTEXT, PROVIDERCERT_HEAD
from mayor_updates.projection import Hold

ROOT = r'C:\Windows'
EXE = ROOT + r'\System32\WindowsPowerShell\v1.0\powershell.exe'
CAT = ROOT + r'\System32\CatRoot\{F750E6C3-38EE-11D1-85E5-00C04FC295EE}\Microsoft-Windows-Client-Features-Package~31bf3856ad364e35~amd64~~10.0.1.cat'
PIN = dict(path=EXE, sha256=sha256(b'image').hexdigest(), signer_sha256=sha256(b'cert').hexdigest(),
           aliases=[EXE, ROOT+r'\WinSxS\amd64_microsoft-windows-powershell-exe_31bf3856ad364e35_10.0.1_none_0123456789abcdef\powershell.exe'],
           volume_serial=7, file_id=9, catalog=dict(path=CAT, sha256=sha256(b'cat').hexdigest(), member_hash='01'*32))
PIN['catalog'].update(volume_serial=7,file_id=10,aliases=[CAT,ROOT+'\\WinSxS\\Catalogs\\'+PIN['catalog']['sha256']+'.cat',
    ROOT+'\\servicing\\Packages\\'+CAT.rsplit('\\',1)[1]])


class Tests(unittest.TestCase):
    def setUp(self):
        for name in ('subprocess.Popen', 'socket.socket', 'socket.getaddrinfo'):
            p=patch(name, side_effect=AssertionError('Forbidden live operation')); p.start(); self.addCleanup(p.stop)

    def test_exact_inbox_paths(self):
        self.assertEqual(m.ps51_paths(PIN,ROOT)[0],EXE)

    def test_path_negative_boundaries(self):
        for key,value in [('path',r'C:\scratch\powershell.exe'), ('aliases',[EXE,EXE]),
                          ('aliases',[EXE,r'C:\scratch\powershell.exe']), ('volume_serial','7')]:
            with self.subTest(key=key,value=value):
                p=copy.deepcopy(PIN); p[key]=value
                with self.assertRaises(Hold):m.ps51_paths(p,ROOT)
        for key,value in [('path',r'C:\scratch\foo.cat'),('member_hash','FF'),('sha256','0')]:
            p=copy.deepcopy(PIN);p['catalog'][key]=value
            with self.assertRaises(Hold):m.ps51_paths(p,ROOT)

    def verifier(self, mutate=None, trust=False):
        v=m.SystemPs51Verifier(copy.deepcopy(PIN),ROOT)
        v.aliases=lambda path,expected:expected
        v._open=lambda path,**kw:path
        v._close=lambda h:None
        v._acl=lambda *a,**k:None
        v.catalog_directory_acl=lambda *a:None
        def info(h):
            iscat=h in PIN['catalog']['aliases']
            row=SimpleNamespace(attributes=0,links=3 if iscat else 2,volume=7,index_high=0,index_low=10 if iscat else 9)
            if mutate and h==EXE:mutate(row)
            return row
        v._info=info
        v._bytes=lambda h,i:b'cat' if h in PIN['catalog']['aliases'] else b'image'
        v.verify_catalog=lambda h: None if trust else (_ for _ in ()).throw(Hold('Unverified signature'))
        return v

    def test_locked_aliases_identity(self):
        self.assertTrue(self.verifier(trust=True).verify())

    def test_file_identity_mismatches_hold(self):
        for key,value in [('links',1),('volume',8),('index_low',10),('attributes',0x10)]:
            with self.subTest(key=key):
                with self.assertRaises(Hold):self.verifier(lambda r:setattr(r,key,value),True).verify()

    def test_signature_failure_closes_handles(self):
        v=self.verifier(); closed=[];v._close=closed.append
        with self.assertRaises(Hold):v.verify()
        self.assertIn(EXE,closed);self.assertIn(CAT,closed)

    def test_catalog_directory_boundary(self):
        v=m.SystemPs51Verifier(PIN,ROOT)
        with self.assertRaises(Hold):v.catalog_directory_acl(1,r'C:\scratch')

    def test_catalog_acl_writer_boundary(self):
        for sid,pass_expected in [(m.CRYPTSVC_SID,True),('S-1-5-21-999',False)]:
            v=m.SystemPs51Verifier(PIN,ROOT)
            acl=c.create_string_buffer(16);c.c_ushort.from_buffer(acl,4).value=1
            ace=c.create_string_buffer(32);c.c_ushort.from_buffer(ace,2).value=20
            m.D.from_buffer(ace,4).value=0x1f01ff
            v._sid=lambda ptr:'S-1-5-18' if ptr==123 else sid
            def call(dll,name,result,types,*args):
                if name=='GetSecurityInfo':
                    c.cast(args[3],c.POINTER(m.P))[0]=123
                    c.cast(args[5],c.POINTER(m.P))[0]=c.addressof(acl)
                    return 0
                if name=='GetAce':c.cast(args[2],c.POINTER(m.P))[0]=c.addressof(ace);return 1
                raise AssertionError(name)
            v._call=call
            if pass_expected:v.catalog_directory_acl(1,ROOT+r'\System32\CatRoot')
            else:
                with self.assertRaises(Hold):v.catalog_directory_acl(1,ROOT+r'\System32\CatRoot')

    def test_cache_only_catalog_trust_and_failure(self):
        for status in (0,-1):
            v=m.SystemPs51Verifier(PIN,ROOT);actions=[]
            der=c.create_string_buffer(b'cert');ctx=CERTCONTEXT();ctx.encoded=c.addressof(der);ctx.length=4
            cert=PROVIDERCERT_HEAD();cert.cert=c.pointer(ctx)
            def call(dll,name,result,types,*args):
                if name=='CryptCATAdminAcquireContext2':c.cast(args[0],c.POINTER(m.P))[0]=123;return 1
                if name=='CryptCATAdminCalcHashFromFileHandle2':
                    c.cast(args[2],c.POINTER(m.D))[0]=32
                    if args[3] is not None:c.memset(args[3],1,32)
                    return 1
                if name=='WinVerifyTrust':
                    t=c.cast(args[2],c.POINTER(m.TRUSTDATA)).contents;actions.append(t.action)
                    self.assertEqual((t.flags,t.revocation,t.choice,t.ui),(0x1080,1,2,2))
                    t.state=234
                    return status if t.action==1 else 0
                if name in ('WTHelperProvDataFromStateData','WTHelperGetProvSignerFromChain'):return 345
                if name=='WTHelperGetProvCertFromChain':return c.addressof(cert)
                if name=='CryptCATAdminReleaseContext':return 1
                raise AssertionError(name)
            v._call=call
            if status==0:v.verify_catalog(77)
            else:
                with self.assertRaises(Hold):v.verify_catalog(77)
            self.assertEqual(actions,[1,2])

    def test_worker_single_link_guard_unchanged(self):
        from mayor_updates.native_launch import NativeWindowsAdapter
        import inspect
        self.assertIn('info.links != 1',inspect.getsource(NativeWindowsAdapter.inspect_file))


if __name__=='__main__':unittest.main()
