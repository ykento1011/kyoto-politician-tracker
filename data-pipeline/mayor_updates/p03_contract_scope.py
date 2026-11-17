"""Offline-only, exact-document guard for the retained P-03 contract link.

This does not extend acquire.py/city_scope.py, construct a live transport, or
activate a job. A later live handoff requires separate approval, private storage
binding, durable reservation and the existing parent wall-clock deadline.
The registered year/identity is a retrieval scope, not bill authentication.
"""
from copy import deepcopy
from hashlib import sha256

from .projection import Hold

URL = 'https://www2.city.kyoto.lg.jp/shikai/img/honkaigi/gian/R7-9/G07-104.pdf'
HOST = 'www2.city.kyoto.lg.jp'
DOCUMENT_ID = 'kyoto-doc-' + sha256(URL.encode()).hexdigest()[:24]
LIMIT = 2 * 1024 * 1024


def contract_scope():
    """Return a fresh disabled plan; no permissive URL canonicalization."""
    return {
        'scope_id': 'kyoto-p03-historical-contract-offline-v1',
        'city_code': 'kyoto', 'policy_ids': ['P-03'],
        'allowed_hosts': [HOST],
        'source': {
            'url': URL, 'document_id': DOCUMENT_ID, 'fiscal_year': 2025,
            'media_type': 'pdf', 'document_kind': 'other_official',
            'policy_ids': ['P-03'],
        },
        'max_requests': 1, 'max_response_bytes': LIMIT,
        'max_total_bytes': LIMIT, 'timeout_seconds': 10,
        'wall_timeout_seconds': 10, 'tls_verify': True,
        'redirects': 0, 'retries': 0, 'follow_links': False,
        'enabled': False, 'network_enabled': False, 'public_writes': False,
    }


def _exact(actual, expected):
    # Reject bool-as-int/float-as-int as well as extra fields and URL variants.
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _exact(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact(a, b) for a, b in zip(actual, expected))
    return actual == expected


def validate_contract_scope(scope, source):
    expected = contract_scope()
    if not _exact(scope, expected) or not _exact(source, expected['source']):
        raise Hold('P-03 contract scope/selection differs from the disabled exact plan')
    return deepcopy(source)


def offline_fetch_options(scope, source):
    """P1 constructor bounds for injected offline responses only.

    P1 reads one extra byte when checking oversize; reserve that byte inside
    the 2 MiB receive limit. Do not pass this plan to a live transport.
    """
    validate_contract_scope(scope, source)
    return {'allowed_hosts': frozenset({HOST}), 'max_bytes': LIMIT - 1,
            'max_redirects': 0, 'timeout_seconds': 10}


def validate_contract_record(scope, source, record, body):
    """Validate identity and readback without writing a CAS or receipt."""
    validate_contract_scope(scope, source)
    expected = {'source_url': URL, 'document_id': DOCUMENT_ID,
                'city_code': 'kyoto', 'fiscal_year': 2025,
                'mime_type': 'application/pdf', 'document_type': 'other_official'}
    if any(not _exact(record.get(k), v) for k, v in expected.items()):
        raise Hold('P-03 contract CAS identity mismatch')
    if type(body) is not bytes or not body.startswith(b'%PDF-') or not 0 < len(body) < LIMIT:
        raise Hold('P-03 contract readback is not an accepted bounded PDF')
    digest = sha256(body).hexdigest()
    if record.get('sha256') != digest or record.get('version_id') != digest:
        raise Hold('P-03 contract readback SHA/version mismatch')
    return digest
