"""Amounts and reviewed overlays shared by proposals and the Kyoto generator."""
from copy import deepcopy

BUDGET_TOTAL_NOTE = '登録済み予算の集計です。確認区分を付けた参考・未確認の予算は除外していますが、全額の原典確認を済ませた総額ではありません。履歴を整理した記録では、同年度・会計・事業の採用額だけを計上し、補正増減額と債務負担行為は加算しません。総額の表示は万円単位に丸めています。'

class Hold(ValueError):
    pass


def policy_id(p):
    value = p.get('id') or p.get('pledge_id')
    if not value:
        raise Hold('Missing policy ID')
    return value


def policies(data):
    rows = data['pledges']
    result = {policy_id(p): p for p in rows}
    if len(result) != len(rows):
        raise Hold('Duplicate policy IDs')
    return result


def format_amount(value, approximate=False):
    if type(value) is not int or value < 0:
        raise Hold('Expected nonnegative integer JPY')
    # Matches the existing P-01 display convention (nearest 10,000 yen).
    if value == 0: return '0円'
    man = (value + 5000) // 10000
    oku, rem = divmod(man, 10000)
    return ('約' if approximate else '') + (f'{oku}億{rem:,}万円' if oku else f'{rem:,}万円')


def included(record):
    aggregation = record.get('aggregation_status')
    if aggregation == 'excluded': return False
    if aggregation not in {None, 'included'}: raise Hold('Unknown aggregation status')
    relation = record.get('policy_relation')
    if 'policy_relation' not in record:  # Preserve untouched legacy policies.
        return True
    if relation not in {'direct', 'contextual', 'unconfirmed'}:
        return False
    if relation != 'direct':
        return False
    if record.get('amount_role') == 'after_change':
        if (aggregation != 'included' or record.get('budget_kind') != 'supplemental'
                or record.get('evidence_status') != 'source_checked'
                or not all(record.get(k) for k in ('series_id', 'fiscal_year_ad', 'account', 'doc_url', 'doc_source'))):
            raise Hold('Explicit sourced fiscal-series selection required')
        return True
    # Deltas, commitments and settlements are not standalone annual totals.
    if record.get('amount_role', 'initial') != 'initial':
        raise Hold('Fiscal-series reconciliation required before total inclusion')
    if record.get('budget_kind', 'initial') != 'initial':
        raise Hold('Non-initial amount cannot enter legacy budget total')
    if record.get('evidence_status') == 'unverified':
        raise Hold('Unverified direct amount cannot enter total')
    return True


def format_record_amount(record):
    """Exact JPY display for explicitly typed history; never round a delta."""
    n = record['amount_jpy']
    role = record['amount_role']
    if role not in {'initial', 'delta', 'after_change', 'commitment'}:
        raise Hold('Unknown budget amount role')
    if type(n) is not int or (n < 0 and role != 'delta'):
        raise Hold('Only supplemental deltas may be negative')
    sign = ('＋' if n >= 0 else '−') if role == 'delta' else ''
    oku, rest = divmod(abs(n), 100000000)
    man, yen = divmod(rest, 10000)
    text = (f'{oku}億' if oku else '') + (f'{man:,}万' if man else '') + (f'{yen:,}' if yen else '')
    return sign + (text or '0') + '円'


def budget_total(pledges):
    """Validate explicit annual series before counting selected totals.

    Untouched legacy records retain their existing treatment. Typed series
    permit one initial or one reconciled after-change total per year/account.
    Delta-only series remain history, never a substitute for an annual total.
    """
    total = 0
    for p in pledges:
        groups = {}
        for r in p.get('budget_records', []):
            if 'amount_role' in r:
                format_record_amount(r)
            if r.get('series_id'):
                if not all(r.get(k) for k in ('fiscal_year_ad', 'account', 'amount_role')):
                    raise Hold('Incomplete fiscal series identity')
                key = (r['series_id'], r['fiscal_year_ad'], r['account'])
                groups.setdefault(key, []).append(r)
            if included(r):
                n = r['amount_jpy']
                if type(n) is not int or n < 0:
                    raise Hold('Invalid budget amount')
                total += n
        for rows in groups.values():
            selected = [r for r in rows if included(r)]
            if len(selected) > 1:
                raise Hold('Duplicate annual total selection')
            if not selected or selected[0].get('amount_role') != 'after_change':
                continue
            roles = {role: [r for r in rows if r['amount_role'] == role]
                     for role in ('initial', 'delta', 'after_change')}
            if any(len(items) != 1 for items in roles.values()) or len(rows) != 3:
                raise Hold('Single documented amendment required; reconcile multi-amendment history separately')
            if any(r.get('evidence_status') != 'source_checked' or
                   r.get('policy_relation') != 'direct' or
                   not r.get('doc_url') or not r.get('doc_source') for r in rows):
                raise Hold('Fiscal series evidence incomplete')
            before, delta, after = (roles[k][0]['amount_jpy'] for k in ('initial', 'delta', 'after_change'))
            if before + delta != after:
                raise Hold('Fiscal series does not reconcile')
    return total


def sync_totals(data):
    total = budget_total(data['pledges'])
    for p in data['pledges']:
        for r in p.get('budget_records', []):
            if 'amount_role' in r:
                r['amount_display'] = format_record_amount(r)
    if 'summary_stats' in data:
        data['summary_stats']['total_allocated_budget_raw'] = total
        data['summary_stats']['total_allocated_budget_jpy'] = format_amount(total)
        data['summary_stats']['budget_total_note'] = BUDGET_TOTAL_NOTE
    if 'kpis' in data:
        matches = [k for k in data['kpis'] if k.get('label') == '関連予算措置総額']
        if len(matches) != 1:
            raise Hold('Configure the aggregate KPI binding for this city')
        matches[0]['value'] = format_amount(total)
        matches[0]['badge'] = '参考・未確認分を除外'
        matches[0]['subtext'] = '登録額の集計（原典確認状況は記録ごとに異なります）'
    return data


def preserve_published(generated, published):
    """Use the accepted published JSON as the overlay, never a review draft.

    The caller must supply the tracked public file from its checked-out base.
    Budget records already using BudgetEvidence and progress event history win
    over stale seed constants. Unannotated policies are left as generated.
    """
    result = deepcopy(generated)
    old = policies({'pledges': published})
    new = policies({'pledges': result})
    if set(old) != set(new):
        raise Hold('Policy inventory changed; explicit migration required')
    for pid, p in old.items():
        if any('policy_relation' in r for r in p.get('budget_records', [])):
            new[pid]['budget_records'] = deepcopy(p['budget_records'])
        for key in ('latest_update', 'progress_history'):
            if key in p:
                new[pid][key] = deepcopy(p[key])
    return result
