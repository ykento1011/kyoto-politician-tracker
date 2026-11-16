"""Offline article queue tests. Documents and people in this file are synthetic."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
import nagoya_article_review as q
import member_history as h

def no_network(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise RuntimeError("Offline tests forbid external effects")
sys.addaudithook(no_network)

URL = "https://www.city.nagoya.jp/shikai/test-article.html"
RAW = b"<html><article id='content'><h1>Test</h1><p>Person A leave Group A 2023-12-25</p></article></html>"
REG = dict(persons=[dict(person_id="nagoya:test-a")], facts=[])
def receipt(raw=RAW, url=URL):
    return dict(url=url, method="GET", status="success", http_status=200,
                bytes=len(raw), sha256=h.digest(raw), completed_utc="2026-11-16T00:00:00Z")
def event(raw=RAW):
    n=next(n for n in q.Tree(raw).nodes if n.tag=="p")
    return dict(candidate_id="test-1",name="Person A",person_id_candidate="nagoya:test-a",
        domain="group",scope="city_council",title="Group A",action="leave",
        effective_on="2023-12-25",date_literal="2023-12-25",position=q.source_position(n),
        source_url=URL,source_sha256=h.digest(raw))
def article(state=None, raw=RAW, candidates=None):
    return q.inspect_article(state or q.empty(),raw,receipt(raw),
                             candidates if candidates is not None else [event(raw)],REG)
def review(row):
    return dict(source_sha256=row["source_sha256"],reviewer="synthetic-human",
                review_reference="synthetic-review",reason="Check identity first",
                reviewed_at="2026-11-16T01:00:00Z",decision="hold")

class ReviewFlowTests(unittest.TestCase):
    def test_baseline_only_and_same_sha(self):
        raw=b"<article id='content'><h1>Index</h1><a href='/shikai/test-article.html'>New</a></article>"
        s,n=q.inspect_index(q.empty(),raw,receipt(raw,"https://www.city.nagoya.jp/shikai/index.html"))
        self.assertEqual(n,1);self.assertFalse(s["queue"][0]["fetch_authorized"])
        self.assertEqual(s["queue"][0]["change"],"baseline-only")
        self.assertEqual(s["queue"][0]["source_url"],receipt(raw,"https://www.city.nagoya.jp/shikai/index.html")["url"])
        self.assertEqual(s["queue"][0]["source_sha256"],h.digest(raw))
        self.assertEqual(s["queue"][0]["after"]["position"]["literal"],"New")
        s2,n=q.inspect_index(s,raw,receipt(raw,"https://www.city.nagoya.jp/shikai/index.html"))
        self.assertEqual(n,0);self.assertEqual(s,s2)
    def test_link_add_remove_and_label(self):
        url="https://www.city.nagoya.jp/shikai/index.html"
        a=b"<article id='content'><h1>I</h1><a href='a.html'>A</a><a href='b.html'>B</a></article>"
        b=b"<article id='content'><h1>I</h1><a href='a.html'>A2</a><a href='c.html'>C</a></article>"
        s,_=q.inspect_index(q.empty(),a,receipt(a,url))
        s,n=q.inspect_index(s,b,receipt(b,url))
        self.assertEqual(n,3)
        self.assertEqual({x["change"] for x in s["queue"][-3:]},{"added","removed","label_changed"})
        added=next(x for x in s["queue"][-3:] if x["change"]=="added")
        self.assertEqual(added["target_url"],"https://www.city.nagoya.jp/shikai/c.html")
        self.assertTrue(all(not x["fetch_authorized"] for x in s["queue"]))
        self.assertEqual(s["queue"][0]["change"],"baseline-only")
    def test_same_article_and_replacement(self):
        s,n=article();self.assertEqual(n,1)
        s2,n=article(s);self.assertEqual(n,0);self.assertEqual(s,s2)
        changed=RAW.replace(b"Test",b"Test amended")
        s3,n=article(s,changed)
        self.assertEqual(n,1);self.assertEqual(len(s3["versions"]),2)
        self.assertEqual(s3["queue"][0],s["queue"][0])
    def test_unknown_identity_and_date_hold(self):
        c=event();c.update(person_id_candidate=None,effective_on=None)
        s,_=article(candidates=[c])
        self.assertIn("identity_unresolved",s["queue"][0]["candidate"]["hold_reasons"])
        self.assertIn("effective_date_unknown",s["queue"][0]["candidate"]["hold_reasons"])
    def test_role_resignation_is_not_membership(self):
        c=event();c.update(domain="role",scope="committee:test",title="Chair",action="ended",effective_on=None)
        s,_=article(candidates=[c]);self.assertEqual(s["queue"][0]["candidate"]["domain"],"role")
        c.update(domain="membership",scope="city_council")
        with self.assertRaises(ValueError):article(candidates=[c])
    def test_same_raw_cannot_silently_change_candidates(self):
        s,_=article();c=event();c["title"]="Other"
        with self.assertRaises(ValueError):article(s,candidates=[c])
    def test_bad_source_position_and_no_implicit_person(self):
        for field,value in (("source_sha256","0"*64),("person_id_candidate","nagoya:unknown"),
                            ("position",dict(dom="/wrong",line=1,literal="missing"))):
            c=event();c[field]=value
            with self.assertRaises(ValueError):article(candidates=[c])
    def test_named_review_and_duplicate_review(self):
        s,_=article();row=s["queue"][0];r=review(row)
        s=q.record_review(s,row["queue_id"],r)
        self.assertEqual(len(q.record_review(s,row["queue_id"],r)["reviews"]),1)
        bad=dict(r,source_sha256="0"*64)
        with self.assertRaises(ValueError):q.record_review(s,row["queue_id"],bad)
    def test_acceptance_requires_identity_date_and_coverage(self):
        s,_=article();row=s["queue"][0];r=dict(review(row),decision="accepted_for_projection")
        with self.assertRaises(ValueError):q.record_review(s,row["queue_id"],r)
        r.update(person_id="nagoya:test-a",identity_confirmed=True,meaning_confirmed=True,
                 effective_on="2023-12-25",confirmed_through="2023-12-25")
        out=q.record_review(s,row["queue_id"],r)
        self.assertEqual(out["reviews"][0]["decision"],"accepted_for_projection")
        self.assertNotIn("facts",out);self.assertEqual(REG["facts"],[])
    def test_processing_failure_leaves_input_unchanged(self):
        s,_=article();before=copy.deepcopy(s)
        with self.assertRaises(ValueError):
            q.inspect_article(s,RAW,dict(receipt(),http_status=503),[event()],REG)
        self.assertEqual(s,before)
        with self.assertRaises(ValueError):
            q.inspect_index(s,b"<html/>",receipt(b"<html/>"))
        self.assertEqual(s,before)
    def test_atomic_save_failure_and_history_separation(self):
        s,_=article()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);head=q.save_queue(root,s)
            before=(root/"article-review-head.json").read_bytes()
            out=q.record_review(s,s["queue"][0]["queue_id"],review(s["queue"][0]))
            with patch.object(q.os,"replace",side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError):q.save_queue(root,out,head)
            self.assertEqual((root/"article-review-head.json").read_bytes(),before)
            self.assertFalse((root/"member-history-head.json").exists())
            with self.assertRaises(ValueError):q.save_queue(root,out,"0"*64)
    def test_repo_storage_is_rejected(self):
        with self.assertRaises(ValueError):
            q.save_queue(Path(__file__).resolve().parents[1]/"frontend/public/data/no-write",q.empty())
    def test_no_event_is_not_no_changes_claim(self):
        s,n=article(candidates=[])
        self.assertEqual(n,1);self.assertEqual(s["queue"][0]["kind"],"article_no_event")

if __name__=="__main__":unittest.main()

