"""Small Kyoto index adapter over saved HTML and P1 URL validation.

Only source-bound listing candidates are returned. A linked PDF is never read,
classified as fact-verified, or downloaded by this adapter.
"""
import re
from collections import Counter
from copy import deepcopy
from bs4 import BeautifulSoup
from .projection import Hold


def saved_index(bridge, source, version):
    rec,body=bridge.record(source['url'],version)
    if rec['mime_type']!='text/html': raise Hold('Expected saved HTML index')
    soup=BeautifulSoup(body,'html.parser')
    signals=bridge.modules['discovery'].parse_saved_html(str(soup))
    if signals.redirect_hints: raise Hold('Index redirect hint requires review')
    base=source['resolution_base']
    if list(signals.base_hints) not in ([],[base]):
        raise Hold('HTML base differs from explicitly configured official base')
    canonical=bridge.modules['discovery'].canonical_official_url
    canonical(base,source['url'],allowed_hosts=frozenset({'www.city.kyoto.lg.jp'}))
    main=soup.select_one(source.get('selector','#mol_contents'))
    if main is None: raise Hold('Official content selector not found')
    expected=f"令和{source['fiscal_year']-2018}年度"
    if expected not in main.get_text(): raise Hold('Index fiscal year does not match configuration')
    links={}; section=''; context=''; month=None; ordinal=0
    for node in main.find_all(['h2','h3','h4','p','a']):
        text=node.get_text(' ',strip=True)
        if node.name in {'h2','h3'}:
            section=text; context=''; month=None
        elif node.name in {'h4','p'} and not node.find('a'):
            # Plain paragraphs such as "9月補正" carry the session on real indexes.
            if len(text)<160:
                context=text
                match=re.fullmatch(r'(1[0-2]|[1-9])月補正(?:予算)?',text)
                if match: month=match.group(1)+'月'
        elif node.name=='a' and node.get('href'):
            ordinal+=1
            raw=node['href']
            try: url=canonical(raw,base,allowed_hosts=frozenset({'www.city.kyoto.lg.jp'}))
            except ValueError: continue
            if not url.lower().endswith('.pdf'): continue
            joined=' '.join([section,context,text])
            kind='budget_document'; round_type='unknown'; status='unconfirmed'
            if '補正' in section:
                kind='budget_supplemental'; round_type='supplemental'
            elif '当初' in section or '当初' in context:
                kind='budget_initial'; round_type='initial'
            elif '事業概要' in section:
                kind='major_projects'
            elif '編成通知' in joined:
                kind='budget_guidance'
            elif '査定' in joined or '要求' in joined:
                kind='budget_request_assessment'
            if '予算案' in joined: status='proposal'
            item={'title':re.sub(r'\(PDF形式[^)]*\)$','',text).strip(),
                  'source_url':url,'fiscal_year':source['fiscal_year'],
                  'document_kind':kind,'budget_round':round_type,
                  'session':month if round_type=='supplemental' else None,
                  'budget_status':status,'account':None,
                  'index_url':source['url'],'index_sha256':rec['sha256'],
                  'retrieved_at':rec['retrieved_at'],'link_content_read':False,
                  'verification_status':'unverified',
                  'locator':{'selector':source.get('selector','#mol_contents'),
                             'anchor_ordinal':ordinal,'href_literal':raw},
                  'classification_basis':{'section':section,'context':context,'anchor_text':text}}
            links.setdefault(url,[]).append(item)
    return {'source_url':source['url'],'sha256':rec['sha256'],
            'title':soup.title.get_text(strip=True) if soup.title else rec['source_title'],
            'fiscal_year':source['fiscal_year'],'resolution_base':base,
            'links':links,'counts':dict(Counter(x['budget_round'] for rows in links.values() for x in rows)),
            'document_kind_counts':dict(Counter(x['document_kind'] for rows in links.values() for x in rows)),
            'status':'listing_candidates_only'}


def comparison_links(inventory):
    # Index SHA/time changes should not mark every unchanged attachment as changed.
    return {url:[{k:deepcopy(v) for k,v in row.items() if k not in
                  {'index_sha256','retrieved_at'}} for row in rows]
            for url,rows in inventory['links'].items()}


def preserved_units(bridge, source, version):
    """Evidence-only fallback when structured budget extraction returns zero.

    No project or amount is manufactured. A future text-only announcement keeps
    its location and exact text, even when no existing mapping rule matches it.
    """
    rec,body=bridge.record(source['url'],version)
    soup=BeautifulSoup(body,'html.parser'); main=soup.select_one(source.get('selector','#mol_contents'))
    if main is None: raise Hold('Content selector missing')
    units=[]; heading=''; position=0; first_h2_seen=False
    for node in main.find_all(['h2','h3','h4','p']):
        position+=1; quote=node.get_text(' ',strip=True)
        if not quote: continue
        if node.name=='h2':
            if first_h2_seen: break  # Preserve the leading announcement, not obsolete sections.
            first_h2_seen=True
        if node.name.startswith('h'): heading=quote
        if source['role']=='progress' and node.name=='p':
            units.append({'kind':'progress_evidence','policy_id':source.get('policy_id'),
                          'source_url':source['url'],'sha256':rec['sha256'],'version_id':rec['version_id'],
                          'retrieved_at':rec['retrieved_at'],'locator':{'selector':source.get('selector','#mol_contents'),
                           'element_position':position,'heading':heading},'quote':quote,
                          'verification_status':'unverified','eligible_for_automatic_publication':False})
    return units
