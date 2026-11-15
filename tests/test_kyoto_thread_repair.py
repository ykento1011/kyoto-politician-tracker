"""No HTTP/API. Kyoto source-role and repair-reuse regressions."""
import copy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"data-pipeline"))
_temporary_root = None
if not os.environ.get("KYOTO_PRIVATE_ROOT"):
    _temporary_root = tempfile.TemporaryDirectory(prefix="kyoto-thread-test-")
    os.environ["KYOTO_PRIVATE_ROOT"] = _temporary_root.name
import kyoto_thread_contract as t
from kyoto_thread_repair import same_analysis_input, make_plan
import kyoto_thread_repair as repair
import kyoto_gemini_budget as budget

def tearDownModule():
    if _temporary_root is not None:
        target=Path(_temporary_root.name).resolve()
        assert target.parent==Path(tempfile.gettempdir()).resolve() and target.name.startswith("kyoto-thread-test-")
        os.environ.pop("KYOTO_PRIVATE_ROOT",None)
        _temporary_root.cleanup()

MASTER=[dict(name=n,aliases=[]) for n in ("甲議員","乙議員","進行委員")]
def statement(seq,speaker,text):
    return dict(id="ssp_1_1_"+str(seq),meeting_id="ssp_1_1",sequence_number=seq,
                speaker=speaker,statement_text=text,meeting_title="TEST",meeting_date="2025-01-01")
def block(seq,title,code,text):
    return dict(minute_id=seq,title=title,minute_type_code=code,body="<pre>"+text+"</pre>")
def build(spec):
    rows=[statement(seq,sp,text) for seq,sp,title,code,text in spec]
    blocks=[block(seq,title,code,text) for seq,sp,title,code,text in spec]
    return t.build(rows,blocks,MASTER,lambda s:s in ("進行いたします。","終わります。"))

class SpeakerTests(unittest.TestCase):
    def test_deputy_question_splits_previous_member(self):
        result=build([(1,"甲議員","委員（甲議員）",5,"制度について伺います。"),
                      (2,"役人","部長（役人）",6,"お答えします。"),
                      (3,"副委員長（乙議員）","副委員長（乙議員）",5,"別の質問をします。"),
                      (4,"役人","部長（役人）",6,"回答です。")])
        self.assertFalse(result["holds"])
        self.assertEqual([[r["sequence_number"] for r in x["related_statements"]] for x in result["threads"]],[[1,2],[3,4]])
        self.assertEqual(result["threads"][1]["councilor_key"],"乙議員")
    def test_same_member_requestion_and_role_alias(self):
        result=build([(1,"乙議員","委員（乙議員）",5,"質問です。"),
                      (2,"役人","部長（役人）",6,"答弁です。"),
                      (3,"副委員長（乙議員）","副委員長（乙議員）",5,"再質問です。")])
        self.assertEqual(len(result["threads"]),1)
        self.assertEqual(len(result["threads"][0]["prompt_statement_ids"]),3)
    def test_chair_procedure_does_not_become_question(self):
        result=build([(1,"委員長（進行委員）","委員長（進行委員）",4,"質疑のある方は挙手願います。"),
                      (2,"甲議員","委員（甲議員）",5,"質問です。"),
                      (3,"委員長（進行委員）","委員長（進行委員）",4,"部長。"),
                      (4,"役人","部長（役人）",6,"回答です。")])
        self.assertEqual(len(result["threads"]),1)
        self.assertNotIn("挙手",str(result["threads"][0]["context_log"]))
        self.assertNotIn("部長。",str(result["threads"][0]["context_log"]))
    def test_chair_can_ask_when_original_marks_question(self):
        result=build([(1,"委員長（進行委員）","委員長（進行委員）",5,"政策について伺います。"),
                      (2,"役人","部長（役人）",6,"回答します。")])
        self.assertEqual(result["threads"][0]["councilor_key"],"進行委員")
    def test_unknown_is_held_not_administration(self):
        result=build([(1,"甲議員","委員（甲議員）",5,"質問です。"),
                      (2,"未知","参考人（未知）",7,"話します。")])
        self.assertEqual(result["holds"][0]["sequence"],2)
        self.assertFalse(result["threads"][0]["has_admin_response"])
    def test_conflicting_master_and_admin_role_is_held(self):
        result=build([(1,"乙議員","部長（乙議員）",6,"回答です。")])
        self.assertEqual(len(result["holds"]),1)
    def test_agenda_change_excludes_next_explanation(self):
        result=build([(197,"甲議員","委員（甲議員）",5,"職員について伺います。"),
                      (199,"役人","部長（役人）",6,"職員について答弁します。"),
                      (206,"委員長（進行委員）","委員長（進行委員）",4,"以上で行財政局を終わります。"),
                      (208,"役人","次長（役人）",6,"次の選挙条例を説明します。"),
                      (210,"副委員長（乙議員）","副委員長（乙議員）",5,"選挙費用を伺います。"),
                      (212,"役人","次長（役人）",6,"選挙費用について回答します。")])
        self.assertEqual([r["sequence_number"] for r in result["threads"][0]["related_statements"]],[197,199,206])
        self.assertNotIn("選挙",str(result["threads"][0]["context_log"]))
        self.assertEqual(result["threads"][1]["main_statement"]["sequence_number"],210)
    def test_filtered_original_chair_boundary_is_preserved(self):
        rows=[statement(1,"甲議員","質問です。"),statement(2,"役人","回答です。"),statement(4,"役人","次議案の説明です。")]
        blocks=[block(1,"委員（甲議員）",5,"質問です。"),block(2,"部長（役人）",6,"回答です。"),
                block(3,"委員長（進行委員）",4,"以上で審査を終わります。"),block(4,"部長（役人）",6,"次議案の説明です。")]
        result=t.build(rows,blocks,MASTER,lambda _:False)
        self.assertEqual([r["sequence_number"] for r in result["threads"][0]["related_statements"]],[1,2])
    def test_timeline_preserves_original_names_and_roles(self):
        result=build([(1,"副委員長（乙議員）","副委員長（乙議員）",5,"質問です。"),(2,"役人","部長（役人）",6,"回答です。")])
        timeline=t.timeline(result["threads"],result["roles"])["1"]
        self.assertEqual(timeline[0]["speaker"],"副委員長（乙議員）")
        self.assertFalse(timeline[0]["is_admin"])
        self.assertTrue(timeline[1]["is_admin"])
    def test_duplicate_ids_stop(self):
        with self.assertRaises(ValueError):
            build([(1,"甲議員","委員（甲議員）",5,"質問です。"),(1,"役人","部長（役人）",6,"回答です。")])

class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.fp=dict(speaker="甲議員",statement_ids=["1","2","3"],prompt_statement_ids=["1","2"],prompt_sha256="a"*64,config={"temperature":0})
    def test_changed_prompt_or_actual_statement_id_cannot_reuse(self):
        for key,value in [("prompt_sha256","b"*64),("prompt_statement_ids",["1","4"]),("speaker","乙議員"),("config",{"temperature":1})]:
            other=copy.deepcopy(self.fp);other[key]=value
            self.assertFalse(same_analysis_input(self.fp,other))
    def test_untransmitted_chair_context_can_be_trimmed_without_resending(self):
        other=copy.deepcopy(self.fp);other["statement_ids"]=["1","2"]
        self.assertTrue(same_analysis_input(self.fp,other))

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=repair.io.ARTIFACT,prefix="thread-repair-synthetic-")
        self.root=Path(self.tmp.name)
        self.value=dict(category="test",summary="test",reasoning="test",keywords=[],
                        scores=dict(evidence=1,solution=1,local_focus=1,constructive=1))
        self.policy=dict(api_go=True,model=budget.MODEL,target_confirmed=True,trial_mode="retrospective_private",
            official_coverage="unknown",estimated_budget_accepted=True,target_review="synthetic",price_reference="synthetic",
            fx_reference="synthetic",sdk_reference="synthetic",budget_stop_jpy="1000",sdk_usage_supported=True,
            pricing_checked_utc=datetime.now(timezone.utc).isoformat(),input_usd_per_million="0.30",
            output_usd_per_million="2.50",jpy_per_usd_upper="250")
        repair.io.write_json(self.root/"policy.json",self.policy)
        self.config=dict(private_root=str(self.root),prepared_stage=str(self.root/"unused-stage"),api_policy=str(self.root/"policy.json"))
        reused=dict(status="analysis_success",analysis=self.value)
        self.plan=dict(revision_id="synthetic-v1",meeting_key="kyoto:1:1",manifest_sha256="a"*64,
            prior_estimated_jpy="1",selected_keys=["ssp_1_1_1","ssp_1_1_3"],pending_keys=["ssp_1_1_3"],
            reused_results={"ssp_1_1_1":reused},
            threads=[dict(main_statement=dict(meeting_id="ssp_1_1",sequence_number=i)) for i in (1,3)],
            fingerprints={"ssp_1_1_3":dict(prompt_sha256=hashlib.sha256(b"synthetic prompt").hexdigest())})
        self.calls=0
    def tearDown(self):
        assert self.root.resolve().parent==repair.io.ARTIFACT.resolve() and self.root.name.startswith("thread-repair-synthetic-")
        self.tmp.cleanup()
    def sender(self,prompt,config):
        self.calls+=1
        return dict(text=json.dumps(self.value),model=budget.MODEL,finish_reason="STOP",
                    usage=dict(prompt_token_count=100,candidates_token_count=20,thoughts_token_count=0,total_token_count=120))
    def legacy(self,path,meter,master):
        return dict(evaluate_thread_with_gemini=lambda t:json.loads(meter.generate_content("synthetic prompt",{}).text))
    def invoke(self,*,resume=False,send=None):
        with patch.object(repair,"make_plan",return_value=self.plan),patch.object(budget,"legacy_functions",side_effect=self.legacy), \
             patch.object(budget,"live_sender",return_value=(send or self.sender,type("Client",(),{"close":lambda s:None})())):
            return repair.run(self.config,resume=resume)
    def test_exact_reuse_and_completed_resume_never_resend(self):
        out=self.invoke();self.assertEqual(self.calls,1)
        state=repair.intake.read_json(out/"receipt.json")
        self.assertEqual(state["success"],2);self.assertEqual(len(state["api_attempts"]),1)
        self.invoke(resume=True);self.assertEqual(self.calls,1)
    def test_durable_response_before_checkpoint_is_recovered(self):
        out=self.invoke();state=repair.intake.read_json(out/"receipt.json")
        state["results"].pop("ssp_1_1_3");state["status"]="in_progress"
        repair.io.write_json(out/"receipt.json",state)
        self.invoke(resume=True);self.assertEqual(self.calls,1)
        self.assertEqual(len(repair.intake.read_json(out/"receipt.json")["results"]),2)
    def test_unknown_billing_blocks_resume_and_preserves_receipt(self):
        def failed(*a):self.calls+=1;raise RuntimeError("synthetic timeout")
        with self.assertRaises(budget.BudgetStop):self.invoke(send=failed)
        out=repair.output_path(self.config,self.plan);before=(out/"receipt.json").read_bytes()
        with self.assertRaises(budget.BudgetStop):self.invoke(resume=True)
        self.assertEqual(self.calls,1);self.assertEqual((out/"receipt.json").read_bytes(),before)
    def test_prior_spend_is_reserved_before_new_request(self):
        self.plan["prior_estimated_jpy"]="999"
        with self.assertRaises(budget.BudgetStop):self.invoke()
        self.assertEqual(self.calls,0)
    def test_modified_plan_cannot_resume_old_revision(self):
        self.invoke();self.plan["manifest_sha256"]="b"*64
        with self.assertRaises(repair.io.Stop):self.invoke(resume=True)
        self.assertEqual(self.calls,1)

@unittest.skipUnless(os.environ.get("KYOTO_REPAIR_TEST_CONFIG"),"Private saved-source fixture is not published")
class Saved6356Tests(unittest.TestCase):
    def test_all_old_threads_and_197_source_boundary(self):
        plan=make_plan(json.loads(Path(os.environ["KYOTO_REPAIR_TEST_CONFIG"]).read_text(encoding="utf-8-sig")))
        self.assertEqual(len(plan["changes"]),14)
        self.assertEqual(len(plan["reused_results"]),10)
        self.assertEqual(len(plan["pending_keys"]),9)
        first=next(t for t in plan["threads"] if t["main_statement"]["sequence_number"]==197)
        second=next(t for t in plan["threads"] if t["main_statement"]["sequence_number"]==210)
        self.assertEqual(first["councilor_key"],"椋田隆知")
        self.assertEqual(second["councilor_key"],"谷口みゆき")
        self.assertFalse(any(r["sequence_number"]>=208 for r in first["related_statements"]))
        self.assertFalse(set(first["prompt_statement_ids"]) & set(second["prompt_statement_ids"]))

if __name__=="__main__":unittest.main()
