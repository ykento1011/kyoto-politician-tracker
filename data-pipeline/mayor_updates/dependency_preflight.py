"""Stdlib-only preflight, adapted from the accepted Kyoto G1/G2 checks.

Private contracts bind the interpreter, dependency versions, runtime digest,
input PINs and output root. No private paths or approvals are shipped here.
This check supplements (never replaces) the existing business-side guards.
"""
import hashlib
from importlib import import_module, metadata
import json
from pathlib import Path
import sys

MODULES = {'jsonschema': 'jsonschema', 'beautifulsoup4': 'bs4'}

class DependencyHold(RuntimeError):
    pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def runtime_digest(runtime):
    return hashlib.sha256(json.dumps(runtime, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()

def require_dependencies(contract):
    if (Path(sys.executable).resolve() != Path(contract['python']).resolve() or
            sha(sys.executable) != contract['python_sha256']):
        raise DependencyHold('HOLD: unapproved Python executable/PIN')
    expected = contract['dependencies']
    if not MODULES.keys() <= expected.keys():
        raise DependencyHold('HOLD: mandatory dependency contract missing')
    for name, version in expected.items():
        if not version or metadata.version(name) != version:
            raise DependencyHold('HOLD: dependency version mismatch: ' + name)
    # Never accept arbitrary module names from a runtime/contract.
    for name in MODULES.values():
        import_module(name)

def require_contract(runtime, contract_path, contract_sha256):
    """Read-only: no business imports, mkdir, reservations or P1 initialization."""
    try:
        if sha(contract_path) != contract_sha256:
            raise DependencyHold('HOLD: preflight contract PIN mismatch')
        contract = json.loads(Path(contract_path).read_text(encoding='utf-8-sig'))
        if runtime.get('network_enabled') is not False:
            raise DependencyHold('HOLD: this entry has no network mode')
        if (runtime_digest(runtime) != contract['runtime_sha256'] or
                runtime['state_root'] != contract['state_root']):
            raise DependencyHold('HOLD: runtime/input/output contract mismatch')
        root = Path(runtime['state_root']).resolve(strict=True)
        if not root.is_dir() or any(p.name.lower() == 'public' or (p/'.git').exists()
                                    for p in (root, *root.parents)):
            raise DependencyHold('HOLD: output must be a provisioned private directory')
        # Runtime digest binds all settings; verify actual bytes before business import.
        specs = [runtime[key] for key in ('config', 'baseline', 'profile')]
        specs += runtime['code_files']
        required = {p.resolve() for p in Path(__file__).parent.glob('*.py')}
        if not required <= {Path(s['path']).resolve() for s in runtime['code_files']}:
            raise DependencyHold('HOLD: executing package must be pinned')
        for spec in specs:
            if sha(spec['path']) != spec['sha256']:
                raise DependencyHold('HOLD: pinned input changed')
        for key in ('config', 'profile'):
            data = json.loads(Path(runtime[key]['path']).read_text(encoding='utf-8-sig'))
            if data.get('network_enabled') is not False or data.get('enabled') is not False:
                raise DependencyHold('HOLD: enabled input in saved-source entry')
        require_dependencies(contract)
        return {'status':'PASS', 'mode':'saved_originals_only'}
    except DependencyHold:
        raise
    except Exception as exc:
        raise DependencyHold('HOLD: dependency/I-O preflight: ' + str(exc)) from exc
