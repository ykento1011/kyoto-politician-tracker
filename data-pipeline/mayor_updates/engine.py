"""Offline proposals. This module has no fetch, git or public-file writer."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from .projection import Hold, policies, format_amount, sync_totals

RELATIONS = {'direct', 'contextual', 'unconfirmed'}
ROLES = {'initial': {'initial'}, 'supplemental': {'delta', 'after_change'},
         'settlement': {'actual'}, 'execution': {'executed'}}


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode()).hexdigest()


def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise Hold('Explicit timezone-aware timestamp required') from exc
    return value


def compare_index(previous, current, *, success=True):
    """Already parsed index entries URL -> metadata. Never infer policy status."""
    if not success:
        return [{'kind': 'index_fetch_failed', 'policy_effect': None}], deepcopy(previous)
    changes = []
    for url in sorted(previous.keys() | current.keys()):
        kind = ('link_added' if url not in previous else
                'link_removed' if url not in current else
                'link_changed' if previous[url] != current[url] else None)
        if kind:
            changes.append({'kind': kind, 'source_url': url, 'policy_effect': None})
    return changes, deepcopy(current)


def compare_documents(previous, observations):
    """Failure retains last good SHA; absence is not a deletion or cancellation."""
    state, changes = deepcopy(previous), []
    for obs in observations:
        url = obs['source_url']
        if obs['status'] != 'ok':
            changes.append({'kind': 'document_fetch_failed', 'source_url': url,
                            'detail': obs.get('detail'), 'policy_effect': None})
            continue
        old = previous.get(url)
        if old is None:
            kind = 'new_document'
        elif old['sha256'] != obs['sha256']:
            kind = 'replacement_document'
        else:
            kind = 'unchanged'
        changes.append({'kind': kind, 'source_url': url,
                        'before_sha256': old['sha256'] if old else None,
                        'after_sha256': obs['sha256'], 'policy_effect': None})
        state[url] = deepcopy(obs)
    return changes, state


def validate_candidate(c, city, allowed):
    if c['city'] != city or c['policy_id'] not in allowed:
        raise Hold('Candidate is outside approved city/policy scope')
    if c['relation'] not in RELATIONS or c['verification_status'] != 'unverified':
        raise Hold('New candidates must remain unverified with explicit relation')
    if c['kind'] not in {'budget', 'progress', 'evidence_note'} or not c.get('reason'):
        raise Hold('Unsupported candidate kind or missing mapping reason')
    evidence = c.get('evidence', [])
    if not evidence:
        raise Hold('No original evidence')
    for e in evidence:
        if (not e['source_url'].startswith('https://') or len(e['sha256']) != 64
                or e['sha256'] != e['version_id'] or not e.get('locator')
                or not e.get('quote') or not e.get('quote_match')):
            raise Hold('Unbound original evidence')
        timestamp(e['retrieved_at'])
    if c['kind'] == 'evidence_note':
        note = c['note']
        if (set(note) != {'submeasure', 'fact_type', 'text', 'limitations'} or
                not all(isinstance(note[k], str) and note[k].strip() for k in note) or
                note['fact_type'] not in {'budget_proposal', 'budget_vote', 'enactment', 'implementation'}):
            raise Hold('Scoped factual note and explicit limitations required')
    elif c['kind'] == 'budget':
        facts = c['facts']
        if facts['budget_kind'] not in ROLES or facts['amount_role'] not in ROLES[facts['budget_kind']]:
            raise Hold('Budget kind / amount role conflict')
        if facts['budget_status'] not in {'proposal', 'enacted', 'unconfirmed', 'actual'}:
            raise Hold('Unknown budget status')
        if type(facts['fiscal_year_ad']) is not int:
            raise Hold('Explicit fiscal year required')
        if type(c['record_index']) is not int or c['record_index'] < 0:
            raise Hold('Invalid budget record index')
        if not isinstance(c['before_record_sha256'], str):
            raise Hold('Original record identity required')
        updates = c['updates']
        permitted = {'fiscal_year', 'project_name', 'doc_url', 'doc_source', 'budget_note',
                     'amount_jpy', 'funding_verification_status'}
        if set(updates) - permitted:
            raise Hold('Unsupported budget field')
        if updates.get('funding_verification_status', 'unverified') != 'unverified':
            raise Hold('Funding confirmation requires a separate explicit workflow')
        if 'amount_jpy' in updates:
            if facts.get('amount_jpy') != updates['amount_jpy'] or not facts.get('amount_original'):
                raise Hold('Amount update lacks original amount evidence')
        if updates.get('doc_url') and updates['doc_url'] not in {e['source_url'] for e in evidence}:
            raise Hold('Record URL is not an evidence URL')
    else:
        event = c['event']
        if event['source_url'] not in {e['source_url'] for e in evidence}:
            raise Hold('Progress URL is not bound to evidence')
        if event.get('event_date') is not None:
            # An announcement date is not automatically the event occurrence date.
            datetime.fromisoformat(event['event_date'])
        datetime.fromisoformat(event['announced_at'])
        if not all(event.get(k) for k in ('label', 'summary', 'source_title')):
            raise Hold('Incomplete progress event')


def propose(base, candidates, *, city, allowed, base_revision):
    """Build a review-only policy patch; source-validated candidates come from bridge."""
    old = policies(base)
    if not set(allowed) <= old.keys():
        raise Hold('Unknown policy in scope')
    result = deepcopy(base)
    new = policies(result)
    used, seen_ids, seen_targets = [], set(), set()
    for c in candidates:
        validate_candidate(c, city, allowed)
        if c['candidate_id'] in seen_ids:
            raise Hold('Duplicate candidate')
        seen_ids.add(c['candidate_id'])
        pid = c['policy_id']
        before = deepcopy(new[pid])
        if c['kind'] == 'evidence_note':
            note = {**deepcopy(c['note']), 'evidence':deepcopy(c['evidence']),
                    'policy_relation':c['relation'], 'stage_certified':False,
                    'include_in_total':False}
            notes = new[pid].setdefault('evidence_notes', [])
            if note not in notes:
                notes.append(note)
        elif c['kind'] == 'budget':
            idx = c['record_index']
            target = (pid, 'budget', idx)
            if target in seen_targets:
                raise Hold('Competing updates to the same record require resolution')
            seen_targets.add(target)
            records = new[pid]['budget_records']
            if idx >= len(records):
                raise Hold('Budget record missing since mapping')
            projected = deepcopy(records[idx])
            projected.update(deepcopy(c['updates']))
            projected['policy_relation'] = c['relation']
            projected['amount_display'] = format_amount(projected['amount_jpy'], c['facts'].get('approximate', False))
            if projected == records[idx]:
                continue  # Already applied: stable monitoring must not re-propose it.
            if digest(old[pid]['budget_records'][idx]) != c['before_record_sha256']:
                raise Hold('Budget record changed since mapping')
            # Complete prior value remains in the packet and accepted handoff receipt.
            records[idx] = projected
            # Initial-only direct totals; supplemental/settlement stay review-held.
            if c['facts']['budget_kind'] != 'initial' and c['relation'] == 'direct':
                raise Hold('Resolve fiscal series in P1 before proposing a direct total')
        else:
            target = (pid, 'progress')
            if target in seen_targets:
                raise Hold('Multiple latest events require explicit ordering')
            seen_targets.add(target)
            event = deepcopy(c['event'])
            current = new[pid].get('latest_update')
            if current and current['announced_at'] > event['announced_at']:
                raise Hold('Refusing an older progress event')
            if current != event:
                if current:
                    history = new[pid].setdefault('progress_history', [])
                    if current not in history:
                        history.append(deepcopy(current))
                new[pid]['latest_update'] = event
        if before != new[pid]:
            used.append(deepcopy(c))
    changed = [pid for pid in old if old[pid] != new[pid]]
    if not changed:
        return None, deepcopy(base)
    if any(c['kind'] != 'evidence_note' for c in used):
        sync_totals(result)
    packet = {'schema_version': 1, 'city': city, 'base_revision': base_revision,
              'base_sha256': digest(base), 'allowed_policies': sorted(allowed),
              'verification_status': 'unverified', 'publication_authorized': False,
              'candidates': used,
              'changes': [{'policy_id': pid, 'before': old[pid], 'after': new[pid],
                           'candidate_ids': [c['candidate_id'] for c in used if c['policy_id'] == pid]}
                          for pid in changed],
              'derived': {key: {'before': base.get(key), 'after': result.get(key)}
                          for key in ('summary_stats', 'kpis') if base.get(key) != result.get(key)}}
    packet['packet_id'] = digest(packet)
    return packet, result


def verify_packet(packet):
    body = {k: v for k, v in packet.items() if k != 'packet_id'}
    if packet.get('packet_id') != digest(body):
        raise Hold('Packet digest mismatch')
    if packet['publication_authorized'] is not False or packet['verification_status'] != 'unverified':
        raise Hold('Review packet status was altered')


def approved_bundle(base, packet, approval):
    """Return an IN-MEMORY handoff only. No public writer and no automatic approval."""
    verify_packet(packet)
    if digest(base) != packet['base_sha256']:
        raise Hold('Stale baseline; regenerate and review changed fields')
    if (approval.get('packet_id') != packet['packet_id'] or not approval.get('reviewer', '').strip()
            or approval.get('decision') != 'approve'):
        raise Hold('Explicit matching review receipt required')
    timestamp(approval.get('reviewed_at'))
    expected = {c['candidate_id'] for c in packet['candidates']}
    if set(approval.get('accepted_candidate_ids', [])) != expected:
        raise Hold('Partial approval: regenerate a smaller packet')
    rebuilt, result = propose(base, packet['candidates'], city=packet['city'],
                              allowed=packet['allowed_policies'], base_revision=packet['base_revision'])
    if rebuilt != packet:
        raise Hold('Packet does not reproduce from its bound candidates')
    return {'packet_id': packet['packet_id'], 'base_sha256': digest(base),
            'result_sha256': digest(result), 'review_receipt': deepcopy(approval),
            'changed_policy_ids': [c['policy_id'] for c in packet['changes']],
            'sources': [deepcopy(e) for c in packet['candidates'] for e in c['evidence']],
            'before_after': deepcopy(packet['changes']), 'data': result,
            'publication_authorized': False, 'state': 'reviewed_awaiting_publication_go'}


def publication_receipt(bundle, *, commit, deployed_url, published_at, published_data):
    """Record externally observed publication, never deploy or manufacture success."""
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise Hold('Full public commit required')
    if digest(published_data) != bundle['result_sha256'] or not deployed_url.startswith('https://'):
        raise Hold('Published data does not match reviewed result')
    timestamp(published_at)
    return {k: deepcopy(bundle[k]) for k in ('packet_id', 'base_sha256', 'result_sha256',
                                             'changed_policy_ids', 'sources')} | {
        'commit': commit, 'deployed_url': deployed_url, 'published_at': published_at}


class PrivateOutput:
    """Only pre-provisioned output roots outside any Git/public tree are accepted."""
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        for p in (self.root, *self.root.parents):
            if (p / '.git').exists() or p.name.lower() == 'public':
                raise Hold('Output must be outside repositories/public directories')

    def write(self, name, content):
        if Path(name).name != name or name in {'.', '..'}:
            raise Hold('Flat private artifact names only')
        dest = self.root / name
        if dest.exists() and dest.is_symlink():
            raise Hold('Symlink output refused')
        # Unique run directories prevent stale proposal files on zero-change runs.
        if dest.exists():
            raise Hold('Artifact already exists; select a new run directory')
        with dest.open('x', encoding='utf-8', newline='\n') as f:
            f.write(content)
        return dest

    def json(self, name, data):
        return self.write(name, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def review_html(packet):
    verify_packet(packet)
    sections = []
    for change in packet['changes']:
        fields = [k for k in change['before'].keys() | change['after'].keys()
                  if change['before'].get(k) != change['after'].get(k)]
        rows = ''.join('<tr><th>' + escape(k) + '</th><td><pre>' +
                       escape(json.dumps(change['before'].get(k), ensure_ascii=False, indent=2)) +
                       '</pre></td><td><pre>' +
                       escape(json.dumps(change['after'].get(k), ensure_ascii=False, indent=2)) +
                       '</pre></td></tr>' for k in sorted(fields))
        evidence = []
        for c in packet['candidates']:
            if c['policy_id'] != change['policy_id']:
                continue
            evidence.append('<h3>' + escape(c['candidate_id']) + '</h3><p>' +
                            escape(c['relation'] + ' / ' + c['reason']) + '</p>')
            for e in c['evidence']:
                evidence.append('<blockquote>' + escape(e['quote']) + '</blockquote><p>' +
                                escape(e['document_title'] + ' / ' + json.dumps(e['locator'], ensure_ascii=False)) +
                                '<br><a href="' + escape(e['source_url'], quote=True) + '">' + escape(e['source_url']) +
                                '</a><br>SHA-256: ' + escape(e['sha256']) + '</p>')
        sections.append('<section><h2>' + escape(change['policy_id']) + '</h2><table><tr><th>項目</th><th>現在</th><th>変更候補</th></tr>' +
                        rows + '</table>' + ''.join(evidence) + '</section>')
    derived = escape(json.dumps(packet['derived'], ensure_ascii=False, indent=2))
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><title>市長トラッカー変更レビュー</title>'
            '<style>body{font:15px sans-serif;max-width:1300px;margin:32px auto;padding:16px;color:#172033}'
            'table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{border:1px solid #ccd;padding:12px;vertical-align:top}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere}blockquote{border-left:4px solid #789;padding:12px;background:#eef3f8}'
            'a{overflow-wrap:anywhere}</style><h1>変更された政策だけの確認</h1>'
            '<p>未承認・未公開。各候補を承認／保留／却下。確認者・日時は本人が入力します。原本リンクを開くと通信が発生します。</p>'
            '<p>予算案の記載確認は議決成立や事業達成の認定ではありません。</p>' + ''.join(sections) +
            '<h2>派生集計の差分</h2><pre>' + derived + '</pre><p>Packet: ' + packet['packet_id'] + '</p></html>')
