"""Receipt-to-replay handoff stays offline and retains the last good state."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,tempfile,unittest
import test_city_replay

class ReceiptTests(unittest.TestCase):
    def setup_case(self,root):
        helper=test_city_replay.ReplayTests();s,b=helper.fixture(root)
        rec,body=b.record.return_value
        rec.update(source_url=s['source']['url'],final_url=s['source']['url'],document_type='other_official',snapshot_relative_path='objects/test.bin')
        b.record.return_value=(rec,body)
        b.index['attempts']=[{'source_url':rec['source_url'],'sha256':rec['sha256'],'outcome':'new_version','observed_at':rec['retrieved_at']}]
        pre={'sources':[{**s['source'],'max_bytes':2097152}], 'code_sha256':deepcopy(b.hashes),
             'limits':{'get_per_url':1,'tls_verify':True,'redirects':0,'retries':0,'wall_timeout_seconds':10}}
        receipt={'stopped':False,'public_writes':0,'receipts':[{'source_url':rec['source_url'],'version':deepcopy(rec),'sha256':rec['sha256'],'stored_bytes':len(body),'readback_pass':True,'new_get_requests':1,'http_status':200,'final_url':rec['source_url'],'status':'stored_new_version'}]}
        def pin(key,value):
            p=root/(key+'.json');p.write_text(json.dumps(value));s[key]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        pin('acquisition_receipt',receipt);pin('acquisition_preflight',pre)
        del s['sha256'];del s['document_id']
        return helper,s,b,receipt,pre,pin

    def test_receipt_derives_identity_and_repeats_without_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d));one=h.run_replay(s,b);two=h.run_replay(s,b)
            self.assertTrue(one['state_advanced']);self.assertEqual(two['new_review_count'],0)
            self.assertEqual(one['sha256'],r['receipts'][0]['sha256'])
            self.assertEqual(one['acquisition_handoff']['original_retrieved_at'],b.record.return_value[0]['retrieved_at'])
            self.assertFalse(one['publication_authorized']);self.assertEqual(one['network_requests'],0)

    def test_bad_receipt_and_scope_keep_previous_state(self):
        mutations=[lambda r,p:r.update(stopped=True),lambda r,p:r['receipts'][0].update(readback_pass=False),
          lambda r,p:r['receipts'][0]['version'].update(city_code='osaka'),lambda r,p:r['receipts'][0].update(stored_bytes=1),lambda r,p:r['receipts'][0]['version'].update(document_id='other'),
          lambda r,p:r['receipts'][0]['version'].update(retrieved_at='2026-11-15T00:00:01+00:00'),
          lambda r,p:p['sources'][0].update(policy_ids=['KOBE-M02']),lambda r,p:p['sources'][0].update(fiscal_year=2025),
          lambda r,p:p['limits'].update(tls_verify=False),lambda r,p:p['code_sha256'].update(test='different'),
          lambda r,p:r['receipts'].append(deepcopy(r['receipts'][0]))]
        for mutate in mutations:
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as d:
                h,s,b,r,p,pin=self.setup_case(Path(d));self.assertTrue(h.run_replay(s,b)['state_advanced'])
                state=Path(s['state_root'])/'state.json';good=state.read_bytes()
                mutate(r,p);pin('acquisition_receipt',r);pin('acquisition_preflight',p)
                self.assertFalse(h.run_replay(s,b)['state_advanced']);self.assertEqual(state.read_bytes(),good)

    def test_stale_receipt_and_manual_sha_conflict_hold(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d));self.assertTrue(h.run_replay(s,b)['state_advanced'])
            state=Path(s['state_root'])/'state.json';good=state.read_bytes()
            s['sha256']='0'*64;self.assertFalse(h.run_replay(s,b)['state_advanced']);del s['sha256']
            b.index['documents'][s['source']['url']]['versions'].append({'sha256':'1'*64,'record':b.record.return_value[0]})
            self.assertFalse(h.run_replay(s,b)['state_advanced']);self.assertEqual(state.read_bytes(),good)

    def test_receipt_pin_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d))
            Path(s['acquisition_receipt']['path']).write_text('{}')
            self.assertFalse(h.run_replay(s,b)['state_advanced'])
            self.assertFalse((Path(s['state_root'])/'state.json').exists())

    def test_unchanged_observation_keeps_original_acquisition_time(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d));new='2026-11-15T01:00:00+00:00'
            r['receipts'][0].update(status='unchanged');r['receipts'][0]['version']['retrieved_at']=new
            b.index['attempts'].append({'source_url':s['source']['url'],'sha256':r['receipts'][0]['sha256'],'outcome':'unchanged','observed_at':new})
            pin('acquisition_receipt',r);v=h.run_replay(s,b);self.assertTrue(v['state_advanced'])
            self.assertNotEqual(v['acquisition_handoff']['original_retrieved_at'],v['acquisition_handoff']['acquisition_observed_at'])
            b.index['attempts'].pop();self.assertFalse(h.run_replay(s,b)['state_advanced'])

    def test_saved_reuse_is_not_reported_as_new_acquisition(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d));r['receipts'][0].update(status='reused_existing',new_get_requests=0,http_status=None)
            pin('acquisition_receipt',r);v=h.run_replay(s,b);self.assertTrue(v['state_advanced'])
            self.assertEqual(v['acquisition_handoff']['acquisition_status'],'reused_existing')

    def test_missing_policy_scope_is_not_inferred(self):
        with tempfile.TemporaryDirectory() as d:
            h,s,b,r,p,pin=self.setup_case(Path(d));del p['sources'][0]['policy_ids'];del p['sources'][0]['policy_id'];pin('acquisition_preflight',p)
            self.assertFalse(h.run_replay(s,b)['state_advanced'])
            p['sources'][0]['policy_id']='KOBE-M01';pin('acquisition_preflight',p)
            self.assertTrue(h.run_replay(s,b)['state_advanced'])

if __name__=='__main__':unittest.main()
