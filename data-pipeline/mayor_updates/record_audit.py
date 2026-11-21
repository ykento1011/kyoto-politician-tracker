"""Read-only audit of one explicitly scheduled periodic/continuous cycle."""
import argparse
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re

from .engine import PrivateOutput


def aware(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('Explicit timezone required')
    return result


def safe_path(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        stat = item.lstat()
        if item.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Redirected record path')
    return path


def read_json(path, evidence):
    raw = safe_path(path).read_bytes()
    evidence[str(path)] = sha256(raw).hexdigest()
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('Duplicate JSON key')
            obj[key] = value
        return obj
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if not isinstance(value, dict):
        raise ValueError('Record must be a JSON object')
    return value


def inspect(schedule_path, records_root, evaluated_at):
    evidence = {}
    result = {'classification': 'invalid_evidence', 'evidence_sha256': evidence,
              'os_start': 'unknown', 'last_good_commit': 'not_verified',
              'publication': 'not_verified', 'automatic_start': 'not_verified',
              'evaluated_at': evaluated_at}
    try:
        now = aware(evaluated_at)
        spec = read_json(Path(schedule_path), evidence)
        result['target'] = spec
        for name in ('approved', 'paused', 'applicable'):
            if type(spec[name]) is not bool:
                raise ValueError('Explicit boolean schedule eligibility required')
        if not isinstance(spec['approval_reference'], str) or not spec['approval_reference'].strip():
            if spec['approved']:
                raise ValueError('Approved schedule requires an approval reference')
        key = spec['cycle_key']
        if not isinstance(key, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', key):
            raise ValueError('Explicit ISO cycle key required')
        date.fromisoformat(key)
        scheduled, deadline = aware(spec['scheduled_at']), aware(spec['deadline'])
        if deadline < scheduled:
            raise ValueError('Deadline precedes schedule')
        identity = spec['identity']
        if not isinstance(identity, dict) or not re.fullmatch('[0-9a-f]{64}', spec['series_id']):
            raise ValueError('Series is the existing manifest SHA, not a guessed label')
        if identity.get('manifest_sha256') != spec['series_id']:
            raise ValueError('Series/identity mismatch')
        if spec['format'] == 'continuous':
            if spec['mode'] != 'offline' or identity.get('city') != spec['city']:
                raise ValueError('Continuous reader supports offline city identity only')
            binding, intent_name = 'loop_identity.json', 'intent.json'
        elif spec['format'] == 'periodic':
            if (spec['city'] != 'kyoto' or identity.get('adapter') != 'kyoto-weekly-v1'
                    or spec['mode'] not in {'offline', 'approved_acquisition'}
                    or identity.get('mode') != spec['mode']):
                raise ValueError('Periodic mode/city identity mismatch')
            binding, intent_name = 'periodic_identity.json', 'reservation.json'
        else:
            raise ValueError('Unsupported record format')
        if not spec['approved'] or spec['paused'] or not spec['applicable']:
            result['classification'] = 'not_expected'
            return result
        root = safe_path(records_root)
        # Listing errors are evidence errors, never an empty successful listing.
        names = {p.name for p in root.iterdir()}
        bound = None
        if binding in names:
            bound = read_json(root/binding, evidence)
            if bound != identity:
                raise ValueError('Saved root identity mismatch')
        cycles = root/'cycles'
        cycle = cycles/key
        found = {}
        if 'cycles' in names:
            safe_path(cycles)
            cycle_names = {p.name for p in cycles.iterdir()}
            if key in cycle_names:
                safe_path(cycle)
                entries = {p.name for p in cycle.iterdir()}
                for name in (intent_name, 'cycle_result.json', 'failure.json', 'safety_hold.json', 'run_status.json'):
                    if name in entries:
                        found[name] = read_json(cycle/name, evidence)
                if bound is None:
                    raise ValueError('Cycle exists without root identity')
                if intent_name not in found:
                    result['classification'] = 'incomplete_evidence'
                    if found:
                        raise ValueError('Result without identity-bearing intent')
                    return result
        if found:
            intent = found[intent_name]
            if any(intent.get(k) != v for k, v in identity.items()) or intent.get('cycle_key') != key:
                raise ValueError('Intent identity/cycle mismatch')
            if spec['format'] == 'continuous' and intent.get('network_requests') != 0:
                raise ValueError('Offline intent mode mismatch')
            for name, item in found.items():
                if 'cycle_key' in item and item['cycle_key'] != key:
                    raise ValueError('Record cycle mismatch: '+name)
                if 'mode' in item and item['mode'] != spec['mode']:
                    raise ValueError('Record mode mismatch: '+name)
                if 'scheduled_at' in item and aware(item['scheduled_at']) != scheduled:
                    raise ValueError('Record scheduled time mismatch: '+name)
            if 'failure.json' in found and not isinstance(found['failure.json'].get('reason'), str):
                raise ValueError('Malformed failure record')
            if ('safety_hold.json' in found and
                    found['safety_hold.json'].get('state') != 'stopped_no_public_change'):
                raise ValueError('Malformed safety HOLD record')
            if ('failure.json' in found or 'safety_hold.json' in found or
                    any(item.get('state') == 'stopped_no_public_change' for item in found.values())):
                result['classification'] = 'hold_or_failure'
            elif 'cycle_result.json' in found:
                summary = found['cycle_result.json']
                if summary.get('cycle_key') != key or summary.get('state') not in {
                        'source_review_pending', 'evidence_review_pending', 'source_version_only',
                        'unchanged', 'review_pending', 'no_policy_diff'}:
                    raise ValueError('Incomplete or unknown result schema')
                result['classification'] = 'result_recorded'
                result['reported_state'] = summary['state']
            else:
                result['classification'] = 'incomplete_evidence'
        else:
            result['classification'] = 'before_deadline' if now < deadline else 'missing_evidence'
        return result
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result.update(classification='invalid_evidence', reason=str(exc))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', required=True)
    parser.add_argument('--records-root', required=True)
    parser.add_argument('--evaluated-at', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = PrivateOutput(args.output)
    root = Path(args.records_root).resolve()
    source = Path(args.schedule).resolve()
    if (out.root == root or root in out.root.parents or out.root in root.parents
            or out.root == source.parent or out.root in source.parents):
        raise ValueError('Output must be separate from input records and schedule')
    result = inspect(args.schedule, args.records_root, args.evaluated_at)
    out.json('operation_record_audit_PRIVATE.json', result)
    if result['classification'] == 'invalid_evidence':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
