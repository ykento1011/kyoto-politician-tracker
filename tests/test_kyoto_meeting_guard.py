"""Reused22 accepted guard cases, generalized with synthetic private fixtures."""
import base64,contextlib,copy,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"data-pipeline"))
TMP=tempfile.TemporaryDirectory(prefix="kyoto-identity-ci-")
P=Path(TMP.name)
os.environ["KYOTO_PRIVATE_ROOT"]=str(P)
import kyoto_one_meeting_guard as g
def offline(event,args):
 if event.startswith("socket.") or event in ("subprocess.Popen","os.system","os.posix_spawn"):raise RuntimeError("offline tests only")
sys.addaudithook(offline)
g.LEDGER.parent.mkdir(parents=True)
g.transport.write_json(g.LEDGER,dict(completeness="unknown",meetings=["kyoto:6346:1"]+["kyoto:"+str(i)+":1" for i in range(10000,10749)]))
g.LEDGER_SHA=g.transport.digest(g.LEDGER.read_bytes())
def tearDownModule():TMP.cleanup()
M=1024*1024
def review():
 return dict(scope="kyoto_meeting_identity_only",council_id="6346",schedule_id="1",meeting_date="2026-05-29",council_year=2026,
  identity_review=dict(city="kyoto",source_kind="meeting",council_id="6346",schedule_id="1",meeting_date="2026-05-29",committee="総務消防委員会",round=5,formal_name="令和8年5月総務消防委員会（第5回）"))
def schedule(name="05月29日－05号",sid=1,extra=None):
 rows=[dict(schedule_id=sid,name=name)]
 if extra:rows+=extra
 return json.dumps(dict(schedules_and_materials=rows),ensure_ascii=False).encode()
def prior(n):return dict(status=200,bytes=n)
def full_approval():
 g.configure(review())
 sources=g.ROOT/"synthetic-sources";sources.mkdir(exist_ok=True)
 def bound(name,value):
  f=sources/name;f.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
  return dict(path=str(f),sha256=g.transport.digest(f.read_bytes()))
 cat=bound("catalog.json",dict(councils=[dict(view_years=[dict(view_year="2026",council_type=[dict(council_type_name1="全会議",councils=[dict(council_id=6346,name=review()["identity_review"]["formal_name"])])])])]))
 act=sources/"activity.html";act.write_text("総務消防委員会 5月29日（第5回）",encoding="utf-8")
 activity=dict(path=str(act),sha256=g.transport.digest(act.read_bytes()),literal="5月29日（第5回）",source_position="synthetic",review_reference="synthetic offline review")
 hist=bound("registered.json",dict(meetings={"kyoto:6346:1":{}}))
 return dict(review(),pm_go=True,identity_sources=dict(catalog=cat,activity=activity),registered_history=hist,identity_code_sha256=g.transport.digest(Path(g.identity.__file__).read_bytes()),reference="Synthetic offline approval fixture only",run_id="synthetic-6346-test",
  limits=dict(g.LIMITS,total_response_bytes=4*M),ledger_sha256=g.LEDGER_SHA,
  transport_sha256=g.TRANSPORT_SHA,guard_sha256=g.transport.digest(Path(g.__file__).read_bytes()),
  path_guard_sha256=g.transport.digest(Path(g.transport.private_storage.__code__.co_filename).read_bytes()),
  requests=[dict(method=m,url=u,body=g.contract(m,u,"1").decode("ascii") if m=="POST" else None) for m,u in g.ALLOWED])
class GuardTests(unittest.TestCase):
 def setUp(self):g.configure(review())
 def test_existing_guard_does_not_enforce_total4MiB(self):
  self.assertNotIn("total_response_bytes",g.LIMITS)
  self.assertEqual(g.LIMITS["http_attempts"]*g.LIMITS["response_body_bytes"],6*M)
 def test_exact_parameters_unchanged(self):
  self.assertIsNone(g.contract("GET",g.transport.TOP))
  self.assertEqual(g.contract("POST",g.SCHEDULE),b"tenant_id=355&power_user=false&council_id=6346")
  self.assertEqual(g.contract("POST",g.MINUTE,"1"),b"tenant_id=355&power_user=false&council_id=6346&schedule_id=1")
  with self.assertRaises(g.Stop):g.contract("GET",g.SCHEDULE)
 def test_review_cannot_authorize_other_meeting(self):
  for field,value in [("council_id","6343"),("schedule_id","2"),("meeting_date","2026-05-25"),("council_year",2025)]:
   x=review();x[field]=value
   with self.assertRaises(g.Stop):g.configure(x)
 def test_existing6346_identity_only_allowed(self):
  out=g.select_schedule(schedule(),"application/json",dict(meetings=["kyoto:6346:1"]))
  self.assertEqual(out["meeting_key"],"kyoto:6346:1")
 def test_wrong_date_round_sid_stop(self):
  for raw in [schedule("05月25日－04号"),schedule("05月29日－04号"),schedule(sid=2)]:
   with self.assertRaises(g.Stop):g.select_schedule(raw,"application/json",dict(meetings=["kyoto:6346:1"]))
 def test_missing_or_ambiguous_schedule_stops(self):
  for raw in [b'{"schedules_and_materials":[]}',schedule(extra=[dict(schedule_id=2,name="05月29日－05号")]),schedule("資料")]:
   with self.assertRaises(g.Stop):g.select_schedule(raw,"application/json",dict(meetings=["kyoto:6346:1"]))
 def test_existing_history_required_for_new_identity_scope(self):
  with self.assertRaises(g.Stop):g.select_schedule(schedule(),"application/json",dict(meetings=[]))
 def test_normal_acquisition_still_rejects_existing6346(self):
  g.configure(dict(scope="kyoto_one_reviewed_meeting",council_id="6346",schedule_id="1",meeting_date="2026-05-29",candidate_review="test"))
  with self.assertRaises(g.Stop):g.select_schedule(schedule(),"application/json",dict(meetings=["kyoto:6346:1"]))
  self.assertEqual(g.STORAGE,g.DEFAULT_STORAGE)
 def test_four_mib_remaining_is_receive_cap(self):
  self.assertEqual(g.response_cap([],1),2*M)
  self.assertEqual(g.response_cap([prior(2*M)],2),2*M)
  self.assertEqual(g.response_cap([prior(2*M),prior(M)],3),M)
 def test_exhausted_budget_stops_before_send(self):
  with self.assertRaises(g.Stop):g.response_cap([prior(2*M),prior(2*M)],3)
 def test_unknown_failed_or_empty_usage_stops(self):
  for a in [{},dict(status=302,bytes=1),dict(status=200,bytes=True),dict(status=200,bytes=0),dict(status=200,bytes=2*M+1)]:
   with self.assertRaises(g.Stop):g.response_cap([a],2)
 def test_fourth_request_and_wrong_order_rejected(self):
  for seq,slot in [([],2),([prior(1)]*3,4)]:
   with self.assertRaises(g.Stop):g.response_cap(seq,slot)
 def test_session_and_body_errors_stop(self):
  with self.assertRaises(g.Stop):g.transport.validate_session(b"<html>access denied</html>","text/html")
  selected=g.select_schedule(schedule(),"application/json",dict(meetings=["kyoto:6346:1"]))
  with self.assertRaises(g.Stop):g.validate_minutes(b'{"tenant_minutes":[]}',"application/json",selected)
 def test_identity_receipt_never_marks_new_or_authorizes_analysis(self):
  selected=g.select_schedule(schedule(),"application/json",dict(meetings=["kyoto:6346:1"]))
  body=json.dumps(dict(tenant_minutes=[dict(minute_id=1,title="開会",body="令和8年5月総務消防委員会（第5回）\n第5回総務消防委員会記録\n◯令和8年5月29日（金）")]),ensure_ascii=False).encode()
  result=g.validate_minutes(body,"application/json",selected)
  self.assertEqual(result["history_status"],"existing_identity_only")
  self.assertFalse(result["analysis_authorized"]);self.assertFalse(result["new_publication_verified"]);self.assertEqual(result["official_coverage"],"unknown")
 def test_worker_honors_dynamic_cap_and_single_use(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   with patch.object(g,"ROOT",Path(td)):
    g.configure(review());trial=g.STORAGE/"test";trial.mkdir(parents=True)
    raw=schedule();selected=g.select_schedule(raw,"application/json",dict(meetings=["kyoto:6346:1"]))
    # Synthetic earlier sizes reserve3MiB; no such HTTP is performed.
    attempts=[prior(2*M),dict(prior(M),sha256=g.transport.digest(raw),content_type="application/json"),dict(receive_cap=M)]
    receipt=dict(status="in_progress",meeting_scope=review(),limits=dict(http_attempts=3,total_response_bytes=4*M),attempts=attempts,
     guard_sha256=g.transport.digest(Path(g.__file__).read_bytes()),transport_sha256=g.transport.digest(Path(g.transport.__file__).read_bytes()),selected_schedule=selected)
    (trial/"receipt.json").write_text(json.dumps(receipt),encoding="utf-8");(trial/"02-schedules.json").write_bytes(raw)
    auth=dict(method="POST",url=g.MINUTE,sid="1")
    (trial/"slot-3.authorized").write_text(json.dumps(auth),encoding="utf-8")
    payload=dict(auth,trial=str(trial),slot=3,cookies=[])
    calls=[]
    def fake(*args):calls.append(g.transport.MAX_BYTES);return dict(mock=True)
    with patch.object(g,"bind_approval",lambda *args:None),patch.object(g.transport,"_https_once",fake),patch.object(g.transport,"MAX_BYTES",2*M),patch.object(g.transport,"request_contract",g.transport.request_contract):
     with patch("sys.stdin",io.StringIO(json.dumps(payload))),contextlib.redirect_stdout(io.StringIO()):g.worker()
     self.assertEqual(calls,[M])
     with patch("sys.stdin",io.StringIO(json.dumps(payload))),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(FileExistsError):g.worker()
     self.assertEqual(calls,[M])
class AdditionalTests(unittest.TestCase):
 def setUp(self):g.configure(review())
 def test_formal_name_mismatch_rejected(self):
  a=review();a["identity_review"]["formal_name"]="環境福祉委員会"
  with self.assertRaises(g.Stop):g.configure(a)
 def test_direct_wrong_body_schedule_rejected(self):
  with self.assertRaises(g.Stop):g.contract("POST",g.MINUTE,"2")
 def test_real_approval_validation_without_network(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   f=Path(td)/"approval.json";a=full_approval();f.write_text(json.dumps(a),encoding="utf-8")
   self.assertEqual(g.validate_approval(f),a)
   for key,value in [("guard_sha256","0"*64),("ledger_sha256","0"*64),("path_guard_sha256","0"*64),("requests",[])]:
    bad=dict(a);bad[key]=value;f.write_text(json.dumps(bad),encoding="utf-8")
    with self.assertRaises(g.Stop):g.validate_approval(f)
 def test_exact_approval_bytes_bound_in_worker(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   f=Path(td)/"approval.json";a=full_approval();f.write_text(json.dumps(a),encoding="utf-8")
   keys=("scope","council_id","schedule_id","meeting_date","council_year","candidate_review","identity_review","identity_sources","registered_history")
   r=dict(approval_file=str(f),approval_sha256=g.transport.digest(f.read_bytes()),limits=a["limits"],meeting_scope={k:a[k] for k in keys if k in a})
   g.bind_approval(r,g.STORAGE/a["run_id"])
   f.write_text(f.read_text()+" ",encoding="utf-8")
   with self.assertRaises(g.Stop):g.bind_approval(r,g.STORAGE/a["run_id"])
 def test_registered_new_acquisition_stops_before_any_request(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   a=full_approval();a["scope"]="kyoto_verified_new_meeting"
   f=Path(td)/"approval.json";f.write_text(json.dumps(a),encoding="utf-8")
   with patch.object(g,"isolated_request") as request,self.assertRaises(g.Stop):g.acquire(f)
   request.assert_not_called()
 def test_cas_readback_and_no_silent_overwrite(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   trial=Path(td);body=b"synthetic-original"
   name=g.preserve_identity_cas(trial,body);self.assertEqual((trial/name).read_bytes(),body)
   self.assertEqual(g.preserve_identity_cas(trial,body),name)
   (trial/name).write_bytes(b"corrupt")
   with self.assertRaises(g.Stop):g.preserve_identity_cas(trial,body)
 def test_incomplete_and_oversized_transport_never_succeeds(self):
  from unittest.mock import MagicMock
  for length,body,cap in [("5",b"a",10),("11",b"",10),(None,b"a"*10,10)]:
   response=MagicMock();response.status=200
   response.getheader.side_effect=lambda key,default=None: {"Content-Length":length,"Content-Encoding":"identity","Transfer-Encoding":None}.get(key,default)
   response.read.return_value=body
   conn=MagicMock();conn.getresponse.return_value=response
   with patch.object(g.transport.http.client,"HTTPSConnection",return_value=conn),patch.object(g.transport,"MAX_BYTES",cap),patch.object(g.transport,"request_contract",lambda m,u:None):
    with self.assertRaises(g.Stop):g.transport._https_once("GET",g.transport.TOP,[])
    self.assertEqual(conn.request.call_count,1)
 def test_mismatch_stops_before_third_request(self):
  with tempfile.TemporaryDirectory(dir=P,prefix="synthetic-") as td:
   with patch.object(g,"ROOT",Path(td)):
    a=full_approval();a["reference"]="Synthetic end-to-end test"
    f=Path(td)/"approval.json";f.write_text(json.dumps(a),encoding="utf-8")
    calls=[]
    def fake(method,url,cookies,trial,slot,sid):
     calls.append(slot);body=b"<html></html>" if slot==1 else schedule("05月25日－04号")
     return dict(body_b64=base64.b64encode(body).decode(),bytes=len(body),status=200,content_type="text/html" if slot==1 else "application/json",started_utc="synthetic",completed_utc="synthetic",cookies=[])
    with patch.object(g,"validate_approval",return_value=a),patch.object(g,"isolated_request",fake),patch.object(g.time,"sleep",lambda _:None):
     with self.assertRaises(g.Stop):g.acquire(f)
    self.assertEqual(calls,[1,2]);receipt=json.loads((g.STORAGE/a["run_id"]/"receipt.json").read_text())
    self.assertEqual(receipt["status"],"stopped");self.assertEqual(receipt["gemini_calls"],0);self.assertFalse(receipt["public_writes"])

if __name__=="__main__":unittest.main()
