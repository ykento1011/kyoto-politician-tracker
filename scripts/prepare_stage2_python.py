"""Exclusive nonproduction Python copy. No interpreter/worker/network launch.

Run only for an approved destination under an existing owner-only root. ACL and
signature verification are separate read-only steps; a copy is not acceptance.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

SEEDS=('ctypes','ctypes.wintypes','dataclasses','hashlib','importlib.abc','importlib.util',
       'json','math','ntpath','pathlib','re','secrets','tempfile','time','subprocess','copy')

def imports(path,module,package):
    tree=ast.parse(path.read_bytes(),filename=str(path))
    result=set()
    class Scan(ast.NodeVisitor):
        def visit_If(self,node):
            # Standalone module self-tests are not worker dependencies.
            if isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name) and node.test.left.id=='__name__':return
            self.generic_visit(node)
        def visit_Import(self,node):result.update(a.name for a in node.names)
        def visit_ImportFrom(self,node):
            prefix=module.split('.') if package else module.split('.')[:-1]
            if node.level:prefix=prefix[:len(prefix)-node.level+1]
            else:prefix=[]
            base='.'.join(prefix+([node.module] if node.module else []))
            if base:result.add(base)
            result.update('.'.join(filter(None,(base,a.name))) for a in node.names if a.name!='*')
    Scan().visit(tree)
    return result

def pe_imports(body):
    if body[:2]!=b'MZ':return []
    pe=struct.unpack_from('<I',body,60)[0];nsec=struct.unpack_from('<H',body,pe+6)[0]
    opt=pe+24;optsize=struct.unpack_from('<H',body,pe+20)[0]
    data=opt+(112 if struct.unpack_from('<H',body,opt)[0]==0x20b else 96)
    sections=[]
    for i in range(nsec):
        pos=opt+optsize+40*i;vsize,rva,size,raw=struct.unpack_from('<IIII',body,pos+8)
        sections.append((rva,max(vsize,size),raw))
    def offset(rva):
        for start,size,raw in sections:
            if start<=rva<start+size:return raw+rva-start
        raise ValueError('Unknown PE RVA')
    def text(rva):
        start=offset(rva);end=body.index(b'\0',start)
        return body[start:end].decode('ascii').lower()
    out=[]
    for directory,step,name_offset in ((1,20,12),(13,32,4)):
        rva,length=struct.unpack_from('<II',body,data+8*directory)
        if not rva:continue
        start=offset(rva)
        for pos in range(start,start+length,step):
            if not any(body[pos:pos+step]):break
            name=struct.unpack_from('<I',body,pos+name_offset)[0]
            if name:out.append(text(name))
    return out

def prepare(source,destination,*,plan_only=False):
    source=Path(source).resolve(strict=True);destination=Path(destination)
    if destination.exists() and not plan_only:raise RuntimeError('HOLD: destination already exists')
    selected={source/'python.exe',source/'python315.dll',source/'python3.dll'}
    pending=list(SEEDS);seen=set();unresolved=set()
    while pending:
        module=pending.pop()
        if module in seen:continue
        seen.add(module)
        parts=module.split('.');file=source/'Lib'/Path(*parts).with_suffix('.py')
        package=source/'Lib'/Path(*parts)/'__init__.py'
        extension=source/'DLLs'/(parts[0]+'.pyd')
        if package.is_file():file=package;is_package=True
        elif file.is_file():is_package=False
        elif len(parts)==1 and extension.is_file():selected.add(extension);continue
        else:
            if len(parts)==1 and module not in sys.builtin_module_names:unresolved.add(module)
            continue
        selected.add(file)
        for i in range(1,len(parts)):
            parent=source/'Lib'/Path(*parts[:i])/'__init__.py'
            if parent.is_file():pending.append('.'.join(parts[:i]))
        pending.extend(imports(file,module,is_package))
    # CPython startup chooses codecs dynamically, independent of AST imports.
    selected.update((source/'Lib/encodings').glob('*.py'))
    selected.add(source/'Lib/os.py')
    lookup={p.name.lower():p for folder in (source,source/'DLLs') for p in folder.iterdir() if p.is_file()}
    pending=list(selected);system=set()
    while pending:
        file=pending.pop()
        for name in pe_imports(file.read_bytes()):
            dep=lookup.get(name)
            if dep is not None:
                if dep not in selected:selected.add(dep);pending.append(dep)
            else:system.add(name)
    if plan_only:
        missing=sorted(p.relative_to(source).as_posix() for p in selected if not (destination/'runtime'/p.relative_to(source)).is_file())
        print(json.dumps({'selected_files':len(selected),'missing_from_existing_copy':missing,
            'unresolved_static_names':sorted(unresolved),'network_requests':0,'writes':0}))
        return
    destination.mkdir()  # exclusive; inheriting only destination parent's ACL
    payload=destination/'runtime';payload.mkdir()
    rows=[]
    for file in sorted(selected):
        if file.is_symlink():raise RuntimeError('HOLD: source symlink')
        relative=file.relative_to(source);target=payload/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        body=file.read_bytes()
        with target.open('xb') as stream:stream.write(body)
        old=sha256(body).hexdigest();new=sha256(target.read_bytes()).hexdigest()
        if old!=new:raise RuntimeError('HOLD: copy SHA differs')
        rows.append({'path':relative.as_posix(),'sha256':new,'bytes':len(body)})
    # Isolated layout: no site import, source directory, environment or pyc copy.
    pth=b'Lib\nDLLs\n'
    with (payload/'python315._pth').open('xb') as stream:stream.write(pth)
    result={'schema_version':1,'mode':'disabled_nonproduction_copy','source_files':rows,
        'generated':[{'path':'python315._pth','sha256':sha256(pth).hexdigest()}],
        'selection':'static worker stdlib import closure + startup codecs + PE/delay-import closure',
        'unresolved_static_names':sorted(unresolved),'system_dll_imports':sorted(system),
        'loaded_dll_resolution':'UNTESTED_NO_PROCESS','signature':'NOT_ACCEPTED_BY_COPY',
        'runtime_launches':0,'network_requests':0}
    with (destination/'copy_manifest.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'copied_files':len(rows),'copied_bytes':sum(r['bytes'] for r in rows),
        'all_copy_sha_equal':True,'generated_config_files':1,'unresolved_static_names':sorted(unresolved),
        'system_dll_imports':sorted(system),'runtime_launches':0,'network_requests':0}))

if __name__=='__main__':prepare(sys.argv[1],sys.argv[2],plan_only='--plan-only' in sys.argv[3:])
