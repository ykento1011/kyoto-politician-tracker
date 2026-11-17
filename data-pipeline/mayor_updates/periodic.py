"""Kyoto weekly adapter: private, reserved cycles; never schedules or publishes.

Default CLI mode replays saved originals with zero HTTP. Live acquisition requires
an explicit flag AND separately approved, pinned private activation settings.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

from . import continuous, weekly
from .engine import PrivateOutput, digest
from .operations import load, run_trial
from .projection import Hold

JST = timezone(timedelta(hours=9))


def local_connectivity():
    """Read Windows' cached connection profiles; never probe a remote endpoint."""
    if os.name != 'nt':
        return 'unknown'
    script = "$ErrorActionPreference='Stop'; @(Get-NetConnectionProfile | ForEach-Object { [string]$_.IPv4Connectivity; [string]$_.IPv6Connectivity }) | ConvertTo-Json -Compress"
    try:
        result = subprocess.run([os.environ.get('MAYOR_PWSH_EXE', 'pwsh.exe'),
            '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return 'unknown'
        states = json.loads(result.stdout)
        known = {'Disconnected', 'NoTraffic', 'Subnet', 'LocalNetwork', 'Internet'}
        if not isinstance(states, list) or not states or any(s not in known for s in states):
            return 'unknown'
        return 'online' if 'Internet' in states else 'offline'
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return 'unknown'


def period(now):
    if now.tzinfo is None:
        raise Hold('An aware clock is required')
    local = now.astimezone(JST)
    due = (local - timedelta(days=local.weekday())).replace(hour=9, minute=0, second=0, microsecond=0)
    if local < due:
        raise Hold('Before this Monday 09:00 JST; no early execution or backfill')
    return {'cycle_key':due.date().isoformat(), 'scheduled_at':due.isoformat(),
            'started_at':local.isoformat(), 'delay_seconds':(local-due).total_seconds(),
            'started_after_noon':local > due.replace(hour=12)}


def durable_record(outbox, key, payload):
    """Publish complete JSON atomically without replacing an existing record."""
    if Path(key).name != key or key in {'.', '..'}:
        raise Hold('Flat record names only')
    dest = outbox / (key + '.json')
    fd, name = tempfile.mkstemp(prefix='.'+key+'.', suffix='.tmp', dir=outbox)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        try:
            # Windows rename refuses an existing destination; POSIX rename would
            # overwrite, so use atomic no-replace link creation there instead.
            if os.name == 'nt':
                os.rename(temp, dest)
            else:
                os.link(temp, dest)
        except FileExistsError as exc:
            raise Hold('Private record already exists; no overwrite') from exc
    finally:
        temp.unlink(missing_ok=True)


def notify(outbox, key, payload):
    """Local outbox only; deliberately no send/ack API."""
    durable_record(outbox, key, payload)


def execute(bridge, config, baseline, rules, state_root, *, now, base_revision,
            acquisition=None, mode='offline'):
    """Internal orchestration; acquisition callback is the existing bounded P1 parent."""
    if mode not in {'offline', 'approved_acquisition'} or (acquisition is None) != (mode == 'offline'):
        raise Hold('Execution mode and acquisition disagree')
    timing = period(now)
    sources = weekly.validate_plan(config)
    rows = continuous.manifest(config, 'kyoto')
    root = PrivateOutput(state_root).root
    cas = Path(bridge.store.root).resolve(strict=True)
    weekly.assert_owner_only(root); weekly.assert_owner_only(cas)
    if root == cas or root in cas.parents or cas in root.parents:
        raise Hold('Periodic state must not overlap CAS')
    identity = {'adapter':'kyoto-weekly-v1', 'mode':mode, 'manifest_sha256':digest(rows),
                'snapshot_root':str(cas), 'schedule':'Monday 09:00 JST'}
    with weekly.single_run(root):
        binding = root/'periodic_identity.json'
        if binding.exists():
            if load(binding) != identity:
                raise Hold('Periodic identity mismatch; offline and live state must be separate')
        else:
            if any(p.name != 'weekly.lock' for p in root.iterdir()):
                raise Hold('Use an empty dedicated state; never adopt existing monitoring state')
            PrivateOutput(root).json(binding.name, identity)
        if (root/'cycles'/timing['cycle_key']).exists():
            raise Hold('Week already reserved; no automatic retry')
        # Only live acquisition needs connectivity. Cached OS status is not proof
        # that the source is reachable; failures after reservation remain terminal.
        if acquisition is not None:
            connection = local_connectivity()
            if connection != 'online':
                waiting = {**timing, 'state':'waiting_for_network',
                    'connectivity':connection, 'state_advanced':False,
                    'new_get_requests':0, 'cycle_reserved':False,
                    'public_writes':0, 'previous_state_retained':True}
                # Dedicated diagnostic only; never replace state.json or touch CAS.
                weekly.atomic_json(root/'network_wait.json', waiting)
                return waiting
        for name in ('cycles', 'outbox'):
            child = root/name
            if child.is_symlink() or (child.exists() and child.resolve().parent != root):
                raise Hold('Private state redirection refused')
            child.mkdir(mode=0o700, exist_ok=True)
            weekly.assert_owner_only(child)
        output = root/'cycles'/timing['cycle_key']
        try:
            output.mkdir(mode=0o700)  # Persistent reservation before GET; never cleared.
        except FileExistsError as exc:
            raise Hold('Week already reserved; no automatic retry') from exc
        weekly.assert_owner_only(output)
        out = PrivateOutput(output)
        durable_record(output, 'reservation', {**identity, **timing,
            'limits':{'requests':3, 'bytes':6291456, 'per_url_bytes':2097152,
                      'child_wall_seconds':10, 'tls':True, 'redirects':0, 'retries':0}})
        prior = load(root/'state.json') if (root/'state.json').exists() else {'monitor':{}, 'seen_reviews':{}}
        acquired = None
        def record_notice(payload):
            try:
                notify(root/'outbox', timing['cycle_key'], payload)
            except Exception as notice_error:
                if not (output/'outbox_failure.json').exists():
                    out.json('outbox_failure.json', {'reason':str(notice_error),
                        'operator_action_required':True})
                raise
        try:
            bridge.store.verify_integrity()
            if acquisition is not None:
                acq = output/'acquisition'; acq.mkdir(mode=0o700); weekly.assert_owner_only(acq)
                acquired = acquisition(sources, acq)
                # P1Bridge caches its index; worker processes append to the store.
                bridge.store.verify_integrity()
                bridge.index = bridge.store.read_index()
            result, _ = run_trial(bridge, config, baseline, rules, output,
                previous=prior.get('monitor'), base_revision=base_revision,
                acquisition=acquired, seen_reviews=prior.get('seen_reviews', {}),
                city='kyoto', allowed=config['cities']['kyoto']['policy_ids'])
            status = load(output/'run_status.json')
            weekly.review_index(output, status)
            stopped = status['state'] == 'stopped_no_public_change'
            reviews = status.get('new_reviews', {})
            observations = []
            for row in rows:
                doc = result['state'].get('documents', {}).get(row['official_url'], {})
                observations.append({**row, 'sha256':doc.get('sha256'),
                    'events':[e for e in result['document_events'] if e['source_url']==row['official_url']],
                    'confirmed_fact':'Source observation only; policy effect requires human review'})
            out.json('observations.json', observations)
            summary = {**timing, 'mode':mode, 'state':status['state'],
                'new_review_count':len(reviews), 'public_writes':0, 'external_notifications':0,
                'new_get_requests':0 if acquired is None else acquired['new_get_requests'],
                'previous_state_retained':stopped}
            if stopped or reviews:
                record_notice({**summary,
                    'kind':'failure' if stopped else 'review_pending',
                    'reviews':reviews, 'observations':observations,
                    'publication_authorized':False})
            # Notification must be durable before advancing the last-good pointer.
            advanced = weekly.commit_success(root, output, prior, result['state'], status)
        except Exception as exc:
            failure = {**timing, 'kind':'failure', 'reason':str(exc),
                'previous_state_retained':True, 'public_writes':0,
                'external_notifications':0, 'publication_authorized':False}
            out.json('failure.json', failure)
            try:
                if not (root/'outbox'/(timing['cycle_key']+'.json')).exists():
                    record_notice(failure)
            except Exception:
                pass  # record_notice already preserved the first outbox diagnostic.
            raise
        summary['state_advanced'] = advanced
        # A receipt-write failure must not be misreported as a rolled-back state commit.
        out.json('cycle_result.json', summary)
        return summary


def run(runtime, *, acquire=False, now=None):
    continuous.configure_shell(runtime)
    root, paths, config = weekly.validate_runtime(runtime, reuse_saved=not acquire)
    if runtime.get('city') != 'kyoto':
        raise Hold('Only Kyoto is approved for this adapter')
    for module in (__file__, continuous.__file__):
        if not any(Path(s['path']).resolve()==Path(module).resolve() for s in runtime['code_files']):
            raise Hold('Periodic and continuous code must be pinned')
    if acquire and runtime.get('periodic_enabled') is not True:
        raise Hold('Periodic acquisition requires separate private activation approval')
    bridge = weekly.P1Bridge(runtime['p1_code_root'], runtime['snapshot_root'])
    callback = None
    if acquire:
        callback = lambda sources, output: weekly.capture_sources(runtime['p1_code_root'],
            runtime['snapshot_root'], sources, output, authorized=True, refresh=True)
    return execute(bridge, config, load(paths['baseline']), load(paths['rules']), root,
        now=now or datetime.now(timezone.utc), base_revision=runtime['base_revision'],
        acquisition=callback, mode='approved_acquisition' if acquire else 'offline')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--acquire', action='store_true', help='Requires separate operational GO and private activation')
    args = parser.parse_args()
    runtime = load(args.runtime)
    continuous.configure_shell(runtime)
    weekly.assert_owner_only(args.runtime)
    result = run(runtime, acquire=args.acquire)
    print(json.dumps(result, ensure_ascii=False))
    if not result['state_advanced'] and result['state'] != 'waiting_for_network':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
