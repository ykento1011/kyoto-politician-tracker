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


def monitor(bridge,sources,previous=None):
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
                inventory=saved_index(bridge,source,rec['sha256']); inventories[url]=inventory
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
    result=monitor(bridge,sources,previous)
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


def main():
    p=argparse.ArgumentParser()
    for flag in ('config','baseline','rules','output','p1-code-root','snapshot-root','base-revision'):
        p.add_argument('--'+flag,required=True)
    p.add_argument('--previous-state'); p.add_argument('--acquisition-receipt')
    p.add_argument('--acquire-authorized',action='store_true'); p.add_argument('--refresh-existing',action='store_true')
    a=p.parse_args(); config=load(a.config); root=Path(a.output).resolve(strict=True)
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
