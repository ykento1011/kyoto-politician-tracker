"""New connection tests only: no native calls, processes or network."""
import copy
import json
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates import stage2_os_adapter as adapter
from mayor_updates import stage2_acceptance as flow
from mayor_updates.projection import Hold
from test_stage2_acceptance_mayor import PLAN, FakePorts, FakeWorker

BINDING = dict(run_id='a'*32, runtime_sha256='c'*64, plan_sha256='b'*64, nonce='d'*64)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        for name in ('subprocess.Popen', 'socket.socket', 'socket.getaddrinfo'):
            p = patch(name, side_effect=AssertionError('Live operation forbidden'))
            p.start(); self.addCleanup(p.stop)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.peer = Mock()
        self.now = 0

    def mailbox(self, mutate=None, respond=True):
        (self.root/'agent_ready.json').write_text(json.dumps(dict(binding=BINDING, identity={'pid':9})))
        def sleep(_):
            self.now += 1
            request = self.root/'request-0001.json'
            response = self.root/'response-0001.json'
            if respond and request.exists() and not response.exists():
                row = json.loads(request.read_bytes())
                row.update(ok=True, result={'value':42})
                row.pop('payload')
                if mutate: mutate(row)
                response.write_text(json.dumps(row))
        return adapter.Mailbox(self.root, BINDING, lambda p:None, self.peer,
                               clock=lambda:self.now, sleep=sleep)

    def test_ipc_authenticated_echo(self):
        box=self.mailbox()
        self.assertEqual(box.call('preflight'), {'value':42})
        self.peer.assert_called_once_with({'pid':9}, elevated=True)

    def test_ipc_rejects_binding_sequence_operation_and_error(self):
        mutations = [lambda r,k=k:r['binding'].update({k:'e'*len(BINDING[k])}) for k in BINDING]
        mutations += [lambda r:r.update(sequence=2), lambda r:r.update(operation='finish'),
                      lambda r:r.update(ok=False,error='PIN mismatch')]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as root:
                self.root=Path(root);self.now=0
                with self.assertRaises(Hold):self.mailbox(mutate).call('preflight')

    def test_peer_pin_failure_prevents_request(self):
        box=self.mailbox();self.peer.side_effect=Hold('PIN/token mismatch')
        with self.assertRaises(Hold):box.call('preflight')
        self.assertFalse(list(self.root.glob('request*')))

    def test_timeout_consumes_sequence_and_independent_stop(self):
        box=self.mailbox(respond=False)
        ports=adapter.WindowsPorts(box,None,PLAN,None,None)
        with self.assertRaises(Hold):ports.set_failure(flow.CONNECTION,True,deadline=2)
        self.assertTrue((self.root/'request-0001.json').exists())
        self.assertTrue((self.root/'STOP.json').exists())
        before=(self.root/'STOP.json').read_bytes()
        box.restore_audit_out_of_band()
        self.assertEqual(before,(self.root/'STOP.json').read_bytes())
        with self.assertRaises(Hold):box.call('set_failure')
        self.assertFalse((self.root/'request-0002.json').exists())

    def test_duplicate_json_rejected(self):
        p=self.root/'duplicate.json';p.write_text('{"run_id":1,"run_id":2}')
        with self.assertRaises(Hold):adapter.read_json(p)

    def test_native_entry_source_disabled_before_io(self):
        from mayor_updates import stage2_native_entry
        with patch.object(Path,'read_bytes',side_effect=AssertionError('No runtime read')):
            with self.assertRaises(Hold):stage2_native_entry.run('missing','a'*64)

    def test_dns_identity_unknown_or_reused_rejected(self):
        fake=FakePorts();ports=adapter.WindowsPorts(None,None,PLAN,None,None)
        ports.dns=fake.dns
        receipt=dict(start_tick=20,end_tick=30,probe_id='system_dns_proxy',
                     resolvers=['192.0.2.53'],query_complete=True,service_send_count_verified=True)
        event=dict(utc_tick=25,owner=copy.deepcopy(fake.dns),tuple=['192.0.2.10',123, '192.0.2.53',53,17])
        self.assertTrue(ports._match(receipt,event))
        for key,value in [('sid',PLAN['sid']),('pid',999),('started',99),('retained_process_handle',False)]:
            changed=copy.deepcopy(event);changed['owner'][key]=value
            try: matched=ports._match(receipt,changed)
            except Hold: matched=False
            self.assertFalse(matched,key)
        self.assertFalse(ports._match(dict(receipt,service_send_count_verified=False),event))

    def test_event_payload_identity_and_xml_pin(self):
        owner=FakePorts().client
        row=dict(xml='<Event/>',xml_sha256=sha256(b'<Event/>').hexdigest(),event_id=5157,
                 provider='Microsoft-Windows-Security-Auditing',record_id=1,utc_tick=25,owner=owner,
                 fields=dict(ProcessID='100',Application='device-path',SourceAddress='192.0.2.10',
                             SourcePort='123',DestAddress='1.1.1.1',DestPort='443',Protocol='6',
                             FilterRTID='2',LayerRTID='1',Direction='%%14593'))
        self.assertEqual(adapter.decode_5157(row,device_to_dos=lambda _:owner['image'])['payload_pid'],100)
        for change in ('pid','hash','image'):
            bad=copy.deepcopy(row)
            if change=='pid':bad['fields']['ProcessID']='101'
            if change=='hash':bad['xml_sha256']='0'*64
            with self.assertRaises(Hold):adapter.decode_5157(bad,device_to_dos=lambda _: 'wrong' if change=='image' else owner['image'])

    def test_worker_bridge_uses_existing_completion_capability(self):
        from mayor_updates import stage2_flow, stage2_guard
        root=self.root/'native';(root/'journal').mkdir(parents=True)
        done=dict(run_id=PLAN['run_id'],plan_sha256=PLAN['native_plan_sha256'],termination_confirmed=True,cleanup_complete=True)
        (root/'journal/termination_confirmed.json').write_text(json.dumps(done))
        with patch.object(stage2_flow,'run_native_stage2',return_value={'synthetic':True}) as launch, \
             patch.object(stage2_flow,'commit_flow_success') as commit, \
             patch.object(stage2_guard,'restore_evidence') as capability:
            bridge=flow.WorkerFlow(root,'fake-spec',{})
            self.assertTrue(bridge.run()['all_descendants_exited'])
            launch.assert_called_once();commit.assert_called_once();capability.assert_called_once()
            capability.side_effect=Hold('Invalid capability')
            with self.assertRaises(Hold):bridge.completion(root)

    def test_new_native_gate_does_not_enable_simulation_as_live(self):
        ports=FakePorts()
        with self.assertRaises(Hold):flow.run(self.root,PLAN,ports,FakeWorker(ports),simulation=False)
        self.assertFalse(list(self.root.iterdir()))

    def test_ports_transaction_with_existing_worker_bridge(self):
        """Drive real WindowsPorts through fake admin RPC, not old FakePorts alone."""
        from mayor_updates import stage2_flow, stage2_guard
        class SimPorts(adapter.WindowsPorts):simulation_only=True
        class SimWorker(flow.WorkerFlow):simulation_only=True
        for failure in ('','dns_identity','audit_restore'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as root:
                root=Path(root);transaction=root/'transaction';transaction.mkdir()
                native=root/'native';(native/'journal').mkdir(parents=True)
                fake=FakePorts();peer=Mock()
                def rpc_call(op,payload=None,**kw):
                    p=payload or {}
                    if op=='preflight':return dict(fake.preflight(PLAN),guardian={'pid':99})
                    if op=='read_audit':return fake.read_audit()
                    if op=='set_failure':
                        if failure=='audit_restore' and not p['value']:raise Hold('restore failure')
                        return fake.set_failure(p['guid'],p['value'])
                    if op=='log_boundary':return fake.log_boundary()
                    if op=='export_security':return fake.export_security(p['phase'],PLAN['run_id'])
                    if op=='apply_rules':
                        rules=['GikaiMikata-Stage2-'+PLAN['run_id']+'-'+d for d in ('Inbound','Outbound')]
                        fake.apply_and_verify_rules(rules)
                        return [dict(id=i+1,rule=r,origin=r,snapshot_unchanged=True) for i,r in enumerate(rules)]
                    if op=='read_denials':
                        rows=[]
                        for e in fake.denials:
                            if e['record_id']<=p['after']:continue
                            owner=copy.deepcopy(e['owner'])
                            if failure=='dns_identity' and e['probe_id']=='system_dns_proxy':owner['started']+=1
                            t=e['tuple'];xml='<Event>'+str(e['record_id'])+'</Event>'
                            rows.append(dict(xml=xml,xml_sha256=sha256(xml.encode()).hexdigest(),event_id=5157,
                                provider='Microsoft-Windows-Security-Auditing',record_id=e['record_id'],utc_tick=25,
                                owner=owner,filter_origin=e['rule_name'],fields=dict(ProcessID=str(owner['pid']),
                                Application=owner['image'],SourceAddress=t[0],SourcePort=str(t[1]),DestAddress=t[2],
                                DestPort=str(t[3]),Protocol=str(t[4]),FilterRTID='2',LayerRTID='1',Direction='%%14593')))
                        return dict(events=rows,lost=0,truncated=False)
                    if op=='dns_evidence':return p['receipt']
                    if op=='confirm_exit':return fake.confirm_local_exit(PLAN['run_id'],p['completion'])
                    if op=='restore_rules':return fake.restore_exact_rules_by_operator(fake.rules)
                    if op=='audit_unchanged':return True
                    raise AssertionError(op)
                rpc=Mock();rpc.call.side_effect=rpc_call
                probes=Mock();probes.run.side_effect=lambda name,blocked,rid,resolvers,deadline:fake.probe(name,blocked=blocked,run_id=rid)
                ports=SimPorts(rpc,probes,PLAN,peer,lambda x:x,clock=lambda:fake.now)
                done=dict(run_id=PLAN['run_id'],plan_sha256=PLAN['native_plan_sha256'],termination_confirmed=True,cleanup_complete=True)
                def native_flow(*args,**kw):
                    fake.call('worker')
                    (native/'journal/termination_confirmed.json').write_text(json.dumps(done))
                    return {'synthetic':True}
                with patch.object(stage2_flow,'run_native_stage2',side_effect=native_flow), \
                     patch.object(stage2_flow,'commit_flow_success'), patch.object(stage2_guard,'restore_evidence'):
                    result=flow.run(transaction,PLAN,ports,SimWorker(native,'fake',{}),simulation=True,clock=lambda:fake.now)
                self.assertEqual(result['state'],'PASS' if not failure else 'HOLD',result['errors'])
                if failure=='dns_identity':self.assertNotIn('worker',fake.calls)
                if failure=='audit_restore':rpc.restore_audit_out_of_band.assert_called()
                if not failure:
                    self.assertEqual((result['client_attempts'],result['event_count']),(9,5))
                    self.assertTrue(result['audit_restored'] and result['firewall_restored'])


if __name__=='__main__':unittest.main()
