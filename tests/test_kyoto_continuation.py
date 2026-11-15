"""New continuation boundaries only: synthetic fixtures, zero network/API calls."""
import ast
import base64
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"data-pipeline"))
_private_test_root=tempfile.TemporaryDirectory(prefix="kyoto-continuation-ci-")
_saved_private_root=os.environ.get("KYOTO_PRIVATE_ROOT")
os.environ["KYOTO_PRIVATE_ROOT"]=_private_test_root.name
import kyoto_continuation as c
import kyoto_gemini_budget as g
import kyoto_one_meeting_guard as f
import kyoto_council_list_guard as io
import kyoto_new_meetings as n
if _saved_private_root is None:os.environ.pop("KYOTO_PRIVATE_ROOT",None)
else:os.environ["KYOTO_PRIVATE_ROOT"]=_saved_private_root

# Synthetic IDs, not a copy of the private 750-meeting history.
_keys=["kyoto:"+str(i)+":1" for i in range(10000,10750)]
_ledger=dict(schema=1,city="kyoto",completeness="unknown",meetings=_keys,
    sources=[dict(sha256="a"*64,coverage="SYNTHETIC CI",official_completeness="unknown",
        meetings=[dict(key=k,records=1,date_min="2026-01-01",date_max="2026-01-01") for k in _keys])])
io.LEDGER.parent.mkdir(parents=True,exist_ok=True)
io.write_json(io.LEDGER,_ledger)
io.LEDGER_SHA=f.LEDGER_SHA=io.digest(io.LEDGER.read_bytes())


def tearDownModule():
    assert Path(_private_test_root.name).resolve()==io.ARTIFACT.resolve()
    assert io.ARTIFACT.name.startswith("kyoto-continuation-ci-")
    _private_test_root.cleanup()



def result():
    return dict(category="test",summary="test",keywords=[],reasoning="test",
                scores=dict(evidence=1,solution=1,local_focus=1,constructive=1))


def response():
    return dict(text=json.dumps(result()),model=g.MODEL,finish_reason="STOP",
                usage=dict(prompt_token_count=100,candidates_token_count=20,
                           thoughts_token_count=30,total_token_count=150))


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=io.ARTIFACT,prefix="continuation-test-")
        self.root=Path(self.tmp.name)
        self.network=patch.object(socket.socket,"connect",side_effect=AssertionError("Network prohibited"))
        self.network.start()
        self.stage=self.root/"ready-synthetic";self.stage.mkdir()
        p=self.stage/"data-pipeline";p.mkdir()
        raw=n.encode([dict(meeting_id="ssp_9000_1",sequence_number=i) for i in (1,2)])
        (p/"sagebase_crawled_data.json").write_bytes(raw)
        m=dict(decision="confirmed_new_meeting",meeting_key="kyoto:9000:1",input_sha256=io.digest(raw),
               files={"data-pipeline/sagebase_crawled_data.json":io.digest(raw)})
        io.write_json(self.stage/"manifest.json",m)
        h=io.digest(n.encode(m))
        io.write_json(self.stage/"READY.json",dict(status="prepared_only",manifest_sha256=h))
        self.policy=self.root/"policy.json"
        io.write_json(self.policy,dict(api_go=True,model=g.MODEL,target_confirmed=True,
            official_coverage="unknown",trial_mode="new_meeting_private",estimated_budget_accepted=True,
            budget_stop_jpy="1000",target_review="SYNTHETIC",price_reference="SYNTHETIC",
            fx_reference="SYNTHETIC",sdk_reference="SYNTHETIC",sdk_usage_supported=True,
            pricing_checked_utc=datetime.now(timezone.utc).isoformat(),input_usd_per_million="0.30",
            output_usd_per_million="2.50",jpy_per_usd_upper="250",
            meeting_key=m["meeting_key"],input_sha256=m["input_sha256"],manifest_sha256=h))
        self.public=ROOT/"frontend/public/data/kyoto_statements_summary.json"
        self.calls=[]

    def tearDown(self):
        self.network.stop()
        # TemporaryDirectory only removes its own verified fixture root.
        assert self.root.parent==io.ARTIFACT and self.root.name.startswith("continuation-test-")
        self.tmp.cleanup()

    def legacy(self,path,meter,master):
        def evaluate(t):
            return json.loads(meter.generate_content("prompt-"+str(t["main_statement"]["sequence_number"]),{}).text)
        return dict(build_debate_threads=lambda rows:[dict(main_statement=r) for r in rows],
                    is_procedural_or_voting=lambda t:False,evaluate_thread_with_gemini=evaluate)

    def run_analysis(self,send,**kwargs):
        def wrapped(p,cfg):self.calls.append(p);return send(p,cfg)
        with patch.object(g,"legacy_functions",side_effect=self.legacy),patch.object(
                g,"live_sender",return_value=(wrapped,Mock())):
            return g.run(self.stage,self.policy,self.public,self.root,**kwargs)

    def interrupted_known_cost(self):
        def send(prompt,cfg):
            r=response()
            if prompt.endswith("2"):r["text"]="INVALID JSON"
            return r
        with self.assertRaises(g.BudgetStop):self.run_analysis(send)
        return next(self.root.glob("gemini-resumable-*"))

    def test_retry_only_unfinished_and_cumulative_cost(self):
        out=self.interrupted_known_cost()
        first=io.digest((out/"receipt.json").read_bytes())
        with self.assertRaises(g.BudgetStop):self.run_analysis(lambda *a:response(),resume=True)
        self.assertEqual(io.digest((out/"receipt.json").read_bytes()),first)
        self.run_analysis(lambda *a:response(),resume=True,retry_failed=True)
        self.assertEqual(self.calls,["prompt-1","prompt-2","prompt-2"])
        r=n.read_json(out/"receipt.json")
        self.assertEqual(r["success"],2);self.assertEqual(len(r["api_attempts"]),3)
        self.assertEqual(g.Decimal(r["total_estimated_jpy"]),g.Decimal("0.11625"))
        self.assertFalse(r["meeting_complete"])

    def test_completed_resume_makes_no_sender(self):
        out=self.run_analysis(lambda *a:response())
        with patch.object(g,"legacy_functions",side_effect=self.legacy),patch.object(
                g,"live_sender",side_effect=AssertionError("Completed threads must not be sent")):
            g.run(self.stage,self.policy,self.public,self.root,resume=True)
        self.assertEqual(len(self.calls),2)

    def test_unknown_usage_blocks_resume_without_overwrite(self):
        with self.assertRaises(g.BudgetStop):
            self.run_analysis(lambda *a:dict(response(),usage={}))
        out=next(self.root.glob("gemini-resumable-*"))
        before=(out/"receipt.json").read_bytes()
        with self.assertRaises(g.BudgetStop):self.run_analysis(lambda *a:response(),resume=True,retry_failed=True)
        self.assertEqual((out/"receipt.json").read_bytes(),before)
        self.assertEqual(len(self.calls),1)

    def test_input_change_cannot_resume(self):
        self.run_analysis(lambda *a:response())
        (self.stage/"data-pipeline/sagebase_crawled_data.json").write_text("[]")
        with self.assertRaises(g.BudgetStop):self.run_analysis(lambda *a:response(),resume=True)
        self.assertEqual(len(self.calls),2)

    def test_atomic_success_can_recover_before_result_checkpoint(self):
        out=self.run_analysis(lambda *a:response())
        r=n.read_json(out/"receipt.json");r["results"]={};r["success"]=0
        io.write_json(out/"receipt.json",r)
        self.run_analysis(lambda *a:response(),resume=True)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(n.read_json(out/"receipt.json")["success"],2)

    def test_concurrent_or_stale_lock_stops(self):
        out=self.run_analysis(lambda *a:response())
        (out/"RUNNING.lock").write_text("held")
        with self.assertRaises(FileExistsError):self.run_analysis(lambda *a:response(),resume=True)
        self.assertEqual(len(self.calls),2)

    def test_cost_tampering_stops(self):
        out=self.run_analysis(lambda *a:response())
        r=n.read_json(out/"receipt.json");r["api_attempts"][0]["cost_jpy"]="0.001"
        io.write_json(out/"receipt.json",r)
        with self.assertRaises(g.BudgetStop):self.run_analysis(lambda *a:response(),resume=True)
        self.assertEqual(len(self.calls),2)

    def test_history_states_do_not_imply_publication_or_completeness(self):
        r=c.record(self.root,"kyoto:9000:1","a"*64,acquired=True,analyzed=True)
        self.assertTrue(r["acquired"]);self.assertTrue(r["analyzed"])
        self.assertFalse(r["published"]);self.assertFalse(r["meeting_complete"])
        before=(self.root/"continuation-history.json").read_bytes()
        c.inspect(self.root)
        self.assertEqual((self.root/"continuation-history.json").read_bytes(),before)
        with self.assertRaises(io.Stop):c.record(self.root,"kyoto:9000:1","a"*64,published=True)
        with self.assertRaises(io.Stop):c.record(self.root,"kyoto:9000:1","b"*64,acquired=True)

    def scope(self,only=False):
        return dict(scope="kyoto_reviewed_council_schedules" if only else "kyoto_one_reviewed_meeting",
                    council_id="9000",schedule_id="2",meeting_date="2026-04-09",council_year=2026,candidate_review="SYNTHETIC")

    def schedules(self):
        return io.json_bytes(dict(tenant_id=355,council_id=9000,schedules_and_materials=[
            dict(schedule_id=1,name="令和8年4月8日"),dict(schedule_id=2,name="令和8年4月9日")]))

    def test_exact_scope_and_schedule_diff(self):
        f.configure(self.scope())
        selected=f.select_schedule(self.schedules(),"application/json",{"meetings":[]})
        self.assertEqual(selected["meeting_key"],"kyoto:9000:2")
        self.assertEqual(f.contract("POST",f.MINUTE,"2"),
                         b"tenant_id=355&power_user=false&council_id=9000&schedule_id=2")
        with self.assertRaises(io.Stop):f.contract("GET","https://example.com")
        f.configure(self.scope(True))
        with self.assertRaises(io.Stop):f.contract("POST",f.MINUTE,"2")
        self.assertEqual(len(f.schedule_candidates(self.schedules(),"application/json",{"meetings":[]})),2)

    def test_wrong_schedule_date_or_existing_meeting_stops(self):
        f.configure(dict(self.scope(),meeting_date="2026-04-10"))
        with self.assertRaises(io.Stop):f.select_schedule(self.schedules(),"application/json",{"meetings":[]})
        f.configure(self.scope())
        with self.assertRaises(io.Stop):
            f.select_schedule(self.schedules(),"application/json",{"meetings":["kyoto:9000:2"]})

    def fake_acquire(self,only,fail=False):
        approval=dict(self.scope(only),pm_go=True,run_id="test",reference="SYNTHETIC",
                      limits=dict(f.LIMITS,http_attempts=2 if only else 3),guard_sha256="fixture")
        path=self.root/"network.json";io.write_json(path,approval)
        f.configure(approval);calls=[]
        def request(method,url,cookies,trial,slot,sid):
            calls.append((method,url,sid))
            if fail and slot==2:raise io.Stop("Synthetic transport failure")
            body=b"<html></html>" if slot==1 else self.schedules() if slot==2 else io.json_bytes(
                dict(tenant_id=355,council_id=9000,schedule_id=2,tenant_minutes=[dict(minute_id=1,title="test",body="test")]))
            return dict(body_b64=base64.b64encode(body).decode(),bytes=len(body),status=200,
                content_type="text/html" if slot==1 else "application/json",cookies=[],
                started_utc=io.utc(),completed_utc=io.utc())
        with patch.object(f,"validate_approval",return_value=approval),patch.object(f,"STORAGE",self.root/"http"),\
             patch.object(f,"isolated_request",side_effect=request),patch.object(f.transport,"validate_session"),\
             patch.object(f.time,"sleep"):
            if fail:
                with self.assertRaises(io.Stop):f.acquire(path)
                self.assertEqual(len(calls),2)
                return n.read_json(self.root/"http/test/receipt.json")
            out=f.acquire(path)
            self.assertEqual(len(calls),2 if only else 3)
            return n.read_json(out/"receipt.json")

    def test_schedule_only_never_fetches_body(self):
        r=self.fake_acquire(True)
        self.assertEqual(r["status"],"schedules_acquired_pending_review")
        self.assertEqual(len(r["schedule_candidates"]),2)

    def test_one_meeting_limits_and_scope(self):
        r=self.fake_acquire(False)
        self.assertEqual(r["status"],"raw_acquired_pending_offline_reconciliation")
        self.assertEqual(r["selected_schedule"]["meeting_key"],"kyoto:9000:2")

    def test_partial_acquisition_never_succeeds(self):
        self.assertEqual(self.fake_acquire(False,True)["status"],"stopped")

    def test_incomplete_analysis_cannot_generate_candidate(self):
        p=self.root/"partial.json";io.write_json(p,{"status":"stopped_incomplete"})
        with self.assertRaises(io.Stop):c.private_project(self.stage,p,self.public,self.root)
        self.assertEqual(list(self.root.glob(".incomplete-*")),[])

    def test_no_implicit_publish_or_scheduler(self):
        with patch.object(c,"root_check",return_value=self.root):
            for op in ("publish","scheduler"):
                with self.assertRaises(io.Stop):c.execute(op,{})
        receipt=self.root/"not-deployed.json";io.write_json(receipt,{"pm_confirmed_deployed":False})
        with self.assertRaises(io.Stop):c.acknowledge_publication(self.root,{"publication_receipt":str(receipt)})

    def test_accepted_analysis_is_reused_without_api(self):
        receipt=self.root/"accepted.json";io.write_json(receipt,{"accepted_success":21})
        m=n.read_json(self.stage/"manifest.json");m["original_raw_sha256"]="a"*64
        io.write_json(self.stage/"manifest.json",m)
        c.record(self.root,m["meeting_key"],"a"*64,acquired=True,analyzed=True,
                 prepared_stage=str(self.stage),analysis_receipt=str(receipt),
                 analysis_receipt_sha256=io.digest(receipt.read_bytes()))
        with patch.object(c,"root_check",return_value=self.root),patch.object(
                g,"run",side_effect=AssertionError("Accepted analyses must not run again")):
            self.assertEqual(c.execute("analyze",{"prepared_stage":str(self.stage)}),str(receipt.parent))

    def test_failed_acquisition_cannot_refetch_with_another_run_id(self):
        approval=dict(self.scope(),run_id="first")
        p=self.root/"network.json";io.write_json(p,approval)
        config=dict(network_approval=str(p))
        with patch.object(c,"root_check",return_value=self.root),patch.object(f,"validate_approval"),patch.object(
                f,"acquire",side_effect=io.Stop("Synthetic failed HTTP")) as call:
            with self.assertRaises(io.Stop):c.execute("acquire",config)
            approval["run_id"]="second";io.write_json(p,approval)
            with self.assertRaises(FileExistsError):c.execute("acquire",config)
            self.assertEqual(call.call_count,1)

    def test_publication_ack_needs_matching_content_and_pm_receipt(self):
        stage=self.root/"candidate";(stage/"data").mkdir(parents=True)
        (stage/"timeline-additions").mkdir()
        row=dict(id="ssp_9000_1_1",meeting_id="ssp_9000_1",sequence_number=1,meeting_title="test",
                 meeting_date="2026-04-09",speaker="test",category="test",summary="test",
                 scoring_reasoning="test",statement_snippet="test",statement_text="test",
                 evidence_score=1,solution_score=1,local_focus_score=1,constructive_score=1,
                 source_url="https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=9000&schedule_id=1#minute_1")
        public=self.root/"observed/kyoto_statements_summary.json";public.parent.mkdir()
        public.write_bytes(n.encode([row]))
        tl=stage/"timeline-additions/ssp_9000_1.json";tl.write_bytes(n.encode({"1":[]}))
        (public.parent/"timelines").mkdir();(public.parent/"timelines/ssp_9000_1.json").write_bytes(tl.read_bytes())
        (stage/"data/kyoto_statements_summary.json").write_bytes(public.read_bytes())
        io.write_json(stage/"READY.json",dict(meeting_key="kyoto:9000:1",added_records=1))
        c.record(self.root,"kyoto:9000:1","a"*64,analyzed=True,candidate_stage=str(stage),
                 candidate_ready_sha256=io.digest((stage/"READY.json").read_bytes()),
                 candidate_files={p.relative_to(stage).as_posix():io.digest(p.read_bytes())
                                  for p in stage.rglob("*.json") if p.name!="READY.json"})
        receipt=self.root/"deployed.json"
        approval=dict(pm_confirmed_deployed=True,meeting_key="kyoto:9000:1",commit="c"*40,
                      approval_reference="SYNTHETIC PM",deployment_reference="SYNTHETIC deployment",
                      summary_sha256="0"*64,timeline_sha256=io.digest(tl.read_bytes()))
        io.write_json(receipt,approval);config=dict(publication_receipt=str(receipt),public_summary=str(public))
        with self.assertRaises(io.Stop):c.acknowledge_publication(self.root,config)
        self.assertFalse(c.history(self.root)["meetings"]["kyoto:9000:1"]["published"])
        approval["summary_sha256"]=io.digest(public.read_bytes());io.write_json(receipt,approval)
        r=c.acknowledge_publication(self.root,config)
        self.assertTrue(r["published"]);self.assertFalse(r["meeting_complete"])

    def test_new_private_adapter_append_and_failure_preserve_baseline(self):
        # Only this new connector is exercised; no accepted real meeting is regenerated.
        code=ROOT/"data-pipeline"
        protected=self.root/"protected/frontend/public/data";protected.mkdir(parents=True)
        public=protected/"kyoto_statements_summary.json"
        old=dict(id="legacy_1",meeting_id="legacy",sequence_number=1,meeting_title="old",
                 meeting_date="2026-01-01",speaker="Old",category="test",summary="old",
                 scoring_reasoning="old",statement_snippet="old",statement_text="old",
                 evidence_score=1,solution_score=1,local_focus_score=1,constructive_score=1,
                 source_url="https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=1&schedule_id=1#minute_1")
        public.write_bytes(n.encode([old]));before=public.read_bytes()
        # Private and protected repository trees are siblings.
        private=self.root/"private";private.mkdir()
        rows=[dict(meeting_id="ssp_9000_1",sequence_number=i,meeting_title="synthetic",
                   meeting_date="2026-04-09",speaker="試験議員"+str(i),statement_text="試験用の質疑本文です。"*4,
                   official_url="https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=9000&schedule_id=1#minute_"+str(i)) for i in (1,2)]
        cache=self.root/"kyoto_raw_statements.json";cache.write_bytes(n.encode(rows))
        master=self.root/"master.json";master.write_bytes(n.encode([{"name":r["speaker"]} for r in rows]))
        ledger=n.read_json(io.LEDGER)
        approval=dict(decision="confirmed_new_meeting",meeting_key="kyoto:9000:1",
                      input_sha256=io.digest(cache.read_bytes()),ledger_sha256=io.digest(n.encode(ledger)),
                      baseline_sha256=io.digest(before),master_sha256=io.digest(master.read_bytes()),
                      review_id="SYNTHETIC",history_gap_review="SYNTHETIC",publication_evidence="SYNTHETIC",
                      original_raw_sha256="a"*64,period_start="2026-04-09",period_end="2026-04-09")
        stage=n.prepare(cache,ledger,approval,public,code,master,private)
        manifest=n.read_json(stage/"manifest.json")
        prepared=n.read_json(stage/"data-pipeline/kyoto_raw_statements.json")
        values={r["id"]:dict(status="analysis_success",analysis=result()) for r in prepared}
        receipt=self.root/"complete.json"
        io.write_json(receipt,dict(status="selected_threads_complete_private_only",success=2,results=values,
                      binding=dict(meeting_key=manifest["meeting_key"],manifest_sha256=io.digest(n.encode(manifest))),
                      api_attempts=[dict(status="success",thread_id=k,analysis=result()) for k in values]))
        ns=dict(build_debate_threads=lambda data:[dict(main_statement=r) for r in data],
                is_procedural_or_voting=lambda t:False)
        with patch.object(g,"legacy_functions",return_value=ns):
            out=c.private_project(stage,receipt,public,private)
        merged=n.read_json(out/"data/kyoto_statements_summary.json")
        self.assertEqual(merged[0],old);self.assertEqual(len(merged),3)
        self.assertEqual(public.read_bytes(),before)
        self.assertEqual([p.name for p in (out/"timeline-additions").iterdir()],["ssp_9000_1.json"])
        good=io.digest((out/"data/kyoto_statements_summary.json").read_bytes())
        with patch.object(g,"legacy_functions",return_value=ns),patch.object(n,"assemble",side_effect=io.Stop("synthetic downstream failure")):
            with self.assertRaises(io.Stop):c.private_project(stage,receipt,public,private)
        self.assertEqual(public.read_bytes(),before)
        self.assertEqual(io.digest((out/"data/kyoto_statements_summary.json").read_bytes()),good)


if __name__=="__main__":unittest.main(verbosity=2)
