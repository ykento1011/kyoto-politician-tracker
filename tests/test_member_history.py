"""Offline member lifecycle regression. All people/notices here are synthetic."""
import ast
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
import member_history as h
from nagoya_roster_evidence import parse_roster

def no_network(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise RuntimeError("Offline test: external effects forbidden")
sys.addaudithook(no_network)

RAW = "<html><article id='content'><p>試験資料：議員甲 議員乙 就任 辞職 会派変更 役職辞任 別名</p></article></html>".encode()
POS = dict(dom="/html[1]/article[1]/p[1]", line=1, literal="試験資料")
RECEIPT = dict(url="https://www.city.nagoya.jp/shikai/test-fixture.html", method="GET",
               status="success", http_status=200, bytes=len(RAW), sha256=h.digest(RAW),
               completed_utc="2026-06-30T12:00:00+09:00")
EV = h.evidence(RAW, RECEIPT)
PERSONS = [dict(person_id="nagoya:a",seed_name="議員甲",seed_district="試験区"),
           dict(person_id="nagoya:b",seed_name="議員乙",seed_district="試験区")]

def state():
    return h.seed_registry(PERSONS, "a" * 64)

def fact(domain="membership", value="member", start="2023-04-12", pid="nagoya:a", **kw):
    f = dict(person_id=pid,domain=domain,value=value,effective_on=start,
             confirmed_through="2026-06-30",scope="name:canonical" if domain=="alias" else "city_council",
             reason="election", decision="confirmed",reviewer="synthetic-reviewer",
             review_reference="synthetic-review-record",source_sha256=EV["sha256"],position=POS)
    f.update(kw)
    return f

def add(s, **kw):
    return h.add_reviewed_fact(s, EV, fact(**kw))

def member(s=None, pid="nagoya:a", name="議員甲"):
    s = state() if s is None else s
    s = add(s,pid=pid)
    return add(s,domain="alias",value=name,pid=pid)

def rows():
    return [dict(name="議員甲",district="試験区",group="会派A",roles=[],position=POS),
            dict(name="議員乙",district="試験区",group="会派B",roles=[],position=POS)]

def altered_evidence():
    raw=RAW.replace(b"</html>",b" <!--version2--> </html>")
    return h.evidence(raw,dict(RECEIPT,bytes=len(raw),sha256=h.digest(raw)))

class MemberHistoryTests(unittest.TestCase):
    def test_evidence_sha_corruption_rejected(self):
        with self.assertRaises(ValueError): h.evidence(RAW+b"x",RECEIPT)
    def test_failed_http_receipt_rejected(self):
        with self.assertRaises(ValueError): h.evidence(RAW,dict(RECEIPT,http_status=503))
    def test_nonofficial_source_rejected(self):
        with self.assertRaises(ValueError): h.evidence(RAW,dict(RECEIPT,url="https://example.org/"))
    def test_same_sha_no_duplicate_review(self):
        s=h.add_observation(state(),EV,rows(),"2026-05-21",["name","district","group"])
        self.assertEqual(s,h.add_observation(s,EV,rows(),"2026-05-21",["name","group"]))
    def test_roster_disappearance_does_not_end_membership(self):
        s=member()
        s=h.add_observation(s,EV,rows(),"2026-05-21",["name","group"])
        result=h.add_observation(s,altered_evidence(),rows()[1:],"2026-06-21",["name","group"])
        self.assertEqual(result["facts"],s["facts"])
        self.assertEqual(result["reviews"][-1]["changes"][0]["field"],"roster_presence")
        self.assertEqual(h.resolve_speaker(result,"議員甲","2026-06-25")["status"],"matched_member")
    def test_date_unknown_stops_without_mutation(self):
        s=state();before=copy.deepcopy(s)
        with self.assertRaises(ValueError): h.add_observation(s,EV,rows(),None,["name","group"])
        self.assertEqual(s,before)
    def test_empty_redesigned_roster_rejected(self):
        with self.assertRaises(ValueError): h.add_observation(state(),EV,[],"2026-05-21",["name","group"])
    def test_homonymous_registry_holds_observation(self):
        s=state();s["persons"][1]["seed_name"]="議員甲"
        result=h.add_observation(s,EV,rows()[:1],"2026-05-21",["name","group"])
        self.assertIsNone(result["observations"][0]["rows"][0]["person_id"])
        self.assertEqual(result["reviews"][0]["changes"][0]["status"],"hold")
    def test_duplicate_person_mapping_rejected(self):
        with self.assertRaises(ValueError): h.add_observation(state(),EV,rows()+rows()[:1],"2026-05-21",["name","group"])
    def test_group_diff_is_candidate_without_effective_date(self):
        s=h.add_observation(state(),EV,rows(),"2026-05-21",["name","group"])
        r=rows();r[0]["group"]="会派C"
        s=h.add_observation(s,altered_evidence(),r,"2026-06-21",["name","group"])
        self.assertIsNone(s["reviews"][-1]["effective_on"])
        self.assertEqual(s["facts"],[])
    def test_membership_before_and_after_resignation(self):
        s=member()
        s=add(s,value="not_member",start="2026-06-01",reason="resignation")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-05-20")["status"],"matched_member")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-06-02")["status"],"hold")
        self.assertEqual(len(s["facts"]),3)
    def test_all_membership_end_reasons(self):
        for reason in h.END_REASONS:
            s=add(member(),value="not_member",start="2026-06-01",reason=reason)
            self.assertEqual(h.at_date(s,"nagoya:a","2026-06-02","membership")["value"],"not_member")
    def test_by_election_requires_distinct_stable_id(self):
        s=member()
        p=dict(person_id="nagoya:new",seed_name="議員丙",seed_district="試験区")
        s=h.register_person(s,p,EV,dict(decision="confirmed",reviewer="r",review_reference="notice",
             source_sha256=EV["sha256"],position=POS))
        s=add(s,pid="nagoya:new",start="2026-06-10",reason="by_election")
        s=add(s,pid="nagoya:new",domain="alias",value="議員丙",start="2026-06-10")
        self.assertEqual(h.resolve_speaker(s,"議員丙","2026-06-09")["status"],"hold")
        self.assertEqual(h.resolve_speaker(s,"議員丙","2026-06-10")["person_id"],"nagoya:new")
        self.assertEqual(s["persons"][:2],PERSONS)
    def test_existing_id_cannot_be_reassigned(self):
        with self.assertRaises(ValueError):
            h.register_person(state(),PERSONS[0],EV,dict(decision="confirmed",reviewer="r",
                review_reference="r",source_sha256=EV["sha256"],position=POS))
    def test_group_change_does_not_end_membership(self):
        s=add(member(),domain="group",value="会派A")
        s=add(s,domain="group",value="会派B",start="2026-06-01")
        self.assertEqual(h.at_date(s,"nagoya:a","2026-05-20","group")["value"],"会派A")
        self.assertEqual(h.at_date(s,"nagoya:a","2026-06-20","group")["value"],"会派B")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-06-20")["status"],"matched_member")
    def test_role_resignation_not_council_resignation(self):
        for scope in ("chamber","committee:finance","union:port","faction:A"):
            s=add(member(),domain="role",scope=scope,title="委員長",value="held")
            s=add(s,domain="role",scope=scope,title="委員長",value="ended",start="2026-06-01",reason="role_resignation")
            self.assertEqual(h.at_date(s,"nagoya:a","2026-06-20","role",scope,"委員長")["value"],"ended")
            self.assertEqual(h.resolve_speaker(s,"議員甲","2026-06-20")["status"],"matched_member")
    def test_role_cannot_be_membership_reason(self):
        with self.assertRaises(ValueError): add(member(),value="not_member",reason="role_resignation")
    def test_same_name_people_hold_even_with_memberships(self):
        s=member(member(),pid="nagoya:b",name="議員甲")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-06-20")["status"],"hold")
    def test_multiple_dated_aliases(self):
        s=add(member(),domain="alias",scope="name:reading",value="ぎいんこう")
        self.assertEqual(h.resolve_speaker(s,"ぎいんこう","2026-06-20")["person_id"],"nagoya:a")
    def test_alias_change_keeps_old_speech_identity(self):
        s=add(member(),domain="alias",value="新表記甲",start="2026-06-01")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-05-20")["person_id"],"nagoya:a")
        self.assertEqual(h.resolve_speaker(s,"新表記甲","2026-06-20")["person_id"],"nagoya:a")
        self.assertEqual(h.resolve_speaker(s,"議員甲","2026-06-20")["status"],"hold")
    def test_meeting_outside_proven_tenure_holds(self):
        self.assertEqual(h.resolve_speaker(member(),"議員甲","2023-04-11")["status"],"hold")
        self.assertEqual(h.resolve_speaker(member(),"議員甲","2023-04-12")["status"],"matched_member")
        self.assertEqual(h.resolve_speaker(member(),"議員甲","2026-07-01")["status"],"hold")
    def test_current_roster_never_certifies_historic_speech(self):
        s=h.add_observation(state(),EV,rows(),"2026-05-21",["name","group"])
        self.assertEqual(h.resolve_speaker(s,"議員甲","2023-06-01")["status"],"hold")
    def test_matched_member_does_not_certify_speech_role(self):
        r=h.resolve_speaker(member(),"議員甲","2026-06-20")
        self.assertEqual((r["speech_role"],r["agenda_boundary"]),("unverified","unverified"))
    def test_conflicting_effective_facts_hold(self):
        s=add(member(),value="not_member",reason="loss_of_seat")
        self.assertEqual(h.at_date(s,"nagoya:a","2026-06-20","membership")["status"],"hold")
    def test_unreviewed_fact_rejected(self):
        with self.assertRaises(ValueError): add(state(),decision="pending")
    def test_missing_effective_date_rejected(self):
        with self.assertRaises(ValueError): add(state(),start=None)
    def test_future_coverage_rejected(self):
        with self.assertRaises(ValueError): add(state(),confirmed_through="2027-04-11")
    def test_missing_source_literal_rejected(self):
        with self.assertRaises(ValueError): add(state(),position=dict(POS,literal="not in source"))
    def test_wrong_source_position_rejected(self):
        with self.assertRaises(ValueError): add(state(),position=dict(POS,line=2))
        with self.assertRaises(ValueError): add(state(),position=dict(POS,dom="/html[1]/p[1]"))
    def test_duplicate_fact_no_duplicate_event(self):
        s=add(state())
        self.assertEqual(s,add(s))
    def test_acquisition_failure_preserves_last_normal(self):
        s=h.add_observation(member(),EV,rows(),"2026-05-21",["name","group"])
        after=h.record_failure(s,EV["url"],EV["observed_at"],"fetch_failed")
        for key in ("persons","observations","facts","reviews"):
            self.assertEqual(s[key],after[key])
    def test_private_cas_append_only_and_failed_save(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"KYOTO_PRIVATE_ROOT":temp}):
            s=member();sha=h.save_private(s)
            self.assertEqual(sha,h.save_private(s,sha))
            old_head=(Path(temp)/"member-history-head.json").read_bytes()
            modified=copy.deepcopy(s);modified["persons"][0]["seed_name"]="reassigned"
            with self.assertRaises(ValueError):h.save_private(modified,sha)
            s2=add(s,domain="group",value="会派A")
            with patch.object(h.os,"replace",side_effect=OSError("synthetic disk failure")):
                with self.assertRaises(OSError):h.save_private(s2,sha)
            self.assertEqual((Path(temp)/"member-history-head.json").read_bytes(),old_head)
            self.assertTrue((Path(temp)/"member-cas"/(sha+".json")).exists())
            resumed=h.save_private(s2,sha)
            self.assertNotEqual(resumed,sha)
            self.assertEqual(json.loads((Path(temp)/"member-history-head.json").read_text())["sha256"],resumed)
    def test_stale_head_and_rewrite_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"KYOTO_PRIVATE_ROOT":temp}):
            s=member();sha=h.save_private(s)
            with self.assertRaises(ValueError):h.save_private(s,"0"*64)
            changed=copy.deepcopy(s);changed["facts"].pop()
            with self.assertRaises(ValueError):h.save_private(changed,sha)
    def test_checkout_is_not_private_storage(self):
        with patch.dict(os.environ,{"KYOTO_PRIVATE_ROOT":str(ROOT)}):
            with self.assertRaises(Exception):h.save_private(state())
    def test_saved_roster_parser_normal_and_redesign(self):
        # Official HTML structure, synthetic names; no private originals in Git.
        body=("<html><article id='content'><h2>試験会派（68人）</h2><dl><dt>団員</dt><dd>"
              +"<br>".join("試験"+str(i) for i in range(68))+"</dd></dl></article></html>").encode()
        r=parse_roster(body,"factions_20260521")
        self.assertEqual(len(r),68)
        with self.assertRaises(ValueError):parse_roster(body.replace(b"<dd>",b"<p>"),"factions_20260521")
    def test_initial_roster_parser_requires_complete_sections(self):
        body=("<html><article id='content'><h2>試験区(68人)</h2><ul>"
              +"".join("<li><strong>試験"+str(i)+"(会派)</strong></li>" for i in range(68))
              +"</ul></article></html>").encode()
        self.assertEqual(len(parse_roster(body,"initial_186")),68)
        with self.assertRaises(ValueError):parse_roster(body.replace(b"68",b"67",1),"initial_186")
    def test_nagoya_cli_default_and_shared_year_only_scope(self):
        source=(ROOT/"data-pipeline/fetch_nagoya_ssp.py").read_text(encoding="utf-8-sig")
        tree=ast.parse(source)
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and n.args
                  and isinstance(n.args[0],ast.Constant) and n.args[0].value=="--start-date")
        default=next(ast.literal_eval(k.value) for k in call.keywords if k.arg=="default")
        self.assertEqual(default,"2023-04-12")
        # Extract only the existing pure index transform; every session call is a stub.
        tree=ast.parse((ROOT/"data-pipeline/scrapers/kaigiroku_scraper.py").read_text(encoding="utf-8-sig"))
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=="get_councils")
        env=dict(List=list,Dict=dict,Any=object,json=json)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),"isolated-index","exec"),env)
        from types import SimpleNamespace as NS
        data=dict(councils=[dict(view_years=[dict(view_year=y,council_type=[dict(councils=[dict(council_id=i,name=y)])])
                  for i,y in enumerate(("2022","2023","2024"))])])
        fake=NS(_init_session=lambda:None,_wait_rate_limit=lambda:None,base_url="fixture",tenant_id="207",timeout=0,
                normalize_text=lambda x:x,_clean_json=lambda x:x,
                session=NS(post=lambda *a,**k:NS(text=json.dumps(data))))
        self.assertEqual(env["get_councils"](fake,default),env["get_councils"](fake,"2023-05-01"))
        self.assertEqual([r["year"] for r in env["get_councils"](fake,default)],["2023","2024"])

if __name__ == "__main__":
    unittest.main()

