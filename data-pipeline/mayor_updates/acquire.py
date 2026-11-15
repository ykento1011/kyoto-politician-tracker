"""One-shot P1 acquisition. No crawler, scheduler, publisher or alternative CAS.

The parent uses the existing P1 single-GET worker pattern with a ten-second
wall deadline. Durable per-URL intent prevents an accidental repeat in a run.
Default: reuse saved originals. A future recheck requires explicit refresh.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from .engine import PrivateOutput
from .projection import Hold
from .p1_bridge import P1Bridge


def utc():
    return datetime.now(timezone.utc).isoformat()


def assert_owner_only(root):
    root=Path(root).resolve(strict=True)
    if os.name != 'nt':
        stat=root.stat()
        if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise Hold('Owner-only private root required')
        return {'owner_only':True,'platform':'posix'}
    literal=str(root).replace("'", "''")
    script = "$a=Get-Acl -LiteralPath '" + literal + "'; $owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value; $actor=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; $bad=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) | Where-Object { $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Value -ne $owner }); if ($owner -ne $actor -or $bad.Count -ne 0) { throw 'Owner-only ACL or execution identity mismatch' }; @{owner_only=$true;actor_is_owner=$true} | ConvertTo-Json -Compress"
    result=subprocess.run([os.environ.get('MAYOR_PWSH_EXE','pwsh.exe'),'-NoProfile','-NonInteractive','-Command',script],
                          capture_output=True,text=True,timeout=10)
    if result.returncode:
        raise Hold('Owner-only ACL check failed: ' + result.stderr[-500:])
    return json.loads(result.stdout)


def validate_sources(sources):
    urls=set()
    for source in sources:
        parsed=urlsplit(source['url'])
        if (parsed.scheme!='https' or parsed.netloc!='www.city.kyoto.lg.jp' or
            parsed.fragment or parsed.query or not parsed.path.endswith('.html') or
            source['url'] in urls or source['max_bytes']!=2097152 or
            source['document_kind'] not in {'budget_index','other_official'} or
            type(source['fiscal_year']) is not int):
            raise Hold('Invalid fixed Kyoto HTML scope')
        urls.add(source['url'])
    if len(sources)>3 or not sources:
        raise Hold('This initial Kyoto connection is limited to three fixed pages')


def worker(code_root,snapshot_root,source,output):
    out=PrivateOutput(output)
    marker=out.root/'single_get_started.json'
    if not marker.exists() or json.loads(marker.read_text(encoding='utf-8'))['source_url'] != source['url']:
        raise Hold('Worker requires a matching parent authorization intent')
    out.json('worker_consumed.json',{'source_url':source['url'],'at_utc':utc()})
    bridge=P1Bridge(code_root,snapshot_root)
    from budget.fetch import SourceFetcher,UrllibTransport
    from budget.adapters.kyoto import DiscoveredDocument
    url=source['url']; year=source['fiscal_year']
    doc=DiscoveredDocument(url,source['title'],f'令和{year-2018}年度',year,
                           'html',source['document_kind'],'unknown',None,
                           url,url,None,None,'discovered_unverified',())
    result=SourceFetcher(bridge.store,transport=UrllibTransport(),
                         allowed_hosts=frozenset({'www.city.kyoto.lg.jp'}),
                         max_bytes=source['max_bytes']-1,max_redirects=0,
                         timeout_seconds=10).fetch_discovered(doc)
    PrivateOutput(output).json('worker_outcome.json',asdict(result))


def capture_sources(code_root,snapshot_root,sources,output,*,authorized=False,refresh=False):
    if not authorized:
        raise Hold('Explicit one-shot acquisition authorization required')
    validate_sources(sources)
    out=PrivateOutput(output)
    # ACLs are verified, never changed. Both run receipts and originals are private.
    acl={'output':assert_owner_only(out.root),'snapshot':assert_owner_only(snapshot_root)}
    bridge=P1Bridge(code_root,snapshot_root)
    out.json('preflight.json',{'at_utc':utc(),'acl':acl,'code_sha256':bridge.hashes,
          'sources':sources,'refresh_existing':refresh,'network_scope':'fixed HTML only',
          'limits':{'get_per_url':1,'tls_verify':True,'redirects':0,'retries':0,
                    'wall_timeout_seconds':10,'max_received_bytes':2097152,
                    'max_accepted_bytes':2097151},'cas_before':bridge.store.verify_integrity()})
    receipts=[]
    for source in sources:
        url=source['url']; history=bridge.store.read_index()['documents'].get(url)
        receipt={'source_url':url,'checked_at_utc':utc(),'new_get_requests':0}
        if history and not refresh:
            record=history['versions'][-1]['record']
            receipt.update(status='reused_existing',version=record,http_status=None,
                           original_retrieved_at=record['retrieved_at'],freshness='saved_version_not_rechecked')
        else:
            key=hashlib.sha256(url.encode()).hexdigest()[:20]
            run=out.root/key; run.mkdir(exist_ok=False)
            runout=PrivateOutput(run)
            runout.json('source.json',source)
            runout.json('single_get_started.json',{'at_utc':utc(),'source_url':url,'authorized_max_get':1})
            cmd=[sys.executable,'-B','-m','mayor_updates.acquire','--worker','--p1-code-root',str(code_root),
                 '--snapshot-root',str(snapshot_root),'--source-file',str(run/'source.json'),'--output',str(run)]
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8',
                 'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
            try:
                completed=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
                if completed.returncode!=0 or not (run/'worker_outcome.json').exists():
                    raise Hold('Worker failed/incomplete; no retry: '+completed.stderr[-500:])
                received=json.loads((run/'worker_outcome.json').read_text(encoding='utf-8'))
                receipt.update(received,new_get_requests=1)
                if not received.get('version'):
                    receipt['stop']=True
            except (subprocess.TimeoutExpired,Hold) as exc:
                receipt.update(status='worker_stop_no_retry',detail=str(exc),new_get_requests=None,new_get_requests_max=1,stop=True)
                bridge.store.record_failure(source_url=url,at=datetime.now(timezone.utc),
                                            status='worker_stop_no_retry',details=str(exc))
        version=receipt.get('version')
        if version:
            sha=version.get('sha256') or version['version_id']
            try:
                body=bridge.store.snapshot_bytes(sha)
                if hashlib.sha256(body).hexdigest()!=sha or len(body)>source['max_bytes']:
                    raise Hold('Readback integrity/size mismatch')
                receipt.update(sha256=sha,stored_bytes=len(body),readback_pass=True)
            except (ValueError,OSError) as exc:
                receipt.update(status='readback_stop',detail=str(exc),stop=True)
        receipts.append(receipt)
        out.json('result_'+source['id']+'.json',receipt)
        if receipt.get('stop'):
            break
    result={'checked_at_utc':utc(),'receipts':receipts,'stopped':any(r.get('stop') for r in receipts),
            'new_get_requests':None if any(r.get('new_get_requests') is None for r in receipts) else sum(r.get('new_get_requests',0) for r in receipts),
            'new_get_requests_max':sum(r.get('new_get_requests_max',r.get('new_get_requests',0)) for r in receipts),
            'cas_after':bridge.store.verify_integrity(),'public_writes':0}
    out.json('acquisition_result.json',result)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker',action='store_true'); p.add_argument('--p1-code-root',required=True)
    p.add_argument('--snapshot-root',required=True); p.add_argument('--output',required=True)
    p.add_argument('--source-file'); p.add_argument('--sources')
    p.add_argument('--authorized-single-run',action='store_true')
    p.add_argument('--refresh-existing',action='store_true')
    a=p.parse_args()
    if a.worker:
        source=json.loads(Path(a.source_file).read_text(encoding='utf-8-sig'))
        validate_sources([source])
        worker(a.p1_code_root,a.snapshot_root,source,a.output)
    else:
        sources=json.loads(Path(a.sources).read_text(encoding='utf-8-sig'))
        result=capture_sources(a.p1_code_root,a.snapshot_root,sources,a.output,
                               authorized=a.authorized_single_run,refresh=a.refresh_existing)
        print(json.dumps(result,ensure_ascii=False))
        if result['stopped']: sys.exit(2)

if __name__=='__main__': main()
