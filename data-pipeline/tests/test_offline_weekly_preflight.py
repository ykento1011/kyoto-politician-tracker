"""Fresh-process entry tests: synthetic contracts only, no P1 or cycle execution."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PIPELINE=Path(__file__).resolve().parents[1]
PACKAGE=PIPELINE/'mayor_updates'
PROFILE=PIPELINE.parent/'config/mayor_offline_weekly.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p)}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

CHILD=r'''
import importlib.abc, importlib.machinery, json, sys, socket
from pathlib import Path
from importlib import metadata
sys.path.insert(0,sys.argv[1]); mode=sys.argv[2]; args=sys.argv[3:]
events=[]
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
class Loader(importlib.abc.Loader):
 def __init__(self,original):self.original=original
 def create_module(self,spec):return self.original.create_module(spec)
 def exec_module(self,module):
  self.original.exec_module(module)
  if module.__name__=='mayor_updates.weekly':
   module.assert_owner_only=lambda path:events.append('owner_check')
   module.P1Bridge=lambda *a,**k:events.append('P1_STUB') or object()
  if module.__name__=='mayor_updates.continuous':
   def cycle(*a,**k):
    assert k['city']=='yokohama' and k['offline_sources'] and callable(k['observation_check'])
    assert a[1]['network_enabled'] is False and a[1]['enabled'] is False
    events.append('CYCLE_STUB');return {'state_advanced':True}
   module.cycle=cycle
class Watch(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith('mayor_updates.') and fullname not in ('mayor_updates.offline_weekly','mayor_updates.dependency_preflight'):
   events.append('business_import:'+fullname)
   if mode!='normal':raise AssertionError('business import before HOLD')
   spec=importlib.machinery.PathFinder.find_spec(fullname,path)
   if spec and spec.loader:spec.loader=Loader(spec.loader)
   return spec
sys.meta_path.insert(0,Watch())
if mode=='missing_dependency':
 original=metadata.version
 def version(name):
  if name=='jsonschema':raise metadata.PackageNotFoundError(name)
  return original(name)
 metadata.version=version
from mayor_updates import offline_weekly
# Real main, preflight, run, prepare and manifest execute; cycle alone is stubbed.
sys.argv=['offline_weekly',*args]
try:
 offline_weekly.main();outcome='PASS'
except Exception as exc:
 outcome=type(exc).__name__+':'+str(exc)
print(json.dumps({'outcome':outcome,'events':events}))
'''

class OfflinePreflightTests(unittest.TestCase):
 def run_case(self,mode):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);state=root/'state';state.mkdir()
   # Existing state sentinel must survive even malformed-input and dependency holds.
   sentinel=state/'last-good';sentinel.write_text('unchanged')
   config=root/'config.json';config.write_text(json.dumps({'network_enabled':False,'enabled':False,'cities':{'yokohama':{}}}))
   baseline=root/'baseline.json';baseline.write_text('{}')
   shell=root/'pwsh.exe';shell.write_bytes(b'SYNTHETIC_NOT_EXECUTED')
   runtime={'network_enabled':False,'state_root':str(state),'config':pin(config),'baseline':pin(baseline),
    'profile':pin(PROFILE),'code_files':[pin(p) for p in PACKAGE.glob('*.py')],
    'city':'yokohama','base_revision':'synthetic-only','p1_code_root':str(root/'no_p1'),
    'snapshot_root':str(root/'no_cas'),'powershell_exe':str(shell)}
   contract={'python':sys.executable,'python_sha256':sha(Path(sys.executable)),
    'dependencies':{name:metadata.version(name) for name in ('jsonschema','beautifulsoup4')},
    'runtime_sha256':digest(runtime),'state_root':str(state)}
   if mode=='contract_mismatch':contract['state_root']=str(root/'wrong')
   if mode=='network_enabled':runtime['network_enabled']=True;contract['runtime_sha256']=digest(runtime)
   if mode=='wrong_profile':
    other=root/'other-profile.json';other.write_bytes(PROFILE.read_bytes());runtime['profile']=pin(other);contract['runtime_sha256']=digest(runtime)
   if mode=='input_changed':config.write_text('{"changed":true}')
   if mode=='missing_dependency_contract':contract['dependencies'].pop('jsonschema')
   if mode=='missing_output':runtime['state_root']=str(root/'missing');contract['state_root']=runtime['state_root'];contract['runtime_sha256']=digest(runtime)
   if mode=='input_network_enabled':
    config.write_text(json.dumps({'network_enabled':True,'enabled':False}));runtime['config']=pin(config);contract['runtime_sha256']=digest(runtime)
   rp=root/'runtime.json';rp.write_text(json.dumps(runtime));cp=root/'contract.json';cp.write_text(json.dumps(contract))
   before={str(p.relative_to(state)):p.read_bytes() for p in state.rglob('*') if p.is_file()}
   result=subprocess.run([sys.executable,'-B','-c',CHILD,str(PIPELINE),mode,'--runtime',str(rp),'--contract',str(cp),'--contract-sha256',sha(cp)],capture_output=True,text=True,timeout=25)
   self.assertEqual(result.returncode,0,result.stderr)
   data=json.loads(result.stdout.splitlines()[-1]);events=data['events']
   if mode=='normal':
    self.assertEqual(data['outcome'],'PASS',data);self.assertEqual(events.count('P1_STUB'),1);self.assertEqual(events.count('CYCLE_STUB'),1)
    self.assertTrue(any(e.startswith('business_import:') for e in events));self.assertIn('owner_check',events)
   else:
    self.assertTrue(data['outcome'].startswith('DependencyHold:HOLD:'),data);self.assertEqual(events,[],data)
   self.assertEqual(before,{str(p.relative_to(state)):p.read_bytes() for p in state.rglob('*') if p.is_file()})
   self.assertFalse((root/'no_p1').exists());self.assertFalse((root/'no_cas').exists())
 def test_normal_real_entry_and_preflight_to_stub(self):self.run_case('normal')
 def test_wrong_profile_before_business_import(self):self.run_case('wrong_profile')
 def test_missing_dependency_before_business_import(self):self.run_case('missing_dependency')
 def test_contract_mismatch_before_business_import(self):self.run_case('contract_mismatch')
 def test_network_enabled_before_business_import(self):self.run_case('network_enabled')
 def test_changed_input_before_business_import(self):self.run_case('input_changed')
 def test_missing_dependency_contract(self):self.run_case('missing_dependency_contract')
 def test_missing_output_before_business_import(self):self.run_case('missing_output')
 def test_input_network_enabled(self):self.run_case('input_network_enabled')

if __name__=='__main__':unittest.main()
