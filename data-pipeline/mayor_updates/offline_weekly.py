"""Common saved-source weekly entry. No acquisition or activation path exists."""
import argparse
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from . import continuous, weekly
from .engine import digest
from .operations import load
from .periodic import period
from .projection import Hold

PROFILE = Path(__file__).resolve().parents[2] / 'config/mayor_offline_weekly.json'


def prepare(config, city):
    profile = load(PROFILE)
    if profile.get('network_enabled') is not False or profile.get('enabled') is not False:
        raise Hold('Saved-source profiles cannot activate communication')
    if city not in profile['cities']:
        raise Hold('No saved-source profile for city')
    sources = profile['cities'][city]
    if not sources or len({s['url'] for s in sources}) != len(sources):
        raise Hold('Missing or duplicate saved sources')
    for source in sources:
        if (source.get('acquisition_enabled') is not False or
                source.get('registration_status') not in {'pending', 'hold', 'approved'} or
                source.get('interval_days') != 7 or source.get('max_bytes') != 2097152):
            raise Hold('Invalid disabled source contract')
    local = deepcopy(config)
    local.update(enabled=False, network_enabled=False)
    local['cities'][city]['monitor_sources'] = deepcopy(sources)
    continuous.manifest(local, city, offline_sources=sources)
    return local, sources


def inspect_saved(bridge, sources):
    """Conservative exceptions only; never infer a political/budget fact."""
    holds = []
    for source in sources:
        doc = bridge.index['documents'].get(source['url'])
        if not doc or not doc.get('versions'):
            continue  # Existing monitor records missing/failed originals.
        record = doc['versions'][-1]['record']
        rec, body = bridge.record(source['url'], record['sha256'])
        if rec.get('mime_type') != 'text/html':
            raise Hold('Saved weekly profile expects HTML')
        main = BeautifulSoup(body, 'html.parser').select(source['selector'])
        if len(main) != 1:
            holds.append({'source_url':source['url'], 'reason':'unknown_or_ambiguous_structure'})
            continue
        text = main[0].get_text(' ', strip=True)
        signals = [word for word in ('訂正', '撤回', '差替', '差し替', '取消', '追補') if word in text]
        if signals:
            holds.append({'source_url':source['url'], 'reason':'correction_or_withdrawal_requires_review',
                          'signals':signals})
    return holds


def run(bridge, config, baseline, state_root, *, city, now, base_revision):
    """Caller supplies a pinned P1 bridge and isolated private state; reads CAS only."""
    timing = period(now)
    local, sources = prepare(config, city)
    holds = inspect_saved(bridge, sources)
    result = continuous.cycle(bridge, local, baseline, [], state_root, city=city,
        cycle_key=timing['cycle_key'], base_revision=base_revision,
        offline_sources=sources, observation_holds=holds)
    return {**result, 'city':city, 'profile_sha256':digest(sources),
            'mode':'saved_originals_only', 'schedule':timing,
            'source_registration_granted':False, 'acquisition_authorized':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    args = parser.parse_args()
    runtime = load(args.runtime)
    if runtime.get('network_enabled') is not False:
        raise Hold('This entry has no network mode')
    continuous.configure_shell(runtime)
    weekly.assert_owner_only(args.runtime)
    required = {path.resolve() for path in Path(__file__).parent.glob('*.py')}
    files = runtime['code_files']
    if not required <= {Path(spec['path']).resolve() for spec in files}:
        raise Hold('Executing common entry and loop must be pinned')
    for spec in files:
        weekly.pinned_input(spec)
    if weekly.pinned_input(runtime['profile']) != PROFILE.resolve():
        raise Hold('Pin the checked-out disabled source profile')
    paths = {key:weekly.pinned_input(runtime[key]) for key in ('config', 'baseline')}
    bridge = weekly.P1Bridge(runtime['p1_code_root'], runtime['snapshot_root'], city_capable=True)
    result = run(bridge, load(paths['config']), load(paths['baseline']), runtime['state_root'],
        city=runtime['city'], now=datetime.now().astimezone(), base_revision=runtime['base_revision'])
    import json
    print(json.dumps(result, ensure_ascii=False))
    if not result['state_advanced']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
