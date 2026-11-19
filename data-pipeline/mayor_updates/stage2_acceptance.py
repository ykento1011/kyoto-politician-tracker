"""One Stage 2 transaction, injected OS ports; live execution stays disabled.

Ports are an observation/privilege boundary, NOT evidence produced by this
module. Synthetic receipts must never be reused as Windows acceptance evidence.
The existing native worker flow is reused through WorkerFlow below.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import time

from .projection import Hold
from .stage2_guard import _record

LIVE_ACCEPTANCE_ENABLED = False
CONNECTION = '0cce9226-69ae-11d9-bed3-505054503030'
PACKET = '0cce9225-69ae-11d9-bed3-505054503030'
PROBES = ('tcp4', 'tcp6', 'dns4', 'dns6', 'system_dns_proxy')
TARGETS = {
    'tcp4': ('1.1.1.1', 443, 6),
    'tcp6': ('2606:4700:4700::1111', 443, 6),
    'dns4': ('1.1.1.1', 53, 17),
    'dns6': ('2606:4700:4700::1111', 53, 17),
}


def require(condition, reason):
    if not condition:
        raise Hold(reason)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def audit_ok(snapshot):
    require(type(snapshot) is dict and set(snapshot) == {CONNECTION, PACKET}, 'Audit shape')
    for value in snapshot.values():
        require(type(value) is dict and set(value) == {'success', 'failure'} and
                all(type(v) is bool for v in value.values()), 'Audit bit types')


def identity(value):
    require(type(value) is dict and type(value.get('pid')) is int and value['pid'] > 0 and
            type(value.get('started')) is int and value['started'] > 0 and
            bool(value.get('image')) and re.fullmatch(r'S-1-[0-9-]+', value.get('sid', '')) and
            value.get('retained_process_handle') is True and
            value.get('image_verified') is True, 'Process/token identity unavailable')
    return {key: value[key] for key in ('pid', 'started', 'image', 'sid')}


def archive_ok(archive, first, last):
    require(type(archive) is dict and archive.get('readback') is True and
            archive.get('owner_only') is True and archive.get('complete') is True and
            archive.get('first_record') <= first and archive.get('last_record') >= last and
            re.fullmatch('[0-9a-f]{64}', archive.get('sha256', '')) and
            archive.get('missing_records') == [], 'Security EVTX preservation incomplete')


class WorkerFlow:
    """Connect the pre-existing worker/Job/HOLD implementation, never replace it.

    args contains the already pinned native plan, worker/leaf specs and code PINs.
    This bridge creates no token, operator acknowledgement or source activation.
    OS ports must separately retain whole-job termination evidence on exceptions.
    """
    simulation_only = False

    def __init__(self, root, spec, args):
        self.root, self.spec, self.args = root, spec, args

    def run(self):
        from .stage2_flow import run_native_stage2, commit_flow_success
        result = run_native_stage2(self.root, self.spec, **self.args)
        commit_flow_success(self.root, result)  # validates the committed journal
        return self.completion(self.root)

    @staticmethod
    def completion(root):
        # Revalidate the existing completion capability before deriving the
        # whole-Job result; never infer it from a caller-provided boolean alone.
        from .stage2_guard import restore_evidence
        done = json.loads((Path(root)/'journal/termination_confirmed.json').read_bytes())
        restore_evidence(Path(root)/'journal', done['run_id'], done['plan_sha256'])
        return {**done, 'all_descendants_exited': done['termination_confirmed']}


def run(root, plan, ports, worker, *, simulation=False, clock=time.monotonic):
    """Finish normal or HOLD with independent audit rollback.

    Every OS port receives a deadline. A blocking native call is NOT bounded by
    Python checks: a live adapter needs its independent local restoration guard.
    No live adapter or command-line activation switch is supplied here.
    """
    require(simulation is True and getattr(ports, 'simulation_only', None) is True and
            getattr(worker, 'simulation_only', None) is True,
            'Live Stage 2 acceptance source-disabled')
    require(type(plan) is dict and re.fullmatch('[0-9a-f]{32}', plan.get('run_id', '')) and
            re.fullmatch('[0-9a-f]{64}', plan.get('native_plan_sha256', '')) and
            re.fullmatch(r'S-1-5-21-[0-9-]+-1004', plan.get('sid', '')) and
            plan.get('audit_seconds') == 60 and type(plan['audit_seconds']) is int and
            plan.get('event_limit') == 64 and type(plan['event_limit']) is int,
            'Fixed Stage 2 plan required')
    root = Path(root).resolve(strict=True)
    require(not any(root.iterdir()), 'Fresh isolated journal required; no retry')
    rid = plan['run_id']
    rules = ['GikaiMikata-Stage2-' + rid + '-' + d for d in ('Inbound', 'Outbound')]
    _record(root, 'start.json', {'plan': plan, 'plan_sha256': digest(plan),
                              'synthetic': True, 'real_execution_authorized': False})
    audit_attempted = firewall_attempted = worker_attempted = False
    original = None
    deadline = None
    errors, events, attempts = [], [], []
    status = {'state': 'HOLD', 'synthetic': True, 'audit_restored': False,
              'firewall_restored': False, 'termination_confirmed': False,
              'real_execution_authorized': False, 'automatic_firewall_restore': False}
    seen_records = {}

    def journal(name, body):
        _record(root, name + '.json', body)

    def remaining():
        require(deadline is not None and clock() < deadline, '60 second audit deadline')
        return deadline

    def collect():
        batch = ports.read_denials(rid, limit=64-len(events), deadline=remaining())
        require(type(batch) is dict and batch.get('truncated') is False and
                batch.get('lost') == 0 and type(batch.get('events')) is list,
                'Security evidence loss/overflow')
        for event in batch['events']:
            record = event.get('record_id')
            require(type(record) is int and record > log_start['latest'], 'Record range')
            if record in seen_records:
                require(seen_records[record] == event, 'Conflicting Security record')
                continue
            require(len(events) < 64, '64 event bound')
            seen_records[record] = event
            events.append(event)
        require(len(events) < 64, '64 event safety stop')
        remaining()

    def probe(probe_id, blocked):
        require(len(attempts) < 9, 'Nine probe limit')
        # Reserve before the side effect; a throw consumes the attempt too.
        attempts.append({'id': probe_id, 'blocked': blocked})
        journal('probe_intent_%02d' % len(attempts), attempts[-1])
        result = ports.probe(probe_id, blocked=blocked, run_id=rid,
                             deadline=remaining() if blocked else clock()+1)
        require(result.get('run_id') == rid and result.get('probe_id') == probe_id and
                result.get('blocked') is blocked and
                type(result.get('client_calls')) is int and result['client_calls'] == 1 and
                type(result.get('retries')) is int and result['retries'] == 0 and
                type(result.get('http_requests')) is int and result['http_requests'] == 0,
                'Probe result binding')
        actor = identity(result['actor'])
        require(actor['sid'] == plan['sid'] and type(result.get('start_tick')) is int and
                type(result.get('end_tick')) is int and
                actor['started'] <= result['start_tick'] <= result['end_tick'],
                'Probe SID/lifetime differs')
        if probe_id in TARGETS:
            require(tuple(result['target']) == TARGETS[probe_id], 'Fixed destination differs')
        else:
            require(result.get('query') == 'stage2-'+rid+'.example.com.' and
                    result.get('resolvers') == preflight['resolvers'], 'DNS query/resolver differs')
        if not blocked:
            require(result.get('reachable') is True, 'Baseline unavailable; not isolation proof')
            journal('probe_result_%02d' % len(attempts), result)
            return
        require(result.get('external_egress') is False, 'Egress or unknown result')
        collect()
        matched = []
        for event in events:
            # Never use the generic ETW header PID or RemoteUserID as token SID.
            if event.get('probe_id') != probe_id:
                continue
            require(event.get('run_id') == rid and event.get('event_id') == 5157 and
                    event.get('filter_id') in filters and
                    event.get('rule_name') == filters[event['filter_id']] and
                    filters[event['filter_id']] == rules[1] and
                    event.get('direction') == 'Outbound' and
                    type(event.get('utc_tick')) is int and
                    result['start_tick'] <= event['utc_tick'] <= result['end_tick'] and
                    event.get('tuple') == result['tuple'], 'Deny/probe/filter binding')
            owner = identity(event['owner'])
            require(owner['started'] <= event['utc_tick'], 'Process created after denial')
            if probe_id == 'system_dns_proxy':
                require(owner == dns and event.get('query') == result['query'], 'DNS service attribution')
            else:
                require(owner == actor, 'PID/start time/image/token SID mismatch')
            matched.append(event)
        require(len(matched) == 1, 'Missing/ambiguous attributable denial')
        if probe_id == 'system_dns_proxy':
            require(result.get('cached') is False and result.get('query_complete') is True and
                    result.get('pending_service_requests') == 0 and
                    type(result.get('service_send_count')) is int and
                    1 <= result['service_send_count'] <= 8 and
                    result.get('service_send_count_verified') is True and
                    identity(result['service_before']) == dns == identity(result['service_after']),
                    'DNS send count/lifetime/completion unproven')
        journal('probe_result_%02d' % len(attempts), result)

    try:
        preflight = ports.preflight(plan)
        require(preflight.get('owner_only') is True and preflight.get('recovery_local') is True and
                preflight.get('source_pins_valid') is True and
                preflight.get('existing_rules_absent') is True and
                preflight.get('gpo_audit_unmanaged') is True and
                preflight.get('bypass_paths_excluded') is True and
                preflight.get('resolvers') and preflight.get('restore_watchdog_ready') is True,
                'PRE-BLOCK prerequisite')
        dns = identity(preflight['dns'])
        require(dns['sid'] == 'S-1-5-20', 'DNS service token SID')
        original = ports.read_audit()
        audit_ok(original)
        require(original == {CONNECTION: {'success': False, 'failure': False},
                             PACKET: {'success': False, 'failure': False}}, 'Audit original differs')
        log_start = ports.log_boundary()
        require(log_start.get('enabled') is True and log_start.get('maximum_bytes') == 20971520 and
                type(log_start.get('oldest')) is int and type(log_start.get('latest')) is int,
                'Security log original')
        archive = ports.export_security('before', rid)
        archive_ok(archive, log_start['oldest'], log_start['latest'])
        journal('baseline', {'audit': original, 'log': log_start, 'archive': archive,
                             'preflight': preflight})
        for name in PROBES[:-1]:
            probe(name, False)
        deadline = clock()+60
        journal('audit_intent', {'guid': CONNECTION, 'failure': True, 'deadline': deadline,
                                 'restore': original, 'packet_drop_unchanged': True})
        audit_attempted = True
        ports.set_failure(CONNECTION, True, deadline=deadline)
        temporary = ports.read_audit()
        audit_ok(temporary)
        require(temporary == {CONNECTION: {'success': False, 'failure': True},
                              PACKET: original[PACKET]}, 'Temporary audit readback')
        journal('temporary_audit', temporary)
        journal('firewall_intent', {'exact_names': rules})
        firewall_attempted = True
        # The port verifies both stores and all rule filters, not names alone.
        filters = ports.apply_and_verify_rules(rules, deadline=remaining())
        require(type(filters) is dict and len(filters) >= 2 and
                set(filters.values()) == set(rules) and
                all(type(k) is int and k > 0 for k in filters), 'Filter IDs unbound')
        journal('filter_binding', [{'id': k, 'rule': v} for k, v in filters.items()])
        for name in PROBES:
            probe(name, True)
        remaining()
        worker_attempted = True
        result = worker.run()
        require(result.get('run_id') == rid and result.get('plan_sha256') == plan['native_plan_sha256'] and
                result.get('termination_confirmed') is True and result.get('cleanup_complete') is True and
                result.get('all_descendants_exited') is True, 'Worker/leaf/Job termination incomplete')
        remaining()
        status['termination_confirmed'] = True
        journal('worker_completion', result)
        collect()
        # Operator acknowledgement must come from the local operator port. No
        # success record is a human acknowledgement or automatic recovery grant.
        release = ports.confirm_local_exit(rid, result, deadline=remaining())
        require(release == {'run_id': rid, 'onsite_exit_confirmed': True}, 'Local acknowledgement absent')
        restored = ports.restore_exact_rules_by_operator(rules, deadline=remaining())
        require(restored.get('removed') == rules and restored.get('both_stores_absent') is True and
                restored.get('baseline_unchanged') is True, 'Firewall delta restoration incomplete')
        status['firewall_restored'] = True
        remaining()
        status['state'] = 'PASS'
    except Exception as exc:
        errors.append(type(exc).__name__+': '+str(exc))
        status['state'] = 'HOLD'
        # A failed flow NEVER removes Firewall rules automatically, even if a
        # late whole-Job termination check eventually succeeds.
        if worker_attempted:
            try:
                status['termination_confirmed'] = ports.stop_and_confirm_job() is True
            except Exception as cleanup:
                errors.append('termination: '+str(cleanup))
    finally:
        # Independent of process/Firewall result and journal-writing success.
        if audit_attempted:
            try:
                ports.set_failure(CONNECTION, original[CONNECTION]['failure'], deadline=None)
                after = ports.read_audit()
                audit_ok(after)
                require(after == original and ports.audit_other_settings_unchanged() is True,
                        'Audit restoration/readback differs')
                status['audit_restored'] = True
            except Exception as exc:
                errors.append('audit restore: '+str(exc))
                status['state'] = 'HOLD'
        else:
            status['audit_restored'] = True  # no audit mutation attempted
        if audit_attempted:
            try:
                end = ports.log_boundary()
                saved = ports.export_security('after', rid)
                archive_ok(saved, log_start['latest']+1, end['latest'])
                require(end.get('cleared') is False and end.get('evidence_missing') is False,
                        'Security record gap/clear detected')
                journal('security_evidence', {'before': log_start, 'after': end,
                                              'archive': saved, 'events': events})
            except Exception as exc:
                errors.append('evidence: '+str(exc))
                status['state'] = 'HOLD'
        status.update(errors=errors, client_attempts=len(attempts), event_count=len(events),
                      firewall_may_remain=firewall_attempted and not status['firewall_restored'],
                      audit_attempted=audit_attempted)
        journal('result', status)
    return status
