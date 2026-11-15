"""Fixed PDF version watch. Separate state; P1 owns HTTP, CAS and versions."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import uuid
from .acquire import assert_owner_only, capture_sources, validate_sources
from .engine import PrivateOutput, digest
from .monitor import pdf_request_plan
from .operations import load
from .p1_bridge import P1Bridge
from .projection import Hold
from .weekly import atomic_json, single_run, pinned_input

STATES=('unchanged','new_saved_version','initial_baseline','fetch_failed','unverifiable')


def check_pdf(body):
    import fitz
    try:
        with fitz.open(stream=body,filetype='pdf') as doc:
            if not doc.is_pdf or doc.is_encrypted or doc.page_count<1:
                raise ValueError('Not an accessible nonempty PDF')
            return doc.page_count
    except Exception as exc:
        raise Hold('PDF structure cannot be validated: '+type(exc).__name__) from exc


def inspect(bridge, source, sha, references):
    rec,body=bridge.record(source['url'],sha)
    if rec['mime_type']!='application/pdf' or rec['fiscal_year']!=source['fiscal_year'] or len(body)>source['max_bytes']:
        raise Hold('PDF metadata/size mismatch')
    pages=check_pdf(body)
    checks=[]
    for ref in references:
        if ref['source_url']!=source['url']: raise Hold('Reference URL mismatch')
        current={**ref,'sha256':sha}
        try:
            evidence=bridge.evidence(current)
            checks.append({'reference_sha256':ref['sha256'],'current_evidence':evidence,'status':'text_preserved'})
        except ValueError as exc:
            checks.append({'reference_sha256':ref['sha256'],'current_sha256':sha,
                           'locator':ref['locator'],'reference_quote':ref['quote'],
                           'status':'unconfirmed','reason':str(exc)})
    return {'record':rec,'bytes':len(body),'page_count':pages,'anchor_checks':checks,
            'policy_verification':'unchanged_by_version_watch'}


def compare_pdf(before, after, *, fetch_ok=True, valid=True):
    if not fetch_ok: return 'fetch_failed'
    if not valid: return 'unverifiable'
    if before is None: return 'initial_baseline'
    return 'unchanged' if before==after else 'new_saved_version'


def reconcile(bridge, sources, bindings, previous, acquisition, baseline):
    """Pure orchestration over saved bytes. No public policy projection or approval."""
    events=[]; next_documents=deepcopy(baseline)
    receipts={r['source_url']:r for r in acquisition['receipts']}
    for source in sources:
        url=source['url']; before=baseline.get(url); r=receipts.get(url)
        event={'source_url':url,'policy_ids':source['policy_ids'],'review_pages':source['review_pages'],
               'before_sha256':before.get('sha256') if before else None,
               'after_sha256':None,'policy_effect':None,'verification_status':'unverified'}
        if not r or r.get('stop') or not r.get('version'):
            event.update(state='unverifiable' if not r or r.get('status') in {'rejected_mime','readback_stop'} else 'fetch_failed',
                         reason=r.get('status') if r else 'not_attempted_after_stop',http_status=r.get('http_status') if r else None)
        else:
            sha=r['sha256']; event['after_sha256']=sha
            try:
                details=inspect(bridge,source,sha,bindings.get(url,[]))
                event.update(state=compare_pdf(event['before_sha256'],sha),details=details,http_status=r.get('http_status'))
                next_documents[url]={'sha256':sha,'record':details['record']}
            except (ValueError,OSError) as exc:
                event.update(state='unverifiable',reason=str(exc),http_status=r.get('http_status'))
        events.append(event)
    stopped=bool(acquisition['stopped'] or any(e['state'] in {'fetch_failed','unverifiable'} for e in events))
    proposed=[]; seen=deepcopy(previous.get('seen_reviews',{}))
    if not stopped:
        for event in events:
            if event['state']!='new_saved_version': continue
            key=digest({k:event[k] for k in ('source_url','before_sha256','after_sha256')})
            if key not in seen:
                proposed.append({**event,'review_key':key,'publication_authorized':False,
                    'instruction':'PDFの版変更のみ。金額・政策進捗・既存対応関係の変更は人手確認まで保留。'})
    return {'events':events,'counts':{s:sum(e['state']==s for e in events) for s in STATES},
            'stopped':stopped,'reviews':proposed,'documents':next_documents if not stopped else deepcopy(baseline)}


def validate_runtime(runtime, *, reuse_saved=False):
    root=PrivateOutput(runtime['state_root']).root
    assert_owner_only(root); assert_owner_only(runtime['snapshot_root'])
    paths={name:pinned_input(runtime[name]) for name in ('config','baseline','bindings')}
    for spec in runtime['code_files']: pinned_input(spec)
    if not any(Path(s['path']).resolve()==Path(__file__).resolve() for s in runtime['code_files']):
        raise Hold('Executing PDF watcher must be pinned')
    config=load(paths['config']); plan=pdf_request_plan(config,allow_enabled=True)
    phase=config['pdf_watch']; sources=phase['sources']
    # City trials retain their existing signed storage/scope guard. Kyoto uses
    # its original adapter and IDs; no running transport limits are widened.
    if phase.get('city_code', 'kyoto') != 'kyoto':
        raise Hold('Non-Kyoto PDF execution requires the existing city trial acquisition path')
    validate_sources(sources,media_type='pdf')
    if config['pdf_watch'].get('timeout_seconds')!=10: raise Hold('PDF timeout must remain 10 seconds')
    if not reuse_saved and not (runtime.get('network_enabled') is True and config['pdf_watch'].get('enabled') is True):
        raise Hold('PDF live acquisition is not activated')
    allowed = set(phase['policy_ids']) if 'phase_id' in phase else {'P-01','P-03'}
    if not sources or any(not s.get('policy_ids') or not set(s['policy_ids'])<=allowed or not s.get('review_pages') for s in sources):
        raise Hold('Explicit PDF policy/page bindings required')
    bindings=load(paths['bindings'])
    if set(bindings)!={s['url'] for s in sources} or any(not refs for refs in bindings.values()):
        raise Hold('Saved evidence references required for every fixed PDF')
    if 'phase_id' in phase:
        marker=root/'phase_binding.json'
        identity={'phase_id':phase['phase_id'],'city_code':phase['city_code'],
                  'sources_sha256':digest(sources), 'snapshot_root':str(Path(runtime['snapshot_root']).resolve())}
        if marker.exists():
            if load(marker)!=identity: raise Hold('Independent PDF phase/state binding mismatch')
        else:
            if (root/'state.json').exists() or (root/'runs').exists():
                raise Hold('Independent PDF phase requires a fresh isolated state directory')
            atomic_json(marker,identity)
    return root,config,bindings,plan


def run(runtime, *, reuse_saved=False):
    root,config,bindings,plan=validate_runtime(runtime,reuse_saved=reuse_saved)
    with single_run(root):
        state_path=root/'state.json'; prior=load(state_path) if state_path.exists() else {'documents':{},'seen_reviews':{}}
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
        runs=root/'runs'; runs.mkdir(exist_ok=True); output=runs/stamp; output.mkdir()
        out=PrivateOutput(output); started=datetime.now(timezone.utc).isoformat()
        try:
            bridge=P1Bridge(runtime['p1_code_root'],runtime['snapshot_root'])
            baseline=deepcopy(prior.get('documents',{})); sources=config['pdf_watch']['sources']
            for source in sources:
                url=source['url']
                if url not in baseline and url in bridge.index['documents']:
                    rec=bridge.index['documents'][url]['versions'][-1]['record']
                    baseline[url]={'sha256':rec['sha256'],'record':rec}
                if url in baseline: inspect(bridge,source,baseline[url]['sha256'],bindings[url])
            if reuse_saved and any(s['url'] not in bridge.index['documents'] for s in sources):
                raise Hold('Offline PDF run requires every original; network fallback is forbidden')
            out.json('baseline_before.json',baseline)
            acqdir=output/'acquisition'; acqdir.mkdir()
            acquisition=capture_sources(runtime['p1_code_root'],runtime['snapshot_root'],sources,acqdir,
                authorized=True,refresh=not reuse_saved,media_type='pdf')
            bridge=P1Bridge(runtime['p1_code_root'],runtime['snapshot_root'])
            result=reconcile(bridge,sources,bindings,prior,acquisition,baseline)
            out.json('pdf_result.json',result)
            if result['reviews']:
                out.json('pdf_review.json',{'reviews':result['reviews'],'publication_authorized':False})
                out.write('pdf_review.html','<!doctype html><html lang="ja"><meta charset="utf-8"><title>PDF差替え確認</title>'
                    '<h1>変更PDFと既存根拠の確認</h1><p>未確認・未公開。差替えだけで政策や金額の変更とは認定しません。</p>'
                    '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+escape(json.dumps(result['reviews'],ensure_ascii=False,indent=2))+'</pre></html>')
            status={'state':'stopped' if result['stopped'] else 'review_pending' if result['reviews'] else 'no_new_review',
                'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
                'counts':result['counts'],'new_review_count':len(result['reviews']),
                'new_get_requests':acquisition['new_get_requests'],'new_get_requests_max':acquisition['new_get_requests_max'],
                'received_body_bytes':None if acquisition['stopped'] else sum(r.get('stored_bytes',0) for r in acquisition['receipts'] if r.get('new_get_requests')),
                'known_success_body_bytes':sum(r.get('stored_bytes',0) for r in acquisition['receipts'] if r.get('new_get_requests') and r.get('readback_pass')),
                'receive_upper_bound':plan['max_received_bytes'],'public_writes':0,'run_dir':str(output)}
            out.json('run_status.json',status)
            if not result['stopped']:
                seen=deepcopy(prior.get('seen_reviews',{}))
                for review in result['reviews']: seen[review['review_key']]=str(output/'pdf_review.json')
                atomic_json(state_path,{'documents':result['documents'],'seen_reviews':seen,
                    'last_success_run':str(output),'last_success_at':status['finished_at_utc'],
                    'base_revision':runtime['base_revision'],'baseline_sha256':runtime['baseline']['sha256']})
            return status
        except Exception as exc:
            out.json('failure.json',{'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
                'state':'stopped','reason':str(exc),'previous_pdf_state_retained':True,'public_writes':0})
            raise


def main():
    p=argparse.ArgumentParser(); p.add_argument('--runtime',required=True); p.add_argument('--reuse-saved',action='store_true'); a=p.parse_args()
    runtime=load(a.runtime)
    if os.name=='nt': os.environ['MAYOR_PWSH_EXE']=runtime['powershell_exe']
    assert_owner_only(a.runtime)
    result=run(runtime,reuse_saved=a.reuse_saved); print(json.dumps(result,ensure_ascii=False))
    if result['state']=='stopped': raise SystemExit(2)

if __name__=='__main__': main()
