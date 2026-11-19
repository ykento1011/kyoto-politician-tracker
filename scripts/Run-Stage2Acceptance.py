"""Explicit offline transaction demo. NO live mode, Windows calls or activation.

The fixture implementation is deliberately loaded from the repository's tests,
not represented as a native OS adapter. Real Stage 2 must not invoke this demo.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', required=True)
    parser.add_argument('--state-root', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    fixture = repo/'data-pipeline/tests/test_stage2_acceptance_mayor.py'
    spec = importlib.util.spec_from_file_location('stage2_offline_fixture', fixture)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Reject any existing directory, even an empty one. No historical state reuse.
    args.state_root.mkdir(exist_ok=False)
    ports = module.FakePorts()
    result = module.flow.run(args.state_root, module.PLAN, ports,
                             module.FakeWorker(ports), simulation=True,
                             clock=lambda: ports.now)
    print(json.dumps({'mode': 'SYNTHETIC_OFFLINE_ONLY', 'result': result,
                      'real_firewall_changes': 0, 'real_audit_changes': 0,
                      'real_probes': 0, 'real_worker_launches': 0}, sort_keys=True))
    return 0 if result['state'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
