"""Saved-index monitoring and request planning; all scheduling is disabled."""
from copy import deepcopy
from datetime import datetime
from .engine import compare_documents, compare_index
from .projection import Hold


def monitor_saved(bridge, city_config, previous=None):
    previous = previous or {'documents': {}, 'indexes': {}}
    observations, indexes, extraction_queue, index_events = [], deepcopy(previous.get('indexes', {})), [], []
    source_urls = {s['url'] for s in city_config['known_saved_sources']}
    index_urls = {u for g in city_config['source_groups'].values() for u in g['index_urls']}
    for url in sorted(source_urls | index_urls):
        doc = bridge.index['documents'].get(url)
        attempts = [a for a in bridge.index['attempts'] if a['source_url'] == url]
        last = attempts[-1] if attempts else None
        record = doc['versions'][-1]['record'] if doc else None
        success_kinds = {'new_version', 'unchanged', 'same_version', 'stored_new_version', 'stored_existing_version'}
        failed = last and last['outcome'] not in success_kinds and (
            record is None or datetime.fromisoformat(last['observed_at']) >= datetime.fromisoformat(record['retrieved_at']))
        ok = bool(record) and not failed
        if ok:
            # Readback integrity and extraction both delegate to P1.
            bridge.record(url, record['sha256'])
            observations.append({'source_url':url,'status':'ok','sha256':record['sha256'],
                                 'retrieved_at':record['retrieved_at']})
            extraction_queue.append(bridge.extract(url, record['sha256']))
        else:
            observations.append({'source_url':url,'status':'failed',
                                 'detail':last['outcome'] if last else 'not_saved'})
        if url in index_urls:
            old = previous.get('indexes', {}).get(url, {})
            try:
                new = bridge.index_links(url, record['sha256'], city_config['allowed_hosts']) if ok else {}
                changes, retained = compare_index(old,new,success=ok)
            except ValueError as exc:
                changes, retained = compare_index(old,{},success=False)
                changes[0]['detail'] = str(exc)
            indexes[url] = retained
            index_events.extend(dict(index_url=url, **c) for c in changes)
    events, state = compare_documents(previous.get('documents',{}),observations)
    return {'events':events, 'index_events':index_events,
            'state':{'documents':state,'indexes':indexes}, 'extractions':extraction_queue,
            'network_requests':0}


def suggest_policy_links(extraction, city_config):
    """Suggest explicit configured terms, never assert a direct relationship."""
    suggestions = []
    for candidate in extraction['candidates']:
        text = candidate.get('project_name','') + ' ' + candidate.get('reason_excerpt','')
        ids = [pid for pid, terms in city_config.get('policy_terms',{}).items()
               if terms and any(term in text for term in terms)]
        if not set(ids) <= set(city_config['policy_ids']):
            raise Hold('Unknown policy term mapping')
        suggestions.append({'candidate':deepcopy(candidate),'possible_policy_ids':ids,
                            'relation':'unconfirmed','mapping_reason':'Configured term match; human confirmation required',
                            'fiscal_year':None,'account':None,'budget_kind':None,'amount_role':None,
                            'verification_status':'unverified','eligible_for_proposal':False})
    return suggestions


def request_plan(config, city, *, groups=None):
    """No DNS/HTTP. Plan only explicitly registered fixed URLs, not discovered links."""
    cfg = config['cities'][city]
    groups = set(groups or cfg['source_groups'])
    if not groups <= cfg['source_groups'].keys():
        raise Hold('Unknown source group')
    if cfg.get('monitor_sources'):
        urls = {s['url']:s['max_bytes'] for s in cfg['monitor_sources']
                if (s['role']=='progress' and 'progress' in groups) or
                   (s['role']=='index' and groups & {'initial','supplemental'})}
    else:
        urls = {u:config['communication']['default_max_bytes'] for g in groups
            for u in cfg['source_groups'][g]['index_urls']}
    for source in cfg['known_saved_sources']:
        if source['kind'] in groups:
            urls[source['url']] = source['max_bytes']
    rows=[{'url':url,'method':'GET','max_requests':1,'max_received_bytes':limit,
           'timeout_seconds':10,'tls_verify':True,'redirects':0,'retries':0}
          for url,limit in sorted(urls.items())]
    return {'city':city, 'requests':rows, 'max_requests':len(rows),
            'max_received_bytes':sum(urls.values()),'paid_api_cost_jpy':0,
            'within_request_cap':len(rows)<=config['communication']['max_requests_per_run'],
            'execution_enabled':False,'approval_required':True,
            'missing_index_groups':[g for g in sorted(groups) if not cfg['source_groups'][g]['index_urls']]}


def pdf_request_plan(config, *, allow_enabled=False):
    """Next-phase fixed PDF plan only. Never fetch or enable PDF monitoring."""
    from urllib.parse import urlsplit
    scope=config['pdf_watch']; sources=scope['sources']
    if (scope.get('enabled') and not allow_enabled) or scope.get('requires_separate_activation') is not True:
        raise Hold('PDF acquisition requires a separate activation decision')
    separate = 'phase_id' in scope
    if separate:
        import re
        city = scope.get('city_code')
        policies = scope.get('policy_ids', [])
        if (not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', str(scope['phase_id'])) or
                city not in config.get('cities', {}) or not policies or
                not set(policies) <= set(config['cities'][city]['policy_ids']) or
                scope.get('allowed_hosts') != ['www.city.' + city + '.lg.jp'] or
                type(scope.get('max_requests_per_run')) is not int or not 1 <= scope['max_requests_per_run'] <= 3 or
                type(scope.get('max_total_received_bytes')) is not int or not 0 < scope['max_total_received_bytes'] <= 6291456 or
                any(scope.get(k) != v for k,v in dict(timeout_seconds=10,tls_verify=True,redirects=0,retries=0).items())):
            raise Hold('Invalid independent PDF phase boundary')
        host = scope['allowed_hosts'][0]
        per_document_cap = 2097152
    else:
        if scope['max_requests_per_run'] != 3 or scope['max_total_received_bytes'] != 25165824:
            raise Hold('Invalid limited PDF request budget')
        host = 'www.city.kyoto.lg.jp'
        per_document_cap = 20971520
    if not 1 <= len(sources) <= scope['max_requests_per_run']:
        raise Hold('PDF phase request budget exceeded')
    seen=set(); rows=[]
    for source in sources:
        parsed=urlsplit(source['url']); limit=source['max_bytes']
        if (parsed.scheme!='https' or parsed.netloc!=host or
                not parsed.path.endswith('.pdf') or parsed.query or parsed.fragment or
                source['url'] in seen or source['max_gets']!=1 or
                type(limit) is not int or not 0 < limit <= per_document_cap):
            raise Hold('Invalid fixed PDF source')
        if separate and (not source.get('policy_ids') or not set(source['policy_ids']) <= set(policies)):
            raise Hold('PDF phase policy scope mismatch')
        seen.add(source['url'])
        rows.append({'url':source['url'],'method':'GET','max_requests':1,
                     'max_received_bytes':limit,'timeout_seconds':10,
                     'tls_verify':True,'redirects':0,'retries':0})
    if sum(r['max_received_bytes'] for r in rows)>scope['max_total_received_bytes']:
        raise Hold('Limited PDF byte budget exceeded')
    return {'requests':rows,'max_requests':len(rows),
            'max_received_bytes':sum(r['max_received_bytes'] for r in rows),
            'execution_enabled':False,'approval_required':True,
            'limitation':scope['limitation']}
