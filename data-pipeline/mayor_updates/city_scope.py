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

def is_kyoto_wave1(scope):
    return scope.get('profile') == KYOTO_WAVE1

def validate_wave1_contract(scope):
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
        if not is_kyoto_wave1(scope) and s.get('index_url') and s['index_url'] not in [r['url'] for r in rows if r['media_type']=='html']:
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

def validate_storage(scope,storage,snapshot_root,output):
    validate_scope(scope)
    root=PrivateOutput(storage['private_root']).root
    # A separate immutable binding leaves every existing city_binding.json intact.
    binding_path=root/('kyoto_p04_p14_binding.json' if is_kyoto_wave1(scope) else 'city_binding.json')
    if hashlib.sha256(binding_path.read_bytes()).hexdigest()!=storage['binding_sha256']:
        raise Hold('Private city binding SHA mismatch')
    binding=json.loads(binding_path.read_text(encoding='utf-8'))
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
