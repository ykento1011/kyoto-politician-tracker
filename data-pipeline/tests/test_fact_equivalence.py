"""Synthetic only: existing socket-blocked PDF/receipt fixtures, no private CAS."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import test_automatic_review as fixtures
from mayor_updates import automatic_review as a
from mayor_updates.fact_equivalence import MODE
from mayor_updates.projection import Hold


class EquivalenceTests(fixtures.AutomaticTests):
    def pin(self, name, value):
        path=self.root/name
        path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
        return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def setUp(self):
        super().setUp()
        self.public=copy.deepcopy(self.baseline)
        self.old_public=self.pin('old_public.json',self.public)
        self.acceptance=[dict(fingerprint=a.engine.digest({'observed':self.observed,
            'public_sha256':self.old_public['sha256']}),decision='accept_existing_fact',
            reviewer='TEST ONLY',reviewed_at='TEST ONLY',review_record_id='TEST ONLY')]
        self.accepted=self.pin('accepted.json',self.acceptance)
        self.proof=dict(old_observed=copy.deepcopy(self.observed),
            old_public_snapshot=self.old_public,accepted_file_sha256=self.accepted['sha256'],
            acceptance_entry_sha256=a.engine.digest(self.acceptance[0]))
        self.proof_pin=self.pin('proof.json',self.proof)
        self.cfg=dict(network_enabled=False,comparison_mode=MODE,offline_test_mode=True,
            rules=self.pin('rules.json',[]),accepted=self.accepted,
            public_snapshot=self.pin('current_public.json',self.public),
            equivalence_proof=self.proof_pin,p1_sha256=self.bridge.hashes,requests=[self.req])
        self.out=self.root/'equivalence_results';self.out.mkdir()
        self.immutable={n:(self.root/n).read_bytes() for n in ('old_public.json','accepted.json')}

    def run_review(self):
        return a.run(self.ledger,self.cfg,self.out)

    def assert_status(self, expected):
        report=self.run_review()
        self.assertEqual(report[expected],1)
        self.assertEqual(report['AUTO_VERIFIED'],0)
        self.assertEqual(report['network_requests'],0)
        self.assertEqual(report['public_writes'],0)
        for name,data in self.immutable.items():self.assertEqual((self.root/name).read_bytes(),data)
        return report

    def test_same_and_other_headline_whitespace_repeat_no_records(self):
        self.assert_status('UNCHANGED')
        other=next(p for p in self.public['pledges'] if p['id']=='P-05')
        other['headline']='  '+other['headline']+'\n'
        self.cfg['public_snapshot']=self.pin('current_public.json',self.public)
        for _ in range(2):self.assertEqual(self.assert_status('UNCHANGED')['new_records'],0)
        proof=self.run_review()['continuations'][0]
        self.assertEqual(proof['old_accepted_fingerprint'],self.acceptance[0]['fingerprint'])
        self.assertFalse(proof['source_registration_authorized'])
        self.assertFalse(proof['publication_authorized'])
        self.assertEqual(list(self.out.iterdir()),[])
        self.cfg['comparison_mode']='strict'
        self.assert_status('HOLD')

    def new_index(self,links):
        self.scan(links)
        _,rows=self.ledger.state(self.ledger.history())
        row=rows[self.req['candidate_id']]
        self.req.update(revision=row['revision'],index_sha256=row['index_sha256'])

    def test_append_only_index_does_not_carry_source_registration(self):
        self.new_index([(self.url,'proposal'),('https://www.city.kyoto.lg.jp/extra.pdf','extra')])
        history=[p.read_bytes() for p in self.state.glob('event-*')]
        self.assert_status('HOLD');self.assert_status('HOLD')
        _,rows=self.ledger.state(self.ledger.history())
        row=rows[self.req['candidate_id']]
        self.assertIsNone(row['decision'])
        with self.assertRaises(Hold):self.ledger.proposal(row)
        self.assertEqual(history,[p.read_bytes() for p in self.state.glob('event-*')])
        self.cfg['comparison_mode']='strict';self.assert_status('HOLD')

    def test_fact_context_and_receipt_changes_hold(self):
        original=copy.deepcopy(self.req)
        for key,value in [('amount','124,000'),('year',2026),('target','other'),('quote','other'),
                          ('unit','yen'),('submeasure','other'),('relation','direct'),
                          ('fact_type','enactment'),('fact_type','achievement')]:
            with self.subTest(key=key,value=value):
                req=copy.deepcopy(original);req['fact'][key]=value
                self.cfg['requests']=[req];self.assert_status('HOLD')
        for key,value in [('text','Budget proposal'),('physical_page',2),('printed_page',104)]:
            req=copy.deepcopy(original);req['fact']['pages'][0][key]=value
            self.cfg['requests']=[req];self.assert_status('HOLD')
        req=copy.deepcopy(original);req['receipt_spec']['source']['url']+='x'
        self.cfg['requests']=[req];self.assert_status('HOLD')
        req=copy.deepcopy(original);req['receipt_spec']['acquisition_receipt']['sha256']='0'*64
        self.cfg['requests']=[req];self.assert_status('HOLD')
        self.cfg['requests']=[original]
        self.bridge.bodies[self.observed['original_sha256']]=b'corrupt';self.assert_status('HOLD')

    def test_other_budget_target_change_and_unknown_public_shape_hold(self):
        for mutate in (
            lambda p:p['pledges'][4].update(stage_level=5),
            lambda p:p['pledges'][4]['budget_records'][0].update(amount_jpy=1),
            lambda p:p['pledges'][3].update(headline='different target text'),
            lambda p:p.update(unknown='new'),
            lambda p:p['pledges'].append(copy.deepcopy(p['pledges'][0])),
            lambda p:p['pledges'][4].update(headline='meaning changed'),
        ):
            public=copy.deepcopy(self.public);mutate(public)
            self.cfg['public_snapshot']=self.pin('current_public.json',public)
            self.assert_status('HOLD')

    def test_missing_and_mismatched_pinned_approval_inputs_hold(self):
        for key,value in [('acceptance_entry_sha256','0'*64),('accepted_file_sha256','0'*64)]:
            proof=copy.deepcopy(self.proof);proof[key]=value
            self.cfg['equivalence_proof']=self.pin('bad_proof.json',proof)
            self.assert_status('HOLD')
        self.cfg['equivalence_proof']=self.proof_pin
        self.cfg['accepted']=self.pin('empty_accepted.json',[]);self.assert_status('HOLD')
        self.cfg['accepted']=self.accepted
        proof=copy.deepcopy(self.proof);proof['old_public_snapshot']={**self.old_public,'sha256':'0'*64}
        self.cfg['equivalence_proof']=self.pin('bad_proof.json',proof)
        with self.assertRaises(Hold):self.run_review()
        self.cfg['equivalence_proof']=self.proof_pin
        (self.root/'old_public.json').unlink()
        with self.assertRaises((Hold,OSError)):self.run_review()

    def test_acl_pin_and_explicit_mode_gate(self):
        with patch.object(a.weekly,'assert_owner_only',side_effect=Hold('ACL failed')):
            with self.assertRaises(Hold):self.run_review()
        self.cfg['offline_test_mode']=False
        with self.assertRaises(Hold):self.run_review()
        self.cfg['offline_test_mode']=True
        self.cfg['network_enabled']=True
        with self.assertRaises(Hold):self.run_review()
        self.cfg['network_enabled']=False
        (self.bridge.code_root/'budget/fixture').write_bytes(b'changed')
        self.assert_status('HOLD')

    def test_index_position_duplicate_context_hold(self):
        for links in (
            [('https://www.city.kyoto.lg.jp/extra.pdf','extra'),(self.url,'proposal')],
            [(self.url,'proposal'),(self.url,'duplicate')],
            [(self.url,'changed context')],
        ):
            self.new_index(links);self.assert_status('HOLD')

    def test_foreign_cas_old_revision_and_explicit_source_hold(self):
        proof=copy.deepcopy(self.proof)
        # Cannot forge another observation even when the proof file itself is repinned.
        proof['old_observed']['document_id']='foreign'
        self.cfg['equivalence_proof']=self.pin('bad_proof.json',proof)
        self.assert_status('HOLD')
        self.cfg['equivalence_proof']=self.proof_pin
        self.ledger.apply(self.request('decision',decision='hold',policy_ids=['P-04']))
        self.assert_status('HOLD')
        p=self.state/'registry_identity.json';identity=json.loads(p.read_text())
        identity['cas_root']='foreign';p.write_text(json.dumps(identity))
        self.assert_status('HOLD')

    def test_unknown_index_html_and_missing_approval_metadata_hold(self):
        # A new heading after the old link is not a permitted bare-link append.
        version=self.save([(self.url,'proposal')])
        body=self.bridge.bodies[version].replace(b'</div>',b'<p>new conditions</p></div>')
        sha=hashlib.sha256(body).hexdigest();self.bridge.bodies[sha]=body
        v=self.bridge.index['documents'][self.source['url']]['versions'][-1]
        v['sha256']=sha;v['record'].update(sha256=sha,version_id=sha)
        self.ledger.apply(dict(operation='scan',source=self.source,index_sha256=sha))
        _,rows=self.ledger.state(self.ledger.history());row=rows[self.req['candidate_id']]
        self.req.update(revision=row['revision'],index_sha256=row['index_sha256'])
        self.assert_status('HOLD')
        accepted=copy.deepcopy(self.acceptance);accepted[0].pop('review_record_id')
        self.cfg['accepted']=self.pin('incomplete_approval.json',accepted)
        self.assert_status('HOLD')

    def test_default_strict_and_auto_verified_unchanged(self):
        self.cfg.pop('comparison_mode');self.cfg.pop('offline_test_mode')
        self.assert_status('UNCHANGED')
        self.cfg['accepted']=self.pin('empty_accepted.json',[])
        self.rule['public_sha256']=self.cfg['public_snapshot']['sha256']
        self.cfg['rules']=self.pin('approved_rule.json',[self.rule])
        result=self.run_review();self.assertEqual(result['AUTO_VERIFIED'],1)
        artifact=json.loads(next(self.out.glob('*.json')).read_text())['result']
        self.assertFalse(artifact['publication_authorized'])
        self.cfg.update(comparison_mode=MODE,offline_test_mode=True)
        self.assert_status('HOLD') # Even a valid AUTO rule cannot be used here.

    def test_attachment_boundary_and_approved_exact_addition(self):
        from mayor_updates.fact_equivalence import addition_proof,list_boundary
        before=('<html><body><div id="mol_contents"><h3>事業概要</h3>'
            '<div class="mol_attachfileblock"><p class="mol_attachfileblock_title">予算案</p>'
            '<ul><li><a href="'+self.url+'">proposal</a></li></ul></div></div>'
            '<footer>footer</footer></body></html>').encode()
        addition=b'<li><a href="https://www.city.kyoto.lg.jp/extra.pdf">Other unrelated series</a></li>'
        pos=list_boundary(before,self.source,self.url)
        after=before[:pos]+addition+before[pos:]
        primary=self.root/'primary.txt';primary.write_text('TEST primary: unrelated series, no correction',encoding='utf-8')
        rule=dict(decision='approve_exact_unrelated_index_addition',
            binding={k:self.observed[k] for k in ('city','candidate_id','source_url','index_sha256','revision')},
            insertion_sha256=hashlib.sha256(addition).hexdigest(),source_registration_authorized=False,
            publication_authorized=False,rule_id='TEST ONLY',version=1,reviewer='TEST ONLY',
            reviewed_at='TEST ONLY',review_record_id='TEST ONLY',
            primary_evidence=dict(path=str(primary),sha256=hashlib.sha256(primary.read_bytes()).hexdigest()),
            primary_quote='TEST primary: unrelated series, no correction',
            correction_withdrawal_supplement_replacement_excluded=True)
        context={'proof':{'index_addition_rule':self.pin('addition_rule.json',rule)}}
        proof=addition_proof(self.ledger,before,after,self.source,self.observed,context)
        self.assertEqual(proof['insertion_byte_offset'],pos)
        with self.assertRaises(Hold):addition_proof(self.ledger,before,after,self.source,self.observed,{'proof':{}})
        for bad in (
            before.replace(b'</footer>',addition+b'</footer>'),
            after.replace(b'proposal',b'changed'),
            before[:pos]+addition.replace(b'extra.pdf',b'test.pdf')+before[pos:],
            before[:pos]+b'<p>correction</p>'+before[pos:],
            after.replace(b'<h3>',b'<h4>'),
        ):
            with self.subTest(html=bad[:30]):
                with self.assertRaises(Hold):addition_proof(self.ledger,before,bad,self.source,self.observed,context)
        for field,value in [('correction_withdrawal_supplement_replacement_excluded',False),
                            ('review_record_id',None),('primary_quote','not in evidence')]:
            bad=copy.deepcopy(rule);bad[field]=value
            ctx={'proof':{'index_addition_rule':self.pin('bad_addition_rule.json',bad)}}
            with self.assertRaises(Hold):addition_proof(self.ledger,before,after,self.source,self.observed,ctx)


for name in dir(fixtures.AutomaticTests):
    if name.startswith('test_') and name not in EquivalenceTests.__dict__:setattr(EquivalenceTests,name,None)

if __name__=='__main__':unittest.main()
