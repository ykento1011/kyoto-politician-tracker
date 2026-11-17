"""Offline recurring review loop. No acquisition, scheduling or publication API.

Each explicit cycle is consumed once, including failures. Original acquisition
remains a separate approved P1 operation; one-shot reservations are never touched.
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from . import weekly
from .operations import load, run_trial
from .engine import PrivateOutput, digest
from .city_scope import official_host
from .projection import Hold
from urllib.parse import urlsplit


def manifest(config, city):
    """Normalize registered sources without guessing a policy/amount relationship."""
    registry = load(Path(__file__).resolve().parents[2] / 'config/mayor_update_sources.json')['cities']
    if city not in registry:
        raise Hold('Unknown city')
    registered = registry[city]['monitor_sources']
    sources = config['cities'][city]['monitor_sources']
    if not sources or sources != registered:
        raise Hold('Use the exact registered sources; source additions need separate review')
    rows = []
    for s in sources:
        u = urlsplit(s['url'])
        if u.scheme != 'https' or u.netloc != official_host(city) or u.query or u.fragment:
            raise Hold('Invalid official source URL')
        policies = s.get('policy_ids', [s['policy_id']] if s.get('policy_id') else [])
        if not set(policies) <= set(registry[city]['policy_ids']):
            raise Hold('Foreign policy')
        rows.append(dict(city=city, source_id=s['id'], official_url=s['url'],
            title=s['title'], fiscal_year=s['fiscal_year'], kind=s['document_kind'],
            media=s.get('media_type', 'html'), cadence_days=s['interval_days'],
            policy_ids=policies, policy_assignment='explicit_candidate' if policies else 'unconfirmed',
            max_bytes=s['max_bytes']))
    return rows


def cycle(bridge, config, baseline, rules, state_root, *, city, cycle_key, base_revision):
    """Consume one offline observation cycle against a private, persistent state."""
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', cycle_key):
        raise Hold('An explicit ISO calendar-date cycle is required')
    date.fromisoformat(cycle_key)
    rows = manifest(config, city)
    root = PrivateOutput(state_root).root
    weekly.assert_owner_only(root)
    cas = Path(bridge.store.root).resolve(strict=True)
    weekly.assert_owner_only(cas)
    if root == cas or root in cas.parents or cas in root.parents:
        raise Hold('Loop state must be separate from CAS')
    with weekly.single_run(root):
        identity = {'city':city, 'manifest_sha256':digest(rows)}
        binding = root / 'loop_identity.json'
        if binding.exists():
            if load(binding) != identity:
                raise Hold('State belongs to another city/source series')
        else:
            if any(p.name != 'weekly.lock' for p in root.iterdir()):
                raise Hold('First cycle requires an empty isolated state, not existing weekly state')
            PrivateOutput(root).json(binding.name, identity)
        cycles = root / 'cycles'; cycles.mkdir(exist_ok=True)
        output = cycles / cycle_key
        try:
            output.mkdir()  # Permanent cycle reservation; never deleted on failure.
        except FileExistsError as exc:
            raise Hold('Cycle already attempted; no automatic retry') from exc
        out = PrivateOutput(output)
        out.json('intent.json', {**identity, 'cycle_key':cycle_key, 'network_requests':0})
        prior = load(root/'state.json') if (root/'state.json').exists() else {'monitor':{}, 'seen_reviews':{}}
        try:
            bridge.store.verify_integrity()
            result, _ = run_trial(bridge, config, baseline, rules, output,
                previous=prior.get('monitor'), base_revision=base_revision,
                seen_reviews=prior.get('seen_reviews', {}), city=city,
                allowed=config['cities'][city]['policy_ids'])
            status = load(output/'run_status.json')
            observations = []
            good_state = (prior.get('monitor', {}) if status['state']=='stopped_no_public_change'
                          else result['state'])
            for row in rows:
                url = row['official_url']
                good = good_state.get('documents', {}).get(url, {})
                events = [e for e in result['document_events'] if e['source_url']==url]
                observations.append({**row, 'last_good_sha':good.get('sha256'),
                    'observed_at':good.get('retrieved_at'), 'detected_change':events,
                    'confirmed_fact':'Saved source observation only; policy effect requires human review',
                    'review_status':'unverified', 'published_revision':None})
            out.json('observations.json', observations)
            weekly.review_index(output, status, city_label=city)
            # Review files and observation metadata are durable before good pointer advances.
            summary = {'cycle_key':cycle_key, 'state':status['state'],
                'new_review_count':len(status.get('new_reviews', {})),
                'network_requests':0, 'public_writes':0,
                'previous_state_retained':status['state']=='stopped_no_public_change'}
            out.json('cycle_result.json', summary)
            summary['state_advanced'] = weekly.commit_success(root, output, prior, result['state'], status)
            return summary
        except Exception as exc:
            out.json('failure.json', {'reason':str(exc), 'previous_state_retained':True,
                'network_requests':0, 'public_writes':0})
            raise


def review_decision(state_root, review_key, decision, reviewer, reason):
    """Append a human hold/rejection. Approval/publication deliberately unsupported."""
    root = PrivateOutput(state_root).root
    weekly.assert_owner_only(root)
    if decision not in {'hold','rejected'} or not reviewer.strip() or not reason.strip():
        raise Hold('Explicit human hold/rejection and reason required')
    with weekly.single_run(root):
        state = load(root/'state.json')
        if review_key not in state.get('seen_reviews', {}):
            raise Hold('Unknown review')
        target = Path(state['seen_reviews'][review_key]).resolve(strict=True)
        if root not in target.parents:
            raise Hold('Review outside private state')
        events = root/'review_events'; events.mkdir(exist_ok=True)
        payload = dict(review_key=review_key, decision=decision, reviewer=reviewer,
            reason=reason, at_utc=datetime.now(timezone.utc).isoformat(),
            review_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), publication_authorized=False)
        PrivateOutput(events).json(uuid.uuid4().hex+'.json', payload)
        return payload


def configure_shell(runtime):
    if os.name == 'nt':
        shell = Path(runtime['powershell_exe']).resolve(strict=True)
        if shell.name.lower() != 'pwsh.exe' or not shell.is_file():
            raise Hold('PowerShell runtime must be explicit')
        os.environ['MAYOR_PWSH_EXE'] = str(shell)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--cycle', required=True)
    args = parser.parse_args()
    runtime = load(args.runtime)
    if runtime.get('network_enabled') is not False:
        raise Hold('This entry is offline only')
    configure_shell(runtime)
    weekly.assert_owner_only(args.runtime)
    if not any(Path(s['path']).resolve()==Path(__file__).resolve() for s in runtime['code_files']):
        raise Hold('Executing continuous entry must be pinned')
    # Reuse pinned code/input checks and the existing Kyoto communication contract.
    root, paths, config = weekly.validate_runtime(runtime, reuse_saved=True)
    if type(runtime.get('p1_city_capable', False)) is not bool:
        raise Hold('Invalid P1 selection')
    bridge = weekly.P1Bridge(runtime['p1_code_root'], runtime['snapshot_root'],
        city_capable=runtime.get('p1_city_capable', False))
    print(json.dumps(cycle(bridge, config, load(paths['baseline']), load(paths['rules']), root,
        city=runtime.get('city','kyoto'), cycle_key=args.cycle,
        base_revision=runtime['base_revision']), ensure_ascii=False))


if __name__ == '__main__':
    main()
