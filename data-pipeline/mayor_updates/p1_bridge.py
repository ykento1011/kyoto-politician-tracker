"""Thin bridge to the separately installed P1. No original/CAS implementation here."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys
import unicodedata
from .projection import Hold
from .engine import digest

PINS = {
    'fetch.py': '6d14aa3a9e7f2da451ccd50c2cd6a6da80e5cf72ca9d78aa0db28dec2fe40472',
    'snapshots.py': '0c4893feeed1fc9987a2fb932e17127a84ede58f159eed6a51c6426703ed5ec0',
    'extract.py': '06b723374a2f8283cc78c701d235334adab41f3259e9e2e44fb60533fb76859f',
    'pdf_extract.py': 'd7280fb0fb241cfcd4e9f317c47792f62e1c7861ad29af9fa2fa1405b37c8d1e',
    'reconcile.py': '6851fd2d83154dbd99d1b80d8a09a1806a7427e2cc008aaf65c3abbf8806cad6',
}


def normal(text):
    # Normalization for matching only; exact captured quote is retained separately.
    return ''.join(unicodedata.normalize('NFKC', text).split())


class P1Bridge:
    def __init__(self, code_root, snapshot_root):
        self.code_root = Path(code_root).resolve(strict=True)
        self.hashes = {}
        for name, expected in PINS.items():
            actual = sha256((self.code_root / 'budget' / name).read_bytes()).hexdigest()
            if actual != expected:
                raise Hold('P1 approved code pin changed: ' + name)
            self.hashes[name] = actual
        # Refuse a previously imported budget package from another working tree.
        if 'budget' in sys.modules:
            if Path(sys.modules['budget'].__file__).resolve().parent != self.code_root / 'budget':
                raise Hold('Conflicting P1 module already loaded')
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.code_root))
        self.modules = {name: importlib.import_module('budget.' + name) for name in
                        ('fetch', 'snapshots', 'extract', 'registry', 'reconcile', 'discovery')}
        for name in self.modules:
            source = self.code_root / 'budget' / (name + '.py')
            self.hashes[source.name] = sha256(source.read_bytes()).hexdigest()
        self.store = self.modules['snapshots'].SnapshotStore(snapshot_root)
        self.registry = self.modules['registry'].BudgetRegistry()
        self.reconciler = self.modules['reconcile'].FiscalReconciler(self.store, registry=self.registry)
        self.index = self.store.read_index()
        self.extractions = {}

    def record(self, url, version):
        document = self.index['documents'].get(url)
        if not document:
            raise Hold('Original URL absent from this isolated CAS')
        matches = [v['record'] for v in document['versions'] if v['sha256'] == version]
        if len(matches) != 1:
            raise Hold('Exact saved version unavailable')
        rec = deepcopy(matches[0])
        body = self.store.snapshot_bytes(version)
        if sha256(body).hexdigest() != version or rec['version_id'] != version:
            raise Hold('Original SHA/version mismatch')
        return rec, body

    def extract(self, url, version):
        rec, _ = self.record(url, version)
        key = (url, version)
        if key not in self.extractions:
            result = self.modules['extract'].extract_from_store(
                self.store, document_id=rec['document_id'], version_id=rec['version_id'])
            self.modules['extract'].add_candidate_evidence_to_registry(
                result, self.registry, source_record=rec)
            self.extractions[key] = result.as_dict()
        return deepcopy(self.extractions[key])

    def evidence(self, spec):
        """Locate a configured quote in exact CAS bytes; no fuzzy project inference.

        This supplies a human-review candidate, NOT P1 verified fiscal evidence.
        PDF printed labels were curated from visual inspection; physical page
        lookup and literal footer presence are independently checked here.
        """
        rec, body = self.record(spec['source_url'], spec['sha256'])
        locator = spec['locator']
        if rec['mime_type'] == 'application/pdf':
            import fitz
            with fitz.open(stream=body, filetype='pdf') as doc:
                page = locator['physical_page']
                if type(page) is not int or not 1 <= page <= len(doc):
                    raise Hold('Invalid physical page')
                text = doc[page - 1].get_text()
                if locator.get('printed_page') is not None:
                    # Only the last 12 non-empty text lines can attest the footer.
                    footer = [normal(x) for x in text.splitlines() if x.strip()][-12:]
                    if str(locator['printed_page']) not in footer:
                        raise Hold('Printed page footer not confirmed')
        elif rec['mime_type'] == 'text/html':
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(body, 'html.parser')
            matches = soup.select(locator['selector'])
            if len(matches) != 1:
                raise Hold('HTML locator must identify one element')
            text = matches[0].get_text('\n', strip=True)
            if locator.get('heading') and normal(locator['heading']) not in normal(text):
                raise Hold('Progress heading/date not present at HTML locator')
        else:
            raise Hold('Unsupported original format')
        needle = normal(spec['quote'])
        if not needle or normal(text).count(needle) != 1:
            raise Hold('Quote absent or ambiguous at specified location')
        return {'source_url': rec['source_url'], 'document_id': rec['document_id'],
                'version_id': rec['version_id'], 'sha256': rec['sha256'],
                'retrieved_at': rec['retrieved_at'], 'mime_type': rec['mime_type'],
                'document_title': spec['document_title'], 'published_at': spec.get('published_at'),
                'locator': deepcopy(locator), 'quote': spec['quote'],
                'quote_match': 'NFKC_whitespace_only', 'quote_sha256': digest(spec['quote']),
                'verification_status': 'unverified'}

    def map_rule(self, rule):
        """A curated rule binds one policy, version and record; changed versions hold."""
        result = deepcopy(rule)
        specs = result.pop('source_specs')
        for spec in specs:
            current = self.index['documents'].get(spec['source_url'])
            if not current or current['versions'][-1]['sha256'] != spec['sha256']:
                raise Hold('Source replaced or unavailable; refresh mapping against current saved version')
        for spec in specs:
            rec, _ = self.record(spec['source_url'], spec['sha256'])
            if rec['city_code'] != result['city']:
                raise Hold('Source belongs to another city')
            if result['kind'] == 'budget' and rec['fiscal_year'] != result['facts']['fiscal_year_ad']:
                raise Hold('Saved document year and candidate year differ')
        result['evidence'] = [self.evidence(spec) for spec in specs]
        result['verification_status'] = 'unverified'
        result['candidate_id'] = 'candidate-' + digest(result)[:24]
        return result

    def index_links(self, url, version, allowed_hosts):
        rec, body = self.record(url, version)
        if rec['mime_type'] != 'text/html':
            raise Hold('Index must be saved HTML')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body, 'html.parser')
        discovery = self.modules['discovery']
        signals = discovery.parse_saved_html(str(soup))
        if signals.base_hints or signals.redirect_hints:
            raise Hold('Index has base/redirect hints; requires explicit review')
        links = {}
        for a in signals.anchors:
            try:
                target = discovery.canonical_official_url(a.raw_href, url,
                            allowed_hosts=frozenset(allowed_hosts))
            except discovery.DiscoveryError:
                continue
            links.setdefault(target, []).append({'label': a.label,
                                                  'headings': list(a.heading_path)})
        return links

    def fiscal_hold_reason(self, facts):
        """Delegate complete fiscal identities to P1, hold unknown identities."""
        required = ('project_id', 'fiscal_year', 'account_id', 'event_kind',
                    'round_type', 'source_line_id', 'proposal_at')
        missing = [key for key in required if facts.get(key) is None]
        if missing:
            return 'P1 fiscal reconciliation held: missing ' + ', '.join(missing)
        line = self.modules['reconcile'].FiscalLine(**facts)
        line.validate()
        return None

    def capture_from_test_transport(self, document, transport, *, max_bytes=2097152):
        """Offline integration seam. Live transport is deliberately unavailable.

        The actual scheduled runner must separately supply the existing approved
        single-GET worker with a PM-approved fixed URL/deadline/ACL scope. This
        seam proves that original persistence and extraction still use P1.
        """
        if getattr(transport, 'offline_fixture', False) is not True:
            raise Hold('Live acquisition disabled in this implementation')
        fetcher = self.modules['fetch'].SourceFetcher(
            self.store, transport=transport, allowed_hosts=frozenset({'www.city.kyoto.lg.jp'}),
            max_bytes=max_bytes - 1, max_redirects=0, timeout_seconds=10)
        return fetcher.fetch_discovered(document)
