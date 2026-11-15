"""Explicit Kyoto-only stages. No implicit HTTP, API, Git, publishing or scheduler.

inspect is read-only. Other operations write only below the existing private root.
Acquisition and analysis require their existing hash-bound policies separately.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata
from typing import Any, Dict, List

import kyoto_council_list_guard as io
import kyoto_one_meeting_guard as fetch
import kyoto_new_meetings as intake
import kyoto_gemini_budget as budget

PARSER_SHA = {
    "base_scraper.py":"92a3010d25f816bdaabf7fa111aa159e444b479bf9be699bbf3aeaa5c13adbe7",
    "kaigiroku_scraper.py":"6c3a59d5f98b28fb59222210e73aa7cc89edbe35ff2fee68f079f869d6b51a29",
}


def root_check(config):
    root=intake._private_root(config["private_root"],config["public_summary"])
    if not root.resolve().is_relative_to(io.ARTIFACT.resolve()):
        raise io.Stop("Continuation must stay inside Codex A private storage")
    if io.digest(io.LEDGER.read_bytes())!=io.LEDGER_SHA:
        raise io.Stop("Frozen 750-meeting history changed")
    return root


def history(root):
    p=root/"continuation-history.json"
    result=intake.read_json(p) if p.exists() else dict(schema=1,frozen_ledger_sha256=io.LEDGER_SHA,meetings={})
    if result.get("schema")!=1 or result.get("frozen_ledger_sha256")!=io.LEDGER_SHA:
        raise io.Stop("History binding changed")
    return result


def record(root,key,raw_sha,**states):
    if not re.fullmatch(r"kyoto:[1-9][0-9]*:[1-9][0-9]*",key) or not re.fullmatch("[0-9a-f]{64}",raw_sha):
        raise io.Stop("Invalid meeting/raw identity")
    lock=root/"history.lock"
    with lock.open("xb") as f: f.write(io.utc().encode())
    try:
        h=history(root)
        previous=h["meetings"].get(key)
        if previous and previous["original_raw_sha256"]!=raw_sha:
            raise io.Stop("Same meeting changed source: correction review, not automatic append")
        row=previous or dict(original_raw_sha256=raw_sha,acquired=False,analyzed=False,
                             published=False,official_coverage="unknown",meeting_complete=False)
        if "published" in states:
            raise io.Stop("This private entry cannot certify production publication")
        row.update(states,updated_utc=io.utc())
        row.update(official_coverage="unknown",meeting_complete=False)
        h["meetings"][key]=row
        io.write_json(root/"continuation-history.json",h)
        return row
    finally:
        lock.unlink()


def inspect(root):
    h=history(root)
    return dict(frozen_history=750,meetings=h["meetings"],
                acquisition_slots=[p.name for p in root.glob("acquisition-*.used")],
                publication_enabled=False,scheduler_enabled=False)


def acknowledge_publication(root,config):
    """Record a separate PM deployment receipt; never publish anything itself."""
    approval=intake.read_json(config["publication_receipt"])
    if (approval.get("pm_confirmed_deployed") is not True
            or not re.fullmatch("[0-9a-f]{40}",approval.get("commit",""))
            or not approval.get("approval_reference") or not approval.get("deployment_reference")):
        raise io.Stop("Separate PM production evidence required")
    key=approval["meeting_key"]
    h=history(root);prior=h["meetings"].get(key,{})
    if not prior.get("candidate_stage") or not prior.get("analyzed"):raise io.Stop("No analyzed private candidate")
    stage=io.safe_path(prior["candidate_stage"])
    ready=intake.read_json(stage/"READY.json")
    if ready.get("meeting_key")!=key or type(ready.get("added_records")) is not int or ready["added_records"]<1:
        raise io.Stop("Candidate scope/addition mismatch")
    if (io.digest((stage/"READY.json").read_bytes())!=prior["candidate_ready_sha256"] or
            any(io.digest((stage/p).read_bytes())!=sha for p,sha in prior["candidate_files"].items())):
        raise io.Stop("Candidate changed")
    public=io.safe_path(config["public_summary"])
    observed=intake.summary_records(public.read_bytes())
    wanted=intake.summary_records((stage/"data/kyoto_statements_summary.json").read_bytes())
    if (io.digest(public.read_bytes())!=approval.get("summary_sha256") or
            any(observed.get(k)!=v for k,v in wanted.items())):raise io.Stop("Published summary evidence mismatch")
    timelines=list((stage/"timeline-additions").glob("*.json"))
    if len(timelines)!=1:raise io.Stop("Expected exactly one timeline")
    original=timelines[0];deployed=io.safe_path(public.parent/"timelines"/original.name)
    if deployed.read_bytes()!=original.read_bytes() or io.digest(deployed.read_bytes())!=approval.get("timeline_sha256"):
        raise io.Stop("Published timeline evidence mismatch")
    quality = None
    if ready.get("publication_scope")=="partial" or prior.get("quality_selection_sha256"):
        quality_path=stage/"QUALITY_SELECTION.json"
        quality=intake.read_json(quality_path)
        digest=io.digest(quality_path.read_bytes())
        if (digest!=ready.get("quality_selection_sha256") or digest!=prior.get("quality_selection_sha256")
                or quality.get("meeting_key")!=key or quality.get("publication_scope")!="partial"
                or set(quality["held_thread_ids"])&set(observed)):
            raise io.Stop("Partial publication quality evidence mismatch")
        mid="ssp_"+key.split(":")[1]+"_"+key.split(":")[2]
        if {k for k,r in wanted.items() if r["meeting_id"]==mid}!=set(quality["accepted_thread_ids"]):
            raise io.Stop("Partial publication escaped its approved IDs")
    lock=root/"history.lock"
    with lock.open("xb") as f:f.write(io.utc().encode())
    try:
        fresh=history(root)
        if fresh!=h:raise io.Stop("History changed during publication acknowledgement")
        fresh["meetings"][key].update(published=True,publication_state="PM_deployment_receipt_recorded",
            publication_receipt_sha256=io.digest(Path(config["publication_receipt"]).read_bytes()),
            publication_commit=approval["commit"],publication_reference=approval["deployment_reference"])
        if quality is not None:
            fresh["meetings"][key].update(publication_state="partial_publication_confirmed",
                publication_scope="partial",published_thread_ids=quality["accepted_thread_ids"],
                held_thread_keys=quality["held_thread_ids"],quality_exclusions=quality["exclusions"],
                official_coverage="unknown",meeting_complete=False)
        io.write_json(root/"continuation-history.json",fresh)
    finally:lock.unlink()
    return fresh["meetings"][key]


def check_receipt(trial):
    trial=io.safe_path(trial)
    if not trial.resolve().is_relative_to(io.ARTIFACT.resolve()):
        raise io.Stop("Raw evidence outside private storage")
    r=intake.read_json(trial/"receipt.json")
    if r.get("status")!="raw_acquired_pending_offline_reconciliation" or len(r.get("attempts",[]))!=3:
        raise io.Stop("Partial acquisition is not ready")
    for attempt in r["attempts"]:
        p=io.safe_path(trial/attempt["raw_file"])
        if p.parent!=trial or attempt["status"]!=200 or io.digest(p.read_bytes())!=attempt["sha256"]:
            raise io.Stop("HTTP result or saved bytes mismatch")
    return r


def parser(code):
    # Same accepted pure parser extraction: no scraper constructor or requests import.
    ns=dict(re=re,unicodedata=unicodedata,datetime=datetime,List=List,Dict=Dict,Any=Any)
    for name,sha in PARSER_SHA.items():
        path=Path(code)/"scrapers"/name
        if io.digest(path.read_bytes().replace(b"\r\n",b"\n"))!=sha: raise io.Stop("Parser changed; review required")
        tree=ast.parse(path.read_text(encoding="utf-8-sig"))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        if cls.name=="BaseScraper":
            cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and
                      n.name in {"normalize_text","clean_speaker","extract_meeting_date"}]
            cls.bases=[]
        else:
            cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="parse_speech_blocks"
                      or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and
                          t.id=="EXCLUDE_SPEAKERS" for t in n.targets)]
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(path),"exec"),ns)
    obj=ns["KaigirokuScraper"]()
    obj.base_url="https://ssp.kaigiroku.net";obj.tenant_dir="kyoto"
    return obj


def prepare(config,root):
    trial=Path(config["acquired_trial"])
    receipt=check_receipt(trial)
    selected=receipt["selected_schedule"]
    key=selected["meeting_key"]
    raw=trial/"03-minutes.json"
    approval=intake.read_json(config["input_approval"])
    if (approval.get("meeting_key")!=key or approval.get("original_raw_sha256")!=io.digest(raw.read_bytes())
            or Path(approval.get("original_raw_path","")).resolve()!=raw.resolve()):
        raise io.Stop("Input acceptance does not identify the acquired original")
    # Council metadata is read from the saved index, not invented from the ID.
    idx=Path(config["saved_index"])
    if io.digest(idx.read_bytes())!=config["saved_index_sha256"]:
        raise io.Stop("Saved council index changed")
    ledger=intake.read_json(io.LEDGER)
    councils=io.parse_index(idx.read_bytes(),config["index_content_type"],ledger)["councils"]
    found=[c for c in councils if c["council_id"]==key.split(":")[1]]
    if len(found)!=1: raise io.Stop("Council metadata not unique")
    fetch.configure(dict(scope="kyoto_one_reviewed_meeting",council_id=key.split(":")[1],
                         schedule_id=key.split(":")[2],meeting_date=selected["meeting_date"],
                         candidate_review=approval["review_id"]))
    data=fetch.decode(raw.read_bytes(),receipt["attempts"][2]["content_type"])
    rows=parser(config["code_dir"]).parse_speech_blocks(data["tenant_minutes"],found[0],selected)
    if not rows or any(intake.meeting_key(r["official_url"],speech=True)!=key or
                       r["meeting_date"]!=selected["meeting_date"] for r in rows):
        raise io.Stop("Parsed source identity/date mismatch")
    folder=root/("parsed-"+io.digest(raw.read_bytes())[:24])
    folder.mkdir(exist_ok=True)
    cache=folder/"kyoto_raw_statements.json"
    encoded=intake.encode(rows)
    if cache.exists():
        if cache.read_bytes()!=encoded: raise io.Stop("Parsed cache changed")
    else:
        with cache.open("xb") as f:f.write(encoded)
    before=history(root)["meetings"].get(key,{})
    if before.get("prepared_stage"):
        raise io.Stop("Preparation already recorded; resume that stage")
    stage=intake.prepare(cache,ledger,approval,config["public_summary"],config["code_dir"],
                         config["master_file"],root)
    record(root,key,io.digest(raw.read_bytes()),acquired=True,prepared_stage=str(stage),
           acquisition_receipt_sha256=io.digest((trial/"receipt.json").read_bytes()))
    return stage


def private_project(stage,receipt_path,public_summary,root,*,repair_config=None):
    """Reuse the accepted private adapter on a new empty copy; never regenerate public files."""
    stage=io.safe_path(stage)
    if stage.parent.resolve()!=root.resolve(): raise io.Stop("Stage is not in selected private root")
    manifest=intake.read_json(stage/"manifest.json")
    if intake.read_json(stage/"READY.json")!={"status":"prepared_only",
            "manifest_sha256":io.digest(intake.encode(manifest))}: raise io.Stop("Uncommitted input")
    receipt=intake.read_json(receipt_path)
    if receipt.get("status")!="selected_threads_complete_private_only":
        raise io.Stop("Incomplete analysis is held")
    binding=receipt.get("binding",{})
    if (binding.get("manifest_sha256")!=io.digest(intake.encode(manifest))
            or binding.get("meeting_key")!=manifest["meeting_key"]):
        raise io.Stop("Receipt belongs to another prepared input")
    rows=intake.read_json(stage/"data-pipeline/kyoto_raw_statements.json")
    ns=budget.legacy_functions(stage/"data-pipeline/batch_analyze_council.py",None,
                              stage/"data-pipeline/master/councilors_kyoto.json")
    repaired = None
    quality = None
    if repair_config is not None:
        import kyoto_thread_repair
        repaired, checked, quality = kyoto_thread_repair.publication_plan(repair_config,receipt_path)
        if checked != receipt:
            raise io.Stop("Repair receipt changed during projection")
        threads = repaired["threads"]
    else:
        if binding.get("thread_revision"):
            raise io.Stop("Repair receipt requires its explicit revision config")
        threads=[t for t in ns["build_debate_threads"](rows) if not ns["is_procedural_or_voting"](t)]
    selected={str(t["main_statement"]["meeting_id"])+"_"+str(t["main_statement"]["sequence_number"]):t
              for t in threads[:budget.MAX_THREADS]}
    if set(selected)!=set(receipt["results"]) or receipt.get("success")!=len(selected):
        raise io.Stop("Results do not cover selected threads")
    charged={a["thread_id"]:a for a in receipt.get("api_attempts",[]) if a.get("status")=="success"}
    if repaired is None and (set(charged)!=set(selected) or any(charged[k].get("analysis")!=v.get("analysis")
                                        for k,v in receipt["results"].items())):
        raise io.Stop("Result is not backed by the saved successful response")
    if quality is not None:
        selected={k:v for k,v in selected.items() if k in quality["accepted_thread_ids"]}
        threads=list(selected.values())
    indexed={r["id"]:r for r in rows}
    zero={k:0 for k in ("evidence","solution","local_focus","constructive")}
    for r in rows:
        r["analysis"]={"is_evaluated":False,"category":"質疑外発言",
                       "reasoning":"代表質疑対象外または未解析","scores":dict(zero)}
    for key,result in receipt["results"].items():
        if result.get("status")!="analysis_success" or key not in indexed:raise io.Stop("Invalid result")
        if quality is not None and key not in selected:
            indexed[key]["analysis"]["reasoning"]="品質審査により公開保留（元の解析記録は別途保全）"
            continue
        indexed[key]["analysis"]=dict(budget.validate_result(result["analysis"]),is_evaluated=True)
        if repaired is not None:
            # Only the new summary uses the official master name. Original input
            # and timeline speaker labels remain untouched and traceable.
            indexed[key]["speaker"]=selected[key]["councilor_key"]
    with intake.private_transaction(root) as (work,completed):
        for name,sha in manifest["files"].items():
            src=io.safe_path(stage/name)
            if not src.resolve().is_relative_to(stage.resolve()) or io.digest(src.read_bytes())!=sha:
                raise io.Stop("Prepared code/input changed")
            dst=work/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
        for name in ("manifest.json","READY.json"):(work/name).write_bytes((stage/name).read_bytes())
        pipeline=work/"data-pipeline"
        (pipeline/"analyzed_kyoto_politicians_term.json").write_bytes(intake.encode(rows))
        # Existing adapter, pinned producer functions, fresh private output only.
        source=pipeline/"generate_static_data.py"
        code=ast.parse(source.read_text(encoding="utf-8-sig"))
        body=[n for n in code.body if isinstance(n,(ast.FunctionDef,ast.Assign))]
        env=dict(__file__=str(source),json=json,os=os,re=re,Path=Path)
        exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),str(source),"exec"),env)
        env["generate_summary"]()
        if repaired is not None:
            import kyoto_thread_contract
            timelines=work/"frontend/public/data/timelines"
            timelines.mkdir()
            content=kyoto_thread_contract.timeline(threads,repaired["roles"])
            (timelines/(rows[0]["meeting_id"]+".json")).write_bytes(intake.encode(content))
        else:
            source=pipeline/"build_timeline_contexts.py"
            tree=ast.parse(source.read_text(encoding="utf-8-sig"))
            funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and
                   n.name in {"load_councilors","fetch_raw_statements","build_timelines"}]
            if len(funcs)!=3 or (work/"frontend/public/data/timelines").exists():
                raise io.Stop("Timeline output must be new and empty")
            env=dict(PROJECT_ROOT=work,Path=Path,os=os,json=json,re=re,shutil=shutil)
            exec(compile(ast.fix_missing_locations(ast.Module(body=funcs,type_ignores=[])),str(source),"exec"),env)
            env["build_timelines"]("kyoto")
    candidate=intake.assemble(completed,public_summary,root)
    if quality is not None:
        # The normal assembler still checks identities, source text, exact timeline
        # coverage and the immutable public baseline before this extra receipt.
        io.write_json(candidate/"QUALITY_SELECTION.json",quality)
        ready=intake.read_json(candidate/"READY.json")
        ready.update(publication_scope="partial",quality_selection_sha256=io.digest((candidate/"QUALITY_SELECTION.json").read_bytes()))
        io.write_json(candidate/"READY.json",ready)
    return candidate


def execute(operation,config):
    root=root_check(config)
    if operation=="inspect":return inspect(root)
    if operation=="ack-publication":return acknowledge_publication(root,config)
    if operation=="councils":return str(io.acquire(config["network_approval"]))
    if operation in ("schedules","acquire"):
        approval=intake.read_json(config["network_approval"])
        expected="kyoto_reviewed_council_schedules" if operation=="schedules" else "kyoto_one_reviewed_meeting"
        if approval.get("scope")!=expected: raise io.Stop("Operation/approval mismatch")
        key="kyoto:"+str(approval.get("council_id"))+":"+str(approval.get("schedule_id"))
        if operation=="acquire" and key in history(root)["meetings"]:
            raise io.Stop("Already acquired/held meeting: reuse saved original, no refetch")
        if operation=="acquire":
            if not re.fullmatch(r"kyoto:[1-9][0-9]*:[1-9][0-9]*",key):raise io.Stop("Invalid selected meeting")
            # Consume a durable meeting slot before the first HTTP attempt; even a
            # crash or failed acquisition cannot silently refetch under another run ID.
            fetch.validate_approval(config["network_approval"])
            with (root/("acquisition-"+key.replace(":","-")+".used")).open("xb") as f:
                f.write(io.json_bytes(dict(run_id=approval["run_id"],status="reserved",utc=io.utc())))
        trial=fetch.acquire(config["network_approval"])
        if operation=="acquire":
            r=check_receipt(trial)
            record(root,key,r["attempts"][2]["sha256"],acquired=True,acquired_trial=str(trial))
        else:
            r=intake.read_json(trial/"receipt.json")
            for s in r["schedule_candidates"]:
                if s["meeting_key"] in history(root)["meetings"]:s["private_history_status"]="already_acquired"
            io.write_json(trial/"schedule-diff.json",r["schedule_candidates"])
        return str(trial)
    if operation=="prepare":return str(prepare(config,root))
    if operation in ("analyze","candidate"):
        stage=Path(config["prepared_stage"])
        manifest=intake.read_json(stage/"manifest.json")
        key=manifest["meeting_key"];rawsha=manifest["original_raw_sha256"]
        if operation=="analyze":
            previous=history(root)["meetings"].get(key,{})
            if previous.get("analyzed"):
                prior=io.safe_path(previous["analysis_receipt"])
                if (previous.get("original_raw_sha256")!=rawsha or
                        Path(previous["prepared_stage"]).resolve()!=stage.resolve() or
                        io.digest(prior.read_bytes())!=previous["analysis_receipt_sha256"]):
                    raise io.Stop("Accepted analysis binding changed; no automatic reanalysis")
                return str(prior.parent)
            try:
                out=budget.run(stage,config["api_policy"],config["public_summary"],root,
                               resume=config.get("resume",False),retry_failed=config.get("retry_failed",False))
            except BaseException:
                record(root,key,rawsha,analysis_state="held_or_failed",analyzed=False)
                raise
            r=intake.read_json(out/"receipt.json")
            record(root,key,rawsha,analyzed=True,analysis_receipt=str(out/"receipt.json"),
                   prepared_stage=str(stage),analysis_receipt_sha256=io.digest((out/"receipt.json").read_bytes()),
                   analyzed_threads=r["success"],deferred_threads=r["deferred_threads"],
                   analysis_state="selected_threads_complete",estimated_jpy=r["total_estimated_jpy"])
            return str(out)
        prior=history(root)["meetings"].get(key,{})
        if prior.get("candidate_stage"):
            saved=io.safe_path(prior["candidate_stage"])
            if (prior.get("original_raw_sha256")!=rawsha or
                    io.digest((saved/"READY.json").read_bytes())!=prior["candidate_ready_sha256"] or
                    any(io.digest((saved/p).read_bytes())!=h for p,h in prior["candidate_files"].items())):
                raise io.Stop("Saved candidate changed")
            return str(saved)
        out=private_project(stage,Path(config["analysis_receipt"]),config["public_summary"],root)
        record(root,key,rawsha,candidate_stage=str(out),publication_state="pending_review",
               candidate_ready_sha256=io.digest((out/"READY.json").read_bytes()),
               candidate_files={p.relative_to(out).as_posix():io.digest(p.read_bytes())
                                for p in out.rglob("*.json") if p.name!="READY.json"})
        return str(out)
    raise io.Stop("No publication or scheduler operation is implemented")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation",choices=("inspect","councils","schedules","acquire","prepare","analyze","candidate","ack-publication"))
    p.add_argument("--config",required=True)
    a=p.parse_args()
    try:print(json.dumps(execute(a.operation,intake.read_json(a.config)),ensure_ascii=False))
    except (Exception,budget.BudgetStop) as e:
        print("STOP: "+str(e));raise SystemExit(1)
