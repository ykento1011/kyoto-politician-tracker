"""Amounts and reviewed overlays shared by proposals and the Kyoto generator."""
from copy import deepcopy

BUDGET_TOTAL_NOTE = '登録済み予算の集計です。確認区分を付けた参考・未確認の予算は除外していますが、全額の原典確認を済ませた総額ではありません。'

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
    # Delta / after-change / settlement are not additive to the legacy total.
    if record.get('amount_role', 'initial') != 'initial':
        raise Hold('Fiscal-series reconciliation required before total inclusion')
    if record.get('budget_kind', 'initial') != 'initial':
        raise Hold('Non-initial amount cannot enter legacy budget total')
    if record.get('evidence_status') == 'unverified':
        raise Hold('Unverified direct amount cannot enter total')
    return True


def sync_totals(data):
    total = 0
    for p in data['pledges']:
        for r in p.get('budget_records', []):
            if included(r):
                n = r['amount_jpy']
                if type(n) is not int or n < 0:
                    raise Hold('Invalid legacy amount')
                total += n
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
