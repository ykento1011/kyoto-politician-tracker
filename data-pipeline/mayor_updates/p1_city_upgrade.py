"""Materialize the reviewed P1 patch in a NEW private code directory, offline.

Never modifies its input. No automatic activation or replacement of live pins.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from .projection import Hold
from .p1_bridge import PINS

def manifest():
    root=Path(__file__).resolve().parents[1]/'p1_patches'
    return root,json.loads((root/'city_identity.json').read_text(encoding='utf-8'))

def prepare_copy(approved_root,destination):
    source=Path(approved_root).resolve(strict=True);dest=Path(destination).resolve()
    if dest==source or source in dest.parents or dest in source.parents or dest.exists():
        raise Hold('Use a new independent code directory')
    patch_root,spec=manifest()
    expected={**{'budget/'+n:h for n,h in PINS.items()},**spec['before']}
    for name,sha in expected.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha:raise Hold('Unexpected P1 input: '+name)
    patch=patch_root/'city_identity.patch'
    if hashlib.sha256(patch.read_bytes()).hexdigest()!=spec['patch_sha256']:raise Hold('Patch SHA mismatch')
    dest.mkdir()
    # Only approved package code and its contract schema; never case data.
    for item in [*(source/'budget').rglob('*.py'),source/'budget/schema/v1.json']:
        target=dest/item.relative_to(source)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(item,target)
    result=subprocess.run(['git','apply','--ignore-space-change',str(patch)],cwd=dest,capture_output=True,text=True)
    if result.returncode:raise Hold('P1 patch failed: '+result.stderr)
    for name,sha in spec['after'].items():
        # Candidate pins use LF regardless of the host Git autocrlf setting.
        path=dest/name
        path.write_text(path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:raise Hold('Unexpected patched P1: '+name)
    return spec['after']
