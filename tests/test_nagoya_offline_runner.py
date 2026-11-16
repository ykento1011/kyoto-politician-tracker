"""Synthetic responses only; no official HTTP, models or public writes."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"data-pipeline"))
import nagoya_offline_runner as r

def offline(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise RuntimeError("Offline regression forbids external effects")
sys.addaudithook(offline)
STAMP = "2026-11-16T00:00:00Z"
DETAIL = "https://www.city.nagoya.jp/shikai/kouhou/1030998/1999999.html"

def html(url, text="baseline"):
    did=r._document_id(url)
    return ("<html><article id='content'><h1>Fixture</h1>"
        "<span class='idnumber'>ページID"+did+"</span><p>"+text+"</p>"
        "<a href='"+DETAIL+"'>Synthetic article</a></article></html>").encode()
def receipt(url, raw):
    return dict(url=url,method="GET",status="success",http_status=200,
        sha256=r.h.digest(raw),bytes=len(raw),completed_utc=STAMP)
def response(raw, **kw):
    return dict(status=200,location=None,tls_verified=True,redirects=0,retries=0,
        elapsed_seconds=0.1,content_type="text/html",content_length=len(raw),chunks=[raw],**kw)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"private"
        self.originals={u:(html(u),receipt(u,html(u))) for u in r.FIXED}
    def contract(self, urls=None):
        targets=[]
        for u in urls or r.FIXED:
            if u in r.FIXED:
                binding=dict(url=u,sha256=self.originals[u][1]["sha256"])
                kind="index" if u in r.INDEXES else "page"
            else:
                source=r.FIXED[-2];raw,rec=self.originals[source]
                ev,nodes=r.review.original(raw,rec)
                n=next(n for n in nodes if n.tag=="a")
                binding=dict(url=source,sha256=rec["sha256"],href=n.attrs["href"],
                             position=r.review.source_position(n));kind="article"
            targets.append(dict(url=u,document_id=r._document_id(u),kind=kind,
                approved=True,approval_reference="synthetic-PM",layout_accepted=True,
                source_binding=binding))
        return dict(mode="offline-synthetic",network_enabled=False,
            publication_enabled=False,scheduler_enabled=False,limits=copy.deepcopy(r.LIMITS),
            storage=str(self.root),code_sha256=r.code_sha(),review_owner="test-reviewer",
            dependency_shas=r.dependency_shas(),
            recovery_owner="test-recovery",targets=targets)
    def run_plan(self, contract=None, changes=None, state=None, head=None, run_id="one", stamp=STAMP):
        c=contract or self.contract()
        responses={t["url"]:response(html(t["url"])) for t in c["targets"]}
        responses.update(changes or {})
        transport=r.SyntheticTransport(responses)
        out,h=r.run_offline(self.root,state or r.initial(),head,c,self.originals,
                            transport,run_id,stamp)
        return out,h,transport
    def test_eight_gets_and_exact_transport_limits(self):
        out,head,t=self.run_plan(self.contract(list(r.FIXED)+[DETAIL]))
        self.assertEqual(len(t.calls),8)
        self.assertTrue(all(c["constraints"]==r.LIMITS for c in t.calls))
        self.assertEqual(out["runs"][0]["attempts"][-1]["url"],DETAIL)
        self.assertFalse((self.root/"member-history-head.json").exists())
        self.assertEqual(r.h.digest((self.root/"article-review-cas"/(head+".json")).read_bytes()),head)
    def test_same_sha_review_zero_and_persisted_frontier_age(self):
        out,head,_=self.run_plan()
        n=len(out["queue"])
        out,head,_=self.run_plan(state=out,head=head,run_id="two",stamp="2026-11-23T00:00:00Z")
        self.assertEqual(len(out["queue"]),n)
        rows=r.backlog(out,"2026-11-23T00:00:00Z")
        detail=next(x for x in rows if x["url"]==DETAIL)
        self.assertTrue(detail["unvisited"]);self.assertEqual(detail["days_waiting"],7)
        self.assertFalse(detail["fetch_authorized"])
        self.assertEqual(len(out["frontier"][r.FIXED[0]]["processed_shas"]),1)
    def test_changed_page_creates_positioned_hold(self):
        c=self.contract([r.FIXED[0]]);out,head,_=self.run_plan(c)
        raw=html(r.FIXED[0],"synthetic amendment")
        newer,_,_=self.run_plan(c,{r.FIXED[0]:response(raw)},out,head,"two")
        self.assertEqual(len(newer["queue"]),len(out["queue"])+1)
        entry=newer["queue"][-1];self.assertEqual(entry["status"],"hold")
        self.assertEqual(entry["change"],"content_changed")
        self.assertTrue(entry["positions"][0]["dom"])
    def test_per_response_limit(self):
        raw=html(r.FIXED[0])+b"x"*(2*r.MIB)
        with self.assertRaises(ValueError):
            self.run_plan(self.contract([r.FIXED[0]]),{r.FIXED[0]:dict(response(raw),content_length=None)})
        self.assertFalse((self.root/"article-review-head.json").exists())
    def test_total_limit_independent_of_response_limit(self):
        urls=list(r.FIXED[:5])
        data={}
        for url in urls:
            raw=html(url);raw=raw.replace(b"</html>",b" "*(2*r.MIB-len(raw))+b"</html>")
            self.assertEqual(len(raw),2*r.MIB)
            data[url]=response(raw)
        transport=r.SyntheticTransport(data)
        with self.assertRaisesRegex(ValueError,"total reservation"):
            r.run_offline(self.root,r.initial(),None,self.contract(urls),self.originals,
                          transport,"one",STAMP)
        self.assertEqual(len(transport.calls),4)
        self.assertFalse((self.root/"article-review-head.json").exists())
    def test_redirect_retry_tls_deadline_empty_partial_and_doc_id_stop(self):
        for key,value in (("status",302),("retries",1),("redirects",1),
                          ("tls_verified",False),("elapsed_seconds",10.01),
                          ("content_length",10000),("chunks",[])):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as td:
                self.root=Path(td)/"private"
                fixture=dict(response(html(r.FIXED[0])));fixture[key]=value
                with self.assertRaises(ValueError):
                    self.run_plan(self.contract([r.FIXED[0]]),{r.FIXED[0]:fixture})
                self.assertFalse((self.root/"article-review-head.json").exists())
        with tempfile.TemporaryDirectory() as td:
            self.root=Path(td)/"private"
            with self.assertRaises(ValueError):
                self.run_plan(self.contract([r.FIXED[0]]),{r.FIXED[0]:response(html(r.FIXED[1]))})
    def test_failure_preserves_committed_normal_state(self):
        c=self.contract([r.FIXED[0]]);out,head,_=self.run_plan(c)
        before=(self.root/"article-review-head.json").read_bytes()
        c=self.contract(list(r.FIXED[:2]))
        bad=dict(response(html(r.FIXED[1])),status=503)
        with self.assertRaises(ValueError):
            self.run_plan(c,{r.FIXED[1]:bad},out,head,"two")
        self.assertEqual((self.root/"article-review-head.json").read_bytes(),before)
        failed=json.loads((self.root/"runner-receipts/two.json").read_text())
        self.assertEqual(failed["status"],"failed")
        self.assertEqual(len(failed["attempts"]),2)
        self.assertEqual(len(out["runs"]),1)
    def test_save_failure_preserves_normal_head(self):
        c=self.contract([r.FIXED[0]]);out,head,_=self.run_plan(c)
        before=(self.root/"article-review-head.json").read_bytes()
        replace=r.review.os.replace
        def fail_head(a,b):
            if Path(b).name=="article-review-head.json":
                raise OSError("synthetic head failure")
            return replace(a,b)
        with patch.object(r.review.os,"replace",side_effect=fail_head):
            with self.assertRaises(OSError):
                self.run_plan(c,state=out,head=head,run_id="two")
        self.assertEqual((self.root/"article-review-head.json").read_bytes(),before)
    def test_permissions_layout_sha_exact_url_and_storage_preflight(self):
        for change in ("url","doc","layout","approval","source","code","dependencies","storage","live"):
            c=self.contract([r.FIXED[0]])
            if change=="url":c["targets"][0]["url"]+="?unexpected=1"
            elif change=="doc":c["targets"][0]["document_id"]="wrong"
            elif change=="layout":c["targets"][0]["layout_accepted"]=False
            elif change=="approval":c["targets"][0]["approved"]=False
            elif change=="source":c["targets"][0]["source_binding"]["sha256"]="0"*64
            elif change=="code":c["code_sha256"]="0"*64
            elif change=="dependencies":c["dependency_shas"]={}
            elif change=="storage":c["storage"]="other"
            else:c["network_enabled"]=True
            t=r.SyntheticTransport({})
            with self.assertRaises(ValueError):
                r.run_offline(self.root,r.initial(),None,c,self.originals,t,"one",STAMP)
            self.assertEqual(t.calls,[])
    def test_detail_href_binding_and_duplicate_plan(self):
        c=self.contract([DETAIL]);c["targets"][0]["source_binding"]["href"]="wrong.html"
        with self.assertRaises(ValueError):self.run_plan(c)
        c=self.contract([r.FIXED[0],r.FIXED[0]])
        with self.assertRaises(ValueError):self.run_plan(c)
    def test_run_id_and_stale_head_no_retry(self):
        c=self.contract([r.FIXED[0]]);out,head,_=self.run_plan(c)
        t=r.SyntheticTransport({})
        with self.assertRaises(FileExistsError):
            r.run_offline(self.root,out,head,c,self.originals,t,"one",STAMP)
        with self.assertRaises(ValueError):
            r.run_offline(self.root,out,"0"*64,c,self.originals,t,"two",STAMP)
        self.assertEqual(t.calls,[])
    def test_custom_live_transport_and_repository_storage_rejected(self):
        with self.assertRaises(ValueError):
            r.run_offline(self.root,r.initial(),None,self.contract(),self.originals,
                          object(),"one",STAMP)
        with self.assertRaises(ValueError):
            r.review._private(Path(__file__).resolve().parents[1]/"frontend/public/data/bad")

    def test_review_worklist_and_time_limits(self):
        c=self.contract([r.FIXED[0]])
        out,head,_=self.run_plan(c)
        self.assertEqual(len(r.review_backlog(out,STAMP)),1)
        row=out["queue"][0]
        reviewed=r.review.record_review(out,row["queue_id"],dict(
            source_sha256=row["source_sha256"],decision="rejected",reviewer="test-human",
            review_reference="test-review",reason="synthetic rejection",reviewed_at=STAMP))
        self.assertEqual(r.review_backlog(reviewed,STAMP),[])
        self.assertNotIn("facts",reviewed)
        with self.assertRaises(ValueError):
            self.run_plan(c,state=out,head=head,run_id="backwards",stamp="2026-11-15T00:00:00Z")
        self.root=Path(self.temp.name)/"deadline"
        with patch.object(r.time,"monotonic",side_effect=[0,11]):
            with self.assertRaisesRegex(ValueError,"deadline"):
                self.run_plan(self.contract([r.FIXED[0]]))

if __name__=="__main__":unittest.main()
