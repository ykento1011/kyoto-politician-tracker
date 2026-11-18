"""Opt-in offline experiment: continuation of an accepted fact, never approval.

No acquisition, registry decision or baseline writer. Unknown differences HOLD.
"""
from copy import deepcopy
from hashlib import sha256
import re
from urllib.parse import urlsplit
from urllib.parse import urljoin
from html.parser import HTMLParser
from bs4 import BeautifulSoup

from .engine import digest
from .index_adapter import saved_index, comparison_links
from .projection import Hold
from .city_scope import official_host

MODE = 'offline_unchanged_equivalence_v1'


def list_boundary(body, source, target):
    """Locate an explicit, balanced attachment UL in original UTF-8 bytes."""
    text = body.decode('utf-8')
    lines = text.splitlines(keepends=True)
    class Spans(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack=[]; self.spans=[]
        def byte_position(self):
            line,col=self.getpos()
            return len((''.join(lines[:line-1])+lines[line-1][:col]).encode('utf-8'))
        def handle_starttag(self, tag, attrs):
            if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
                self.stack.append((tag,self.byte_position()))
        def handle_startendtag(self, tag, attrs):
            pass
        def handle_endtag(self, tag):
            if not self.stack or self.stack[-1][0]!=tag:
                raise Hold('equivalence_unbalanced_html')
            opened,start=self.stack.pop()
            if opened=='ul':self.spans.append((start,self.byte_position()))
    parser=Spans();parser.feed(text);parser.close()
    if parser.stack:raise Hold('equivalence_unbalanced_html')
    soup=BeautifulSoup(text,'html.parser')
    if len(soup.select(source.get('selector','#mol_contents')))!=1:
        raise Hold('equivalence_ambiguous_content')
    matches=[]
    for start,end in parser.spans:
        fragment=BeautifulSoup(body[start:end].decode('utf-8')+'</ul>','html.parser')
        anchors=[a for a in fragment.find_all('a',href=True)
                 if urljoin(source['resolution_base'],a['href'])==target]
        if len(anchors)==1:matches.append((start,end))
    if len(matches)!=1:raise Hold('equivalence_ambiguous_list')
    targets=[a for a in soup.find_all('a',href=True)
             if urljoin(source['resolution_base'],a['href'])==target]
    if len(targets)!=1:raise Hold('equivalence_duplicate_target')
    anchor=targets[0];li=anchor.parent;ul=li.parent;block=ul.parent
    if (li.name!='li' or ul.name!='ul' or block.name!='div'
            or block.get('class')!=['mol_attachfileblock']
            or block.select_one('.mol_attachfileblock_title') is None
            or block.find_parent(id='mol_contents') is None):
        raise Hold('equivalence_unknown_attachment_list')
    return matches[0][1]


def addition_proof(registry, before, after, source, old, context):
    from . import weekly
    from .operations import load
    position=list_boundary(before,source,old['source_url'])
    size=len(after)-len(before)
    if size<=0 or after[:position]!=before[:position] or after[position+size:]!=before[position:]:
        raise Hold('equivalence_unproven_index_delta')
    addition=after[position:position+size]
    # No arbitrary HTML. Existing bytes include headings, neighbours and suffix.
    match=re.fullmatch(rb'<li><a href="(https://[^"<>]+\.pdf)">([^<>&]+)</a></li>',addition)
    if not match:raise Hold('equivalence_unknown_index_structure')
    url=match[1].decode('utf-8');parsed=urlsplit(url)
    if parsed.netloc!=official_host(registry.city) or parsed.query or parsed.fragment:
        raise Hold('equivalence_foreign_index_addition')
    soup=BeautifulSoup(after.decode('utf-8'),'html.parser')
    if sum(urljoin(source['resolution_base'],a['href'])==url for a in soup.find_all('a',href=True))!=1:
        raise Hold('equivalence_duplicate_index_link')
    if list_boundary(after,source,old['source_url'])!=position+size:
        raise Hold('equivalence_list_boundary_changed')
    spec=context['proof'].get('index_addition_rule')
    if not spec:raise Hold('equivalence_unrelatedness_rule_missing')
    def pinned(spec):
        path=weekly.pinned_input(spec);weekly.assert_owner_only(path)
        return path
    rule=load(pinned(spec))
    binding={k:old[k] for k in ('city','candidate_id','source_url','index_sha256','revision')}
    if (rule.get('decision')!='approve_exact_unrelated_index_addition'
            or rule.get('binding')!=binding or rule.get('insertion_sha256')!=sha256(addition).hexdigest()
            or rule.get('source_registration_authorized') is not False
            or rule.get('publication_authorized') is not False
            or not all(rule.get(k) for k in ('rule_id','version','reviewer','reviewed_at','review_record_id'))):
        raise Hold('equivalence_unrelatedness_rule_mismatch')
    evidence=pinned(rule['primary_evidence']).read_bytes()
    # Exact saved primary evidence is required, not a machine-written assertion.
    quote=rule.get('primary_quote')
    if not isinstance(quote,str) or not quote or quote.encode('utf-8') not in evidence:
        raise Hold('equivalence_primary_evidence_mismatch')
    if rule.get('correction_withdrawal_supplement_replacement_excluded') is not True:
        raise Hold('equivalence_semantic_dependency_unresolved')
    return dict(insertion_byte_offset=position,insertion_sha256=sha256(addition).hexdigest(),
        prefix_sha256=sha256(before[:position]).hexdigest(),suffix_sha256=sha256(before[position:]).hexdigest(),
        unrelatedness_rule_sha256=spec['sha256'],primary_evidence_sha256=rule['primary_evidence']['sha256'])


def public_projection(value, policy):
    """Only whitespace presentation changes in OTHER policies' headlines.

    Every other key/value, including other budgets and shared totals, remains
    in the digest. No arbitrary fields may be supplied as an exclusion list.
    """
    value = deepcopy(value)
    if (not isinstance(value, dict) or set(value) != {'mayor_info', 'summary_stats', 'pledges',
                                                   'city_name', 'mayor_name', 'kpis'}
            or not isinstance(value['pledges'], list)):
        raise Hold('equivalence_unknown_public_schema')
    ids = []
    for row in value['pledges']:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str):
            raise Hold('equivalence_unknown_policy_schema')
        ids.append(row['id'])
        if row['id'] != policy:
            if not isinstance(row.get('headline'), str):
                raise Hold('equivalence_missing_headline')
            row['headline'] = ' '.join(row['headline'].split())
    if len(ids) != len(set(ids)) or ids.count(policy) != 1:
        raise Hold('equivalence_ambiguous_policy')
    return value


def index_equivalent(registry, old, observed, context):
    # Prove both revisions actually occur in the immutable, checked event chain.
    history = registry.history()
    prefix = next((i+1 for i,e in enumerate(history) if e['event_sha256']==old['revision']), None)
    if prefix is None:
        raise Hold('equivalence_missing_old_revision')
    _, rows = registry.state(history[:prefix])
    oldrow = rows.get(old['candidate_id'])
    if (not oldrow or not oldrow['active'] or oldrow['index_sha256'] != old['index_sha256']
            or oldrow['source_url'] != old['source_url']):
        raise Hold('equivalence_old_revision_mismatch')
    _, rows = registry.state(history)
    row = rows[observed['candidate_id']]
    if (row.get('decision') or {}).get('decision') in {'hold','reject'}:
        raise Hold('equivalence_source_explicitly_blocked')
    if (row['revision'] != observed['revision'] or row['index_sha256'] != observed['index_sha256']
            or row['index_url'] != oldrow['index_url'] or row['fiscal_year'] != oldrow['fiscal_year']):
        raise Hold('equivalence_index_identity_mismatch')
    source = next((s for s in registry.config['monitor_sources']
                   if s.get('role')=='index' and s['url']==row['index_url']), None)
    if source is None:
        raise Hold('equivalence_unregistered_index')
    inventories = []
    bodies = []
    for obs in (old, observed):
        rec, body = registry.bridge.record(source['url'], obs['index_sha256'])
        if (sha256(body).hexdigest()!=obs['index_sha256'] or rec['sha256']!=obs['index_sha256']
                or rec['city_code']!=registry.city or rec['fiscal_year']!=source['fiscal_year']
                or rec['source_url']!=source['url'] or rec['final_url']!=source['url']):
            raise Hold('equivalence_index_readback_mismatch')
        inventories.append(comparison_links(saved_index(registry.bridge,source,obs['index_sha256'],city=registry.city)))
        bodies.append(body)
    url = old['source_url']
    if not inventories[0].get(url) or inventories[0].get(url)!=inventories[1].get(url):
        raise Hold('equivalence_listing_context_or_position_changed')
    before, after = bodies
    proof={}
    if before != after:
        proof=addition_proof(registry,before,after,source,old,context)
    return {'old_index_sha256':old['index_sha256'], 'new_index_sha256':observed['index_sha256'],
            'old_revision':old['revision'], 'new_revision':observed['revision'],
            'target_listing_sha256':digest(inventories[0][url]),**proof}


def prove(registry, observed, accepted, public, context):
    old = context['proof']['old_observed']
    old_public_sha = context['old_public_sha256']
    fingerprint = digest({'observed':old, 'public_sha256':old_public_sha})
    prior = [x for x in accepted if x.get('fingerprint')==fingerprint
             and x.get('decision')=='accept_existing_fact'
             and all(x.get(k) for k in ('reviewer','reviewed_at','review_record_id'))]
    # The proof pins the entire pre-existing acceptance entry, not a new signer.
    if len(prior)!=1 or digest(prior[0])!=context['proof']['acceptance_entry_sha256']:
        raise Hold('equivalence_acceptance_record_mismatch')
    if context['proof']['accepted_file_sha256']!=context['accepted_file_sha256']:
        raise Hold('equivalence_acceptance_file_mismatch')
    normalized = deepcopy(observed)
    for k in ('revision','index_sha256'):
        normalized[k] = old[k]
    if digest(normalized) != digest(old):
        raise Hold('equivalence_fact_original_receipt_changed')
    indexes = index_equivalent(registry, old, observed, context)
    left = public_projection(context['old_public'],old['fact']['policy_id'])
    right = public_projection(public,old['fact']['policy_id'])
    if digest(left) != digest(right):
        raise Hold('equivalence_public_dependency_changed')
    return {'mode':MODE, 'old_accepted_fingerprint':fingerprint,
            'acceptance_entry_sha256':digest(prior[0]),
            'proof_sha256':context['proof_sha256'],
            'old_public_sha256':old_public_sha, 'new_public_sha256':context['public_sha256'],
            'public_projection_sha256':digest(left), 'fact_projection_sha256':digest(normalized),
            **indexes, 'source_registration_authorized':False, 'publication_authorized':False}
