"""Source-bound one-shot operation: acquire/reuse -> detect -> bind -> private review.

Public data is an input only. The scheduler and publication remain separate.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
from .acquire import capture_sources
from .engine import PrivateOutput, compare_documents, compare_index, propose, review_html, digest
from .index_adapter import saved_index, comparison_links, preserved_units
from .p1_bridge import P1Bridge
from .projection import Hold, policies


def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def monitor(bridge,sources,previous=None,*,city="kyoto"):
    previous=previous or {'documents':{},'indexes':{}}
    observations=[]; inventories={}; indexes=deepcopy(previous.get('indexes',{})); events=[]
    holds=[]; extractions=[]; fallback=[]; success={'new_version','unchanged'}
    for source in sources:
        url=source['url']; doc=bridge.index['documents'].get(url)
        attempts=[a for a in bridge.index['attempts'] if a['source_url']==url]
        failed=bool(attempts and attempts[-1]['outcome'] not in success)
        if not doc or failed:
            observations.append({'source_url':url,'status':'failed','detail':attempts[-1]['outcome'] if attempts else 'not_saved'})
            if source['role']=='index': events.append({'kind':'index_fetch_failed','index_url':url,'policy_effect':None})
            holds.append({'source_url':url,'reason':'Acquisition failed or original absent; retain last good state'})
            continue
        rec=doc['versions'][-1]['record']; bridge.record(url,rec['sha256'])
        observations.append({'source_url':url,'status':'ok','sha256':rec['sha256'],'retrieved_at':rec['retrieved_at']})
        extracted=bridge.extract(url,rec['sha256']); extractions.append(extracted)
        if source['role']=='index':
            try:
                inventory=saved_index(bridge,source,rec['sha256'],city=city); inventories[url]=inventory
                normalized=comparison_links(inventory)
                prior=previous.get('indexes',{}).get(url,{})
                delta,retained=compare_index(prior,normalized)
                events.extend(dict(index_url=url,baseline_creation=url not in previous.get('indexes',{}),**e) for e in delta)
                indexes[url]=retained
            except ValueError as exc:
                holds.append({'source_url':url,'reason':str(exc)})
                events.append({'kind':'index_parse_failed','index_url':url,'policy_effect':None})
        elif not extracted['candidates']:
            fallback.extend(preserved_units(bridge,source,rec['sha256']))
    document_events,documents=compare_documents(previous.get('documents',{}),observations)
    return {'document_events':document_events,'index_events':events,'inventories':inventories,
            'state':{'documents':documents,'indexes':indexes},'extractions':extractions,
            'fallback_units':fallback,'holds':holds}


def run_trial(bridge,config,baseline,rules,output,*,previous=None,base_revision,acquisition=None,seen_reviews=None,city="kyoto",allowed=None):
    out=PrivateOutput(output)
    seen_reviews = seen_reviews or {}
    emitted = {}
    def emit(name, payload):
        # Stable content keys ignore transport timestamps, not source hashes/pages.
        def stable(value):
            if isinstance(value, dict):
                return {k: stable(v) for k,v in value.items() if k not in
                        {'retrieved_at','checked_at_utc','packet_id','base_revision'}}
            if isinstance(value, list): return [stable(v) for v in value]
            return value
        key = digest({'artifact':name,'content':stable(payload)})
        if key in seen_reviews: return False
        out.json(name, payload); emitted[key] = name
        return True
    legacy_kyoto = city == 'kyoto' and allowed is None
    rules = deepcopy(rules)
    for rule in rules:
        if 'city' not in rule and legacy_kyoto:
            specs = rule.get('source_specs', [])
            if not specs:
                raise Hold('Legacy Kyoto rule lacks saved source identity')
            for spec in specs:
                url = spec['source_url']; parsed = urlsplit(url)
                doc = bridge.index['documents'].get(url)
                versions = [v for v in doc['versions'] if v['sha256'] == spec.get('sha256')] if doc else []
                if (parsed.scheme != 'https' or parsed.netloc != 'www.city.kyoto.lg.jp' or
                        len(versions) != 1 or versions[0]['record'].get('city_code') != 'kyoto'):
                    raise Hold('Legacy Kyoto city inference requires an exact Kyoto saved version')
            rule['city'] = 'kyoto'  # In memory only; explicit foreign/null cities never fall back.
    allowed = ['P-03'] if legacy_kyoto else allowed
    city_config = config.get('cities', {}).get(city, {})
    if (not allowed or not set(allowed) <= set(city_config.get('policy_ids', [])) or
            not set(allowed) <= set(policies(baseline)) or
            any(r.get('city') != city or r['policy_id'] not in allowed for r in rules)):
        raise Hold('Explicit city/policy review scope required')
    sources=city_config['monitor_sources']
    for source in sources:
        doc=bridge.index['documents'].get(source['url'])
        if doc and any(v['record'].get('city_code')!=city for v in doc['versions']):
            raise Hold('Review source belongs to another city')
    result=monitor(bridge,sources,previous,city=city)
    out.json('monitor_result.json',result); out.json('monitor_state.json',result['state'])
    changed={e['source_url'] for e in result['document_events'] if e['kind'] in {'new_document','replacement_document'}}
    listing_changes=any(e['kind'] in {'link_added','link_changed','link_removed'} for e in result['index_events'])
    if result['holds'] or (acquisition and acquisition.get('stopped')):
        out.json('run_status.json',{'state':'stopped_no_public_change','proposal_count':0,
                   'holds':result['holds'],'acquisition':acquisition,'public_writes':0})
        return result,None
    progress_urls={s['url'] for s in sources if s['role']=='progress'}
    progress_changed=changed & progress_urls
    changed_targets={e['source_url'] for e in result['index_events']
                     if e['kind'] in {'link_added','link_changed','link_removed'}}
    affected={r['policy_id'] for r in rules if r['source_specs'][0]['source_url'] in (changed_targets | progress_changed)}
    if not affected:
        # An index SHA change alone is not a policy change. Keep discovery signals
        # without requesting a redundant policy review or pretending to read PDFs.
        unmatched=[e for e in result['index_events'] if not e.get('baseline_creation') and
                   e['kind'] in {'link_added','link_changed','link_removed'}]
        if unmatched:
            emit('source_review_queue.json',{'listing_changes':unmatched,
                    'policy_assignment':'unconfirmed','linked_content_read':False,
                    'documents':{u:{'sha256':v['sha256']} for u,v in result['state']['documents'].items()}})
        # Preserve changed announcements even without a policy mapping rule.
        # This is an evidence review, never an invented policy or budget update.
        if progress_changed:
            emit('evidence_review_queue.json',{
                'source_units':[u for u in result['fallback_units'] if u['source_url'] in progress_changed],
                'changed_documents':[e for e in result['document_events'] if e['source_url'] in progress_changed],
                'city':city,'policy_ids':allowed,'policy_assignment':'unconfirmed',
                'verification_status':'unverified','publication_authorized':False})
        state='source_review_pending' if unmatched else 'evidence_review_pending' if emitted else 'source_version_only' if changed else 'unchanged'
        out.json('run_status.json',{'state':state,'proposal_count':0,'public_writes':0,'new_reviews':emitted})
        return result,None
    candidates=[]; mapping_holds=[]
    for rule in rules:
        if rule['policy_id'] not in affected: continue
        # Mapping is configured explicitly; source changes do not assign policy IDs by guess.
        try:
            candidates.append(bridge.map_rule(rule))
        except ValueError as exc:
            mapping_holds.append({'policy_id':rule['policy_id'],'reason':str(exc),
                                  'source_positions':rule['source_specs'],'verification_status':'unverified'})
    packet,candidate=propose(baseline,candidates,city=city,allowed=allowed,base_revision=base_revision)
    manual_units=[u for u in result['fallback_units'] if u['source_url'] in changed]
    if manual_units or mapping_holds:
        emit('evidence_review_queue.json',{'holds':mapping_holds,'source_units':manual_units,
                                              'verification_status':'unverified','publication_authorized':False,
                'changed_documents':[e for e in result['document_events'] if e['source_url'] in changed],
                'index_changes':result['index_events'],
                'current_index_evidence':[row for inv in result.get('inventories',{}).values()
                    for url,rows in inv['links'].items() if url in changed_targets for row in rows]})
    if packet and not emit('review_packet.json',packet):
        packet = None
    status={'state':'review_pending' if packet else 'no_policy_diff','proposal_count':len(packet['changes']) if packet else 0,
            'candidate_count':len(packet['candidates']) if packet else 0,'mapping_holds':mapping_holds,
            'public_writes':0,'acquisition':acquisition,'automatic_approval':False,'new_reviews':emitted}
    out.json('run_status.json',status)
    if packet:
        out.json('candidate_tracker_PRIVATE.json',candidate)
        out.write('review.html',review_html(packet))
        out.json('review_receipt_template.json',{'packet_id':packet['packet_id'],'reviewer':'','reviewed_at':'',
                                                'decision':None,'accepted_candidate_ids':[],'publication_authorized':False})
    return result,packet


def receipt_identity(spec, source, bridge):
    """Bind a pinned acquisition receipt to the current saved version, without HTTP."""
    from datetime import datetime
    from .weekly import pinned_input
    receipt=load(pinned_input(spec['acquisition_receipt']))
    preflight=load(pinned_input(spec['acquisition_preflight']))
    url=source['url']
    rows=[r for r in receipt['receipts'] if r.get('source_url')==url]
    sources=[s for s in preflight['sources'] if s.get('url')==url]
    if (receipt.get('stopped') is not False or receipt.get('public_writes')!=0 or
            len(rows)!=1 or len(sources)!=1):
        raise Hold('Acquisition receipt is stopped or source selection is ambiguous')
    row=rows[0]; acquired=sources[0]; version=row['version']
    if (row.get('stop') or row.get('readback_pass') is not True or
            row.get('status') not in {'stored_new_version','unchanged','reused_existing'}):
        raise Hold('Successful acquisition/readback receipt required')
    scoped=acquired.get('policy_ids')
    if scoped is None and acquired.get('policy_id'):scoped=[acquired['policy_id']]
    if (not scoped or not set(spec['policy_ids'])<=set(scoped) or
            not set(source['policy_ids'])<=set(scoped)):
        raise Hold('Receipt preflight lacks the explicit requested policy scope')
    for key in ('fiscal_year','document_kind'):
        if acquired.get(key)!=source.get(key):raise Hold('Receipt source metadata differs: '+key)
    if acquired.get('media_type',source['media_type'])!=source['media_type']:
        raise Hold('Receipt source medium differs')
    limits=preflight['limits']
    if any(limits.get(k)!=v for k,v in {'get_per_url':1,'tls_verify':True,'redirects':0,
            'retries':0,'wall_timeout_seconds':10}.items()):
        raise Hold('Acquisition safeguards are not attested')
    if any(preflight['code_sha256'].get(k)!=v for k,v in bridge.hashes.items()):
        raise Hold('Acquisition P1 code differs from the pinned replay code')
    sha=row['sha256']; doc=bridge.index['documents'].get(url)
    if not doc or doc['versions'][-1]['sha256']!=sha:
        raise Hold('Receipt refers to a stale or missing saved version')
    rec,body=bridge.record(url,sha)
    for key in ('document_id','version_id','source_url','final_url','snapshot_relative_path'):
        if version.get(key)!=rec.get(key):raise Hold('Receipt/CAS identity mismatch: '+key)
    for key in ('city_code','fiscal_year','mime_type','document_type','sha256'):
        if key in version and version[key]!=rec.get(key):raise Hold('Receipt metadata contradicts CAS: '+key)
    if (rec['city_code']!=spec['city'] or rec['source_url']!=url or rec['final_url']!=url or
            rec['document_type']!=source['document_kind'] or
            row['stored_bytes']!=len(body) or len(body)>acquired['max_bytes']):
        raise Hold('Receipt/CAS city, kind, URL or byte count mismatch')
    observed=version['retrieved_at']
    def utc_time(value):
        t=datetime.fromisoformat(value.replace('Z','+00:00'))
        if t.utcoffset() is None or t.utcoffset().total_seconds()!=0:raise Hold('UTC receipt time required')
        return t
    observed_time=utc_time(observed); original_time=utc_time(rec['retrieved_at'])
    if row['status']=='reused_existing':
        if row.get('new_get_requests')!=0 or observed_time!=original_time:
            raise Hold('Saved reuse timestamp/request count mismatch')
    else:
        if row.get('new_get_requests')!=1 or row.get('http_status')!=200 or row.get('final_url')!=url:
            raise Hold('Successful single GET receipt required')
        outcome='new_version' if row['status']=='stored_new_version' else 'unchanged'
        if not any(a.get('source_url')==url and a.get('sha256')==sha and
                a.get('outcome')==outcome and utc_time(a['observed_at'])==observed_time
                for a in bridge.index['attempts']):
            raise Hold('Acquisition observation is absent from the CAS ledger')
    if observed_time<original_time:raise Hold('Receipt predates the original saved version')
    if spec.get('sha256',sha)!=sha or spec.get('document_id',rec['document_id'])!=rec['document_id']:
        raise Hold('Manually supplied identity conflicts with acquisition receipt')
    audit={'receipt_sha256':spec['acquisition_receipt']['sha256'],
           'preflight_sha256':spec['acquisition_preflight']['sha256'],
           'city':spec['city'],'source_url':url,'policy_ids':spec['policy_ids'],
           'document_id':rec['document_id'],'sha256':sha,'stored_bytes':len(body),
           'original_retrieved_at':rec['retrieved_at'],'acquisition_observed_at':observed,
           'acquisition_status':row['status'],'policy_binding':'explicit_acquisition_scope',
           'verification_status':'unverified','publication_authorized':False}
    return sha,rec['document_id'],audit


def replay_saved(spec):
    """Replay one explicitly bound city series, offline, using existing P1/state tools.

    Acquisition is deliberately separate. A new version needs an explicit SHA in
    the private spec; this entry cannot fetch, schedule, or publish anything.
    """
    import hashlib
    import re
    import uuid
    from datetime import datetime, timezone
    from .city_scope import official_host, signature
    from .weekly import atomic_json, single_run, commit_success, review_index, pinned_input
    from .acquire import assert_owner_only
    root = PrivateOutput(spec['state_root']).root
    assert_owner_only(root)
    with single_run(root):
        output = root / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:8])
        output.mkdir(); out = PrivateOutput(output)
        summary = {'city':spec.get('city'), 'series_id':spec.get('series_id'),
                   'run_dir':str(output), 'network_requests':0, 'public_writes':0,
                   'state_advanced':False, 'new_review_count':0}
        try:
            city=spec['city']; allowed=spec['policy_ids']; source=deepcopy(spec['source'])
            if spec.get('network_enabled',False) is not False:
                raise Hold('Saved replay has no network mode; acquisition needs a separate approved scope')
            registry=load(Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json')['cities']
            if (city not in registry or not allowed or len(set(allowed))!=len(allowed) or
                    not set(allowed)<=set(registry[city]['policy_ids']) or
                    not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',spec['series_id'])):
                raise Hold('Explicit city, policy and series identity required')
            url=source['url']; parsed=urlsplit(url); medium=source['media_type']
            if (parsed.scheme!='https' or parsed.netloc!=official_host(city) or parsed.query or parsed.fragment or
                    medium not in {'html','pdf'} or not parsed.path.endswith('.'+medium) or
                    source['role'] not in {'index','progress'} or
                    (source['role']=='index' and medium!='html') or
                    not set(source['policy_ids']) or not set(source['policy_ids'])<=set(allowed)):
                raise Hold('Invalid single official source/policy scope')
            if source['role']=='progress' and source.get('policy_id') not in allowed:
                raise Hold('Evidence policy is outside the replay scope')
            cas=Path(spec['snapshot_root']).resolve(strict=True)
            assert_owner_only(cas)
            if cas==root or cas in root.parents or root in cas.parents or not (cas/'index.json').is_file():
                raise Hold('Existing CAS and isolated state must be separate')
            baseline_path=pinned_input(spec['baseline']); baseline=load(baseline_path)
            baseline_city=baseline.get('city_code')
            # Legacy Kyoto JSON predates city_code. Keep its existing bytes;
            # require its explicit city label, official bulletin and policy IDs.
            if 'city_code' not in baseline and city=='kyoto':
                info=baseline.get('mayor_info',{})
                bulletin=urlsplit(info.get('bulletin_pdf',''))
                if (info.get('city_label')=='京都市' and bulletin.scheme=='https' and
                        bulletin.netloc==official_host('kyoto') and
                        set(policies(baseline))<=set(registry['kyoto']['policy_ids'])):
                    baseline_city='kyoto'
            if baseline_city!=city or not set(allowed)<=set(policies(baseline)):
                raise Hold('Baseline belongs to a different city/policy')
            bridge=P1Bridge(spec['p1_code_root'],cas,city_capable=spec.get('city_capable',False))
            if 'acquisition_receipt' in spec or 'acquisition_preflight' in spec:
                expected,declared_id,audit=receipt_identity(spec,source,bridge)
                out.json('acquisition_handoff.json',audit)
                summary['acquisition_handoff']=audit
            else:
                expected=spec['sha256'];declared_id=spec['document_id']
            if not re.fullmatch('[0-9a-f]{64}',expected):raise Hold('Exact SHA required')
            document_id=city+'-doc-'+hashlib.sha256(url.encode()).hexdigest()[:24]
            if declared_id!=document_id:raise Hold('Document ID does not match city/URL')
            if any(v['record'].get('city_code')!=city for d in bridge.index['documents'].values() for v in d['versions']):
                raise Hold('CAS contains another city')
            doc=bridge.index['documents'].get(url)
            if not doc or doc['versions'][-1]['sha256']!=expected:
                raise Hold('Saved current version differs from the explicitly pinned SHA')
            rec,body=bridge.record(url,expected)
            if (rec['city_code']!=city or rec['document_id']!=document_id or
                    rec['fiscal_year']!=source['fiscal_year'] or
                    rec['mime_type']!={'html':'text/html','pdf':'application/pdf'}[medium]):
                raise Hold('Saved source identity/year/medium mismatch')
            binding={'kind':'offline_city_series_v1','city':city,'series_id':spec['series_id'],
                     'policy_ids':allowed,'source':source,'snapshot_root':str(cas),
                     'p1_code_root':str(Path(spec['p1_code_root']).resolve()),
                     'baseline_sha256':spec['baseline']['sha256']}
            binding_path=root/'replay_binding.json';state_path=root/'state.json'
            if binding_path.exists():
                if load(binding_path)!=binding:raise Hold('Replay state is bound to a different series')
            elif state_path.exists():raise Hold('Cannot adopt an existing unbound/live state')
            else:atomic_json(binding_path,binding)
            prior=load(state_path) if state_path.exists() else {'monitor':{},'seen_reviews':{}}
            config={'cities':{city:{'policy_ids':allowed,'monitor_sources':[source]}}}
            result,packet=run_trial(bridge,config,baseline,[],output,previous=prior.get('monitor'),
                seen_reviews=prior.get('seen_reviews',{}),base_revision=spec['base_revision'],city=city,allowed=allowed)
            if packet is not None:raise Hold('Evidence-only replay must not propose public policy changes')
            status=load(output/'run_status.json');review_index(output,status,city_label=city)
            committed=commit_success(root,output,prior,result['state'],status)
            summary.update(state=status['state'],state_advanced=committed,
                new_review_count=len(status.get('new_reviews',{})),source_url=url,
                document_id=document_id,sha256=expected,readback_bytes=len(body),
                readback_match=True,document_events=result['document_events'],
                index_event_count=len(result['index_events']),binding_sha256=signature(binding),
                p1_code_sha256=bridge.hashes,automatic_approval=False,publication_authorized=False)
        except Exception as exc:
            summary.update(state='stopped_no_public_change',reason=str(exc),previous_state_retained=True)
            out.json('failure.json',summary)
        out.json('replay_result.json',summary)
        return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--replay-spec',help='Private pinned single-series spec; zero HTTP and persistent review dedup')
    for flag in ('config','baseline','rules','output','p1-code-root','snapshot-root','base-revision'):
        p.add_argument('--'+flag)
    p.add_argument('--previous-state'); p.add_argument('--acquisition-receipt')
    p.add_argument('--acquire-authorized',action='store_true'); p.add_argument('--refresh-existing',action='store_true')
    a=p.parse_args()
    if a.replay_spec:
        from .acquire import assert_owner_only
        assert_owner_only(a.replay_spec)
        result=replay_saved(load(a.replay_spec))
        print(json.dumps(result,ensure_ascii=False))
        if not result['state_advanced']:raise SystemExit(2)
        return
    for flag in ('config','baseline','rules','output','p1_code_root','snapshot_root','base_revision'):
        if not getattr(a,flag):p.error('Missing required argument: '+flag)
    config=load(a.config); root=Path(a.output).resolve(strict=True)
    if a.acquire_authorized and a.acquisition_receipt: raise ValueError('Choose one acquisition input')
    receipt=load(a.acquisition_receipt) if a.acquisition_receipt else None
    if a.acquire_authorized:
        acquisition_dir=root/'acquisition'; acquisition_dir.mkdir(exist_ok=False)
        receipt=capture_sources(a.p1_code_root,a.snapshot_root,config['cities']['kyoto']['monitor_sources'],
                                acquisition_dir,authorized=True,refresh=a.refresh_existing)
    bridge=P1Bridge(a.p1_code_root,a.snapshot_root)
    run_trial(bridge,config,load(a.baseline),load(a.rules),root,
              previous=load(a.previous_state) if a.previous_state else None,
              base_revision=a.base_revision,acquisition=receipt)

if __name__=='__main__': main()
