"""Explicit Kobe HTML acquisition/processing connection; disabled until approved.

The public entry is kobe_acquisition. connect also retains synthetic test seams.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from . import weekly
from .operations import receipt_identity
from .p1_bridge import P1Bridge
from .projection import Hold

URL = 'https://www.city.kobe.lg.jp/z/shikaijimukyoku/giann_etc/r8/yosantokubetsu.html'
SOURCE = {'id': 'kobe-r8-budget-committee', 'url': URL, 'fiscal_year': 2026,
          'document_kind': 'budget_index', 'media_type': 'html',
          'policy_ids': ['KOBE-M01'], 'max_bytes': 2097152,
          'title': '令和8年度予算特別委員会索引'}
LIMITS = {'get_per_url': 1, 'max_received_bytes': 2097152,
          'max_total_received_bytes': 2097152, 'max_accepted_bytes': 2097151,
          'wall_timeout_seconds': 10, 'tls_verify': True, 'redirects': 0,
          'retries': 0, 'link_following': 0}
JST = timezone(timedelta(hours=9))


def read_pinned(spec):
    return json.loads(weekly.pinned_input(spec).read_text(encoding='utf-8-sig'))


def aware(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.utcoffset() is None:
            raise ValueError('timezone missing')
        return result
    except (ValueError, AttributeError, TypeError) as exc:
        raise Hold('Explicit timezone-aware time required') from exc


def directory(value):
    """Reject redirected paths before resolving; reuse existing ACL enforcement."""
    path = Path(value).absolute()
    for ancestor in (path, *path.parents):
        info = ancestor.lstat()
        if ancestor.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise Hold('Reparse/symlink storage is not allowed')
    if not path.is_dir():
        raise Hold('Pre-existing approved directory required')
    weekly.assert_owner_only(path)
    return path.resolve(strict=True)


def clock():
    return datetime.now(timezone.utc)


def validate(contract, approval, now, *, own_attempt=None):
    if (contract.get('mode') != 'kobe-html1-reobservation-v1' or
            contract.get('city') != 'kobe' or contract.get('source') != SOURCE or
            contract.get('limits') != LIMITS):
        raise Hold('Exact Kobe HTML1 contract required')
    if contract.get('enabled') is not True or contract.get('network_enabled') is not True:
        raise Hold('Candidate is disabled')
    if now.utcoffset() is None:
        raise Hold('Aware start clock required')
    local = now.astimezone(JST)
    week = (local.date() - timedelta(days=local.weekday())).isoformat()
    # The accepted saved-cycle week can never be reopened by this candidate.
    if week == '2026-11-16':
        raise Hold('Known consumed Kobe cycle week')
    expected = {key: contract[key] for key in
                ('city', 'source', 'series_root', 'cas_root', 'p1_code_root')}
    if (any(approval.get(k) != v for k, v in expected.items()) or
            approval.get('week') != week or approval.get('approved') is not True or
            not approval.get('approval_reference') or
            not aware(approval.get('valid_from')) <= now < aware(approval.get('valid_until'))):
        raise Hold('Week/source/root/validity approval mismatch')
    root = directory(contract['series_root'])
    cas = directory(contract['cas_root'])
    directory(contract['p1_code_root'])
    if root == cas or root in cas.parents or cas in root.parents:
        raise Hold('Reservation root and CAS must be separate')
    # Canonical root is controlled by the separately pinned deployment contract,
    # never by a run name, output directory or the per-week approval.
    identity = read_pinned(contract['series_identity'])
    expected_identity = {'city': 'kobe', 'url': URL, 'series_root': str(root), 'cas_root': str(cas)}
    if 'processing_state_root' in contract:
        expected_identity['processing_state_root'] = str(directory(contract['processing_state_root']))
    if identity != expected_identity:
        raise Hold('Canonical series identity mismatch')
    if not contract.get('legacy_reservations') or not contract.get('legacy_state_roots'):
        raise Hold('Known legacy evidence must not be omitted')
    for spec in contract['legacy_reservations']:
        legacy = read_pinned(spec)
        if legacy.get('url') != URL:
            raise Hold('Legacy reservation identity mismatch')
        terminal = read_pinned(spec['termination_evidence'])
        if (terminal.get('reservation_sha256') != spec['sha256'] or
                terminal.get('termination_confirmed') is not True or
                not terminal.get('approval_reference')):
            raise Hold('Legacy termination is unknown')
    for value in contract['legacy_state_roots']:
        old = directory(value)
        if list(old.rglob('*.lock')) or (old / 'cycles' / week).exists():
            raise Hold('Legacy lock or consumed cycle')
    for attempt in root.iterdir():
        if attempt.name == 'weekly.lock':
            continue
        if attempt == own_attempt:
            continue
        if not attempt.is_dir() or not (attempt/'reservation.json').is_file():
            raise Hold('Unknown or interrupted reservation entry')
        end = attempt / 'completed.json'
        if not end.is_file():
            raise Hold('Previous acquisition outcome/termination unresolved')
        # Failure records deliberately never count as successful completion.
        if json.loads(end.read_text()).get('termination_confirmed') is not True:
            raise Hold('Previous termination unresolved')
    return root, cas, week


def append_json(path, value):
    # Exclusive create: failed/unknown attempts cannot be overwritten or retried.
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def acquisition_scope():
    return dict(profile='kobe_html1_reobservation', city_code='kobe',
        policy_ids=['KOBE-M01'], allowed_hosts=['www.city.kobe.lg.jp'],
        enabled=True, network_enabled=True, sources=[dict(SOURCE)],
        max_requests=1, max_requests_by_media={'html':1, 'pdf':0},
        max_total_bytes=2097152, timeout_seconds=10, tls_verify=True,
        redirects=0, retries=0)


def validate_ticket(scope, storage, snapshot_root, output):
    """Parent AND worker check the pinned authorization and permanent reservation.

    This is a distinct scope, not a skip flag on the old permanent-URL contract.
    No binding, approval, or legacy marker is generated here.
    """
    contract = read_pinned(storage['connection_contract'])
    approval = read_pinned(storage['connection_approval'])
    if approval.get('contract_sha256') != storage['connection_contract']['sha256']:
        raise Hold('Ticket contract PIN mismatch')
    out = Path(storage['attempt_output']).resolve(strict=True)
    root, cas, week = validate(contract, approval, clock(), own_attempt=out)
    expected = root / sha256(('kobe\n'+URL+'\n'+week).encode()).hexdigest()
    if (scope != acquisition_scope() or out != expected or
            Path(storage['state_root']).resolve() != root or
            Path(snapshot_root).resolve() != cas or
            Path(output).resolve() not in (out, out/sha256(URL.encode()).hexdigest()[:20])):
        raise Hold('Acquisition ticket root/output/scope mismatch')
    reservation = json.loads((out/'reservation.json').read_text())
    if any(reservation.get(k) != v for k,v in dict(city='kobe', url=URL, week=week,
            contract_sha256=storage['connection_contract']['sha256'],
            approval_sha256=storage['connection_approval']['sha256'], retry_allowed=False).items()):
        raise Hold('Acquisition reservation mismatch')
    if (out/'completed.json').exists() or (out/'failure.json').exists():
        raise Hold('Acquisition attempt already terminal')
    return root


def run_connected(runtime):
    """Concrete adapters: existing acquisition parent -> exact CAS -> real cycle.

    Called only after the stdlib dependency/input preflight in the public entry.
    External boundaries (worker/P1) can be replaced in tests; adapters are real.
    """
    from . import acquire as parent, continuous, offline_weekly
    contract_spec = runtime['connection_contract']
    approval_spec = runtime['connection_approval']
    contract = read_pinned(contract_spec)
    continuous.configure_shell(runtime)
    config, baseline = read_pinned(runtime['config']), read_pinned(runtime['baseline'])
    if weekly.pinned_input(runtime['profile']) != offline_weekly.PROFILE.resolve():
        raise Hold('Wrong processing profile')
    local, sources = offline_weekly.prepare(config, 'kobe')
    if len(sources) != 1 or any(sources[0].get(k) != v for k,v in SOURCE.items()):
        raise Hold('Processing/acquisition source disagreement')
    state = directory(contract['processing_state_root'])
    if str(state) != runtime['state_root'] or runtime['city'] != 'kobe':
        raise Hold('Processing state/city binding mismatch')
    root, cas, week = validate(contract, read_pinned(approval_spec), clock())
    if any(a == b or a in b.parents or b in a.parents
           for a,b in ((state,root),(state,cas))):
        raise Hold('Processing state must be separate from acquisition and CAS')
    identity = read_pinned(contract['series_identity'])
    if identity.get('processing_state_root') != str(state):
        raise Hold('Canonical processing state missing')
    if (state/'weekly.lock').exists() or (state/'cycles'/week).exists():
        raise Hold('Processing state locked or cycle consumed')
    if (baseline.get('city_code') != 'kobe' or
            not runtime.get('base_revision') or runtime.get('network_enabled') is not False):
        raise Hold('Private processing contract mismatch')

    def acquisition(**kw):
        storage = dict(connection_contract=contract_spec, connection_approval=approval_spec,
            attempt_output=str(kw['output']), state_root=str(root), snapshot_root=str(cas))
        result = parent.capture_sources(kw['p1_code_root'], cas, [kw['source']], kw['output'],
            authorized=True, refresh=True, media_type='html', scope=acquisition_scope(), storage=storage)
        child = kw['output']/sha256(URL.encode()).hexdigest()[:20]
        evidence = json.loads((child/'termination.json').read_text())
        if evidence.get('termination_confirmed') is not True:
            raise Hold('worker_termination_unknown: cycle not started')
        if result['stopped'] or evidence.get('returncode') != 0:
            raise Hold('acquisition_failed: cycle not started')
        if (evidence.get('outcome_sha256') !=
                sha256((child/'worker_outcome.json').read_bytes()).hexdigest() or
                evidence.get('intent_sha256') != sha256((child/'single_get_started.json').read_bytes()).hexdigest()):
            raise Hold('Acquisition termination evidence identity mismatch')
        def pin(name):
            path=kw['output']/name
            return {'path':str(path), 'sha256':sha256(path.read_bytes()).hexdigest()}
        return dict(termination_confirmed=True, acquisition_receipt=pin('acquisition_result.json'),
                    acquisition_preflight=pin('preflight.json'))

    def process(**kw):
        # One evaluation clock AFTER acquisition, distinct from overall start.
        evaluated_at = clock()
        bridge = kw['bridge']
        def exact_observation():
            current = bridge.store.read_index()
            doc = current['documents'].get(URL)
            if not doc or doc['versions'][-1]['sha256'] != kw['sha256']:
                raise Hold('Acquired version changed before cycle')
            if bridge.record(URL,kw['sha256'])[0]['document_id'] != kw['document_id']:
                raise Hold('Processing document identity mismatch')
            append_json(state/'cycles'/kw['cycle_key']/'acquisition_handoff.json',
                        {**kw['acquisition_audit'], 'processing_started_at':evaluated_at.isoformat()})
            return offline_weekly.inspect_saved(bridge, sources)
        result = continuous.cycle(bridge, local, baseline, [], state, city='kobe',
            cycle_key=kw['cycle_key'], base_revision=runtime['base_revision'],
            offline_sources=sources, observation_check=exact_observation, evaluated_at=evaluated_at)
        return result
    return connect(contract_spec, approval_spec, acquire=acquisition, process=process)


def connect(contract_spec, approval_spec, *, acquire, process):
    """Shared orchestration; run_connected supplies the concrete adapters.

    acquire writes the standard acquisition_result/preflight under its fixed
    output and must confirm worker termination. process receives only the exact
    receipt-verified version, with no permission to acquire or publish.
    """
    contract, approval = read_pinned(contract_spec), read_pinned(approval_spec)
    if approval.get('contract_sha256') != contract_spec['sha256']:
        raise Hold('Approval is not bound to the deployment contract')
    root, _, _ = validate(contract, approval, clock())
    with weekly.single_run(root):
        return _connect_locked(contract_spec, approval_spec, contract, approval, acquire, process)


def _connect_locked(contract_spec, approval_spec, contract, approval, acquire, process):
    now = clock()
    root, cas, week = validate(contract, approval, now)
    key = sha256(('kobe\n' + URL + '\n' + week).encode()).hexdigest()
    output = root / key
    try:
        output.mkdir()  # Atomic; independent of run name, scope revision or caller.
    except FileExistsError as exc:
        raise Hold('This source/week was already attempted') from exc
    append_json(output/'reservation.json', {'city': 'kobe', 'url': URL, 'week': week,
        'started_at': now.isoformat(), 'contract_sha256': contract_spec['sha256'],
        'approval_sha256': approval_spec['sha256'], 'retry_allowed': False})
    phase = 'acquisition'
    result = None
    try:
        # Do not carry an earlier week/validity check across slow validation or
        # the weekly boundary. This only ignores our own already-consumed slot.
        _, _, current_week = validate(contract, approval, clock(), own_attempt=output)
        if current_week != week:
            raise Hold('Week changed before acquisition')
        acquisition_started = clock()
        local_start = acquisition_started.astimezone(JST)
        if (not aware(approval['valid_from']) <= acquisition_started < aware(approval['valid_until']) or
                (local_start.date() - timedelta(days=local_start.weekday())).isoformat() != week):
            raise Hold('Approval expired during validation')
        outcome = acquire(source=dict(SOURCE), limits=dict(LIMITS), output=output,
                          cas_root=cas, p1_code_root=Path(contract['p1_code_root']))
        acquisition_finished = clock()
        if outcome.get('termination_confirmed') is not True:
            raise Hold('Worker termination unknown')
        # Recreate after acquisition, rather than reuse the pre-acquisition index.
        bridge = P1Bridge(contract['p1_code_root'], cas, city_capable=True)
        if Path(bridge.store.root).resolve() != cas:
            raise Hold('P1 uses a different CAS')
        receipt_spec = outcome['acquisition_receipt']
        preflight_spec = outcome['acquisition_preflight']
        for spec, name in ((receipt_spec, 'acquisition_result.json'),
                           (preflight_spec, 'preflight.json')):
            if Path(spec['path']).absolute() != output/name:
                raise Hold('Receipt path outside reserved output')
        receipt, preflight = read_pinned(receipt_spec), read_pinned(preflight_spec)
        if preflight.get('sources') != [SOURCE]:
            raise Hold('Unexpected acquisition source selection')
        if any(preflight.get('limits', {}).get(k) != v for k, v in LIMITS.items()):
            raise Hold('Acquisition limits differ')
        if (receipt.get('new_get_requests') != 1 or
                receipt.get('new_get_requests_max') != 1):
            raise Hold('Exactly one completed GET receipt required')
        spec = {'city': 'kobe', 'policy_ids': ['KOBE-M01'],
                'document_id': 'kobe-doc-' + sha256(URL.encode()).hexdigest()[:24],
                'acquisition_receipt': receipt_spec, 'acquisition_preflight': preflight_spec}
        version, document, audit = receipt_identity(spec, SOURCE, bridge)
        observed = aware(audit['acquisition_observed_at'])
        if (not acquisition_started <= observed <= acquisition_finished or
                not aware(approval['valid_from']) <= observed < aware(approval['valid_until']) or
                acquisition_finished >= aware(approval['valid_until']) or
                (observed.astimezone(JST).date() - timedelta(
                    days=observed.astimezone(JST).weekday())).isoformat() != week):
            raise Hold('Receipt observation is outside this authorized acquisition attempt')
        rec, _ = bridge.record(URL, version)
        if rec.get('fiscal_year') != 2026 or rec.get('mime_type') != 'text/html':
            raise Hold('Wrong CAS year or medium')
        append_json(output/'verified_handoff.json', audit)
        phase = 'private_cycle'
        result = process(bridge=bridge, source=dict(SOURCE), sha256=version,
                         document_id=document, acquisition_audit=audit,
                         cycle_key=week, network_enabled=False, publication_authorized=False)
        if (type(result.get('state_advanced')) is not bool or
                type(result.get('public_writes')) is not int or result['public_writes'] != 0 or
                type(result.get('network_requests')) is not int or result['network_requests'] != 0):
            raise Hold('Private processing incomplete or communication/publication nonzero/unknown')
        if not result['state_advanced'] and result.get('state') != 'stopped_no_public_change':
            raise Hold('Unknown processing outcome')
        phase = 'completion_receipt'
        append_json(output/'completed.json', {'termination_confirmed': True,
            'receipt_sha256': receipt_spec['sha256'], 'private_result': result,
            'publication_authorized': False})
        return {'state': 'private_result_saved' if result['state_advanced'] else 'content_hold',
                'private_result': result, 'week': week, 'output': str(output),
                'acquisition_audit': audit, 'public_writes': 0}
    except Exception as exc:
        # A final receipt failure must not pretend an already committed cycle
        # was rolled back. Unknown cycle exceptions require its own evidence.
        retained = True if phase == 'acquisition' else (
            not result['state_advanced'] if result is not None and
            type(result.get('state_advanced')) is bool else None)
        append_json(output/'failure.json', {'reason': str(exc), 'retry_allowed': False,
            'phase': phase, 'previous_state_retained': retained, 'private_result': result})
        raise
