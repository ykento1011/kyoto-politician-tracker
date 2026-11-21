"""Offline CLI. No command performs HTTP, git, publication or generation in-place."""
import argparse
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from .engine import PrivateOutput, propose, review_html, approved_bundle, publication_receipt, Hold
from .p1_bridge import P1Bridge
from .monitor import monitor_saved, request_plan


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def record_publication(args, out):
    """Validate caller-supplied observation, not independently verify deployment."""
    names = ('baseline', 'packet', 'approval', 'published_data')
    if any(not getattr(args, name) for name in names):
        raise Hold('Explicit baseline, packet, approval and published data required')
    if not all((args.commit, args.deployed_url, args.published_at)):
        raise Hold('Explicit commit, HTTPS URL and aware publication time required')
    paths = {name: Path(getattr(args, name)).resolve(strict=True) for name in names}
    if paths['published_data'] in [paths[n] for n in names[:3]]:
        raise Hold('Publication observation must be a separate supplied input')
    url = urlsplit(args.deployed_url)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or any(c.isspace() or ord(c) < 32 for c in args.deployed_url)):
        raise Hold('Valid absolute HTTPS publication URL required')
    try:
        url.port  # Reject malformed/out-of-range ports as well.
        when = datetime.fromisoformat(args.published_at.replace('Z', '+00:00'))
        if when.utcoffset() is None:
            raise ValueError('timezone missing')
    except ValueError as exc:
        raise Hold('Timezone-aware publication timestamp required') from exc
    # Hash the very bytes parsed, rather than rereading potentially changed files.
    raw = {name: path.read_bytes() for name, path in paths.items()}
    data = {name: json.loads(body.decode('utf-8-sig')) for name, body in raw.items()}
    bundle = approved_bundle(data['baseline'], data['packet'], data['approval'])
    receipt = publication_receipt(bundle, commit=args.commit,
        deployed_url=args.deployed_url, published_at=args.published_at,
        published_data=data['published_data'])
    receipt['observation_inputs'] = {name: {'sha256': sha256(body).hexdigest()}
                                     for name, body in raw.items()}
    receipt['verification_scope'] = 'supplied observation consistency only; deployment not independently verified'
    receipt['comparison_method'] = 'canonical JSON digest equality; candidate/public raw-byte equality not verified'
    out.json('publication_receipt_PRIVATE.json', receipt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['propose', 'handoff', 'monitor', 'publication-receipt'])
    parser.add_argument('--baseline')
    parser.add_argument('--output', required=True, help='Existing unique private run directory')
    parser.add_argument('--config')
    parser.add_argument('--previous-state')
    parser.add_argument('--rules')
    parser.add_argument('--city')
    parser.add_argument('--policies', nargs='+')
    parser.add_argument('--base-revision')
    parser.add_argument('--p1-code-root')
    parser.add_argument('--snapshot-root')
    parser.add_argument('--packet')
    parser.add_argument('--approval')
    parser.add_argument('--published-data', help='Saved JSON explicitly observed on the public side')
    parser.add_argument('--commit', help='Full externally observed public commit; no default')
    parser.add_argument('--deployed-url')
    parser.add_argument('--published-at', help='Explicit ISO timestamp with timezone; no clock fallback')
    args = parser.parse_args()
    out = PrivateOutput(args.output)
    if args.command == 'publication-receipt':
        record_publication(args, out)
        return
    if args.command == 'monitor':
        bridge = P1Bridge(args.p1_code_root, args.snapshot_root)
        config = load(args.config)
        result = monitor_saved(bridge, config['cities'][args.city],
                               load(args.previous_state) if args.previous_state else None)
        out.json('monitor_result.json', result)
        out.json('monitor_state.json', result['state'])
        out.json('future_request_plan.json', request_plan(config, args.city))
        return
    base = load(args.baseline)
    if args.command == 'handoff':
        # Human supplied receipt; no default approval/reviewer/timestamp.
        bundle = approved_bundle(base, load(args.packet), load(args.approval))
        out.json('reviewed_handoff_PRIVATE.json', bundle)
        return
    bridge = P1Bridge(args.p1_code_root, args.snapshot_root)
    mapped, holds = [], []
    for rule in load(args.rules):
        try:
            for spec in rule['source_specs']:
                bridge.extract(spec['source_url'], spec['sha256'])
            mapped.append(bridge.map_rule(rule))
        except ValueError as exc:
            holds.append({'rule_policy_id': rule.get('policy_id'), 'reason': str(exc)})
    out.json('p1_extraction_receipts.json', list(bridge.extractions.values()))
    packet, result = propose(base, mapped, city=args.city,
                             allowed=args.policies, base_revision=args.base_revision)
    out.json('run_status.json', {'proposal_count': len(packet['changes']) if packet else 0,
                                'holds': holds, 'network_requests': 0})
    if packet is None:
        return  # Deliberately no empty review/proposal artifacts.
    out.json('review_packet.json', packet)
    out.json('candidate_tracker_PRIVATE.json', result)
    out.write('review.html', review_html(packet))
    out.json('review_receipt_template.json', {
        'packet_id': packet['packet_id'], 'reviewer': '', 'reviewed_at': '',
        'decision': None, 'accepted_candidate_ids': [], 'publication_authorized': False})


if __name__ == '__main__':
    main()
