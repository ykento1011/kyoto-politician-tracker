"""Fixed isolated bootstrap; source-disabled, no activation command-line switch."""
from pathlib import Path
from hashlib import sha256
import importlib.abc
import importlib.util
import json
import re
import sys

LIVE_BOOTSTRAP_ENABLED = False

PACKAGE_FILES=frozenset(('__init__','worker_ipc','native_launch','launch_contract',
                        'projection','stage2_guard','stage2_flow'))


class PinnedPackage(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    """Compile only approved .py bytes; never consult pyc/PATH/package caches."""
    def __init__(self,root,pins):
        self.root=Path(root)
        self.pins=dict(pins)
        required={'data-pipeline/mayor_updates/'+name+'.py' for name in PACKAGE_FILES}
        required.add('scripts/Stage2Worker.py')
        if set(self.pins)!=required or any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v) for v in self.pins.values()):
            raise RuntimeError('Exact source PIN set required')
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='mayor_updates':name='__init__'
        elif fullname.startswith('mayor_updates.'):name=fullname[len('mayor_updates.'):]
        else:return None
        if name not in PACKAGE_FILES or '.' in name:raise ImportError('Unpinned worker module')
        return importlib.util.spec_from_loader(fullname,self,is_package=name=='__init__')
    def create_module(self,spec):return None
    def exec_module(self,module):
        name='__init__' if module.__name__=='mayor_updates' else module.__name__.split('.')[-1]
        relative='data-pipeline/mayor_updates/'+name+'.py'
        source=self.root/relative
        with source.open('rb') as stream:body=stream.read(1024*1024+1)
        if len(body)>1024*1024 or sha256(body).hexdigest()!=self.pins[relative]:raise ImportError('Worker source SHA differs')
        module.__file__=str(source)
        if name=='__init__':module.__path__=[]  # no PathFinder fallback
        exec(compile(body,str(source),'exec',dont_inherit=True),module.__dict__)

def main():
    if LIVE_BOOTSTRAP_ENABLED is not True:
        raise SystemExit('Stage 2 worker live entry disabled')
    # Parent pins this bootstrap and every required package byte under retained
    # owner-only/non-reparse/read locks before starting the isolated interpreter.
    if len(sys.argv)!=3 or sys.argv[1]!='--stage2-worker':raise SystemExit('Fixed worker request required')
    root=Path(__file__).resolve().parents[1]
    with open(sys.argv[2],'rb') as stream:body=stream.read(16*1024+1)
    if len(body)>16*1024:raise SystemExit('Request exceeds fixed bootstrap bound')
    request=json.loads(body.decode('utf-8'))
    # Routing bytes are untrusted here; the parent holds their verified file and
    # ancestry locks. worker_entry independently checks all request bytes/ACLs.
    if Path(request['code_root']).resolve()!=root:raise SystemExit('Fixed code root differs')
    pins=request['code_pins']
    if sha256(Path(__file__).read_bytes()).hexdigest()!=pins['scripts/Stage2Worker.py']:
        raise SystemExit('Bootstrap SHA differs')
    if any(name=='mayor_updates' or name.startswith('mayor_updates.') for name in sys.modules):
        raise SystemExit('Unexpected preloaded worker package')
    loader=PinnedPackage(root,pins)
    sys.meta_path.insert(0,loader)
    try:
        from mayor_updates.worker_ipc import worker_entry
        worker_entry(sys.argv[2])  # independently source-disabled
    finally:sys.meta_path.remove(loader)

if __name__=='__main__':main()
