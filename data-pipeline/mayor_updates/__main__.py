"""Offline CLI. No command performs HTTP, git, publication or generation in-place."""
import argparse
import json
from pathlib import Path
from .engine import PrivateOutput, propose, review_html, approved_bundle
from .p1_bridge import P1Bridge
from .monitor import monitor_saved, request_plan


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['propose', 'handoff', 'monitor'])
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
    args = parser.parse_args()
    out = PrivateOutput(args.output)
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
