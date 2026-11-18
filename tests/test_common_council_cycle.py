"""Only synthetic documents in Git; no live HTTP or existing data writes."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"data-pipeline"))
from council_updates import providers as p
from council_updates import cycle as c

def offline(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise RuntimeError("Offline cycle test forbids external effects")
sys.addaudithook(offline)
DAYS = ["2026-11-02T10:00:00+09:00", "2026-11-09T10:00:00+09:00",
        "2026-11-16T10:00:00+09:00", "2026-11-23T10:00:00+09:00"]
WEEKS = ["2026-W45","2026-W46","2026-W47","2026-W48"]

def row(city="kyoto", cid="1", sid="1", body="Original"):
    return dict(city=city,council_id=cid,schedule_id=sid,meeting_date="2026-06-01",
        formal_name="Synthetic committee",schedule_name="06月01日－01号",
        source_position="/fixture/meetings/0",
        statements={"1":dict(speaker_raw="Synthetic member",body_html=body,
                            source_position="/fixture/statements/0")})
def snap(records=None, day=0, city="kyoto"):
    records=records if records is not None else {city+":1:1":row(city)}
    return p.fixture_snapshot(p.config(city),records,DAYS[day])
def bundle(data, phase, city="kyoto", cid="1"):
    cfg=p.config(city);raw=p.encode(data)
    url="https://ssp.kaigiroku.net/dnp/search/"+("councils/index" if phase=="index" else "minutes/get_schedule_all")
    approval=dict(guard_sha256="a"*64,tenant_id=cfg["tenant_id"],council_id=cid,
                  council_year=2026,scope="synthetic_schedule_scope",reference="synthetic-review",
                  post_parameters=dict(tenant_id=cfg["tenant_id"]))
    receipt=dict(status="council_index_acquired_only" if phase=="index" else "schedules_acquired_pending_review",
        guard_sha256="a"*64,reference="synthetic-review",
        meeting_scope=dict(council_id=cid,council_year=2026,scope="synthetic_schedule_scope"),
        limits=dict(tls_verify=True,retries=0,redirects=0),
        attempts=[dict(method="POST",url=url,http_status=200,sha256=p.digest(raw),
            response_bytes=len(raw),completed_utc=DAYS[0],raw_file="fixture.json")])
    return dict(raw=raw,receipt=receipt,approval=approval,simulated=True)
def provider_snapshot(city="kyoto", name="06月01日－01号"):
    index=bundle({"councils":[{"tenant_id":p.config(city)["tenant_id"],"view_years":[
        {"view_year":"2026","council_type":[{"councils":[{"council_id":1,"name":"Synthetic council"}]}]}]}]},"index",city)
    schedules=bundle({"schedules_and_materials":[{"schedule_id":1,"name":name}]},"schedules",city)
    return p.ssp_snapshot(p.config(city),index,schedules,"1",DAYS[0]),index,schedules

class CommonCycleTests(unittest.TestCase):
    def baseline(self, city="kyoto"):
        return c.cycle(c.initial(city,"synthetic-scope"),snap(city=city),WEEKS[0])[0]
    def test_baseline_frozen_and_same_version_zero(self):
        s=self.baseline();before=copy.deepcopy(s["baseline"])
        s2,r=c.cycle(s,snap(day=1),WEEKS[1])
        self.assertEqual(r["status"],"same-version");self.assertEqual(r["new_reviews"],0)
        self.assertEqual(s2["baseline"],before);self.assertEqual(s2["reviews"],[])
    def test_new_meeting_is_unverified_candidate(self):
        s=self.baseline();data={"kyoto:1:1":row(),"kyoto:1:2":row(sid="2")}
        out,r=c.cycle(s,snap(data,1),WEEKS[1])
        self.assertEqual(r["new_reviews"],1)
        self.assertEqual(out["reviews"][0]["kind"],"new-meeting-candidate")
        self.assertFalse(out["reviews"][0]["publication_authorized"])
        self.assertEqual(out["baseline"],s["baseline"])
    def test_same_count_text_speaker_and_metadata_corrections_hold(self):
        for field,value in (("body_html","Corrected"),("speaker_raw","Other")):
            s=self.baseline();changed=row()
            changed["statements"]["1"][field]=value
            out,r=c.cycle(s,snap({"kyoto:1:1":changed},1),WEEKS[1])
            self.assertEqual(r["status"],"HOLD");self.assertEqual(out["last_good"],s["last_good"])
        changed=row();changed["formal_name"]="Another council"
        _,r=c.cycle(self.baseline(),snap({"kyoto:1:1":changed},1),WEEKS[1])
        self.assertEqual(r["status"],"HOLD")
    def test_existing_meeting_supplement_and_missing_statement_hold(self):
        s=self.baseline()
        for speeches in ({},dict(row()["statements"],**{"2":dict(speaker_raw="X",body_html="Added",source_position="/2")}),None):
            changed=row();changed["statements"]=speeches
            out,r=c.cycle(s,snap({"kyoto:1:1":changed},1),WEEKS[1])
            self.assertEqual(r["status"],"HOLD");self.assertEqual(out["last_good"],s["last_good"])
    def test_missing_meeting_hold_and_hold_replay_not_success(self):
        s=self.baseline()
        out,r=c.cycle(s,snap({},1),WEEKS[1]);self.assertEqual(r["status"],"HOLD")
        replay,r=c.cycle(out,snap({},2),WEEKS[2])
        self.assertEqual(r["status"],"same-version-HOLD");self.assertEqual(r["new_reviews"],0)
        self.assertEqual(replay["last_good"],s["last_good"])
    def test_known_version_rollback_detects_missing_meeting_without_duplicate_review(self):
        a=self.baseline()
        rows={"kyoto:1:1":row(),"kyoto:1:2":row(sid="2")}
        b,_=c.cycle(a,snap(rows,1),WEEKS[1])
        rollback,r=c.cycle(b,snap(day=2),WEEKS[2])
        self.assertEqual(r["status"],"same-version-HOLD")
        self.assertEqual(r["new_reviews"],0)
        self.assertEqual(r["hold_reasons"][0]["meeting_key"],"kyoto:1:2")
        self.assertEqual(rollback["last_good"],b["last_good"])
    def test_same_week_and_wrong_scope_rejected(self):
        s=self.baseline()
        with self.assertRaises(ValueError):c.cycle(s,snap(),WEEKS[0])
        wrong=snap(day=1);wrong["scope"]="different"
        with self.assertRaises(ValueError):c.cycle(s,wrong,WEEKS[1])
    def test_same_source_cannot_change_interpretation(self):
        s=self.baseline();x=snap(day=1);x["records"]["kyoto:1:1"]["formal_name"]="Changed without new source"
        with self.assertRaises(ValueError):c.cycle(s,x,WEEKS[1])
    def test_bad_city_date_source_and_clock(self):
        for field,value in (("city","osaka"),("meeting_date","2026-02-30")):
            bad=row();bad[field]=value
            with self.assertRaises(ValueError):c.cycle(c.initial("kyoto","synthetic-scope"),snap({"kyoto:1:1":bad}),WEEKS[0])
        s=self.baseline()
        with self.assertRaises(ValueError):c.cycle(s,snap(day=1),"2026-W40")
    def test_term_boundary_and_unknown_term(self):
        old=row();old["meeting_date"]="2023-04-30"
        out,r=c.cycle(c.initial("kyoto","synthetic-scope"),snap({"kyoto:1:1":old}),WEEKS[0])
        self.assertEqual(r["excluded_term"],["kyoto:1:1"]);self.assertEqual(out["last_good"],{})
        _,r=c.cycle(c.initial("osaka","synthetic-scope"),snap(city="osaka"),WEEKS[0])
        self.assertEqual(r["status"],"HOLD")
    def test_nagoya_same_engine_synthetic_not_real_certification(self):
        s=self.baseline("nagoya")
        out,r=c.cycle(s,snap(day=1,city="nagoya"),WEEKS[1])
        self.assertEqual(r["status"],"same-version");self.assertEqual(r["origin"],"synthetic")
        self.assertEqual(out["city"],"nagoya");self.assertFalse(r["published"])
    def test_ssp_same_adapter_two_cities_and_bound_ids(self):
        for city in ("kyoto","nagoya"):
            x,index,schedules=provider_snapshot(city)
            self.assertIn(city+":1:1",x["records"])
            self.assertEqual(x["origin"],"synthetic")
            self.assertTrue(all(e["simulated"] for e in x["evidence"]))
            s,r=c.cycle(c.initial(city,x["scope"]),x,WEEKS[0])
            self.assertEqual(r["status"],"baseline-only")
            schedules["approval"]["council_id"]="2"
            with self.assertRaises(ValueError):
                p.ssp_snapshot(p.config(city),index,schedules,"1",DAYS[0])
    def test_receipt_tenant_partial_and_sha_fail(self):
        _,index,schedules=provider_snapshot()
        for raw in (b"", b"x"*(2*1024*1024+1), None):
            b=copy.deepcopy(index);b["raw"]=raw
            with self.assertRaisesRegex(ValueError,"Saved response"):
                p.ssp_snapshot(p.config("kyoto"),b,schedules,"1",DAYS[0])
        for change in ("tenant","sha","status"):
            b=copy.deepcopy(index)
            if change=="tenant":b["approval"]["post_parameters"]["tenant_id"]="207"
            elif change=="sha":b["raw"]+=b" "
            else:b["receipt"]["status"]="stopped"
            with self.assertRaises(ValueError):p.ssp_snapshot(p.config("kyoto"),b,schedules,"1",DAYS[0])
    def test_receipt_scope_cannot_be_relabelled_and_city_pins_not_shared(self):
        _,index,schedules=provider_snapshot()
        for field,value in (("council_id","2"),("council_year",2025),("scope","another")):
            bad=copy.deepcopy(schedules);bad["receipt"]["meeting_scope"][field]=value
            with self.assertRaises(ValueError):p.ssp_snapshot(p.config("kyoto"),index,bad,"1",DAYS[0])
        for city in ("kyoto","nagoya"):
            _,i,s=provider_snapshot(city);i.pop("simulated");i["run_id"]="pretend"
            with self.assertRaises(ValueError):p.ssp_snapshot(p.config(city),i,s,"1",DAYS[0])
    def test_materials_and_undated_are_not_new_meetings(self):
        for name in ("資料", "会議名のみ"):
            x,_,_=provider_snapshot(name=name)
            _,r=c.cycle(c.initial("kyoto",x["scope"]),x,WEEKS[0])
            self.assertEqual(r["status"],"HOLD")
    def test_jsonp_and_unimplemented_provider(self):
        x={"councils":[]}
        self.assertEqual(p.decode(b"jQuery1("+p.encode(x)+b");"),x)
        with self.assertRaises(ValueError):p.decode(b"callback({});")
        with self.assertRaises(ValueError):p.ssp_snapshot(p.config("kobe"),{},{},"1",DAYS[0])
    def test_atomic_failure_keeps_normal_and_consumes_week(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"private"
            s,_,head=c.stage(root,None,snap(),WEEKS[0])
            before=(root/"normal.json").read_bytes()
            with patch.object(c.os,"replace",side_effect=OSError("synthetic disk failure")):
                with self.assertRaises(OSError):c.stage(root,head,snap(day=1),WEEKS[1])
            self.assertEqual((root/"normal.json").read_bytes(),before)
            self.assertTrue((root/"kyoto-2026-W46.attempt.json.failure.json").exists())
            with self.assertRaises(FileExistsError):c.stage(root,head,snap(day=1),WEEKS[1])
            self.assertEqual(s["reviews"],[])
    def test_public_storage_is_forbidden(self):
        with self.assertRaises(ValueError):
            c.stage(Path(__file__).resolve().parents[1]/"frontend/public/data/no-write",None,snap(),WEEKS[0])
    def test_provider_failure_preserves_normal_and_consumes_week(self):
        _,index,schedules=provider_snapshot()
        request=dict(city="kyoto",scope="council:1",observed_at=DAYS[0],
            ssp_inputs=dict(index=index,schedules=schedules,council_id="1"))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"private"
            _,_,head=c.stage(root,None,request,WEEKS[0])
            before=(root/"normal.json").read_bytes()
            bad=copy.deepcopy(request);bad["observed_at"]=DAYS[1]
            bad["ssp_inputs"]["schedules"]["raw"]+=b"tamper"
            with self.assertRaises(ValueError):c.stage(root,head,bad,WEEKS[1])
            self.assertEqual((root/"normal.json").read_bytes(),before)
            with self.assertRaises(FileExistsError):c.stage(root,head,bad,WEEKS[1])

if __name__=="__main__":unittest.main()
