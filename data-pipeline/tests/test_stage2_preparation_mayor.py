"""Preparation inventory/probe bounds without native, networking or subprocess."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
import ipaddress
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'data-pipeline'))
from mayor_updates.launch_contract import FixedLaunch
from mayor_updates.stage2_flow import plan_bytes
from mayor_updates.projection import Hold

class PreparationTests(unittest.TestCase):
    def setUp(self):
        for name in ('subprocess.Popen','socket.socket.connect','socket.getaddrinfo'):
            p=patch(name,side_effect=AssertionError('Real operation forbidden'));p.start();self.addCleanup(p.stop)
    def test_all_native_activation_differences_still_disabled(self):
        data=json.loads((ROOT/'config/stage2_activation_inventory.json').read_bytes())
        self.assertFalse(data['enabled'])
        changes=data['source_changes_required_for_separately_approved_native_run']
        self.assertEqual(len(changes),5)
        for change in changes:
            text=(ROOT/change['file']).read_text(encoding='utf-8')
            self.assertFalse(change['current']);self.assertTrue(change['candidate'])
            self.assertEqual(text.count(change['symbol']+' = False'),1)
        restore=(ROOT/'scripts/Restore-Stage2Firewall.ps1').read_text()
        self.assertIn('$script:LiveFirewallChangesEnabled=$false',restore)
        self.assertIn("if($Apply){throw 'Live Firewall changes disabled",restore)
    def test_fixed_probe_addresses_and_finite_attempt_budget(self):
        data=json.loads((ROOT/'config/stage2_probe_plan.json').read_bytes())
        self.assertFalse(data['enabled']);self.assertFalse(data['network_enabled'])
        self.assertEqual(data['retry_count'],0);self.assertEqual(data['http_requests'],0)
        self.assertEqual(sum(p['baseline_attempts']+p['blocked_attempts'] for p in data['probes']),9)
        self.assertEqual(data['max_client_attempts'],9)
        for p in data['probes'][:4]:
            self.assertEqual(ipaddress.ip_address(p['destination']).version,p['family'])
            self.assertIn(p['port'],(53,443))
            if p['transport']=='UDP':self.assertEqual(p['max_datagrams_per_attempt'],1)
        self.assertEqual(data['probes'][-1]['service_sid'],'S-1-5-20')
        self.assertEqual(data['probes'][-1]['baseline_attempts'],0)
    def test_native_plan_proposal_does_not_grant_execution(self):
        spec=FixedLaunch(r'C:\fixture\pwsh.exe',(),sha256(b'x').hexdigest(),'b'*64,'S-1-5-21-1-2-3-1004')
        synthetic=json.loads(plan_bytes(spec,'a'*32,'b'*64))
        native=json.loads(plan_bytes(spec,'a'*32,'b'*64,simulation=False))
        self.assertTrue(synthetic['synthetic']);self.assertFalse(native['synthetic'])
        self.assertFalse(native['live_enabled']);self.assertFalse(native['fixed_launch']['enabled'])
        with self.assertRaises(Hold):plan_bytes(spec,'a'*32,'b'*64,simulation=1)
    def test_copy_preparation_never_has_process_or_download_backend(self):
        path=ROOT/'scripts/prepare_stage2_python.py'
        spec=importlib.util.spec_from_file_location('stage2_copy',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.pe_imports(b'ordinary source'),[])
        text=path.read_text()
        self.assertNotIn('subprocess',text.replace("'subprocess'",''))
        self.assertIn("destination.mkdir()",text)
        self.assertIn("target.open('xb')",text)

if __name__=='__main__':unittest.main()
