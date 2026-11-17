"""Synthetic approval artifacts are TEST-only. Socket connections are blocked."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import fitz
import test_source_registry_mayor as fixtures
from mayor_updates import automatic_review as a
from mayor_updates.p1_bridge import P1Bridge


class AutomaticTests(fixtures.RegistryTests):
    def setUp(self):
        super().setUp();self.scan([(self.url,'proposal')]);self.spec=self.receipt_spec()
        self.bridge.code_root=self.root/'p1';(self.bridge.code_root/'budget').mkdir(parents=True)
        code=self.bridge.code_root/'budget/fixture';code.write_bytes(b'TEST')
        self.bridge.hashes={'fixture':hashlib.sha256(b'TEST').hexdigest()}
        pre=self.root/'acquisition_preflight.json';v=json.loads(pre.read_text());v['code_sha256']=self.bridge.hashes
        pre.write_text(json.dumps(v));self.spec['acquisition_preflight']['sha256']=hashlib.sha256(pre.read_bytes()).hexdigest()
        pdf=fitz.open();page=pdf.new_page();page.insert_text((50,50),'Budget proposal 2025\nProject lunch\nTarget schools\n70,000 thousand yen\nFootnote: all schools, no construction\n103')
        body=pdf.tobytes();pdf.close();sha=hashlib.sha256(body).hexdigest()
        old=self.bridge.index['documents'][self.url]['versions'][-1]['record']
        rec={**old,'sha256':sha,'version_id':sha}
        self.bridge.bodies[sha]=body
        self.bridge.index['documents'][self.url]['versions']=[{'record':rec,'sha256':sha}]
        self.bridge.index['attempts'][-1]['sha256']=sha
        path=self.root/'acquisition_receipt.json';receipt=json.loads(path.read_text())
        receipt['receipts'][0].update(version=rec,sha256=sha,stored_bytes=len(body))
        path.write_text(json.dumps(receipt));self.spec['acquisition_receipt']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        self.bridge.evidence=lambda spec:P1Bridge.evidence(self.bridge,spec)
        with fitz.open(stream=body,filetype='pdf') as pdf:text=pdf[0].get_text()
        self.fact=dict(policy_id='P-04',submeasure='P-04/test',fact_type='budget_proposal',
            relation='contextual',year=2025,project='Project lunch',target='Target schools',
            amount='70,000',unit='thousand yen',quote='Footnote: all schools, no construction',
            limitations='Vote, enactment and outcomes unconfirmed',
            pages=[dict(physical_page=1,printed_page=103,text=text)])
        self.req=self.request('auto_review',receipt_spec=self.spec,fact=self.fact)
        self.ledger.apply(self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04']))
        row,observed=a.inspect(self.ledger,self.req)
        self.public_sha='f'*64
        self.rule=dict(rule_id='TEST-exact',version=1,reviewer='TEST human',reviewed_at='2026-11-17',
            review_record_id='TEST-only',decision='approve_exact_budget_note_rule',
            binding={k:observed[k] for k in ('city','candidate_id','revision','index_sha256','source_url','document_id')},
            expected_fact=copy.deepcopy(self.fact),public_sha256=self.public_sha,
            budget_addition=False,stage_change=False,contradiction_review='cleared')
        self.observed=observed

    def evaluate(self,req=None,rules=None,accepted=None):
        return a.decide(self.ledger,req or self.req,[self.rule] if rules is None else rules,accepted or [],self.public_sha)

    def test_auto_verified_and_unchanged(self):
        result=self.evaluate();self.assertEqual(result['status'],'AUTO_VERIFIED')
        self.assertFalse(result['private_publication_candidate']['publication_authorized'])
        accepted=[dict(fingerprint=result['fingerprint'],decision='accept_existing_fact',reviewer='TEST human',reviewed_at='2026-11-17',review_record_id='TEST')]
        same=self.evaluate(accepted=accepted);self.assertEqual(same['status'],'UNCHANGED')
        self.assertNotIn('private_publication_candidate',same)

    def test_wrong_fields_pages_footnotes_and_inferences_hold(self):
        for key,value in [('amount','124,000'),('year',2026),('target','other children'),
                          ('relation','direct'),('policy_id','P-14'),('fact_type','enactment'),
                          ('fact_type','budget_vote'),('fact_type','implementation'),('fact_type','achievement')]:
            with self.subTest(key=key,value=value):
                req=copy.deepcopy(self.req);req['fact'][key]=value
                self.assertEqual(self.evaluate(req)['status'],'HOLD')
        for key,value in [('physical_page',2),('printed_page',104),('text','Budget proposal 2025\n')]:
            req=copy.deepcopy(self.req);req['fact']['pages'][0][key]=value
            self.assertEqual(self.evaluate(req)['status'],'HOLD')
        self.assertEqual(self.evaluate(rules=[])['status'],'HOLD')
        for key,value in [('budget_addition',True),('stage_change',True),('public_sha256','a'*64),('review_record_id',None)]:
            rule=copy.deepcopy(self.rule);rule[key]=value
            self.assertEqual(self.evaluate(rules=[rule])['status'],'HOLD')

    def test_registration_index_receipt_and_cas_mismatch_hold(self):
        self.ledger.apply(self.request('decision',decision='hold',policy_ids=['P-04']))
        self.assertEqual(self.evaluate()['status'],'HOLD')
        self.ledger.apply(self.request('decision',decision='approve_for_source_registration',policy_ids=['P-04']))
        req=copy.deepcopy(self.req);req['receipt_spec']['city']='kobe'
        self.assertEqual(self.evaluate(req)['status'],'HOLD')
        req=copy.deepcopy(self.req);req['receipt_spec']['acquisition_receipt']['sha256']='0'*64
        self.assertEqual(self.evaluate(req)['status'],'HOLD')
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')}
        version=self.observed['original_sha256'];self.bridge.bodies[version]=b'broken'
        self.assertEqual(self.evaluate()['status'],'HOLD')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})

    def test_index_and_foreign_registry_invalidate_accepted_fact(self):
        good=self.evaluate();accepted=[dict(fingerprint=good['fingerprint'],decision='accept_existing_fact',reviewer='TEST',reviewed_at='date',review_record_id='TEST')]
        self.save([(self.url,'changed')])
        self.assertEqual(self.evaluate(accepted=accepted)['status'],'HOLD')
        p=self.state/'registry_identity.json';identity=json.loads(p.read_text());identity['cas_root']='foreign'
        p.write_text(json.dumps(identity));self.assertEqual(self.evaluate()['status'],'HOLD')

    def test_acl_and_code_pin_hold(self):
        from mayor_updates.projection import Hold
        with patch.object(a.weekly,'assert_owner_only',side_effect=Hold('ACL failed')):
            self.assertEqual(self.evaluate()['status'],'HOLD')
        (self.bridge.code_root/'budget/fixture').write_bytes(b'changed')
        self.assertEqual(self.evaluate()['status'],'HOLD')

    def test_output_dedup_preserves_history_and_public_data(self):
        def pin(name,value):
            p=self.root/name;p.write_text(json.dumps(value));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        public=pin('public.json',self.baseline);self.public_sha=public['sha256'];self.rule['public_sha256']=self.public_sha
        config=dict(network_enabled=False,rules=pin('rules.json',[self.rule]),accepted=pin('accepted.json',[]),
            public_snapshot=public,p1_sha256=self.bridge.hashes,requests=[self.req])
        out=self.root/'auto';out.mkdir()
        before={p.name:p.read_bytes() for p in self.state.glob('event-*')};base=(self.root/'public.json').read_bytes()
        first=a.run(self.ledger,config,out);second=a.run(self.ledger,config,out)
        self.assertEqual(first['AUTO_VERIFIED'],1);self.assertEqual(first['new_records'],1)
        self.assertEqual(second['new_records'],0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.glob('event-*')})
        self.assertEqual(base,(self.root/'public.json').read_bytes())


for name in vars(fixtures.RegistryTests):
    if name.startswith('test_') and name not in AutomaticTests.__dict__:setattr(AutomaticTests,name,None)

if __name__=='__main__':unittest.main()
