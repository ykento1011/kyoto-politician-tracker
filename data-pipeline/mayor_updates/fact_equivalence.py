"""Opt-in offline experiment: continuation of an accepted fact, never approval.

No acquisition, registry decision or baseline writer. Unknown differences HOLD.
"""
from copy import deepcopy
from hashlib import sha256
import re
from urllib.parse import urlsplit

from .engine import digest
from .index_adapter import saved_index, comparison_links
from .projection import Hold
from .city_scope import official_host

MODE = 'offline_unchanged_equivalence_v1'


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


def index_equivalent(registry, old, observed):
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
    if before != after:
        # Deliberately narrow byte proof. No generic DOM diff or normalization.
        if (not before.endswith(b'</div>') or not after.endswith(b'</div>')
                or not after.startswith(before[:-6])):
            raise Hold('equivalence_unproven_index_delta')
        addition = after[len(before)-6:-6].decode('utf-8')
        pattern = r'<a href="(https://[^"<>]+\.pdf)">([^<>&]+)</a>'
        matches = list(re.finditer(pattern, addition))
        if not matches or ''.join(m.group(0) for m in matches)!=addition:
            raise Hold('equivalence_unknown_index_structure')
        urls = [m.group(1) for m in matches]
        if len(urls)!=len(set(urls)) or any(u in inventories[0] for u in urls):
            raise Hold('equivalence_duplicate_index_link')
        for u in urls:
            parsed = urlsplit(u)
            if parsed.netloc!=official_host(registry.city) or parsed.query or parsed.fragment:
                raise Hold('equivalence_foreign_index_addition')
    return {'old_index_sha256':old['index_sha256'], 'new_index_sha256':observed['index_sha256'],
            'old_revision':old['revision'], 'new_revision':observed['revision'],
            'target_listing_sha256':digest(inventories[0][url])}


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
    indexes = index_equivalent(registry, old, observed)
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
