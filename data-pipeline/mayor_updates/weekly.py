"""Persistent owner-run entry: private acquisition and review, never publication.

The single state pointer commits only after all successful artifacts are durable.
A failed/interrupted run retains the previous pointer. A stale lock requires an
operator check; it is never removed automatically or used to retry a GET.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import uuid
from .acquire import assert_owner_only, capture_sources, validate_sources
from .engine import PrivateOutput
from .operations import load, run_trial
from .p1_bridge import P1Bridge
from .projection import Hold


def atomic_json(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists(): temp.unlink()


@contextmanager
def single_run(root):
    lock = root / 'weekly.lock'
    try:
        f = lock.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise Hold('Concurrent or interrupted run: inspect weekly.lock; no automatic retry') from exc
    try:
        with f:
            json.dump({'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat()},f)
            f.flush(); os.fsync(f.fileno())
        yield
    finally:
        lock.unlink()


def validate_plan(config):
    sources = config['cities']['kyoto']['monitor_sources']
    validate_sources(sources)
    c = config['communication']
    required = {'method':'GET','tls_verify':True,'redirects':0,'retries':0,
                'timeout_seconds':10,'max_requests_per_run':3,
                'max_total_received_bytes':6291456,'follow_discovered_links':False}
    if any(c.get(k) != v for k,v in required.items()) or sum(s['max_bytes'] for s in sources)>6291456:
        raise Hold('Kyoto weekly HTML communication limits changed')
    if config.get('pdf_watch',{}).get('enabled'):
        raise Hold('PDF monitoring is a separate, not-yet-enabled acquisition path')
    return sources


def pinned_input(spec):
    path = Path(spec['path']).resolve(strict=True)
    assert_owner_only(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
        raise Hold('Pinned local input changed: ' + path.name)
    return path


def validate_runtime(runtime, *, reuse_saved):
    root = PrivateOutput(runtime['state_root']).root
    assert_owner_only(root); assert_owner_only(runtime['snapshot_root'])
    paths = {name:pinned_input(runtime[name]) for name in ('config','baseline','rules')}
    for spec in runtime['code_files']: pinned_input(spec)
    if not runtime['code_files'] or not any(Path(s['path']).resolve()==Path(__file__).resolve() for s in runtime['code_files']):
        raise Hold('Executing weekly entry must be pinned')
    config = load(paths['config']); validate_plan(config)
    if not reuse_saved and not (runtime.get('network_enabled') is True and
            config.get('network_enabled') is True and config.get('enabled') is True and
            config['cities']['kyoto'].get('enabled') is True):
        raise Hold('Weekly live acquisition is not activated')
    return root, paths, config


def commit_success(root, output, prior, monitor_state, status):
    if status['state']=='stopped_no_public_change':
        return False
    state = deepcopy(prior)
    state.update(schema_version=1, monitor=monitor_state, last_success_run=str(output),
                 last_success_at=datetime.now(timezone.utc).isoformat())
    seen = state.setdefault('seen_reviews',{})
    for key,name in status.get('new_reviews',{}).items():
        seen[key] = str(output / name)
    # The pointer contains both monitoring and review identities in one commit.
    atomic_json(root / 'state.json',state)
    return True


def review_index(output, status, *, city_label="京都"):
    reviews = status.get('new_reviews',{})
    if not reviews: return
    rows=[]
    for name in reviews.values():
        payload=load(output/name)
        rows.append('<h2>'+escape(name)+'</h2><pre>'+escape(json.dumps(payload,ensure_ascii=False,indent=2))+'</pre>')
    PrivateOutput(output).write('new_reviews.html','<!doctype html><html lang="ja"><meta charset="utf-8">'
        '<title>'+escape(city_label)+'・今回変わった根拠の確認</title><style>body{max-width:1100px;margin:32px auto;font-family:sans-serif}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>今回の変更だけを確認</h1>'
        '<p>未確認・未公開。原本の変更は政策中止や予算変更を自動的に意味しません。</p>'+''.join(rows)+'</html>')


def run(runtime, *, reuse_saved=False):
    root,paths,config=validate_runtime(runtime,reuse_saved=reuse_saved)
    with single_run(root):
        state_path=root/'state.json'
        prior=load(state_path) if state_path.exists() else {'schema_version':1,'monitor':{},'seen_reviews':{}}
        run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
        runs=root/'runs'; runs.mkdir(exist_ok=True)
        output=runs/run_id; output.mkdir()
        out=PrivateOutput(output)
        try:
            acquisition=None
            if not reuse_saved:
                acq=output/'acquisition'; acq.mkdir()
                acquisition=capture_sources(runtime['p1_code_root'],runtime['snapshot_root'],
                    config['cities']['kyoto']['monitor_sources'],acq,authorized=True,refresh=True)
            bridge=P1Bridge(runtime['p1_code_root'],runtime['snapshot_root'])
            result,_=run_trial(bridge,config,load(paths['baseline']),load(paths['rules']),output,
                previous=prior.get('monitor'),base_revision=runtime['base_revision'],acquisition=acquisition,
                seen_reviews=prior.get('seen_reviews',{}))
            status=load(output/'run_status.json')
            review_index(output,status)
            committed=commit_success(root,output,prior,result['state'],status)
            return {'run_dir':str(output),'state':status['state'],'state_advanced':committed,
                    'new_review_count':len(status.get('new_reviews',{})),
                    'new_get_requests':0 if reuse_saved else acquisition['new_get_requests'],
                    'public_writes':0}
        except Exception as exc:
            out.json('failure.json',{'state':'stopped_no_public_change','reason':str(exc),
                                    'previous_state_retained':True,'public_writes':0})
            raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',required=True)
    p.add_argument('--reuse-saved',action='store_true',help='Offline replay; zero HTTP, even when activation is disabled')
    a=p.parse_args()
    runtime=load(a.runtime)
    if os.name=='nt':
        shell=Path(runtime['powershell_exe']).resolve(strict=True)
        if shell.name.lower()!='pwsh.exe': raise Hold('PowerShell runtime must be explicit')
        os.environ['MAYOR_PWSH_EXE']=str(shell)
    assert_owner_only(a.runtime)
    result=run(runtime,reuse_saved=a.reuse_saved)
    print(json.dumps(result,ensure_ascii=False))
    if not result['state_advanced']: raise SystemExit(2)

if __name__=='__main__': main()
