"""Offline cross-meeting, delta-candidate and semantic-review regressions."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_kyoto_meeting_guard as fixture
import kyoto_candidate_changes as changes
import kyoto_saved_workflow as replay
g=fixture.g

def candidate(cid=None):
    x=dict(committee="総務消防委員会",session_number=4,meeting_date="2026-05-25",
           official_date_confirmed=True,source_kind="meeting")
    if cid:x["council_id"]=str(cid)
    return x

class GenericIdentityTests(unittest.TestCase):
    def setUp(self):g.configure(fixture.review())
    def test_new_and_known_routes_remain_separate(self):
        a=fixture.review();a["scope"]="kyoto_verified_new_meeting";g.configure(a)
        raw=fixture.schedule()
        with self.assertRaises(g.Stop):g.select_schedule(raw,"application/json",{"meetings":["kyoto:6346:1"]})
        g.REGISTERED_KEYS={"kyoto:6346:1"}
        with self.assertRaises(g.Stop):g.select_schedule(raw,"application/json",{"meetings":[]})
        g.REGISTERED_KEYS=set()
        self.assertEqual(g.select_schedule(raw,"application/json",{"meetings":[]})["schedule_id"],"1")
        g.configure(fixture.review())
        with self.assertRaises(g.Stop):g.select_schedule(raw,"application/json",{"meetings":[]})
    def test_different_reviewed_meeting_does_not_require_id_substitution_in_code(self):
        a=fixture.review()
        a.update(council_id="9001",meeting_date="2026-06-08")
        a["identity_review"].update(council_id="9001",meeting_date="2026-06-08",round=6,formal_name="令和8年6月総務消防委員会（第6回）")
        g.configure(a)
        selected=g.select_schedule(fixture.schedule("06月08日－06号"),"application/json",{"meetings":["kyoto:9001:1"]})
        self.assertEqual(selected["meeting_key"],"kyoto:9001:1")
        self.assertIn(b"council_id=9001",g.contract("POST",g.SCHEDULE))
    def test_materials_6280_6281_and_missing_may25_ids_stop(self):
        for cid in ("6280","6281"):
            a=fixture.review();a["council_id"]=cid;a["identity_review"].update(council_id=cid,source_kind="materials")
            with self.assertRaises(g.Stop):g.configure(a)
        a=fixture.review();a["identity_review"]["schedule_id"]=None
        with self.assertRaises(g.Stop):g.configure(a)
    def test_5716_before_term_and_boundary_day(self):
        a=fixture.review()
        a.update(council_id="5716",meeting_date="2022-12-19",council_year=2022)
        a["identity_review"].update(council_id="5716",meeting_date="2022-12-19",formal_name="令和4年12月総務消防委員会（第5回）")
        with self.assertRaises(g.Stop):g.configure(a)
        t=fixture.review()["identity_review"];t.update(meeting_date="2023-05-01",formal_name="令和5年5月総務消防委員会（第5回）")
        self.assertEqual(g.identity.target(t)["meeting_date"],"2023-05-01")
    def test_wrong_opening_is_rejected_after_correct_schedule(self):
        selected=g.select_schedule(fixture.schedule(),"application/json",{"meetings":["kyoto:6346:1"]})
        for body in ("wrong", "令和8年5月総務消防委員会（第5回）\n第5回総務消防委員会記録\n◯令和8年5月25日（月）"):
            raw=json.dumps({"tenant_minutes":[dict(minute_id=1,title="開会",body=body)]},ensure_ascii=False).encode()
            with self.assertRaises(ValueError):g.validate_minutes(raw,"application/json",selected)
    def test_source_or_registered_history_change_prevents_approval(self):
        with tempfile.TemporaryDirectory(dir=fixture.P) as td:
            a=fixture.full_approval();f=Path(td)/"approval.json";f.write_text(json.dumps(a),encoding="utf-8")
            g.validate_approval(f)
            history=Path(a["registered_history"]["path"]);original=history.read_bytes()
            try:
                history.write_bytes(b"{}")
                with self.assertRaises(g.Stop):g.validate_approval(f)
            finally:history.write_bytes(original)

class CandidateChangesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=fixture.P);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.row=candidate();self.key=changes.candidate_key(self.row)
    def evidence(self,name,items):
        folder=self.root/name;folder.mkdir(exist_ok=True)
        raw={"councils":[{"view_years":[{"view_year":"2026","council_type":[dict(council_type_name1=kind,councils=[dict(council_id=cid,name=title)]) for cid,title,kind in items]}]}]}
        p=folder/"index.json";p.write_text(json.dumps(raw,ensure_ascii=False),encoding="utf-8")
        receipt=folder/"receipt.json";receipt.write_text(json.dumps(dict(status="council_index_acquired_only",attempts=[dict(method="POST",url=changes.INDEX_URL,http_status=200,sha256=changes.sha(p),response_bytes=p.stat().st_size,raw_file=p.name)])),encoding="utf-8")
        return dict(path=str(p),sha256=changes.sha(p),receipt_path=str(receipt),receipt_sha256=changes.sha(receipt))
    def old(self):
        return self.evidence("old",[(6346,"令和8年5月総務消防委員会（第5回）","全会議")])
    def records(self,e):
        return {self.key:dict(candidate_key=self.key,checked_index_sha256=[e["sha256"]],checked_reference_sha256=[])}
    def jsonp_evidence(self,e,body=None):
        p=Path(e["path"])
        p.write_bytes(body if body is not None else b"jQuery123_456("+p.read_bytes()+b");")
        rp=Path(e["receipt_path"]);receipt=json.loads(rp.read_text(encoding="utf-8"))
        receipt["attempts"][0].update(sha256=changes.sha(p),response_bytes=p.stat().st_size)
        rp.write_text(json.dumps(receipt),encoding="utf-8")
        return dict(e,sha256=changes.sha(p),receipt_sha256=changes.sha(rp))
    def test_saved_jsonp_receipt_and_same_sha_skip_without_rewrite(self):
        e=self.jsonp_evidence(self.old());p=Path(e["path"]);original=p.read_bytes()
        g.transport.parse_index(original,"application/javascript",{"meetings":[]})
        self.assertEqual(changes.validated_index(e),e["sha256"])
        out=changes.reevaluate(e,e,[self.row],self.records(e))
        self.assertEqual(out["candidates"][0]["state"],"skip")
        self.assertFalse(out["network_authorized"]);self.assertEqual(p.read_bytes(),original)
    def test_changed_jsonp_index_reaches_related_candidate_review(self):
        old=self.jsonp_evidence(self.old())
        new=self.jsonp_evidence(self.evidence("new",[(9001,"令和8年5月総務消防委員会（第4回）","全会議")]))
        out=changes.reevaluate(old,new,[self.row],self.records(old))
        self.assertEqual(out["candidates"][0]["state"],"held_schedule_unknown")
        self.assertEqual(out["changed_council_ids"],["6346","9001"])
    def test_bom_and_optional_jsonp_semicolon(self):
        e=self.old();plain=Path(e["path"]).read_bytes()
        for raw in (b"\xef\xbb\xbf"+plain,b" \n jQuery9("+plain+b") \n"):
            wrapped=self.jsonp_evidence(e,raw)
            self.assertEqual(changes.validated_index(wrapped),wrapped["sha256"])
    def test_unknown_or_incomplete_jsonp_is_rejected(self):
        e=self.old();plain=Path(e["path"]).read_bytes()
        for raw in (b"callback("+plain+b");",b"jQuery.a("+plain+b");",
                    b"jQuery1("+plain,b"jQuery1("+plain+b"); extra()"):
            with self.subTest(raw=raw[:12]):
                wrapped=self.jsonp_evidence(e,raw)
                with self.assertRaises(ValueError):changes.validated_index(wrapped)
                with self.assertRaises((ValueError,g.Stop)):g.transport.parse_index(raw,"application/javascript",{"meetings":[]})
    def test_jsonp_original_tamper_is_still_rejected(self):
        e=self.jsonp_evidence(self.old());p=Path(e["path"])
        p.write_bytes(p.read_bytes()+b" ")
        with self.assertRaises(ValueError):changes.validated_index(e)
    def test_receipts_remain_strict_json(self):
        e=self.jsonp_evidence(self.old());p=Path(e["receipt_path"])
        p.write_bytes(b"jQuery1("+p.read_bytes()+b");");e["receipt_sha256"]=changes.sha(p)
        with self.assertRaises(json.JSONDecodeError):changes.validated_index(e)


    def test_same_sha_never_requeries(self):
        e=self.old();out=changes.reevaluate(e,e,[self.row],self.records(e))
        self.assertEqual(out["candidates"][0]["state"],"skip");self.assertFalse(out["network_authorized"])
    def test_changed_unrelated_index_does_not_recheck_candidate(self):
        old=self.old();new=self.evidence("new",[(6346,"令和8年5月総務消防委員会（第5回）","全会議"),(9000,"令和8年6月環境福祉委員会（第1回）","全会議")])
        result=changes.reevaluate(old,new,[self.row],self.records(old))["candidates"][0]
        self.assertEqual(result["reason"],"unrelated_index_change")
    def test_related_change_rechecks_but_does_not_guess_schedule(self):
        old=self.old();new=self.evidence("new",[(9001,"令和8年5月総務消防委員会（第4回）","全会議")])
        result=changes.reevaluate(old,new,[self.row],self.records(old))["candidates"][0]
        self.assertEqual(result["state"],"held_schedule_unknown");self.assertFalse(result["identifiers_confirmed"])
    def test_materials_and_out_of_term_excluded(self):
        old=self.old();new=self.evidence("new",[(6280,"令和8年5月総務消防委員会（第4回）","資料")])
        result=changes.reevaluate(old,new,[candidate("6280")],{})["candidates"][0]
        self.assertEqual(result["state"],"excluded_materials")
        row=candidate();row["meeting_date"]="2022-12-19"
        self.assertEqual(changes.reevaluate(old,old,[row],{})["candidates"][0]["state"],"excluded_before_term")
    def test_date_unknown_not_outside_term_or_eligible(self):
        e=self.old();row=candidate();row.update(meeting_date=None,source_position="tr[1]")
        self.assertEqual(changes.reevaluate(e,e,[row],{})["candidates"][0]["state"],"held_date_unknown")
        row=candidate();row["official_date_confirmed"]=False
        self.assertEqual(changes.reevaluate(e,e,[row],{})["candidates"][0]["state"],"held_date_unverified")
    def test_duplicate_observations_rejected(self):
        e=self.old()
        with self.assertRaises(ValueError):changes.reevaluate(e,e,[self.row,self.row],{})
    def test_materials_with_unknown_date_are_not_analysis_candidates(self):
        e=self.old();row=dict(council_id="6280",source_kind="materials",meeting_date=None)
        self.assertEqual(changes.reevaluate(e,e,[row],{})["candidates"][0]["state"],"excluded_materials")
    def mapping(self):
        p=self.root/"reference.html"
        literal="https://ssp.kaigiroku.net/tenant/kyoto/SpMinuteView.html?council_id=9001&schedule_id=1"
        p.write_text(literal,encoding="utf-8")
        reference=dict(candidate_key=self.key,kind="official_identifier_reference",path=str(p),sha256=changes.sha(p),
                       source_url="https://www2.city.kyoto.lg.jp/shikai/example.html",source_position="a[1]",literal=literal,council_id="9001",schedule_id="1")
        target=dict(city="kyoto",source_kind="meeting",council_id="9001",schedule_id="1",meeting_date="2026-05-25",committee="総務消防委員会",round=4,formal_name="令和8年5月総務消防委員会（第4回）")
        return dict(reference=reference,target=target)
    def test_new_official_mapping_promotes_only_to_review(self):
        e=self.evidence("new",[(9001,"令和8年5月総務消防委員会（第4回）","全会議")]);mapping=self.mapping()
        result=changes.reevaluate(e,e,[self.row],self.records(e),{self.key:mapping})["candidates"][0]
        self.assertEqual(result["state"],"identity_review_candidate")
        self.assertFalse(result["identifiers_confirmed"]);self.assertFalse(result["network_authorized"])
    def test_recording_or_mismatched_mapping_cannot_promote(self):
        e=self.evidence("new",[(9001,"令和8年5月総務消防委員会（第4回）","全会議")])
        for change in ("recording","date"):
            mapping=self.mapping()
            if change=="recording":mapping["reference"]["kind"]="official_recording"
            else:mapping["target"]["meeting_date"]="2026-05-24"
            with self.assertRaises(ValueError):changes.reevaluate(e,e,[self.row],{}, {self.key:mapping})
    def test_corrupt_index_or_receipt_stops(self):
        e=self.old();Path(e["path"]).write_bytes(b"{}")
        with self.assertRaises(ValueError):changes.reevaluate(e,e,[self.row],{})
    def test_previously_checked_reference_and_index_do_not_reopen(self):
        e=self.evidence("new",[(9001,"令和8年5月総務消防委員会（第4回）","全会議")]);mapping=self.mapping()
        records=self.records(e);records[self.key]["checked_reference_sha256"]=[mapping["reference"]["sha256"]]
        result=changes.reevaluate(e,e,[self.row],records,{self.key:mapping})["candidates"][0]
        self.assertEqual(result["state"],"skip")

class SemanticReviewTests(unittest.TestCase):
    def setUp(self):
        self.plan=dict(meeting_key="kyoto:1:1",input_sha256="a"*64,original_raw_sha256="b"*64,selected_keys=["ssp_1_1_1","ssp_1_1_3"],
          threads=[dict(main_statement=dict(meeting_id="ssp_1_1",sequence_number=i),related_statements=[dict(id="ssp_1_1_"+str(i))]) for i in (1,3)])
        self.state=dict(results={k:dict(analysis=dict(summary="synthetic",reasoning="synthetic")) for k in self.plan["selected_keys"]})
        self.digests={k:replay.io.digest(replay.intake.encode(v["analysis"])) for k,v in self.state["results"].items()}
        self.approval=dict(scope="approved_partial_publication",approval_reference="synthetic",meeting_key="kyoto:1:1",input_sha256="a"*64,original_raw_sha256="b"*64,plan_sha256=replay.repair.plan_digest(self.plan),analysis_receipt_sha256="c"*64,
            accepted={"ssp_1_1_1":dict(analysis_sha256=self.digests["ssp_1_1_1"],source_reference="source1")},
            exclusions=[dict(statement_id="ssp_1_1_3",meeting_key="kyoto:1:1",analysis_sha256=self.digests["ssp_1_1_3"],source_reference="source3",source_statement_ids=["ssp_1_1_3"],reason="incorrect condition")])
        self.review=dict(reviews={"ssp_1_1_1":dict(decision="accepted_for_partial_publication",summary_and_reasoning_reviewed=True,positions="1",note="source and result compared",result_sha256=self.digests["ssp_1_1_1"]),
                                "ssp_1_1_3":dict(decision="hold",reason="reasoning condition missing")})
    def test_partial_acceptance_keeps_held_analysis_immutable(self):
        before=copy.deepcopy(self.state)
        out=replay.semantic_gate(self.review,self.plan,self.state,self.approval,"c"*64)
        self.assertEqual(out["accepted_thread_ids"],["ssp_1_1_1"]);self.assertEqual(self.state,before)
    def test_summary_only_review_cannot_pass(self):
        self.review["reviews"]["ssp_1_1_1"]["summary_and_reasoning_reviewed"]=False
        with self.assertRaises(replay.io.Stop):replay.semantic_gate(self.review,self.plan,self.state,self.approval,"c"*64)
    def test_all_selected_can_pass_without_claiming_meeting_complete(self):
        a=copy.deepcopy(self.approval);a.update(scope="approved_selected_results",exclusions=[])
        key="ssp_1_1_3";a["accepted"][key]=dict(analysis_sha256=self.digests[key],source_reference="source3")
        self.review["reviews"][key]=dict(decision="accepted_for_partial_publication",summary_and_reasoning_reviewed=True,
            positions="3",note="source checked",result_sha256=self.digests[key])
        out=replay.semantic_gate(self.review,self.plan,self.state,a,"c"*64)
        self.assertEqual(len(out["accepted_thread_ids"]),2);self.assertFalse(out["meeting_complete"])
    def test_reasoning_change_invalidates_acceptance(self):
        self.state["results"]["ssp_1_1_1"]["analysis"]["reasoning"]="changed"
        with self.assertRaises(replay.io.Stop):replay.semantic_gate(self.review,self.plan,self.state,self.approval,"c"*64)
    def test_held_source_cannot_leak_into_accepted_timeline(self):
        self.plan["threads"][0]["related_statements"].append(dict(id="ssp_1_1_3"))
        self.approval["plan_sha256"]=replay.repair.plan_digest(self.plan)
        with self.assertRaises(replay.io.Stop):replay.semantic_gate(self.review,self.plan,self.state,self.approval,"c"*64)
    def test_candidate_cannot_change_reviewed_meaning_or_attribution(self):
        key="ssp_1_1_1";axes=("evidence","solution","local_focus","constructive")
        original=dict(id=key,meeting_id="ssp_1_1",sequence_number=1,meeting_date="2026-05-25",source_url="synthetic")
        thread=dict(main_statement=original,councilor_key="synthetic-member")
        result=dict(summary="reviewed summary",reasoning="reviewed reasoning",scores={k:1 for k in axes})
        row=dict(original,speaker="synthetic-member",summary=result["summary"],scoring_reasoning=result["reasoning"],
                 **{k+"_score":1 for k in axes})
        state=dict(results={key:dict(analysis=result)})
        replay.verify_summary_results({key:row},{key},[thread],state)
        for field,value in (("scoring_reasoning","changed"),("summary","changed"),("speaker","other"),
                            ("source_url","other"),("evidence_score",2)):
            bad=dict(row);bad[field]=value
            with self.assertRaises(replay.io.Stop):replay.verify_summary_results({key:bad},{key},[thread],state)

if __name__=="__main__":unittest.main()
