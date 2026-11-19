"""One offline transaction: audit, probes, worker and independent recovery."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import stage2_acceptance as flow
from mayor_updates.projection import Hold

PLAN = {'run_id': 'a'*32, 'native_plan_sha256': 'b'*64,
        'sid': 'S-1-5-21-1-2-3-1004', 'audit_seconds': 60, 'event_limit': 64}


class FakePorts:
    simulation_only = True

    def __init__(self, fail='', mutate=None):
        self.fail, self.mutate = fail, mutate
        self.now = 0.
        self.audit = {flow.CONNECTION: {'success': False, 'failure': False},
                      flow.PACKET: {'success': False, 'failure': False}}
        self.calls, self.denials = [], []
        self.rules = []
        self.client = dict(pid=100, started=10, image='fixture-probe.exe', sid=PLAN['sid'],
                           retained_process_handle=True, image_verified=True)
        self.dns = dict(pid=200, started=5, image='fixture-svchost.exe', sid='S-1-5-20',
                        retained_process_handle=True, image_verified=True)

    def call(self, name):
        self.calls.append(name)
        self.now += .1
        if self.fail == name:
            raise OSError('synthetic '+name)

    def preflight(self, plan):
        self.call('preflight')
        return dict(owner_only=True, recovery_local=True, source_pins_valid=True,
                    existing_rules_absent=True, gpo_audit_unmanaged=True,
                    bypass_paths_excluded=True, resolvers=['192.0.2.53'], dns=self.dns,
                    restore_watchdog_ready=True)

    def read_audit(self):
        self.call('read_audit')
        return copy.deepcopy(self.audit)

    def set_failure(self, guid, value, **kw):
        self.call('enable' if value else 'restore_audit')
        assert guid == flow.CONNECTION
        self.audit[guid]['failure'] = value
        if not value and self.mutate == 'late_audit_restore': self.now+=61
        if not value and self.mutate == 'audit_tail_events': self.add_tail(59)
        if value and self.mutate == 'success_bit':
            self.audit[guid]['success'] = True
        if value and self.mutate == 'packet_bit':
            self.audit[flow.PACKET]['failure'] = True
        if value and self.mutate == 'enable_then_fail':
            raise OSError('side effect before throw')

    def audit_other_settings_unchanged(self):
        return True

    def log_boundary(self):
        self.call('log_boundary')
        return dict(enabled=True, maximum_bytes=20971520, oldest=1, latest=100+len(self.denials),
                    cleared=self.mutate == 'clear', evidence_missing=self.mutate == 'record_gap')

    def export_security(self, phase, rid):
        self.call('export_'+phase)
        return dict(readback=True, owner_only=True, complete=self.mutate != 'incomplete_archive',
                    first_record=1, last_record=100+len(self.denials), sha256='c'*64, missing_records=[])

    def apply_and_verify_rules(self, rules, **kw):
        self.call('rules')
        self.rules = rules
        return {1: rules[0], 2: rules[1]}

    def probe(self, name, *, blocked, run_id, **kw):
        self.call('blocked_'+name if blocked else 'baseline_'+name)
        target = flow.TARGETS.get(name, ('192.0.2.53', 53, 17))
        result = dict(run_id=run_id, probe_id=name, blocked=blocked, client_calls=1,
                      retries=0, http_requests=0, actor=self.client, target=target,
                      reachable=True, external_egress=False, start_tick=20, end_tick=30,
                      tuple=['192.0.2.10', 34567, *target])
        if ':' in target[0]: result['tuple'][0]='2001:db8::10'
        if self.mutate == 'wrong_observed_destination':
            result['tuple']=['192.0.2.10',34567,'203.0.113.1',22,6]
        if self.mutate == 'wrong_observed_family': result['tuple'][0]='2001:db8::10'
        if name == 'system_dns_proxy':
            result.update(query='stage2-'+run_id+'.example.com.', resolvers=['192.0.2.53'],
                          cached=False, query_complete=True, pending_service_requests=0,
                          service_send_count=1, service_send_count_verified=True,
                          service_before=self.dns, service_after=self.dns)
        if blocked:
            event = dict(run_id=run_id, probe_id=name, event_id=5157,
                         record_id=101+len(self.denials), filter_id=2, rule_name=self.rules[1],
                         direction='Outbound', utc_tick=25, tuple=result['tuple'],
                         owner=copy.deepcopy(self.dns if name == 'system_dns_proxy' else self.client))
            if self.mutate == 'inbound_filter':
                event.update(filter_id=1, rule_name=self.rules[0])
            if self.mutate == 'boolean_count': result['client_calls']=True
            if name == 'system_dns_proxy':
                event['query'] = result['query']
            if self.mutate == 'missing_deny':
                return result
            for key in ('filter_id', 'event_id', 'run_id', 'tuple', 'rule_name', 'utc_tick'):
                if self.mutate == key:
                    event[key] = 999 if isinstance(event[key], int) else 'wrong'
            if self.mutate == 'sid': event['owner']['sid'] = 'S-1-5-21-9-1006'
            if self.mutate == 'pid_reuse': event['owner']['started'] += 1
            if self.mutate == 'duplicate_deny':
                extra=copy.deepcopy(event);extra['record_id']+=1000;self.denials.append(extra)
            if name == 'system_dns_proxy':
                if self.mutate == 'dns_requester': event['owner']=self.client
                if self.mutate == 'dns_count': result['service_send_count']=9
                if self.mutate == 'dns_unknown_count': result['service_send_count_verified']=False
                if self.mutate == 'dns_pending': result['pending_service_requests']=1
                if self.mutate == 'dns_cached': result['cached']=True
            self.denials.append(event)
            if self.mutate == 'deadline': self.now+=61
        return result

    def read_denials(self, rid, limit, after_record, **kw):
        self.call('read_denials')
        values=copy.deepcopy([e for e in self.denials if e['record_id']>after_record])
        if self.mutate == 'event_cap':
            values=[dict(values[0], record_id=101+i) for i in range(64)]
        return dict(events=values[:limit], truncated=len(values)>limit or self.mutate=='truncated',
                    lost=1 if self.mutate=='lost' else 0)

    def confirm_local_exit(self, rid, result, **kw):
        self.call('operator')
        if self.mutate == 'operator_tail_events': self.add_tail(59)
        if self.mutate == 'operator_cancel': raise KeyboardInterrupt('synthetic cancellation')
        return dict(run_id=rid, onsite_exit_confirmed=True)

    def add_tail(self, count):
        last=max(e['record_id'] for e in self.denials)
        self.denials.extend(dict(self.denials[0],record_id=last+i+1) for i in range(count))

    def restore_exact_rules_by_operator(self, rules, **kw):
        self.call('restore_rules')
        return dict(removed=rules, both_stores_absent=True, baseline_unchanged=True)

    def stop_and_confirm_job(self):
        self.call('stop_job')
        return self.mutate != 'unknown_exit'


class FakeWorker:
    simulation_only = True

    def __init__(self, ports): self.ports=ports

    def run(self):
        self.ports.call('worker')
        return dict(run_id=PLAN['run_id'], plan_sha256=PLAN['native_plan_sha256'],
                    termination_confirmed=True, cleanup_complete=True,
                    all_descendants_exited=self.ports.mutate != 'unknown_exit')


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        for name in ('subprocess.Popen', 'socket.socket.connect', 'socket.getaddrinfo'):
            p=patch(name, side_effect=AssertionError('Live OS/network forbidden'))
            p.start();self.addCleanup(p.stop)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def execute(self, **kw):
        ports=FakePorts(**kw)
        result=flow.run(self.root, PLAN, ports, FakeWorker(ports), simulation=True, clock=lambda:ports.now)
        return result, ports

    def test_full_transaction(self):
        result, ports=self.execute()
        self.assertEqual(result['state'], 'PASS')
        self.assertEqual((result['client_attempts'],result['event_count']),(9,5))
        self.assertTrue(result['audit_restored'] and result['firewall_restored'])
        self.assertLess(ports.calls.index('export_before'),ports.calls.index('enable'))
        self.assertLess(ports.calls.index('worker'),ports.calls.index('restore_rules'))
        self.assertLess(ports.calls.index('restore_rules'),ports.calls.index('restore_audit'))
        self.assertFalse(json.loads((self.root/'result.json').read_bytes())['real_execution_authorized'])

    def test_attribution_failures_keep_firewall_and_restore_audit(self):
        for case in ('missing_deny','filter_id','event_id','run_id','tuple','rule_name','utc_tick',
                     'sid','pid_reuse','duplicate_deny','inbound_filter','boolean_count','dns_requester','dns_count',
                     'dns_unknown_count','dns_pending','dns_cached','truncated','lost','event_cap','deadline'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                ports=FakePorts(mutate=case)
                r=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(r['state'],'HOLD')
                self.assertTrue(r['audit_restored'])
                self.assertNotIn('restore_rules',ports.calls)
                self.assertLessEqual(r['event_count'],64)

    def test_failures_at_side_effect_boundaries(self):
        for phase in ('enable','rules','blocked_tcp4','read_denials','worker','operator','restore_rules'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as root:
                ports=FakePorts(fail=phase)
                r=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(r['state'],'HOLD')
                self.assertTrue(r['audit_restored'])
                self.assertIn('restore_audit', ports.calls)

    def test_partial_enable_still_restores(self):
        r,ports=self.execute(mutate='enable_then_fail')
        self.assertEqual(r['state'],'HOLD');self.assertTrue(r['audit_restored'])
        self.assertNotIn('rules',ports.calls)

    def test_mutation_or_restore_failure_cannot_pass(self):
        for kw in ({'mutate':'success_bit'},{'mutate':'packet_bit'}, {'fail':'restore_audit'}):
            with tempfile.TemporaryDirectory() as root:
                ports=FakePorts(**kw)
                r=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(r['state'],'HOLD');self.assertFalse(r['audit_restored'])

    def test_security_evidence_gap_or_clear_holds(self):
        for case in ('clear','record_gap','incomplete_archive'):
            with tempfile.TemporaryDirectory() as root:
                ports=FakePorts(mutate=case)
                r=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(r['state'],'HOLD');self.assertTrue(r['audit_restored'])

    def test_export_failure_never_enables_audit(self):
        r,ports=self.execute(fail='export_before')
        self.assertEqual(r['state'],'HOLD');self.assertNotIn('enable',ports.calls)

    def test_unconfirmed_job_never_removes_firewall(self):
        r,ports=self.execute(mutate='unknown_exit')
        self.assertFalse(r['termination_confirmed']);self.assertNotIn('restore_rules',ports.calls)
        self.assertTrue(r['audit_restored'])

    def test_failed_evidence_write_still_restores_audit(self):
        original=flow._record
        def failing(root,name,body):
            if name=='filter_binding.json':raise OSError('synthetic disk full')
            original(root,name,body)
        with patch.object(flow,'_record',side_effect=failing):
            r,ports=self.execute()
        self.assertEqual(r['state'],'HOLD');self.assertTrue(r['audit_restored'])
        self.assertNotIn('restore_rules',ports.calls)

    def test_live_rejected_before_start_record_or_ports(self):
        ports=FakePorts()
        with self.assertRaises(Hold):flow.run(self.root,PLAN,ports,FakeWorker(ports))
        self.assertEqual(ports.calls,[]);self.assertEqual(list(self.root.iterdir()),[])

    def test_consumed_run_never_retries(self):
        self.execute()
        ports=FakePorts()
        with self.assertRaises(Hold):
            flow.run(self.root,PLAN,ports,FakeWorker(ports),simulation=True)
        self.assertEqual(ports.calls,[])

    def test_connects_existing_worker_completion_protocol(self):
        # Reuse the accepted fixture/engine, not a second launch/Job algorithm.
        from test_stage2_flow_mayor import FlowTests
        from mayor_updates import stage2_flow
        from hashlib import sha256
        fixture=FlowTests('test_single_launch_job_journal_plan_and_manual_handoff')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        plan=dict(PLAN, native_plan_sha256=sha256(stage2_flow.plan_bytes(
            fixture.spec, PLAN['run_id'], fixture.script_sha)).hexdigest())
        class ExistingWorker:
            simulation_only=True
            def run(self):
                result=fixture.run_flow()
                stage2_flow.commit_flow_success(fixture.root,result)
                return flow.WorkerFlow.completion(fixture.root)
        ports=FakePorts()
        result=flow.run(self.root,plan,ports,ExistingWorker(),simulation=True,clock=lambda:ports.now)
        self.assertEqual(result['state'],'PASS')
        self.assertTrue(result['termination_confirmed'])
        self.assertEqual(fixture.api.creations,1)

    def test_late_rollback_is_restored_but_cannot_pass(self):
        result,ports=self.execute(mutate='late_audit_restore')
        self.assertEqual(result['state'],'HOLD');self.assertTrue(result['audit_restored'])
        self.assertTrue(any('including rollback' in x for x in result['errors']))

    def test_final_drain_includes_operator_and_rollback_events(self):
        for case in ('operator_tail_events','audit_tail_events'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                ports=FakePorts(mutate=case)
                result=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(result['state'],'HOLD');self.assertTrue(result['audit_restored'])
                self.assertEqual(result['event_count'],64)
                self.assertIn('export_after',ports.calls)

    def test_observed_tuple_must_match_fixed_metadata(self):
        for case in ('wrong_observed_destination','wrong_observed_family'):
            with tempfile.TemporaryDirectory() as root:
                ports=FakePorts(mutate=case)
                result=flow.run(root,PLAN,ports,FakeWorker(ports),simulation=True,clock=lambda:ports.now)
                self.assertEqual(result['state'],'HOLD')
                self.assertNotIn('enable',ports.calls)

    def test_cancel_restores_audit_and_preserves_block(self):
        result,ports=self.execute(mutate='operator_cancel')
        self.assertEqual(result['state'],'HOLD');self.assertTrue(result['audit_restored'])
        self.assertNotIn('restore_rules',ports.calls)


if __name__=='__main__':unittest.main()
