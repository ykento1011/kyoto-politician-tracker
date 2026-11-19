"""Offline demo and source-disabled, fully pinned native entry bootstrap.

The fixture implementation is deliberately loaded from the repository's tests,
not represented as a native OS adapter. --runtime cannot enable source gates.
"""
import argparse
import importlib.util
import importlib.abc
from hashlib import sha256
import json
from pathlib import Path
import sys

PARENT_MODULES=frozenset(('__init__','projection','launch_contract','native_launch','stage2_guard',
    'stage2_flow','worker_ipc','stage2_acceptance','stage2_os_adapter','stage2_windows_identity','stage2_native_entry'))


def native_runtime(path, expected_sha):
    """Verify all controller source bytes before importing a native entry.

    No sys.path/pyc/package fallback. Old worker's exact eight-PIN contract is
    unchanged; this is a distinct controller PIN set, not a worker permission.
    """
    import re
    if not expected_sha or not re.fullmatch('[0-9a-f]{64}',expected_sha):
        raise ValueError('Fixed runtime SHA required')
    body=path.read_bytes()
    if len(body)>65536 or sha256(body).hexdigest()!=expected_sha:raise ValueError('Runtime SHA/size')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate runtime key')
            result[key]=value
        return result
    value=json.loads(body.decode('utf-8-sig'),object_pairs_hook=pairs)
    root=Path(value['code_root'])
    required={'data-pipeline/mayor_updates/'+name+'.py' for name in PARENT_MODULES}
    required.update(('scripts/Run-Stage2Acceptance.py','scripts/Stage2Worker.py','scripts/Stage2AdminBridge.ps1'))
    pins=value['controller_code_pins']
    if set(pins)!=required:raise ValueError('Exact controller dependency PIN set required')
    source={}
    for name,pin in pins.items():
        raw=(root/name).read_bytes()
        if len(raw)>1024*1024 or sha256(raw).hexdigest()!=pin:raise ValueError('Controller source PIN differs')
        source[name]=raw
    if sha256(Path(__file__).read_bytes()).hexdigest()!=pins['scripts/Run-Stage2Acceptance.py']:
        raise ValueError('Entry source differs')
    if any(k=='mayor_updates' or k.startswith('mayor_updates.') for k in sys.modules):
        raise ValueError('Unverified preloaded package refused')
    class PinnedController(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if fullname=='mayor_updates':name='__init__'
            elif fullname.startswith('mayor_updates.'):name=fullname[len('mayor_updates.'):]
            else:return None
            if name not in PARENT_MODULES or '.' in name:raise ImportError('Unpinned controller module')
            return importlib.util.spec_from_loader(fullname,self,is_package=name=='__init__')
        def create_module(self,spec):return None
        def exec_module(self,module):
            name='__init__' if module.__name__=='mayor_updates' else module.__name__.split('.')[-1]
            relative='data-pipeline/mayor_updates/'+name+'.py'
            module.__file__=str(root/relative)
            if name=='__init__':module.__path__=[]
            exec(compile(source[relative],module.__file__,'exec',dont_inherit=True),module.__dict__)
    loader=PinnedController();sys.meta_path.insert(0,loader)
    try:
        from mayor_updates.stage2_native_entry import run
        return run(path,expected_sha)
    finally:sys.meta_path.remove(loader)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--offline', action='store_true')
    mode.add_argument('--runtime',type=Path)
    parser.add_argument('--runtime-sha256')
    parser.add_argument('--state-root', type=Path)
    args = parser.parse_args()
    if args.runtime:
        result=native_runtime(args.runtime,args.runtime_sha256)
        return 0 if result['state']=='PASS' else 1
    if args.state_root is None:parser.error('--state-root is required in offline mode')
    repo = Path(__file__).resolve().parents[1]
    fixture = repo/'data-pipeline/tests/test_stage2_acceptance_mayor.py'
    spec = importlib.util.spec_from_file_location('stage2_offline_fixture', fixture)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Reject any existing directory, even an empty one. No historical state reuse.
    args.state_root.mkdir(exist_ok=False)
    ports = module.FakePorts()
    result = module.flow.run(args.state_root, module.PLAN, ports,
                             module.FakeWorker(ports), simulation=True,
                             clock=lambda: ports.now)
    print(json.dumps({'mode': 'SYNTHETIC_OFFLINE_ONLY', 'result': result,
                      'real_firewall_changes': 0, 'real_audit_changes': 0,
                      'real_probes': 0, 'real_worker_launches': 0}, sort_keys=True))
    return 0 if result['state'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
