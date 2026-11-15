"""Offline saved-record replay; reuses identity, thread, quality and append guards.

No acquisition/analysis entry point is called. Semantic acceptance is an explicit,
hash-bound saved review of BOTH summary and reasoning, not an automatic AI verdict.
"""
import argparse
import json
from pathlib import Path
import kyoto_one_meeting_guard as guard
import kyoto_meeting_identity as identity
import kyoto_new_meetings as intake
import kyoto_gemini_budget as budget
import kyoto_thread_contract as threads
import kyoto_thread_repair as repair

io = guard.transport

def load_bound(spec):
    path = io.safe_path(spec["path"])
    if not path.resolve().is_relative_to(io.ARTIFACT.resolve()):
        raise io.Stop("Saved replay inputs must be private")
    raw = path.read_bytes()
    if io.digest(raw) != spec.get("sha256"):
        raise io.Stop("Saved replay artifact changed")
    return raw

def semantic_gate(review, plan, state, approval, receipt_sha):
    if approval.get("scope") == "approved_selected_results":
        # All selected threads may pass; this still never means full meeting coverage.
        accepted = approval.get("accepted", {})
        if (not accepted or set(accepted) != set(plan["selected_keys"]) or approval.get("exclusions")
                or not approval.get("approval_reference")
                or approval.get("meeting_key") != plan["meeting_key"]
                or approval.get("plan_sha256") != repair.plan_digest(plan)
                or approval.get("input_sha256") != plan["input_sha256"]
                or approval.get("original_raw_sha256") != plan["original_raw_sha256"]
                or approval.get("analysis_receipt_sha256") != receipt_sha):
            raise io.Stop("Complete selected-result review binding mismatch")
        for key, entry in accepted.items():
            if (not entry.get("source_reference") or entry.get("analysis_sha256") !=
                    io.digest(intake.encode(state["results"][key]["analysis"]))):
                raise io.Stop("Accepted result/source review changed")
        selection = dict(meeting_key=plan["meeting_key"],accepted_thread_ids=plan["selected_keys"],
                         held_thread_ids=[],publication_scope="selected_results",official_coverage="unknown",meeting_complete=False)
    else:
        selection = repair.quality_selection(approval, plan, state, receipt_sha)
    reviews = review.get("reviews", {})
    if set(reviews) != set(plan["selected_keys"]):
        raise io.Stop("Every selected result needs saved content review")
    for key in selection["accepted_thread_ids"]:
        entry = reviews[key]
        if (entry.get("decision") != "accepted_for_partial_publication"
                or entry.get("summary_and_reasoning_reviewed") is not True
                or not entry.get("positions") or not entry.get("note")
                or entry.get("result_sha256") != io.digest(intake.encode(state["results"][key]["analysis"]))):
            raise io.Stop("Summary AND reasoning/source review missing or changed")
    for key in selection["held_thread_ids"]:
        entry = reviews[key]
        if entry.get("decision") != "hold" or not entry.get("reason"):
            raise io.Stop("Held result requires an explicit semantic reason")
    return selection

def verify_summary_results(candidate, accepted, selected_threads, state):
    """Saved projection must still contain exactly the reviewed meaning/scores."""
    by_key = {threads.thread_key(t): t for t in selected_threads}
    for key in accepted:
        row, thread, result = candidate[key], by_key[key], state["results"][key]["analysis"]
        if row.get("summary") != result.get("summary") or row.get("scoring_reasoning") != result.get("reasoning"):
            raise io.Stop("Candidate summary/reasoning differs from reviewed result")
        for axis in ("evidence", "solution", "local_focus", "constructive"):
            if row.get(axis+"_score") != int(result["scores"][axis]):
                raise io.Stop("Candidate score differs from reviewed result")
        original = thread["main_statement"]
        if (row.get("speaker") != thread["councilor_key"] or
                any(row.get(f) != original.get(f) for f in
                    ("meeting_id", "sequence_number", "meeting_date", "source_url"))):
            raise io.Stop("Candidate speaker/source identity changed")

def inspect(config):
    files = {k: load_bound(v) for k,v in config["files"].items()}
    read = lambda k: json.loads(files[k])
    target = identity.target(config["target"])
    key = "kyoto:"+target["council_id"]+":"+target["schedule_id"]
    history = read("history")
    if key not in history["meetings"]:
        raise io.Stop("Saved replay requires a registered meeting")
    guard.configure(dict(scope="kyoto_meeting_identity_only",identity_review=target,
        council_id=target["council_id"],schedule_id=target["schedule_id"],
        meeting_date=target["meeting_date"],council_year=int(target["meeting_date"][:4])))
    guard.REGISTERED_KEYS = set(history["meetings"])
    receipt = read("acquisition")
    if receipt.get("status") not in ("raw_acquired_pending_offline_reconciliation","identity_confirmed_private_only"):
        raise io.Stop("Incomplete acquisition")
    for name,url in (("schedules",guard.SCHEDULE),("minutes",guard.MINUTE)):
        attempts=[a for a in receipt["attempts"] if a.get("method")=="POST" and a.get("url")==url]
        if len(attempts)!=1 or attempts[0].get("status")!=200 or attempts[0].get("sha256")!=io.digest(files[name]):
            raise io.Stop("Saved HTTP/source binding mismatch")
    selected=guard.select_schedule(files["schedules"],"application/json",{"meetings":history["meetings"]})
    if receipt.get("selected_schedule") != selected:
        raise io.Stop("Selected official schedule changed")
    identity_result=guard.validate_minutes(files["minutes"],"application/json",selected)
    blocks=read("minutes")["tenant_minutes"]; rows=read("rows"); master=read("master")
    if any(intake.meeting_key(r["official_url"],speech=True)!=key or r["meeting_date"]!=target["meeting_date"] for r in rows):
        raise io.Stop("Parsed input identity mismatch")
    ns=budget.legacy_functions(Path(config["files"]["legacy"]["path"]),None,Path(config["files"]["master"]["path"]))
    built=threads.build(rows,blocks,master,ns["is_procedural_call"])
    if built["holds"]:
        raise io.Stop("Unconfirmed speaker or agenda boundary")
    selected_threads=[t for t in built["threads"] if not ns["is_procedural_or_voting"](t)]
    report=dict(meeting_key=key,identity=identity_result,threads=len(selected_threads),
        official_coverage="unknown",meeting_complete=False,HTTP=0,Gemini=0,publication_authorized=False)
    if not selected_threads:
        return dict(report,status="no_substantive_questions"), None
    plan,state,policy=read("plan"),read("analysis"),read("api_policy")
    manifest=read("prepared_manifest")
    if (plan["meeting_key"]!=key or plan["original_raw_sha256"]!=io.digest(files["minutes"])
            or plan["input_sha256"]!=manifest["input_sha256"]
            or plan["manifest_sha256"]!=io.digest(intake.encode(manifest))
            or manifest["files"]["data-pipeline/kyoto_raw_statements.json"]!=io.digest(files["rows"])
            or state.get("binding",{}).get("manifest_sha256")!=plan["manifest_sha256"]
            or state.get("status")!="selected_threads_complete_private_only"
            or [threads.thread_key(t) for t in selected_threads]!=plan["selected_keys"]):
        raise io.Stop("Saved plan/input/selection mismatch")
    for thread in selected_threads:
        if threads.fingerprint(ns,thread)!=plan["fingerprints"][threads.thread_key(thread)]:
            raise io.Stop("Speaker, membership or exact model prompt changed")
    repair.validate_attempts(plan,state,policy)  # Recover saved usage/results; no API client.
    selection=semantic_gate(read("content_review"),plan,state,read("quality_approval"),io.digest(files["analysis"]))
    accepted=set(selection["accepted_thread_ids"]); held=set(selection["held_thread_ids"])
    if accepted & held:
        raise io.Stop("Quality partition overlaps")
    candidate=intake.summary_records(files["candidate_summary"])
    baseline=intake.summary_records(files["baseline"])
    if set(candidate)-set(baseline)!=accepted or any(candidate.get(k)!=v for k,v in baseline.items()):
        raise io.Stop("Saved candidate changes old records or quality partition")
    verify_summary_results(candidate, accepted, selected_threads, state)
    allowed=[t for t in selected_threads if threads.thread_key(t) in accepted]
    timeline=threads.timeline(allowed,built["roles"])
    if timeline!=read("candidate_timeline"):
        raise io.Stop("Saved timeline does not match reviewed boundaries")
    report.update(status="reviewed_partial_replay",accepted=len(accepted),held=len(held),
        held_thread_ids=selection["held_thread_ids"],source_hashes={k:v["sha256"] for k,v in config["files"].items()})
    return report, dict(rows=rows,addition=[candidate[k] for k in plan["selected_keys"] if k in accepted],
                        timeline=timeline,selection=selection,baseline=files["baseline"])

def stage(config):
    report, data = inspect(config)
    if data is None:
        return report
    root=intake._private_root(config["output_root"],config["files"]["baseline"]["path"])
    if not root.resolve().is_relative_to(io.ARTIFACT.resolve()):
        raise io.Stop("Replay output must remain private")
    with intake.private_transaction(root) as (work,prepared):
        raw=work/"data-pipeline/kyoto_raw_statements.json";raw.parent.mkdir()
        raw.write_bytes(intake.encode(data["rows"]))
        public=work/"frontend/public/data";public.mkdir(parents=True)
        (public/"statements_summary.json").write_bytes(intake.encode(data["addition"]))
        timeline=public/"timelines";timeline.mkdir()
        mid=data["rows"][0]["meeting_id"]
        (timeline/(mid+".json")).write_bytes(intake.encode(data["timeline"]))
        manifest=dict(meeting_key=report["meeting_key"],baseline_sha256=io.digest(data["baseline"]),
                      files={"data-pipeline/kyoto_raw_statements.json":io.digest(raw.read_bytes())})
        io.write_json(work/"manifest.json",manifest)
        io.write_json(work/"READY.json",dict(status="prepared_only",manifest_sha256=io.digest(intake.encode(manifest))))
    candidate=intake.assemble(prepared,config["files"]["baseline"]["path"],root)
    io.write_json(candidate/"QUALITY_SELECTION.json",data["selection"])
    ready=intake.read_json(candidate/"READY.json")
    ready.update(status="offline_replay_not_for_publication",publication_enabled=False)
    io.write_json(candidate/"READY.json",ready)
    io.write_json(candidate/"REPLAY.json",report)
    return dict(report,candidate_stage=str(candidate),live_publication_candidate=False)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation",choices=("inspect","stage"))
    parser.add_argument("--config",required=True)
    args=parser.parse_args()
    cfg=intake.read_json(args.config)
    try:
        result=inspect(cfg)[0] if args.operation=="inspect" else stage(cfg)
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,KeyError,OSError,io.Stop) as exc:
        raise SystemExit("STOP: "+str(exc))
