"""Offline, append-only source registration; no acquisition/publication API."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from . import weekly
from .continuous import configure_shell
from .engine import PrivateOutput, compare_index, digest
from .index_adapter import saved_index, comparison_links
from .operations import load, receipt_identity
from .periodic import durable_record
from .city_scope import official_host
from .projection import Hold


def registry_config(city):
    cities = load(Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json')['cities']
    if city not in cities:
        raise Hold('Unknown city')
    return cities[city]


def pdf_url(city, url):
    u = urlsplit(url)
    if (u.scheme != 'https' or u.netloc != official_host(city) or u.query or u.fragment
            or not u.path.endswith('.pdf')):
        raise Hold('Exact official HTTPS PDF required')


def candidate_id(city, url, year):
    return city+'-source-'+digest([city, url, year])[:24]


def reviewer(request):
    if not all(isinstance(request.get(k), str) and request[k].strip() for k in ('reviewer','reason')):
        raise Hold('Named reviewer and reason required')
    return {k:request[k].strip() for k in ('reviewer','reason')}


class Registry:
    def __init__(self, root, bridge, city):
        self.root = PrivateOutput(root).root
        self.bridge = bridge; self.city = city; self.config = registry_config(city)
        self.cas = Path(bridge.store.root).resolve(strict=True)
        weekly.assert_owner_only(self.root); weekly.assert_owner_only(self.cas)
        if self.root == self.cas or self.root in self.cas.parents or self.cas in self.root.parents:
            raise Hold('Registry must be separate from CAS')

    def history(self):
        events = []; previous = None
        for number, path in enumerate(sorted(self.root.glob('event-*.json')), 1):
            if path.is_symlink() or path.name != f'event-{number:08d}.json':
                raise Hold('Registry event sequence mismatch')
            event = load(path); checksum = event.pop('event_sha256')
            if event.get('previous') != previous or digest(event) != checksum:
                raise Hold('Registry history checksum mismatch')
            event['event_sha256'] = checksum; events.append(event); previous = checksum
        return events

    def state(self, events):
        indexes = {}; candidates = {}
        for event in events:
            data = event['data']
            if event['kind'] == 'scan':
                indexes[data['index_url']] = data['inventory']
                for change in data['changes']:
                    cid = change['candidate_id']
                    if change['kind'] == 'link_removed':
                        candidates[cid]['active'] = False
                        candidates[cid]['last_change'] = 'link_removed'
                    else:
                        candidates[cid] = {**deepcopy(change), 'active':True,
                            'revision':event['event_sha256'], 'decision':None, 'evidence':None,
                            'last_change':change['kind']}
            elif event['kind'] == 'decision':
                candidates[data['candidate_id']]['decision'] = {**deepcopy(data),'recorded_at':event['recorded_at']}
            elif event['kind'] == 'evidence':
                candidates[data['candidate_id']]['evidence'] = {**deepcopy(data),'recorded_at':event['recorded_at']}
        return indexes, candidates

    def current(self, candidates, request):
        row = candidates.get(request['candidate_id'])
        if not row or not row['active']:
            raise Hold('Candidate absent from current index')
        if request.get('revision') != row['revision'] or request.get('index_sha256') != row['index_sha256']:
            raise Hold('Review refers to stale candidate/index evidence')
        return row

    def scan(self, request, indexes):
        source = request['source']; version = request['index_sha256']
        registered = [s for s in self.config['monitor_sources'] if s.get('role') == 'index']
        if source not in registered or not re.fullmatch('[a-f0-9]{64}', version):
            raise Hold('Pinned registered index required')
        document = self.bridge.index['documents'].get(source['url'])
        attempts = [a for a in self.bridge.index['attempts'] if a['source_url']==source['url']]
        if (not document or document['versions'][-1]['sha256'] != version or
                (attempts and attempts[-1]['outcome'] not in {'new_version','unchanged'})):
            raise Hold('Index is stale or latest acquisition failed; retain previous registry')
        rec, body = self.bridge.record(source['url'], version)
        if (sha256(body).hexdigest() != version or rec['sha256'] != version
                or rec['source_url'] != source['url'] or rec['final_url'] != source['url']
                or rec['fiscal_year'] != source['fiscal_year']):
            raise Hold('Index readback SHA mismatch')
        inventory = saved_index(self.bridge, source, version, city=self.city)
        for url, rows in inventory['links'].items():
            pdf_url(self.city, url)
            for row in rows:
                if (row['fiscal_year'] != source['fiscal_year'] or row['index_sha256'] != version
                        or type(row['locator']['anchor_ordinal']) is not int or row['locator']['anchor_ordinal'] < 1):
                    raise Hold('Invalid saved listing evidence')
        previous = indexes.get(source['url'])
        if previous and previous['sha256'] == version:
            return None
        changes, _ = compare_index(comparison_links(previous) if previous else {}, comparison_links(inventory))
        changes = [{**c, 'candidate_id':candidate_id(self.city,c['source_url'],source['fiscal_year']),
            'city':self.city, 'fiscal_year':source['fiscal_year'], 'index_url':source['url'],
            'index_sha256':version, 'listings':inventory['links'].get(c['source_url'], [])} for c in changes]
        return {'index_url':source['url'], 'inventory':inventory, 'changes':changes}

    def decision(self, row, request):
        who = reviewer(request)
        decision = request['decision']
        if decision not in {'hold','reject','approve_for_source_registration'}:
            raise Hold('Only source registration decisions allowed')
        policies = request.get('policy_ids', [])
        if not isinstance(policies,list) or not set(policies) <= set(self.config['policy_ids']):
            raise Hold('Unknown or foreign policy')
        pdf_url(self.city, row['source_url'])
        return {**who, 'candidate_id':row['candidate_id'], 'revision':row['revision'],
            'index_sha256':row['index_sha256'], 'decision':decision, 'policy_ids':sorted(set(policies)),
            'acquisition_authorized':False, 'publication_authorized':False}

    def attach(self, row, request):
        who = reviewer(request); spec = deepcopy(request['receipt_spec'])
        source = spec['source']
        if (spec['city'] != self.city or source['url'] != row['source_url']
                or source['fiscal_year'] != row['fiscal_year'] or source['media_type'] != 'pdf'
                or not spec['policy_ids'] or not set(spec['policy_ids']) <= set(self.config['policy_ids'])
                or source['policy_ids'] != spec['policy_ids']):
            raise Hold('Receipt is not bound to this candidate/policy/year/medium')
        version, docid, audit = receipt_identity(spec, source, self.bridge)
        rec, body = self.bridge.record(source['url'], version)
        if (sha256(body).hexdigest() != version or rec['mime_type'] != 'application/pdf'
                or rec['fiscal_year'] != row['fiscal_year']):
            raise Hold('PDF readback mismatch')
        notes = []
        for note in request.get('notes', []):
            if (note['policy_id'] not in spec['policy_ids'] or not note.get('subject')
                    or note['fact_type'] not in {'budget_proposal','budget_vote','enactment','implementation','unconfirmed'}):
                raise Hold('Invalid scoped evidence note')
            evidence = self.bridge.evidence({'source_url':source['url'], 'sha256':version,
                'document_title':rec['source_title'], 'locator':note['locator'], 'quote':note['quote']})
            notes.append({**deepcopy(note), 'evidence':evidence, 'policy_certified':False})
        return {**who, 'candidate_id':row['candidate_id'], 'revision':row['revision'],
            'index_sha256':row['index_sha256'], 'audit':audit, 'notes':notes,
            'policy_certified':False, 'publication_authorized':False}

    def proposal(self, row):
        decision = row['decision']
        if not decision or decision['decision'] != 'approve_for_source_registration':
            raise Hold('Current source-registration approval required')
        pdf_url(self.city,row['source_url'])
        return {'city':self.city, 'enabled':False, 'network_enabled':False,
            'candidate_id':row['candidate_id'], 'revision':row['revision'],
            'registration_review':decision, 'publication_authorized':False,
            'communication':{'max_requests':1,'max_total_bytes':2097152,'timeout_seconds':10,
                'tls_verify':True,'redirects':0,'retries':0,'follow_links':False},
            'source':{'id':row['candidate_id'], 'url':row['source_url'],
                'title':row['listings'][0]['title'], 'fiscal_year':row['fiscal_year'],
                'media_type':'pdf', 'document_kind':'other_official', 'max_bytes':2097152,
                'policy_ids':decision['policy_ids'], 'index_url':row['index_url'],
                'index_sha256':row['index_sha256'], 'index_locators':[r['locator'] for r in row['listings']]},
            'remaining_gates':['PM communication GO','fixed P1/scope and binding validation',
                'owner-only storage','persistent one-shot reservation','human policy evidence review']}

    def report(self, candidates):
        rows = []
        for cid, row in sorted(candidates.items()):
            evidence = row['evidence']; decision = row['decision']
            policies = sorted(set((decision or {}).get('policy_ids',[]) +
                (evidence or {}).get('audit',{}).get('policy_ids',[])))
            notes = (evidence or {}).get('notes',[])
            rows.append({'candidate_id':cid, 'title':row['listings'][0]['title'],
                'official_url':row['source_url'], 'fiscal_year':row['fiscal_year'],
                'fiscal_year_basis':'index_context; PDF scope requires human confirmation',
                'index_sha256':row['index_sha256'], 'locators':[r['locator'] for r in row['listings']],
                'revision':row['revision'], 'active':row['active'], 'last_change':row['last_change'],
                'policy_ids':policies, 'policy_assignment':'candidate_only' if policies else 'unconfirmed',
                'registration_status':(decision or {}).get('decision','pending'),
                'hold_reason':(decision or {}).get('reason'),
                'original_status':'原本SHA・receipt照合済み' if evidence else '取得待ち',
                'original_sha256':(evidence or {}).get('audit',{}).get('sha256'),
                'document_id':(evidence or {}).get('audit',{}).get('document_id'),
                'evidence_status':'原典確認済み（引用位置照合・政策認定ではない）' if notes else '政策との対応確認待ち',
                'notes':notes, 'next_evidence':'議決・施行・実績待ち（各段階は別審査）',
                'publication_authorized':False})
        return {'city':self.city, 'network_requests':0, 'public_writes':0, 'sources':rows,
            'policies':[{'policy_id':p, 'candidate_ids':[r['candidate_id'] for r in rows if p in r['policy_ids']],
                'status':'根拠候補あり・政策認定は別審査' if any(p in r['policy_ids'] for r in rows) else '政策との対応確認待ち'}
                for p in self.config['policy_ids']]}

    def apply(self, request):
        with weekly.single_run(self.root):
            identity = {'city':self.city, 'cas_root':str(self.cas), 'schema':'source-registry-v1'}
            binding = self.root/'registry_identity.json'
            if binding.exists():
                if load(binding) != identity: raise Hold('Registry identity mismatch')
            else:
                if any(p.name != 'weekly.lock' for p in self.root.iterdir()):
                    raise Hold('Use empty isolated registry root')
                durable_record(self.root, 'registry_identity', identity)
            events = self.history(); indexes, candidates = self.state(events)
            op = request['operation']
            if op == 'report': return self.report(candidates)
            if op == 'scan': data = self.scan(request, indexes)
            else:
                row = self.current(candidates,request)
                if op == 'proposal': return self.proposal(row)
                if op == 'decision': data = self.decision(row,request)
                elif op == 'evidence': data = self.attach(row,request)
                else: raise Hold('Unknown registry operation')
                prior = row['decision' if op=='decision' else 'evidence']
                if prior and {k:v for k,v in prior.items() if k!='recorded_at'} == data: data = None
            if data is None: return {'new_events':0,'network_requests':0,'public_writes':0}
            event = {'kind':op, 'data':data, 'recorded_at':datetime.now(timezone.utc).isoformat(),
                'previous':events[-1]['event_sha256'] if events else None}
            event['event_sha256'] = digest(event)
            durable_record(self.root, f'event-{len(events)+1:08d}', event)
            return {'new_events':1, 'event_sha256':event['event_sha256'],
                'changes':len(data.get('changes',[])), 'network_requests':0,'public_writes':0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True, help='Empty owner-only output outside Git')
    args = parser.parse_args(); request = load(args.request)
    configure_shell(request); weekly.assert_owner_only(args.request)
    if request.get('network_enabled') is not False: raise Hold('Offline only')
    for pin in request['code_files']: weekly.pinned_input(pin)
    if not any(Path(p['path']).resolve()==Path(__file__).resolve() for p in request['code_files']):
        raise Hold('Registry code must be pinned')
    bridge = weekly.P1Bridge(request['p1_code_root'],request['snapshot_root'],city_capable=True)
    registry = Registry(request['registry_root'],bridge,request['city'])
    out = PrivateOutput(args.output); weekly.assert_owner_only(out.root)
    for protected in (registry.cas,registry.root):
        if out.root == protected or out.root in protected.parents or protected in out.root.parents:
            raise Hold('Report output must be separate from CAS and registry')
    result = registry.apply(request['action']); out.json('result.json',result)
    report = registry.apply({'operation':'report'}); out.json('review.json',report)
    out.write('review.html','<!doctype html><meta charset="utf-8"><title>原典候補の人手審査</title>'
        '<h1>原典候補の人手審査</h1><p>取得・登録は政策認定や公開許可ではありません。</p>'
        '<table><tr><th>資料</th><th>政策候補・年度</th><th>確認状態</th><th>次の原典</th></tr>'+''.join(
            '<tr><td>'+escape(r['title'])+'<br>'+escape(r['official_url'])+'</td><td>'+escape(str(r['policy_ids']))+
            ' / '+str(r['fiscal_year'])+'</td><td>'+escape(r['original_status']+' / '+r['evidence_status'])+
            '<br>'+escape(r['registration_status']+' / '+str(r['hold_reason']))+
            '<details><summary>出典位置・履歴・引用</summary><pre>'+escape(json.dumps(r,ensure_ascii=False,indent=2))+
            '</pre></details></td><td>'+escape(r['next_evidence'])+'</td></tr>' for r in report['sources'])+'</table>')
    print(json.dumps({'network_requests':0,'public_writes':0,'candidates':len(report['sources'])}))


if __name__ == '__main__': main()
