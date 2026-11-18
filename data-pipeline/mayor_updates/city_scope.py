"""Explicit fixed-source city trial scope; no transport, CAS or publication."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from .projection import Hold
from .engine import PrivateOutput

KYOTO_WAVE1 = 'kyoto_p04_p14_r7_pdfs'
KYOTO_INDEX_URL = 'https://www.city.kyoto.lg.jp/gyozai/page/0000335933.html'
KYOTO_INDEX_SHA = 'be45c0421b1ca127853416f420991cd8d288841fb46ce6e76f0bc601860180bd'
KYOTO_WAVE1_DOCS = (
    ('P-04', '07_kouhou_kowaka.pdf', 119),
    ('P-14', '06_kouhou_hohuku.pdf', 118),
)

YOKOHAMA_MAJOR_PDF = 'yokohama_r8_major_pdf'
YOKOHAMA_INDEX_URL = 'https://www.city.yokohama.lg.jp/city-info/zaisei/jokyo/yosan/r8/r8yosan.html'
YOKOHAMA_INDEX_SHA = '872f5c8da45129bd6a3296269942880e20eeac8de6a163bb556e2bde294ae98b'
YOKOHAMA_PDF_URL = YOKOHAMA_INDEX_URL.removesuffix('r8yosan.html') + 'r8yosan.files/R8yosan-shuyou.pdf'
YOKOHAMA_PDF_HREF = 'r8yosan.files/R8yosan-shuyou.pdf'
YOKOHAMA_PDF_LABEL = '資料編（主要事業一覧）（PDF：1,014KB）'
YOKOHAMA_INDEX_HEADING = '令和８年度予算（令和８年１月26日）'
# Existing approved city-capable P1 candidate plus exact Yokohama directory patch.
YOKOHAMA_P1_SHA = 'df02598305964e5d3bea333301ecccb93e26702db6f0a43a5fe6f8c180dd57d2'


def is_yokohama_major_pdf(scope):
    return scope.get('profile') == YOKOHAMA_MAJOR_PDF


def yokohama_major_pdf_scope():
    """Disabled fixed contract; source/policy correspondence is not approved here."""
    return dict(profile=YOKOHAMA_MAJOR_PDF, city_code='yokohama', enabled=False,
        network_enabled=False, allowed_hosts=['www.city.yokohama.lg.jp'],
        policy_ids=['YOKOHAMA-M01'], policy_relation='unconfirmed', method='GET',
        max_requests=1, max_requests_by_media={'html':0,'pdf':1},
        max_total_bytes=2097152, timeout_seconds=10, wall_timeout_seconds=10,
        tls_verify=True, redirects=0, retries=0, follow_discovered_links=False,
        index_sha256=YOKOHAMA_INDEX_SHA, p1_manifest_sha256=YOKOHAMA_P1_SHA,
        sources=[dict(id='yokohama-r8-major-projects', url=YOKOHAMA_PDF_URL,
            title='令和8年度予算・資料編（主要事業一覧）', media_type='pdf',
            document_kind='other_official', fiscal_year=2026, max_bytes=2097152,
            policy_ids=['YOKOHAMA-M01'], policy_relation='unconfirmed',
            index_url=YOKOHAMA_INDEX_URL, index_anchor=17,
            document_id='yokohama-doc-'+hashlib.sha256(YOKOHAMA_PDF_URL.encode()).hexdigest()[:24])])


def yokohama_binding_name(scope):
    expected = yokohama_major_pdf_scope()
    enabled, network = scope.get('enabled'), scope.get('network_enabled')
    if type(enabled) is not bool or type(network) is not bool or enabled != network:
        raise Hold('Yokohama activation requires matching booleans')
    expected.update(enabled=enabled, network_enabled=network)
    # Canonical serialization also distinguishes True from 1 and rejects extras.
    if signature(scope) != signature(expected):
        raise Hold('Fixed Yokohama one-PDF contract changed')
    return 'yokohama_r8_major_pdf_active_binding.json' if enabled else 'yokohama_r8_major_pdf_binding.json'


def validate_yokohama_index(snapshot_root):
    """Only read the approved index; never add it to the acquisition selection."""
    from bs4 import BeautifulSoup
    root = Path(snapshot_root).resolve(strict=True)
    relative = 'objects/'+YOKOHAMA_INDEX_SHA[:2]+'/'+YOKOHAMA_INDEX_SHA+'.bin'
    try:
        index = json.loads(_existing_path(root/'index.json').read_text(encoding='utf-8'))
        versions = index['documents'][YOKOHAMA_INDEX_URL]['versions']
        if len(versions) != 1 or versions[0]['sha256'] != YOKOHAMA_INDEX_SHA:
            raise ValueError('Index missing, replaced or ambiguous')
        rec = versions[0]['record']
        expected = dict(city_code='yokohama', source_url=YOKOHAMA_INDEX_URL,
            final_url=YOKOHAMA_INDEX_URL, sha256=YOKOHAMA_INDEX_SHA,
            version_id=YOKOHAMA_INDEX_SHA, fiscal_year=2026, mime_type='text/html',
            document_type='budget_index', snapshot_relative_path=relative,
            document_id='yokohama-doc-'+hashlib.sha256(YOKOHAMA_INDEX_URL.encode()).hexdigest()[:24])
        if any(rec.get(k) != v for k,v in expected.items()):
            raise ValueError('Index metadata mismatch')
        obj = root/relative
        if obj.is_symlink() or obj.resolve(strict=True) != obj.absolute():
            raise ValueError('Linked index original refused')
        body = obj.read_bytes()
        if hashlib.sha256(body).hexdigest() != YOKOHAMA_INDEX_SHA:
            raise ValueError('Index SHA mismatch')
        soup = BeautifulSoup(body.decode('utf-8'), 'html.parser')
        main = soup.select('#tmp_contents')
        if len(main) != 1 or soup.find('base') or soup.find('meta', attrs={'http-equiv':lambda v: v and v.lower()=='refresh'}):
            raise ValueError('Unknown index structure or redirect')
        links = main[0].find_all('a', href=True)
        anchor = links[16]
        heading = anchor.find_previous(['h2','h3','h4'])
        if (anchor.get('href') != YOKOHAMA_PDF_HREF or
                anchor.get_text(' ',strip=True) != YOKOHAMA_PDF_LABEL or
                heading is None or main[0] not in heading.parents or
                heading.get_text(' ',strip=True) != YOKOHAMA_INDEX_HEADING or
                len(main[0].find_all('a',href=YOKOHAMA_PDF_HREF)) != 1):
            raise ValueError('Index anchor/title/year mismatch')
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise Hold('Pinned Yokohama saved index verification failed') from exc


def _existing_path(path):
    raw = Path(path)
    real = raw.resolve(strict=True)
    if raw.is_symlink() or raw.absolute() != real:
        raise Hold('Linked or noncanonical private path refused')
    return real


def _directory_identity(path):
    stat = path.stat()
    return {'device':stat.st_dev, 'inode':stat.st_ino}


def validate_yokohama_storage(scope, storage, snapshot_root, output, code_root):
    """Strict separate binding; no file creation, fallback or ACL modification."""
    from .acquire import assert_owner_only
    try:
        root = PrivateOutput(_existing_path(storage['private_root'])).root
        cas = _existing_path(snapshot_root); state = _existing_path(storage['state_root'])
        out = _existing_path(output); code = _existing_path(code_root)
        binding_path = _existing_path(root/yokohama_binding_name(scope))
        if (not cas.is_dir() or not state.is_dir() or not out.is_dir() or not code.is_dir() or
                cas == state or cas in state.parents or state in cas.parents or
                root not in cas.parents or root not in state.parents or state not in out.parents or
                code == cas or code in cas.parents or cas in code.parents or
                code == state or code in state.parents or state in code.parents):
            raise Hold('Yokohama CAS/state/output/code isolation mismatch')
        for path in (root, cas, state, out, binding_path, code):
            assert_owner_only(path)
        raw = binding_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != storage['binding_sha256']:
            raise Hold('Yokohama dedicated binding SHA mismatch')
        binding = json.loads(raw.decode('utf-8'))
        expected = dict(city_code='yokohama', scope_sha256=signature(scope),
            snapshot_root=str(cas), state_root=str(state), p1_code_root=str(code),
            snapshot_identity=_directory_identity(cas), state_identity=_directory_identity(state),
            index_sha256=YOKOHAMA_INDEX_SHA, p1_manifest_sha256=YOKOHAMA_P1_SHA,
            guard_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            acquire_code_sha256=hashlib.sha256(Path(__file__).with_name('acquire.py').read_bytes()).hexdigest())
        if signature(binding) != signature(expected):
            raise Hold('Yokohama dedicated binding identity mismatch')
        manifest = storage['p1_files']
        manifest_sha = hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if manifest_sha != YOKOHAMA_P1_SHA or str(code) != storage['p1_code_root']:
            raise Hold('Yokohama fixed P1 manifest/root mismatch')
        for name, sha in manifest.items():
            file = _existing_path(code/name)
            if code not in file.parents or hashlib.sha256(file.read_bytes()).hexdigest() != sha:
                raise Hold('Yokohama fixed P1 code PIN mismatch')
        ledger = json.loads(_existing_path(cas/'index.json').read_text(encoding='utf-8'))
        if any(v['record'].get('city_code') != 'yokohama' for doc in ledger['documents'].values() for v in doc['versions']):
            raise Hold('Yokohama CAS contains another city')
        validate_yokohama_index(cas)
        return state
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise Hold('Yokohama private binding/code/index validation failed') from exc

def is_kyoto_wave1(scope):
    return scope.get('profile') == KYOTO_WAVE1

def wave1_binding_name(scope):
    enabled, network = scope.get('enabled'), scope.get('network_enabled')
    if type(enabled) is not bool or type(network) is not bool or enabled != network:
        raise Hold('Kyoto wave1 activation flags must be matching booleans')
    return 'kyoto_p04_p14_active_binding.json' if enabled else 'kyoto_p04_p14_binding.json'

def validate_wave1_contract(scope):
    wave1_binding_name(scope)
    if (scope['city_code'] != 'kyoto' or scope['policy_ids'] != ['P-04', 'P-14'] or
            scope['max_requests'] != 2 or scope['max_requests_by_media'] != {'html': 0, 'pdf': 2} or
            scope['max_total_bytes'] != 4194304 or len(scope['sources']) != 2 or
            scope.get('index_sha256') != KYOTO_INDEX_SHA):
        raise Hold('Invalid fixed Kyoto wave1 contract')
    for row, (policy, filename, anchor) in zip(scope['sources'], KYOTO_WAVE1_DOCS):
        url = 'https://www.city.kyoto.lg.jp/gyozai/cmsfiles/contents/0000335/335933/' + filename
        expected = dict(id='kyoto-r7-' + policy.lower(), url=url, policy_ids=[policy],
                        fiscal_year=2025, media_type='pdf', document_kind='other_official',
                        max_bytes=2097152, index_url=KYOTO_INDEX_URL, index_anchor=anchor,
                        document_id='kyoto-doc-' + hashlib.sha256(url.encode()).hexdigest()[:24])
        if any(row.get(k) != v for k, v in expected.items()):
            raise Hold('Kyoto wave1 URL/policy/year/document identity mismatch')

class _IndexLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth = 0; self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div' and (self.depth or attrs.get('id') == 'mol_contents'):
            self.depth += 1
        if self.depth and tag == 'a':
            self.links.append(attrs.get('href'))
    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1

def validate_wave1_index(snapshot_root):
    """Read only: require the pinned original and its existing CAS record."""
    root = Path(snapshot_root).resolve(strict=True)
    sha = KYOTO_INDEX_SHA
    relative = 'objects/' + sha[:2] + '/' + sha + '.bin'
    try:
        index = json.loads((root/'index.json').read_text(encoding='utf-8'))
        records = [v['record'] for v in index['documents'][KYOTO_INDEX_URL]['versions']
                   if v['sha256'] == sha]
        if len(records) != 1:
            raise ValueError('Expected one pinned index version')
        rec = records[0]
        expected = dict(city_code='kyoto', source_url=KYOTO_INDEX_URL, final_url=KYOTO_INDEX_URL,
                        sha256=sha, version_id=sha, fiscal_year=2025, mime_type='text/html',
                        snapshot_relative_path=relative)
        if any(rec.get(k) != v for k, v in expected.items()):
            raise ValueError('Index record mismatch')
        body = (root/relative).read_bytes()
        if hashlib.sha256(body).hexdigest() != sha:
            raise ValueError('Index original SHA mismatch')
        parser = _IndexLinks(); parser.feed(body.decode('utf-8'))
        for _, filename, anchor in KYOTO_WAVE1_DOCS:
            if parser.links[anchor-1] != './cmsfiles/contents/0000335/335933/' + filename:
                raise ValueError('Index anchor mismatch')
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise Hold('Saved Kyoto wave1 index verification failed') from exc

def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def official_host(city):
    # Nagoya uses city.nagoya.jp. Do not infer or accept arbitrary alternative hosts.
    return 'www.city.nagoya.jp' if city == 'nagoya' else 'www.city.'+city+'.lg.jp'

# Exact opt-in, not a general trailing-slash HTML rule. The registered source
# still passes city/policy, transport, storage and per-source selection checks.
DIRECTORY_HTML = frozenset({
    ('yokohama', 'https://www.city.yokohama.lg.jp/city-info/zaisei/'),
})

def is_registered_directory_html(city, url, medium):
    return medium == 'html' and (city, url) in DIRECTORY_HTML


def validate_scope(scope):
    if is_yokohama_major_pdf(scope):
        yokohama_binding_name(scope)
    registry=json.loads((Path(__file__).resolve().parents[2]/'config/mayor_update_sources.json').read_text(encoding='utf-8'))['cities']
    city=scope['city_code']
    if city not in registry or not scope['policy_ids'] or not set(scope['policy_ids'])<=set(registry[city]['policy_ids']):
        raise Hold('City/policy scope mismatch')
    if scope['allowed_hosts'] != [official_host(city)]:
        raise Hold('Explicit official host must match city')
    if any(scope.get(k)!=v for k,v in dict(timeout_seconds=10,redirects=0,retries=0,tls_verify=True).items()):
        raise Hold('City trial communication safeguards changed')
    rows=scope['sources']; caps=scope['max_requests_by_media']
    if is_kyoto_wave1(scope):
        validate_wave1_contract(scope)
    elif is_yokohama_major_pdf(scope):
        pass  # Exact dedicated contract already checked; generic limits unchanged.
    elif (not rows or len(rows)>scope['max_requests'] or scope['max_requests']>2 or
            caps!={'html':1,'pdf':1} or scope['max_total_bytes']!=4194304):
        raise Hold('Initial city trial is limited to one HTML and one PDF')
    seen=set(); ids=set()
    for s in rows:
        u=urlsplit(s['url']); medium=s['media_type']
        if (medium not in caps or u.scheme!='https' or u.netloc not in scope['allowed_hosts'] or
                u.query or u.fragment or not (u.path.endswith('.'+medium) or is_registered_directory_html(city,s['url'],medium)) or s['url'] in seen or s['id'] in ids or
                s['max_bytes']!=2097152 or type(s['fiscal_year']) is not int or not 2019<=s['fiscal_year']<=2100 or
                s['document_kind'] not in {'budget_index','other_official'} or
                not s['policy_ids'] or not set(s['policy_ids'])<=set(scope['policy_ids'])):
            raise Hold('Invalid city fixed document')
        if not (is_kyoto_wave1(scope) or is_yokohama_major_pdf(scope)) and s.get('index_url') and s['index_url'] not in [r['url'] for r in rows if r['media_type']=='html']:
            raise Hold('Index provenance must be a fixed HTML source in this scope')
        seen.add(s['url']);ids.add(s['id'])
    if any(sum(s['media_type']==m for s in rows)>cap for m,cap in caps.items()) or sum(s['max_bytes'] for s in rows)>scope['max_total_bytes']:
        raise Hold('City trial request/receive budget exceeded')
    return city

def validate_selection(scope,sources,media_type):
    validate_scope(scope)
    if not sources or len({s['url'] for s in sources})!=len(sources):
        raise Hold('Empty or duplicate source selection')
    for s in sources:
        if s not in scope['sources'] or s['media_type']!=media_type:
            raise Hold('Source is not the pinned city/year/kind/policy selection')

def validate_storage(scope,storage,snapshot_root,output,*,code_root=None):
    validate_scope(scope)
    if is_yokohama_major_pdf(scope):
        return validate_yokohama_storage(scope,storage,snapshot_root,output,code_root)
    root=PrivateOutput(storage['private_root']).root
    # A separate immutable binding leaves every existing city_binding.json intact.
    binding_path=root/(wave1_binding_name(scope) if is_kyoto_wave1(scope) else 'city_binding.json')
    if is_kyoto_wave1(scope):
        if not binding_path.is_file() or binding_path.is_symlink():
            raise Hold('Required Kyoto wave1 binding is missing or a symlink')
        if not Path(snapshot_root).is_dir() or not Path(storage['state_root']).is_dir():
            raise Hold('Existing Kyoto CAS and state required')
        # Reuse the acquisition ACL check; do not change permissions here.
        from .acquire import assert_owner_only
        for path in (root, binding_path, Path(snapshot_root), Path(storage['state_root'])):
            assert_owner_only(path)
    if hashlib.sha256(binding_path.read_bytes()).hexdigest()!=storage['binding_sha256']:
        raise Hold('Private city binding SHA mismatch')
    try:
        binding=json.loads(binding_path.read_text(encoding='utf-8'))
        required={'city_code','scope_sha256','snapshot_root','state_root'}
        if is_kyoto_wave1(scope) and (not isinstance(binding,dict) or not required<=binding.keys() or
                any(not isinstance(binding[k],str) or not binding[k] for k in required)):
            raise Hold('Malformed Kyoto wave1 binding')
    except (ValueError, UnicodeError) as exc:
        if not is_kyoto_wave1(scope):
            raise
        raise Hold('Malformed Kyoto wave1 binding') from exc
    cas=Path(snapshot_root).resolve();state=Path(storage['state_root']).resolve();out=Path(output).resolve()
    if (binding['city_code']!=scope['city_code'] or binding['scope_sha256']!=signature(scope) or
            cas!=Path(binding['snapshot_root']).resolve() or state!=Path(binding['state_root']).resolve() or
            cas==state or cas in state.parents or state in cas.parents or
            root not in cas.parents or root not in state.parents or state not in out.parents):
        raise Hold('Private city/CAS/state scope mismatch')
    if is_kyoto_wave1(scope):
        if not cas.is_dir() or not state.is_dir() or binding.get('index_sha256') != KYOTO_INDEX_SHA:
            raise Hold('Existing Kyoto CAS/state and pinned index binding required')
        validate_wave1_index(cas)
    return state

def reserve_request(scope,storage,source):
    if scope.get('enabled') is not True or scope.get('network_enabled') is not True:
        raise Hold('City trial network is disabled')
    state=Path(storage['state_root'])
    marker=state/('single_request_'+hashlib.sha256(source['url'].encode()).hexdigest()+'.json')
    try:
        with marker.open('x',encoding='utf-8') as f: json.dump({'url':source['url'],'scope_sha256':signature(scope),'max_bytes':source['max_bytes']},f)
    except FileExistsError as exc:
        raise Hold('This city trial URL was already attempted; no retry') from exc
