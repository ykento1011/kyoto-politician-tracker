"""Synthetic offline contract tests; no private originals or network needed."""
import copy
import hashlib
import json
from unittest.mock import patch
import unittest
import test_source_registry_mayor as fixtures
from mayor_updates import evidence_handoff as h
from mayor_updates.projection import Hold


class HandoffTests(fixtures.RegistryTests):
    # Reuse fixture helpers, not the parent's already-covered test methods.
    def setUp(self):
        super().setUp(); self.scan([(self.url,'予算案')])
        self.out=self.root/'handoff';self.out.mkdir()
        self.spec=self.receipt_spec()
        def evidence(s):
            rec,_=self.bridge.record(s['source_url'],s['sha256'])
            return dict(s,document_id=rec['document_id'],version_id=s['sha256'],
                retrieved_at=rec['retrieved_at'],quote_match='exact',verification_status='unverified')
        self.bridge.evidence=evidence

    def action(self,op='evidence_packet'):
        return self.request(op,network_enabled=False,receipt_spec=self.spec,notes=[dict(
            policy_id='P-04',subject='保育料',submeasure='P-04/second-child',
            relation='direct',fact_type='budget_proposal',quote='proposal only',
            locator={'physical_page':1,'printed_page':103},limitations='Vote/enactment/implementation unconfirmed')])

    def test_handoff_dedup_corruption_and_history_preservation(self):
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        req=self.action();result=h.run(self.ledger,req,self.out)
        self.assertEqual(result['new_records'],1)
        self.assertEqual(h.run(self.ledger,req,self.out)['new_records'],0)
        packet=json.loads((self.out/(result['record_id']+'.json')).read_text(encoding='utf-8'))
        self.assertEqual(packet['units'][0]['fact_type'],'budget_proposal')
        self.assertEqual(packet['verification_status'],'unverified')
        sha=packet['audit']['sha256'];self.bridge.bodies[sha]=b'broken'
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})
        self.assertEqual(len(list(self.out.glob('*.json'))),1)

    def test_unapproved_and_stale_index_hold(self):
        req=self.action('acquisition_plan')
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
        self.ledger.apply(self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04']))
        self.save([(self.url,'changed')])
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
        self.assertEqual(list(self.out.glob('*.json')),[])

    def test_index_change_expires_unchanged_link_approval_and_can_be_reviewed_again(self):
        self.ledger.apply(self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04']))
        old=self.request('proposal')
        self.scan([(self.url,'予算案'),(self.url.replace('test.pdf','new.pdf'),'new')])
        _,rows=self.ledger.state(self.ledger.history())
        row=next(r for r in rows.values() if r['source_url']==self.url)
        self.assertIsNone(row['decision'])
        with self.assertRaises(Hold):self.ledger.apply(old)
        req=dict(operation='decision',candidate_id=row['candidate_id'],revision=row['revision'],
            index_sha256=row['index_sha256'],reviewer='TEST human',reason='new index review',
            decision='approve_for_source_registration',policy_ids=['P-04'])
        self.ledger.apply(req);req['operation']='proposal'
        self.assertFalse(self.ledger.apply(req)['network_enabled'])

    def test_policy_receipt_scope_and_empty_notes_hold(self):
        req=self.action();req['notes'][0]['policy_id']='P-14'
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)

        req=self.action();req['notes']=[]
        result=h.run(self.ledger,req,self.out)
        packet=json.loads((self.out/(result['record_id']+'.json')).read_text(encoding='utf-8'))
        self.assertEqual(packet['status'],'policy_relationship_unconfirmed')
        req['operation']='public_review'
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)

    def test_foreign_registry_binding_holds_without_output(self):
        req=self.action()
        path=self.state/'registry_identity.json'
        identity=json.loads(path.read_text(encoding='utf-8'))
        identity['city']='kobe';path.write_text(json.dumps(identity))
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
        self.assertEqual(list(self.out.glob('*.json')),[])

    def test_human_approval_required_and_only_note_added(self):
        baseline=self.root/'baseline.json';baseline.write_text(json.dumps(self.baseline),encoding='utf-8')
        req=self.action('public_review');req.update(baseline=dict(path=str(baseline),sha256=hashlib.sha256(baseline.read_bytes()).hexdigest()),
            base_revision='fixture',displays=[dict(policy_id='P-04',submeasure='P-04/second-child',text='Budget proposal only')])
        before=baseline.read_bytes();result=h.run(self.ledger,req,self.out)
        review=json.loads((self.out/(result['record_id']+'.json')).read_text(encoding='utf-8'))
        packet=review['packet'];change=packet['changes'][0]
        self.assertEqual(set(change['after'])-set(change['before']),{'evidence_notes'})
        self.assertEqual({k:v for k,v in change['after'].items() if k!='evidence_notes'},change['before'])
        self.assertEqual(packet['derived'],{})
        req['operation']='public_proposal';req['approval']={}
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
        req['approval']=dict(packet_id=packet['packet_id'],reviewer='TEST human',decision='approve',
            reviewed_at='2026-11-17T00:00:00+00:00',accepted_candidate_ids=[c['candidate_id'] for c in packet['candidates']])
        result=h.run(self.ledger,req,self.out)
        proposal=json.loads((self.out/(result['record_id']+'.json')).read_text(encoding='utf-8'))['proposal']
        self.assertFalse(proposal['publication_authorized']);self.assertNotIn('data',proposal)
        self.assertEqual(h.run(self.ledger,req,self.out)['new_records'],0)
        self.assertEqual(baseline.read_bytes(),before)
        req['displays'][0]['text']='changed after approval'
        with self.assertRaises(Hold):h.run(self.ledger,req,self.out)

    def test_disabled_plan_reuses_storage_and_never_reserves(self):
        self.ledger.apply(self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04']))
        req=self.action('acquisition_plan')
        source=dict(self.spec['source'],id='fixed',document_id='kyoto-doc-'+hashlib.sha256(self.url.encode()).hexdigest()[:24])
        scope=dict(city_code='kyoto',policy_ids=['P-04'],allowed_hosts=['www.city.kyoto.lg.jp'],
            enabled=False,network_enabled=False,timeout_seconds=10,redirects=0,retries=0,tls_verify=True,
            sources=[source],max_requests=1,max_requests_by_media={'html':1,'pdf':1},max_total_bytes=4194304)
        path=self.root/'scope.json';path.write_text(json.dumps(scope))
        req.update(scope=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
            storage=dict(private_root=str(self.root),state_root=str(self.state),binding_sha256='pin'),
            acquisition_output=str(self.state/'future-output'),p1_sha256=self.bridge.hashes)
        self.bridge.index['documents'].pop(self.url)  # unsaved synthetic candidate
        with patch.object(h.city_scope,'validate_storage',return_value=self.state) as validate:
            result=h.run(self.ledger,req,self.out);validate.assert_called_once()
            plan=json.loads((self.out/(result['record_id']+'.json')).read_text(encoding='utf-8'))
            self.assertFalse(plan['network_enabled']);self.assertFalse(plan['reservation_created'])
            self.assertEqual(list(self.state.glob('single_request*')),[])
            marker=self.state/('single_request_'+hashlib.sha256(self.url.encode()).hexdigest()+'.json')
            marker.write_text('{}')
            with self.assertRaises(Hold):h.run(self.ledger,req,self.out)
            self.assertEqual(marker.read_text(),'{}')


# Inherit helpers only. Parent tests are run separately by existing CI.
for name in vars(fixtures.RegistryTests):
    if name.startswith('test_') and name not in HandoffTests.__dict__:
        setattr(HandoffTests,name,None)

if __name__=='__main__':unittest.main()
