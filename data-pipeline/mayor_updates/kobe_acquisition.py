"""Disabled-by-contract Kobe HTML1 entry. No schedule or automatic activation."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--contract-sha256', required=True)
    args = parser.parse_args()
    runtime = json.loads(Path(args.runtime).read_text(encoding='utf-8-sig'))
    from .dependency_preflight import require_contract
    # Reuse offline processing preflight; acquisition requires its own separately
    # pinned, explicit per-week authorization, checked before any reservation.
    require_contract(runtime, args.contract, args.contract_sha256)
    from . import weekly, continuous
    continuous.configure_shell(runtime)
    weekly.assert_owner_only(args.runtime)
    weekly.assert_owner_only(args.contract)
    for spec in runtime['code_files'] + runtime['resource_files']:
        weekly.pinned_input(spec)
    from .kobe_html_connection import run_connected
    result = run_connected(runtime)
    print(json.dumps(result, ensure_ascii=False))
    if result['state'] != 'private_result_saved':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
