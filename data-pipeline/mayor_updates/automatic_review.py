"""Offline exact-fact review. No source approval, acquisition or public writer.

Trusted rule/baseline files must be owner-only, pinned inputs supplied by an
operator. This module never creates human approvals. Changed context is HOLD,
not evidence of non-performance. Only non-additive budget-proposal notes qualify.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import time

from . import engine, weekly
from .continuous import configure_shell
from .evidence_handoff import current
from .operations import load, receipt_identity
from .periodic import durable_record
from .projection import Hold
from .source_registry import Registry


FACT_KEYS = {'policy_id', 'submeasure', 'fact_type', 'relation', 'year',
             'project', 'target', 'amount', 'unit', 'quote', 'limitations', 'pages'}


def pinned(spec):
    path = weekly.pinned_input(spec)
    weekly.assert_owner_only(path)
    return load(path)


def inspect(registry, request):
    """Re-use registry revision, receipt observations and P1 literal PDF checks."""
    weekly.assert_owner_only(registry.bridge.code_root)
    for name, expected in registry.bridge.hashes.items():
        path=registry.bridge.code_root/'budget'/name
        weekly.assert_owner_only(path)
        if sha256(path.read_bytes()).hexdigest()!=expected: raise Hold('p1_pin_mismatch')
    weekly.assert_owner_only(registry.root);weekly.assert_owner_only(registry.cas)
    row = current(registry, request)
    spec = request['receipt_spec']; source = spec['source']; fact = request['fact']
    if (spec['city'] != registry.city or source['url'] != row['source_url'] or
            source['fiscal_year'] != row['fiscal_year'] or source['media_type'] != 'pdf' or
            source['policy_ids'] != spec['policy_ids'] or
            fact['policy_id'] not in spec['policy_ids'] or
            fact['policy_id'] not in registry.config['policy_ids']):
        raise Hold('city_policy_source_mismatch')
    for key in ('acquisition_receipt','acquisition_preflight'):
        weekly.assert_owner_only(weekly.pinned_input(spec[key]))
    version, docid, audit = receipt_identity(spec, source, registry.bridge)
    rec, body = registry.bridge.record(source['url'], version)
    if (sha256(body).hexdigest() != version or rec['city_code'] != registry.city or
            rec['fiscal_year'] != fact['year'] or rec['mime_type'] != 'application/pdf'):
        raise Hold('original_identity_mismatch')
    if set(fact) != FACT_KEYS or not fact['pages']:
        raise Hold('incomplete_fact')
    # Full page text is retained, including surrounding paragraphs and footnotes.
    # Printed page is checked against the PDF footer by the existing P1 bridge.
    pages = []
    for page in fact['pages']:
        if set(page) != {'physical_page', 'printed_page', 'text'} or not page['text'].strip():
            raise Hold('missing_page_context')
        if type(page['physical_page']) is not int or type(page['printed_page']) is not int:
            raise Hold('invalid_page')
        evidence = registry.bridge.evidence(dict(source_url=source['url'], sha256=version,
            document_title=rec['source_title'], locator={k:page[k] for k in
            ('physical_page','printed_page')}, quote=page['text']))
        # Equality, not mere substring: a truncated page must not lose a footnote.
        import fitz
        with fitz.open(stream=body, filetype='pdf') as pdf:
            actual = pdf[page['physical_page']-1].get_text()
        if actual != page['text']:
            raise Hold('page_context_or_footnote_mismatch')
        pages.append(evidence)
    text = '\n'.join(p['text'] for p in fact['pages'])
    for key in ('project','target','amount','unit','quote'):
        if not isinstance(fact[key], str) or not fact[key] or fact[key] not in text:
            raise Hold('literal_field_mismatch:'+key)
    if not fact['submeasure'] or not fact['limitations']:
        raise Hold('missing_branch_or_limitations')
    return row, {'city':registry.city, 'candidate_id':row['candidate_id'],
        'revision':row['revision'], 'index_sha256':row['index_sha256'],
        'source_url':source['url'], 'document_id':docid, 'source_title':rec['source_title'],
        'original_sha256':version, 'receipt':audit, 'fact':deepcopy(fact), 'pages':pages}


def decide(registry, request, rules, accepted, public_sha):
    result = {'status':'HOLD', 'publication_authorized':False, 'public_writes':0,
        'policy_certified':False, 'budget_addition':False,
        'requested_fact':deepcopy(request.get('fact')), 'reason':None,
        'question':'原典・既存事実との差異と、政策枝番への対応を確認してください。'}
    source=request.get('receipt_spec',{}).get('source',{})
    result['unverified_source_claim']={k:source.get(k) for k in ('url','title','fiscal_year')}
    result['candidate_id']=request.get('candidate_id')
    result['existing_fact_differences'] = [
        {'rule_id':r.get('rule_id'), 'fields':{
            k:{'expected':r.get('expected_fact',{}).get(k),'requested':request.get('fact',{}).get(k)}
            for k in sorted(FACT_KEYS) if r.get('expected_fact',{}).get(k)!=request.get('fact',{}).get(k)}}
        for r in rules if r.get('expected_fact',{}).get('policy_id')==request.get('fact',{}).get('policy_id')
        and r.get('expected_fact',{}).get('submeasure')==request.get('fact',{}).get('submeasure')]
    try:
        row, observed = inspect(registry, request)
        result['observed'] = observed
        fingerprint = engine.digest({'observed':observed,'public_sha256':public_sha})
        result['fingerprint'] = fingerprint
        # An accepted baseline is a separate operator-pinned human review artifact;
        # a previous machine result alone must never create this trust.
        prior = [x for x in accepted if x.get('fingerprint') == fingerprint and
                 x.get('decision') == 'accept_existing_fact' and x.get('reviewer') and
                 x.get('reviewed_at') and x.get('review_record_id')]
        if prior:
            result.update(status='UNCHANGED', reason='accepted_fact_and_public_snapshot_identical',
                          question=None)
            return result
        registry.proposal(row)  # current human source registration is mandatory
        f = request['fact']
        if f['fact_type'] != 'budget_proposal' or f['relation'] not in {'direct','contextual'}:
            raise Hold('new_vote_enactment_performance_or_achievement_requires_human_review')
        matched=[]
        for rule in rules:
            binding = {k:observed[k] for k in ('city','candidate_id','revision',
                'index_sha256','source_url','document_id')}
            if (rule.get('binding') == binding and rule.get('expected_fact') == f and
                    rule.get('public_sha256') == public_sha and
                    rule.get('decision') == 'approve_exact_budget_note_rule' and
                    all(rule.get(k) for k in ('rule_id','version','reviewer','reviewed_at','review_record_id')) and
                    rule.get('budget_addition') is False and rule.get('stage_change') is False and
                    rule.get('contradiction_review') == 'cleared'):
                matched.append(rule)
        if len(matched) != 1:
            raise Hold('no_unique_approved_rule_for_exact_context_and_current_public_snapshot')
        if f['policy_id'] not in row['decision']['policy_ids']:
            raise Hold('source_registration_policy_mismatch')
        rule=matched[0]
        result.update(status='AUTO_VERIFIED', reason=None, question=None,
            auto_verified_by_rule=True, rule_id=rule['rule_id'], rule_version=rule['version'],
            rule_sha256=engine.digest(rule), checks={'receipt_original':True,
            'full_page_context_and_footer':True,'exact_fields_and_policy_rule':True,
            'current_public_snapshot':True,'non_additive_proposal_only':True},
            private_publication_candidate={'kind':'evidence_note','fact':deepcopy(f),
                'source_url':observed['source_url'],'sha256':observed['original_sha256'],
                'verification_status':'auto_verified_by_rule','publication_authorized':False,
                'budget_addition':False,'stage_change':False})
    except (Hold, KeyError, ValueError, TypeError, OSError, IndexError, RuntimeError) as exc:
        result['reason']=str(exc)
        result['question']='この理由を解消する証拠または明示的な審査判断が必要です。未実施・未達成を意味しません。'
    return result


def run(registry, config, output):
    if config.get('network_enabled') is not False: raise Hold('offline_only')
    out=engine.PrivateOutput(output); weekly.assert_owner_only(out.root)
    for protected in (registry.root,registry.cas):
        weekly.assert_owner_only(protected)
        if out.root==protected or out.root in protected.parents or protected in out.root.parents:
            raise Hold('output_must_be_isolated')
    rules=pinned(config['rules']); accepted=pinned(config['accepted'])
    public_path=weekly.pinned_input(config['public_snapshot'])
    public_sha=sha256(public_path.read_bytes()).hexdigest()
    if registry.bridge.hashes != config['p1_sha256']: raise Hold('p1_pin_mismatch')
    started=time.perf_counter(); counts={k:0 for k in ('UNCHANGED','AUTO_VERIFIED','HOLD')}
    new=0
    with weekly.single_run(out.root):
        for request in config['requests']:
            result=decide(registry,request,rules,accepted,public_sha)
            counts[result['status']]+=1
            if result['status']=='UNCHANGED': continue
            key=engine.digest(result)
            dest=out.root/(key+'.json')
            if dest.exists():
                if load(dest)['result']!=result: raise Hold('existing_result_corrupted')
                continue
            durable_record(out.root,key,{'result':result,
                'verification_code_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
                'verified_at':datetime.now(timezone.utc).isoformat(),
                'actor':'machine:exact-fact-review-v1'})
            new+=1
    return {**counts,'new_records':new,'human_review_required':counts['HOLD'],
        'elapsed_seconds':time.perf_counter()-started,'network_requests':0,'public_writes':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();weekly.assert_owner_only(args.request)
    config=load(args.request);configure_shell(config)
    for pin in config['code_files']: weekly.pinned_input(pin)
    if not any(Path(p['path']).resolve()==Path(__file__).resolve() for p in config['code_files']):
        raise Hold('review_code_must_be_pinned')
    bridge=weekly.P1Bridge(config['p1_code_root'],config['snapshot_root'],city_capable=True)
    registry=Registry(config['registry_root'],bridge,config['city'])
    print(run(registry,config,args.output))


if __name__=='__main__':main()
