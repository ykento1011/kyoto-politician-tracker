"""Offline acceptance tests. Synthetic fixtures never imply real approval."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mayor_updates.engine import (Hold, digest, propose, compare_documents, compare_index,
                                 approved_bundle, publication_receipt, PrivateOutput, review_html)
from mayor_updates.projection import sync_totals, included, format_amount, preserve_published, policies
from mayor_updates.monitor import request_plan, suggest_policy_links

URL='https://www.city.kyoto.lg.jp/fixture.pdf'
def base():
    return {'pledges':[{'id':'P-01','stage_level':3,'budget_records':[
        {'amount_jpy':271000000,'amount_display':'2億7,100万円','policy_relation':'direct'},
        {'amount_jpy':269000000,'amount_display':'2億6,900万円','policy_relation':'contextual'}]},
        {'id':'P-03','stage_level':4,'stage_label':'契約可決・着工','milestone':{'title':'過去の契約可決'},
         'budget_records':[{'fiscal_year':'令和7年度','project_name':'登録名','amount_jpy':124000000,'amount_display':'1億2,400万円'},
                           {'fiscal_year':'令和8年度','project_name':'登録名2','amount_jpy':190000000,'amount_display':'1億9,000万円'}]}],
        'summary_stats':{'total_allocated_budget_raw':585000000,'total_allocated_budget_jpy':'5億8,500万円'},
        'kpis':[{'label':'関連予算措置総額','value':'5億8,500万円'}]}

def evidence():
    return {'source_url':URL,'document_title':'TEST fixture only','version_id':'a'*64,'sha256':'a'*64,
            'retrieved_at':'2026-11-15T00:00:00+00:00','locator':{'physical_page':1,'printed_page':188},
            'quote':'約1.9億円','quote_match':'NFKC_whitespace_only'}

def budget():
    return {'candidate_id':'fixture-budget','city':'kyoto','policy_id':'P-03','kind':'budget',
            'verification_status':'unverified','relation':'contextual','reason':'TEST contextual fixture',
            'evidence':[evidence()],'record_index':1,'before_record_sha256':digest(base()['pledges'][1]['budget_records'][1]),
            'facts':{'budget_kind':'initial','amount_role':'initial','budget_status':'proposal',
                     'fiscal_year_ad':2026,'approximate':True},
            'updates':{'fiscal_year':'令和8年度当初予算（案）','doc_url':URL,'doc_source':'印刷p.188／物理1',
                       'funding_verification_status':'unverified'}}

def progress():
    return {'candidate_id':'fixture-progress','city':'kyoto','policy_id':'P-03','kind':'progress',
            'verification_status':'unverified','relation':'direct','reason':'TEST progress fixture',
            'evidence':[evidence()], 'event':{'announced_at':'2026-11-05','event_date':None,
                'kind':'construction_paused','label':'一時停止','summary':'TEST 工事一時停止。開始時期は未定。',
                'source_url':URL,'source_title':'TEST official announcement'}}

def run(cs, data=None):
    return propose(data or base(),cs,city='kyoto',allowed=['P-03'],base_revision='test-base')

def approval(packet):
    return {'packet_id':packet['packet_id'],'reviewer':'SYNTHETIC TEST REVIEWER',
            'reviewed_at':'2026-11-15T00:00:00+00:00','decision':'approve',
            'accepted_candidate_ids':[c['candidate_id'] for c in packet['candidates']]}

class EngineTests(unittest.TestCase):
    def test_new_same_url_replacement_failure_and_unchanged(self):
        old={URL:{'source_url':URL,'status':'ok','sha256':'a'*64}}
        changes,state=compare_documents(old,[{'source_url':URL,'status':'ok','sha256':'b'*64}])
        self.assertEqual(changes[0]['kind'],'replacement_document')
        same,_=compare_documents(state,[state[URL]])
        self.assertEqual(same[0]['kind'],'unchanged')
        failed,retained=compare_documents(state,[{'source_url':URL,'status':'failed'}])
        self.assertEqual(retained,state)
        self.assertEqual(failed[0]['kind'],'document_fetch_failed')
        added,_=compare_documents({},[state[URL]])
        self.assertEqual(added[0]['kind'],'new_document')

    def test_index_add_change_remove_and_failure(self):
        old={'a':{'label':'old'},'b':{'label':'b'}}
        events,_=compare_index(old,{'a':{'label':'new'},'c':{'label':'c'}})
        self.assertEqual({e['kind'] for e in events},{'link_added','link_changed','link_removed'})
        self.assertTrue(all(e['policy_effect'] is None for e in events))
        events,state=compare_index(old,{},success=False)
        self.assertEqual(state,old)
        self.assertEqual(events[0]['kind'],'index_fetch_failed')

    def test_absent_document_is_not_cancellation(self):
        state={URL:{'sha256':'a'*64}}
        events,after=compare_documents(state,[])
        self.assertEqual(events,[]); self.assertEqual(after,state)

    def test_no_candidate_no_proposal(self):
        packet,result=run([])
        self.assertIsNone(packet); self.assertEqual(result,base())

    def test_changed_policy_only_and_source_preserved(self):
        packet,data=run([budget(),progress()])
        self.assertEqual([x['policy_id'] for x in packet['changes']],['P-03'])
        self.assertEqual(data['pledges'][0],base()['pledges'][0])
        self.assertEqual(data['pledges'][1]['stage_level'],4)
        self.assertEqual(data['pledges'][1]['milestone'],base()['pledges'][1]['milestone'])
        self.assertEqual(packet['candidates'][0]['evidence'],budget()['evidence'])
        self.assertFalse(packet['publication_authorized'])
        self.assertIn('印刷p.188',review_html(packet))

    def test_accepted_result_rerun_has_zero_proposal(self):
        cs=[budget(),progress()]
        _,data=run(cs)
        packet,result=run(cs,data)
        self.assertIsNone(packet)
        self.assertEqual(result,data)

    def test_reference_excluded_and_display_synced(self):
        _,data=run([budget()])
        self.assertEqual(data['summary_stats']['total_allocated_budget_raw'],395000000)
        self.assertEqual(data['kpis'][0]['value'],data['summary_stats']['total_allocated_budget_jpy'])
        self.assertEqual(data['pledges'][1]['budget_records'][1]['amount_display'],'約1億9,000万円')

    def test_unknown_keeps_amount_but_not_total(self):
        c=budget(); c['relation']='unconfirmed'; c['facts']['approximate']=False
        _,data=run([c]); self.assertEqual(data['pledges'][1]['budget_records'][1]['amount_jpy'],190000000)
        self.assertEqual(data['summary_stats']['total_allocated_budget_raw'],395000000)

    def test_no_cross_city_or_policy(self):
        for city,pid in [('osaka','P-03'),('kyoto','P-02')]:
            c=budget(); c['city']=city; c['policy_id']=pid
            with self.assertRaises(Hold): run([c])

    def test_unconfirmed_formal_status_rejected(self):
        c=budget(); c['verification_status']='verified'
        with self.assertRaises(Hold): run([c])

    def test_initial_supplemental_settlement_roles(self):
        c=budget(); c['facts']['budget_kind']='supplemental'
        with self.assertRaises(Hold): run([c])
        c['facts']['amount_role']='delta'
        packet,_=run([c]); self.assertEqual(packet['candidates'][0]['facts']['amount_role'],'delta')
        c['relation']='direct'
        with self.assertRaises(Hold): run([c])
        c['relation']='contextual'; c['facts'].update(budget_kind='settlement',amount_role='actual',budget_status='actual')
        self.assertIsNotNone(run([c])[0])

    def test_amount_change_requires_original_amount(self):
        c=budget(); c['updates']['amount_jpy']=1
        with self.assertRaises(Hold): run([c])

    def test_funding_cannot_be_silently_verified(self):
        c=budget(); c['updates']['funding_verification_status']='verified'
        with self.assertRaises(Hold): run([c])

    def test_bad_version_unbound_quote_and_url(self):
        for field,value in [('version_id','b'*64),('quote_match',False),('quote','')]:
            c=budget(); c['evidence'][0][field]=value
            with self.assertRaises(Hold): run([c])
        c=budget(); c['updates']['doc_url']='https://example.org/wrong'
        with self.assertRaises(Hold): run([c])

    def test_no_unapproved_fields_or_stage_change(self):
        c=budget(); c['updates']['stage_level']=5
        with self.assertRaises(Hold): run([c])

    def test_stale_record_or_duplicate_target(self):
        c=budget(); c['before_record_sha256']='b'*64
        with self.assertRaises(Hold): run([c])
        a,b=budget(),budget(); b['candidate_id']='other'
        with self.assertRaises(Hold): run([a,b])

    def test_progress_history_and_old_event_rejected(self):
        data=base(); old=progress()['event']; old['announced_at']='2025-12-04'
        data['pledges'][1]['latest_update']=old
        _,result=run([progress()],data)
        self.assertEqual(result['pledges'][1]['progress_history'],[old])
        old['announced_at']='2027-01-01'
        with self.assertRaises(Hold): run([progress()],data)

    def test_approval_required_no_blank_reviewer_or_time(self):
        packet,_=run([budget()])
        for field in ('reviewer','reviewed_at','decision','packet_id'):
            a=approval(packet); a[field]=''
            with self.assertRaises(Hold): approved_bundle(base(),packet,a)

    def test_partial_approval_and_stale_base_rejected(self):
        packet,_=run([budget(),progress()]); a=approval(packet)
        a['accepted_candidate_ids']=[]
        with self.assertRaises(Hold): approved_bundle(base(),packet,a)
        altered=base(); altered['pledges'][0]['stage_level']=4
        with self.assertRaises(Hold): approved_bundle(altered,packet,approval(packet))

    def test_tampered_packet_rejected_even_with_rehashed_changes(self):
        packet,_=run([budget()]); a=approval(packet)
        packet['changes'][0]['after']['stage_level']=5
        with self.assertRaises(Hold): approved_bundle(base(),packet,a)
        packet['packet_id']=digest({k:v for k,v in packet.items() if k!='packet_id'})
        with self.assertRaises(Hold): approved_bundle(base(),packet,approval(packet))

    def test_valid_review_handoff_still_does_not_publish(self):
        packet,result=run([budget()]); bundle=approved_bundle(base(),packet,approval(packet))
        self.assertEqual(bundle['data'],result); self.assertFalse(bundle['publication_authorized'])
        self.assertEqual(bundle['before_after'],packet['changes'])

    def test_publication_receipt_requires_matching_published_data(self):
        packet,result=run([budget()]); bundle=approved_bundle(base(),packet,approval(packet))
        kwargs=dict(commit='c'*40,deployed_url='https://example.org/TEST',published_at='2026-11-15T00:00:00Z')
        with self.assertRaises(Hold): publication_receipt(bundle,published_data=base(),**kwargs)
        receipt=publication_receipt(bundle,published_data=result,**kwargs)
        self.assertEqual(receipt['commit'],'c'*40)

    def test_private_output_rejects_public_git_traversal_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=PrivateOutput(root)
            with self.assertRaises(Hold): out.write('../escape','bad')
            out.json('test.json',{})
            with self.assertRaises(Hold): out.json('test.json',{})
            pub=root/'public'; pub.mkdir()
            with self.assertRaises(Hold): PrivateOutput(pub)
            (root/'.git').mkdir()
            with self.assertRaises(Hold): PrivateOutput(root)

    def test_generator_overlay_prevents_rollback_without_mutating_seed(self):
        packet,result=run([budget(),progress()])
        seed=base()['pledges']; original=copy.deepcopy(seed)
        merged=preserve_published(seed,result['pledges'])
        self.assertEqual(merged,result['pledges']); self.assertEqual(seed,original)
        with self.assertRaises(Hold): preserve_published(seed,result['pledges'][:-1])

    def test_legacy_total_format_and_direct_rules(self):
        self.assertEqual(format_amount(15000),'2万円')
        self.assertTrue(included({'amount_jpy':1}))
        for r in ('contextual','unconfirmed','unexpected',None):
            self.assertFalse(included({'policy_relation':r,'amount_jpy':1}))
        with self.assertRaises(Hold): included({'policy_relation':'direct','amount_role':'delta'})

    def test_policy_suggestion_is_not_automatic_fact(self):
        result=suggest_policy_links({'candidates':[{'project_name':'給食センター','reason_excerpt':'TEST'}]},
                                    {'policy_ids':['P-03'],'policy_terms':{'P-03':['給食センター']}})
        self.assertEqual(result[0]['relation'],'unconfirmed')
        self.assertFalse(result[0]['eligible_for_proposal'])

@unittest.skipUnless(os.environ.get('MAYOR_PRIVATE_PROOF'), 'Private saved-source integration path not configured')
class SavedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mayor_updates.p1_bridge import P1Bridge
        cls.root=Path(os.environ['MAYOR_PRIVATE_PROOF'])
        cls.demo=cls.root/'demo/run_04'
        cls.p1=os.environ['MAYOR_P1_CODE']
        cls.cas=os.environ['MAYOR_PRIVATE_CAS']
        cls.bridge=P1Bridge(cls.p1,cls.cas)
        cls.load=staticmethod(lambda path:json.loads(path.read_text(encoding='utf-8-sig')))
        cls.config=cls.load(cls.root/'candidate/config/mayor_update_sources.json')

    def test_four_originals_integrity_no_extra_sources(self):
        self.assertGreaterEqual(len(self.bridge.index['documents']),4)
        for url,d in self.bridge.index['documents'].items():
            self.bridge.record(url,d['versions'][-1]['sha256'])

    def test_39_policies_and_stages_unchanged(self):
        baseline=self.load(self.demo/'baseline_kyoto.json'); after=self.load(Path(os.environ.get('MAYOR_FINAL_DATA', str(self.demo/'candidate_tracker_PRIVATE.json'))))
        a,b=policies(baseline),policies(after)
        self.assertEqual({pid:p for pid,p in a.items() if pid!='P-03'}, {pid:p for pid,p in b.items() if pid!='P-03'})
        for key in ('stage_level','stage_label','milestone','legislative_bill'):
            self.assertEqual(a['P-03'][key],b['P-03'][key])
        self.assertEqual(sum(len(x['policy_ids']) for x in self.config['cities'].values()),40)
        repo=self.root.parent/'publication/repo/frontend/public/data'
        for city in self.config['cities']:
            import hashlib
            saved=self.load(self.demo/(city+'_baseline_fingerprint.json'))
            self.assertEqual(hashlib.sha256((repo/(city+'_mayor_tracker.json')).read_bytes()).hexdigest(),saved['file_sha256'])

    def test_quote_page_and_version_mismatch_hold(self):
        spec=self.load(self.demo/'mapping_rules.json')[1]['source_specs'][0]
        self.assertTrue(self.bridge.evidence(spec)['quote_match'])
        for field,value in [('quote','NOT IN SOURCE'),('sha256','0'*64)]:
            bad=copy.deepcopy(spec); bad[field]=value
            with self.assertRaises(Hold): self.bridge.evidence(bad)
        bad=copy.deepcopy(spec); bad['locator']['physical_page']=1
        with self.assertRaises(Hold): self.bridge.evidence(bad)

    def test_saved_monitor_nochange_and_plan_no_network(self):
        from mayor_updates.monitor import monitor_saved
        first=monitor_saved(self.bridge,self.config['cities']['kyoto'])
        second=monitor_saved(self.bridge,self.config['cities']['kyoto'],first['state'])
        self.assertEqual({e['kind'] for e in first['events']},{'new_document'})
        self.assertEqual({e['kind'] for e in second['events']},{'unchanged'})
        plan=request_plan(self.config,'kyoto')
        self.assertEqual(plan['max_requests'],4)
        self.assertFalse(plan['execution_enabled'])
        self.assertTrue(all(s['policy_effect'] is None for s in first['events']))

    def test_p1_fiscal_line_uses_existing_reconciler(self):
        self.assertIn('missing',self.bridge.fiscal_hold_reason({}))
        facts=dict(project_id='TEST',fiscal_year=2026,account_id='TEST',event_kind='budget_initial',
                   round_type='initial',session=None,source_line_id='TEST',proposal_at='2026-01-01T00:00:00Z')
        self.assertIsNone(self.bridge.fiscal_hold_reason(facts))
        facts['round_type']='supplemental'; facts['session']='TEST'
        with self.assertRaises(ValueError): self.bridge.fiscal_hold_reason(facts)

    def test_p1_fetcher_stores_fixture_and_detects_replacement(self):
        from mayor_updates.p1_bridge import P1Bridge
        from budget.adapters.kyoto import DiscoveredDocument
        from budget.fetch import HTTPResponse
        from mayor_updates.monitor import monitor_saved
        class FixtureTransport:
            offline_fixture=True
            def __init__(self): self.calls=[]; self.body=b'<html><body>TEST initial fixture</body></html>'
            def request(self,url,**kwargs):
                self.calls.append((url,kwargs))
                return HTTPResponse(200,{'Content-Type':'text/html'},self.body,True)
        with tempfile.TemporaryDirectory() as tmp:
            bridge=P1Bridge(self.p1,Path(tmp)/'private_snapshot')
            transport=FixtureTransport(); url='https://www.city.kyoto.lg.jp/TEST-OFFLINE.html'
            doc=DiscoveredDocument(url,'TEST offline fixture','令和8年度',2026,'html','budget_index','unknown',None,url,url,None,None,'discovered_unverified',())
            first=bridge.capture_from_test_transport(doc,transport)
            self.assertIsNotNone(first.version)
            self.assertEqual(transport.calls[0][1],{'timeout_seconds':10,'max_bytes':2097151})
            bridge.index=bridge.store.read_index()
            old=bridge.index['documents'][url]['versions'][0]['sha256']
            self.assertEqual(bridge.store.snapshot_bytes(old),transport.body)
            transport.body=b'<html><body>TEST replacement fixture</body></html>'
            second=bridge.capture_from_test_transport(doc,transport)
            self.assertTrue(second.version.new_version)
            self.assertEqual(len(bridge.store.read_index()['documents'][url]['versions']),2)
            with self.assertRaises(Hold): bridge.capture_from_test_transport(doc,object())

    def test_generator_function_keeps_reviewed_overlay(self):
        path=self.root/'candidate/data-pipeline/build_mayor_tracker.py'
        spec=importlib.util.spec_from_file_location('isolated_mayor_builder',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        candidate=Path(os.environ.get('MAYOR_FINAL_DATA', str(self.demo/'candidate_tracker_PRIVATE.json')))
        result=module.generation_pledges(candidate)
        accepted=self.load(candidate)
        self.assertEqual(policies({'pledges':result})['P-03']['budget_records'],policies(accepted)['P-03']['budget_records'])
        self.assertEqual(policies({'pledges':result})['P-03']['latest_update'],policies(accepted)['P-03']['latest_update'])
        stats=module.calculate_summary_stats(result)
        self.assertEqual(stats['total_allocated_budget_raw'],9830158000)
        self.assertEqual(stats['total_allocated_budget_jpy'],'98億3,016万円')

if __name__=='__main__': unittest.main(verbosity=2)
