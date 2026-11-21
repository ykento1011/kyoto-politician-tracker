"""Non-active Kobe HTML connection candidate; no CLI or default live transport.

The two callbacks are integration seams, exercised only with stubs in this PR.
Deployment approval must pin this module, its callers, and both input contracts.
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
          'policy_ids': ['KOBE-M01'], 'max_bytes': 2097152}
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


def validate(contract, approval, now):
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
    if identity != {'city': 'kobe', 'url': URL, 'series_root': str(root),
                    'cas_root': str(cas)}:
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
    for attempt in root.glob('*/reservation.json'):
        end = attempt.parent / 'completed.json'
        if not end.is_file():
            raise Hold('Previous acquisition outcome/termination unresolved')
        # Failure records deliberately never count as successful completion.
        if json.loads(end.read_text()) .get('termination_confirmed') is not True:
            raise Hold('Previous termination unresolved')
    return root, cas, week


def append_json(path, value):
    # Exclusive create: failed/unknown attempts cannot be overwritten or retried.
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def connect(contract_spec, approval_spec, *, now, acquire, process):
    """Candidate orchestration. No live callback is supplied or enabled here.

    acquire writes the standard acquisition_result/preflight under its fixed
    output and must confirm worker termination. process receives only the exact
    receipt-verified version, with no permission to acquire or publish.
    """
    contract, approval = read_pinned(contract_spec), read_pinned(approval_spec)
    if approval.get('contract_sha256') != contract_spec['sha256']:
        raise Hold('Approval is not bound to the deployment contract')
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
    try:
        outcome = acquire(source=dict(SOURCE), limits=dict(LIMITS), output=output,
                          cas_root=cas, p1_code_root=Path(contract['p1_code_root']))
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
        rec, _ = bridge.record(URL, version)
        if rec.get('fiscal_year') != 2026 or rec.get('mime_type') != 'text/html':
            raise Hold('Wrong CAS year or medium')
        append_json(output/'verified_handoff.json', audit)
        result = process(bridge=bridge, source=dict(SOURCE), sha256=version,
                         document_id=document, acquisition_audit=audit,
                         cycle_key=week, network_enabled=False, publication_authorized=False)
        if result.get('state_advanced') is not True:
            raise Hold('Private processing did not advance normally')
        append_json(output/'completed.json', {'termination_confirmed': True,
            'receipt_sha256': receipt_spec['sha256'], 'private_result': result,
            'publication_authorized': False})
        return {'state': 'private_result_saved', 'week': week, 'output': str(output),
                'acquisition_audit': audit, 'public_writes': 0}
    except Exception as exc:
        append_json(output/'failure.json', {'reason': str(exc), 'retry_allowed': False,
                                         'previous_state_retained': True})
        raise
