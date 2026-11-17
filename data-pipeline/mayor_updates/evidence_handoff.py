"""Offline registration -> acquisition preflight -> quoted evidence -> private PR plan.

No acquisition, reservation creation, public writer or approval generator exists here.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from . import engine, weekly, city_scope
from .continuous import configure_shell
from .operations import load
from .periodic import durable_record
from .projection import Hold
from .source_registry import Registry


def current(registry, request):
    registry.bridge.index = registry.bridge.store.read_index()
    indexes, rows = registry.state(registry.history())
    row = registry.current(rows, request, indexes)
    # A changed index needs a fresh human approval even if this PDF link survived.
    if row['index_sha256'] != indexes[row['index_url']]['sha256']:
        raise Hold('Index changed since candidate review; human re-registration required')
    return row


def acquisition_plan(registry, row, request):
    plan = registry.proposal(row)  # requires explicit registration review
    scope = weekly.pinned_input(request['scope'])
    scope = load(scope)
    if scope.get('enabled') is not False or scope.get('network_enabled') is not False:
        raise Hold('Acquisition plan requires a disabled scope')
    city_scope.validate_scope(scope)
    if scope['city_code'] != registry.city:
        raise Hold('Foreign scope')
    sources = [s for s in scope['sources'] if s['url'] == row['source_url']]
    if len(sources) != 1:
        raise Hold('Candidate must occur exactly once in fixed scope')
    source = sources[0]
    expected_id = registry.city+'-doc-'+sha256(source['url'].encode()).hexdigest()[:24]
    if (source['policy_ids'] != row['decision']['policy_ids'] or
            source['fiscal_year'] != row['fiscal_year'] or source['media_type'] != 'pdf' or
            source.get('document_id') != expected_id or source['max_bytes'] != 2097152):
        raise Hold('Fixed source identity does not match human registration')
    storage = request['storage']
    for p in (storage['private_root'], storage['state_root'], registry.cas):
        weekly.assert_owner_only(p)
    state = city_scope.validate_storage(scope, storage, registry.cas, request['acquisition_output'])
    if registry.bridge.hashes != request['p1_sha256']:
        raise Hold('Fixed P1 code hashes mismatch')
    registry.bridge.store.verify_integrity()
    marker = state/('single_request_'+sha256(source['url'].encode()).hexdigest()+'.json')
    if marker.exists():
        raise Hold('URL reservation exists; no retry or deletion permitted')
    saved = registry.bridge.index['documents'].get(source['url'])
    existing_sha = None
    if saved:
        existing_sha = saved['versions'][-1]['sha256']
        rec, body = registry.bridge.record(source['url'], existing_sha)
        if sha256(body).hexdigest() != existing_sha or rec['document_id'] != expected_id:
            raise Hold('Existing original identity mismatch')
    return {**plan, 'source':deepcopy(source), 'scope_sha256':city_scope.signature(scope),
            'binding_sha256':storage['binding_sha256'], 'p1_sha256':registry.bridge.hashes,
            'document_id':expected_id, 'existing_sha256':existing_sha,
            'next_action':'reuse_saved_original' if saved else 'await_separate_communication_GO',
            'reservation_created':False, 'executable':False}


def evidence_packet(registry, row, request):
    # Reuse receipt, observation history, current original SHA and literal quote checks.
    attached = registry.attach(row, request)
    units = []
    for note in attached['notes']:
        for key in ('submeasure', 'limitations'):
            if not isinstance(note.get(key), str) or not note[key].strip():
                raise Hold('Policy branch and limitations required')
        if note.get('relation') not in engine.RELATIONS:
            raise Hold('Explicit policy relation required')
        units.append({k:deepcopy(note[k]) for k in
            ('policy_id','submeasure','fact_type','relation','quote','locator','limitations','evidence')})
    packet = {'city':registry.city, 'candidate_id':row['candidate_id'],
        'revision':row['revision'], 'index_sha256':row['index_sha256'],
        'audit':attached['audit'], 'units':units, 'verification_status':'unverified',
        'publication_authorized':False,
        'status':'human_policy_review_required' if units else 'policy_relationship_unconfirmed'}
    packet['evidence_packet_id'] = engine.digest(packet)
    return packet


def public_packet(registry, row, request):
    evidence = evidence_packet(registry, row, request)
    if not evidence['units']:
        raise Hold('No policy evidence to propose; unconfirmed remains on hold')
    base = load(weekly.pinned_input(request['baseline']))
    candidates = []
    displays = request['displays']
    if len(displays) != len(evidence['units']):
        raise Hold('Each quoted fact needs one separately reviewed display')
    for unit, display in zip(evidence['units'], displays):
        if (display.get('policy_id') != unit['policy_id'] or
                display.get('submeasure') != unit['submeasure'] or not display.get('text')):
            raise Hold('Display does not identify the quoted policy branch')
        candidate = {'city':registry.city, 'policy_id':unit['policy_id'],
            'kind':'evidence_note', 'relation':unit['relation'],
            'verification_status':'unverified', 'reason':request['reason'],
            'evidence':[unit['evidence']],
            'note':{'submeasure':unit['submeasure'], 'fact_type':unit['fact_type'],
                    'text':display['text'], 'limitations':unit['limitations']}}
        candidate['candidate_id'] = engine.digest(candidate)
        candidates.append(candidate)
    packet, _ = engine.propose(base,candidates,city=registry.city,
        allowed=sorted({u['policy_id'] for u in evidence['units']}),
        base_revision=request['base_revision'])
    if packet is None:
        return {'status':'already_present','publication_authorized':False}
    result = {'evidence':evidence,'packet':packet,'publication_authorized':False}
    if request['operation'] == 'public_proposal':
        bundle = engine.approved_bundle(base,packet,request['approval'])
        # Only private proposal data: omit a ready-to-write public JSON payload.
        result['proposal'] = {k:v for k,v in bundle.items() if k != 'data'}
    return result


def run(registry, request, output):
    out = engine.PrivateOutput(output); weekly.assert_owner_only(out.root)
    for protected in (registry.root, registry.cas):
        if out.root == protected or out.root in protected.parents or protected in out.root.parents:
            raise Hold('Private handoff output must be isolated from registry/CAS')
    if request.get('network_enabled') is not False:
        raise Hold('Offline only')
    with weekly.single_run(registry.root), weekly.single_run(out.root):
        row = current(registry,request)
        op = request['operation']
        if op == 'acquisition_plan': result = acquisition_plan(registry,row,request)
        elif op == 'evidence_packet': result = evidence_packet(registry,row,request)
        elif op in {'public_review','public_proposal'}: result = public_packet(registry,row,request)
        else: raise Hold('Unknown handoff action')
        key = engine.digest(result)
        dest = out.root/(key+'.json')
        if dest.exists():
            if load(dest) != result: raise Hold('Existing handoff content mismatch')
            new = 0
        else:
            durable_record(out.root,key,result); new = 1
        return {'record_id':key,'new_records':new,'network_requests':0,'public_writes':0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args(); config = load(args.request)
    configure_shell(config); weekly.assert_owner_only(args.request)
    if config.get('network_enabled') is not False: raise Hold('Offline only')
    for pin in config['code_files']: weekly.pinned_input(pin)
    if not any(Path(p['path']).resolve()==Path(__file__).resolve() for p in config['code_files']):
        raise Hold('Handoff code must be pinned')
    bridge = weekly.P1Bridge(config['p1_code_root'],config['snapshot_root'],city_capable=True)
    registry = Registry(config['registry_root'],bridge,config['city'])
    print(run(registry,config['action'],args.output))


if __name__ == '__main__': main()
