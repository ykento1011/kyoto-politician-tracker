"""Disabled Stage 2 composition. Synthetic adapters only; no OS/CLI entry point.

An immutable plan links one fixed leaf launch, the parent journal and an offline
restoration request. It never applies rules, generates an operator approval or
authorizes recovery. A live contained-worker provisioner remains a separate gate.
"""
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time

from .launch_contract import FixedLaunch, _spec, simulate_fixed_launch
from .projection import Hold
from .stage2_guard import _record, supervise, publish_success, restore_evidence

LIVE_FLOW_ENABLED = False


def plan_bytes(spec, run_id, restore_script_sha256):
    """Deterministic proposal bytes, never a source or human approval receipt."""
    _spec(spec)
    if (not re.fullmatch('[0-9a-f]{32}', run_id)
            or not re.fullmatch('[0-9a-f]{64}', restore_script_sha256)):
        raise Hold('Fixed run and restoration script SHA required')
    prefix = 'GikaiMikata-Stage2-' + run_id
    return json.dumps({'schema_version': 1, 'run_id': run_id,
        'synthetic': True, 'live_enabled': False, 'fixed_launch': asdict(spec),
        'restore_script_sha256': restore_script_sha256,
        'network_plan': {'scope': 'whole_host', 'profiles': 'Any',
            'ipv4': True, 'ipv6': True, 'protocol': 'Any',
            'redirect_retry': False, 'automatic_apply': False},
        'added_rules': [{'name': prefix+'-'+d, 'direction': d}
                        for d in ('Inbound', 'Outbound')]},
        sort_keys=True).encode()


class _BudgetAPI:
    """Only delegates to a supplied synthetic API, checking the shared budget."""
    simulation_only = True

    def __init__(self, api, clock, deadline, cleanup_reserve):
        self.api, self.clock, self.deadline = api, clock, deadline
        self.reserve = cleanup_reserve
        self.closed = False
        self.terminated = False

    def __getattr__(self, name):
        method = getattr(self.api, name)
        def call(*args, **kwargs):
            cleanup = name in ('terminate_and_confirm', 'close_handles')
            available = self.deadline-self.clock()-(0 if cleanup else self.reserve)
            if available <= 0 and not cleanup:
                raise Hold('Shared Stage 2 work budget expired')
            if name == 'wait':
                # Leaf wait cannot consume the parent's cleanup reserve.
                kwargs['timeout_seconds'] = min(kwargs['timeout_seconds'], max(0, available))
            result = method(*args, **kwargs)
            if name == 'terminate_and_confirm': self.terminated = result is True
            if name == 'close_handles': self.closed = True
            if self.clock() >= self.deadline-(0 if cleanup else self.reserve):
                raise Hold('Shared Stage 2 budget exceeded during API call')
            return result
        return call


class _LaunchWorker:
    """Synchronous synthetic worker; explicitly not real Windows containment."""
    simulation_only = True

    def __init__(self, spec, api, run_id, plan_sha, clock, deadline):
        self.spec, self.run_id, self.plan_sha = spec, run_id, plan_sha
        self.api = _BudgetAPI(api, clock, deadline, 2)
        self.report = None
        self.consumed = False

    def start_verification(self):
        if self.consumed: raise Hold('Single launch already consumed')
        self.consumed = True
        result = simulate_fixed_launch(self.spec, self.api, simulation=True)
        if result.get('image_verified') is not True or result.get('exit_code') != 0:
            raise Hold('Fixed launch evidence incomplete')
        self.report = dict(run_id=self.run_id, plan_sha256=self.plan_sha,
            image_verified=True, process_exited=True, all_descendants_exited=True,
            validation_complete=self.api.closed)

    def wait_for_result(self, *, timeout_seconds): return self.report
    def confirm_empty_job(self, *, timeout_seconds):
        return self.report is not None and self.api.closed
    def close_handles(self, *, timeout_seconds): return self.api.closed
    def kill_and_confirm(self, *, timeout_seconds):
        # Leaf cleanup already ran. Never terminate via closed/reused handles.
        return self.api.closed and (self.report is not None or self.api.terminated)


def simulate_stage2(root, spec, api, *, run_id, expected_plan_sha256,
                    restore_script, expected_restore_sha256,
                    simulation=False, clock=time.monotonic):
    """One local synthetic flow, no Firewall calls and no automatic restoration.

    Caller supplies an empty nonproduction scratch. All journal writes are under
    it. Expected hashes are fixed inputs, not machine-generated human approvals.
    Native adapters are rejected before writes; LIVE_FLOW_ENABLED is not a switch
    to a real mode. Real provisioning/OS isolation must be separately authorized.
    """
    if (LIVE_FLOW_ENABLED is not False or simulation is not True
            or getattr(api, 'simulation_only', None) is not True
            or not isinstance(spec, FixedLaunch)):
        raise Hold('Live Stage 2 flow disabled')
    started = clock()
    _spec(spec)
    root = Path(root).resolve(strict=True)
    if any(root.iterdir()): raise Hold('Fresh flow scratch required; never retry a consumed run')
    body = plan_bytes(spec, run_id, expected_restore_sha256)
    digest = sha256(body).hexdigest()
    if (digest != expected_plan_sha256
            or sha256(Path(restore_script).read_bytes()).hexdigest() != expected_restore_sha256):
        raise Hold('Fixed plan or offline restoration script differs')
    deadline = started+min(10, spec.timeout_seconds)
    journal = root/'journal'
    try:
        # The plan is outside the empty supervisor journal, but bound by its SHA.
        _record(root, 'plan.json', json.loads(body))
        actual = (root/'plan.json').read_bytes()
        if actual != body: raise Hold('Plan bytes differ from fixed proposal')
        plan_sha = sha256(actual).hexdigest()
        journal.mkdir(exist_ok=False)
        budget = math.floor(deadline-clock())
        if budget < 3: raise Hold('Insufficient total Stage 2 budget after preflight')
        worker = _LaunchWorker(spec, api, run_id, plan_sha, clock, deadline)
        result = supervise(journal, run_id, plan_sha, worker,
            clock=clock, total_seconds=budget, simulation=True)
        if clock() >= deadline: raise Hold('Total flow deadline exceeded')
        request = {'schema_version': 1, 'run_id': run_id,
            'plan_sha256': plan_sha, 'proposal_sha256': digest,
            'restore_script_sha256': expected_restore_sha256,
            'plan_file': 'plan.json', 'journal_directory': 'journal',
            'operator_acknowledgement': 'NOT_PROVIDED',
            'automatic_restore': False, 'restoration_authorized': False,
            'real_execution_authorized': False, 'mode': 'synthetic_only'}
        _record(root, 'restore_request.json', request)
        if clock() >= deadline: raise Hold('Restore handoff missed total deadline')
        # Withhold the supervisor capability until the entire flow returns on
        # time. A late handoff + failed HOLD write must not leave restoration-
        # eligible success evidence. Never serialize this private capability.
        return {**request, '_supervisor_result': result}
    except Exception as exc:
        for target in (root, journal) if journal.exists() else (root,):
            try: _record(target, 'HOLD.json', {'run_id': run_id,
                'state': 'HOLD', 'restore_prohibited': True,
                'reason': type(exc).__name__, 'automatic_restore': False})
            except Exception: pass  # Absent handoff/operator ack never grants recovery.
        raise Hold('Stage 2 integration HOLD; keep isolation, no automatic restore') from exc


def commit_flow_success(root, result):
    """Post-return audit only; no human acknowledgement or OS authorization."""
    root = Path(root)
    if (root/'HOLD.json').exists(): raise Hold('Flow HOLD blocks completion commit')
    saved = json.loads((root/'restore_request.json').read_bytes())
    public = {k:v for k,v in result.items() if k != '_supervisor_result'}
    if saved != public or sha256((root/'plan.json').read_bytes()).hexdigest() != saved['plan_sha256']:
        raise Hold('Flow handoff identity mismatch')
    publish_success(root/'journal', result['_supervisor_result'])
    return restore_evidence(root/'journal', saved['run_id'], saved['plan_sha256'])
