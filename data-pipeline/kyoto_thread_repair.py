"""Explicit, hash-bound Kyoto speaker repair; prior analysis remains immutable.

Uses the accepted legacy prompt and budget Meter. Unknown roles stop before API.
A separate revision receipt records exact prompt reuse and new billable attempts.
"""
import argparse
import ast
from decimal import Decimal
import json
import os
from pathlib import Path
import re

import kyoto_council_list_guard as io
import kyoto_new_meetings as intake
import kyoto_gemini_budget as budget
import kyoto_thread_contract as contract

CODE_FILES = ("kyoto_thread_contract.py", "kyoto_thread_repair.py",
              "kyoto_gemini_budget.py", "kyoto_continuation.py", "kyoto_new_meetings.py")

def code_hashes():
    return {name:io.digest((Path(__file__).parent/name).read_bytes()) for name in CODE_FILES}

def checked_stage(config, *, analysis_code=None):
    root = intake._private_root(config["private_root"], config["public_summary"])
    if not root.resolve().is_relative_to(io.ARTIFACT.resolve()):
        raise io.Stop("Repair must remain in private Codex A storage")
    stage = io.safe_path(config["prepared_stage"])
    if stage.parent.resolve()!=root.resolve() or not stage.name.startswith("ready-"):
        raise io.Stop("A committed private input stage is required")
    manifest = intake.read_json(stage/"manifest.json")
    ready = intake.read_json(stage/"READY.json")
    if ready!={"status":"prepared_only","manifest_sha256":io.digest(intake.encode(manifest))}:
        raise io.Stop("Prepared manifest changed")
    for name,sha in manifest["files"].items():
        file = io.safe_path(stage/name)
        if not file.resolve().is_relative_to(stage.resolve()) or io.digest(file.read_bytes())!=sha:
            raise io.Stop("Prepared input/master/legacy code changed")
    original = io.safe_path(config["original_raw"])
    if io.digest(original.read_bytes())!=manifest["original_raw_sha256"]:
        raise io.Stop("Original body changed")
    policy = intake.read_json(config["api_policy"])
    budget.policy_check(policy)
    if (policy.get("meeting_key")!=manifest["meeting_key"]
        or policy.get("input_sha256")!=manifest["input_sha256"]
        or policy.get("manifest_sha256")!=ready["manifest_sha256"]
        or policy.get("thread_revision")!=contract.REVISION
        or policy.get("thread_code_sha256")!=(analysis_code if analysis_code is not None else code_hashes())
        or not re.fullmatch(r"[a-z0-9-]{4,90}",policy.get("revision_id",""))):
        raise io.Stop("Explicit repair revision/code/input policy mismatch")
    return root,stage,manifest,policy

def old_fingerprint(ns, thread, rows):
    chair = ns["find_meeting_chair"](rows)
    candidate = dict(thread)
    candidate["prompt_statement_ids"] = [
        r["id"] for r in thread["related_statements"]
        if not (chair is not None and ns["clean_name"](r["speaker"])==chair)
        and not ns["is_procedural_call"](r["statement_text"].strip())]
    return contract.fingerprint(ns,candidate)

def same_analysis_input(before, after):
    # Chair/procedure-only timeline context never sent to Gemini is audited separately.
    # Every actual model-input statement ID, speaker, prompt byte and config must match.
    return all(before[k]==after[k] for k in ("speaker","prompt_statement_ids","prompt_sha256","config"))


def reviewed_results(config, policy, keys):
    path = io.safe_path(config["prior_content_review"])
    if io.digest(path.read_bytes()) != policy.get("prior_content_review_sha256"):
        raise io.Stop("Prior content review changed")
    review = intake.read_json(path)
    if set(review) != set(keys):
        raise io.Stop("Every prior result requires an explicit content review")
    for item in review.values():
        if (item.get("decision") not in ("reuse", "invalidate")
                or not item.get("reason") or not item.get("source_reference")):
            raise io.Stop("Incomplete semantic review")
        note = item.get("reanalysis_instruction")
        if note is not None and (item["decision"] != "invalidate" or not isinstance(note,str) or not 1 <= len(note) <= 1000):
            raise io.Stop("Reanalysis instruction requires explicit invalidation")
    return review


def saved_repair_prior(config, policy, prior, ns, manifest):
    """Reuse a hash-approved first repair, without re-executing its old code/API.

    Chained receipts already containing reused results need a separate ancestry review.
    Never silently treat those results as newly charged successes.
    """
    path = io.safe_path(prior["plan_file"])
    old_plan = intake.read_json(path)
    previous_policy_path = io.safe_path(config["prior_api_policy"])
    if io.digest(previous_policy_path.read_bytes()) != policy.get("prior_api_policy_sha256"):
        raise io.Stop("Previous pricing/revision policy changed")
    previous_policy = intake.read_json(previous_policy_path)
    if (plan_digest(old_plan) != policy.get("prior_plan_sha256")
            or old_plan.get("manifest_sha256") != io.digest(intake.encode(manifest))
            or old_plan.get("original_raw_sha256") != manifest["original_raw_sha256"]
            or old_plan.get("code_sha256") != previous_policy.get("thread_code_sha256")
            or old_plan.get("model") != budget.MODEL
            or old_plan.get("reused_results") or Decimal(old_plan.get("prior_estimated_jpy","-1")) != 0):
        raise io.Stop("Prior repair binding/ancestry is unsupported or changed")
    if path.parent.resolve() != output_path(config,old_plan).resolve():
        raise io.Stop("Prior plan outside its exact revision")
    keys = [contract.thread_key(t) for t in old_plan["threads"]]
    if keys != old_plan["selected_keys"] or set(keys) != set(prior["results"]):
        raise io.Stop("Prior repair does not cover its threads")
    meter, recovered = validate_attempts(old_plan,prior,previous_policy)
    if recovered != prior["results"]:
        raise io.Stop("Prior repair response evidence incomplete")
    for thread in old_plan["threads"]:
        key = contract.thread_key(thread)
        if contract.fingerprint(ns,thread) != old_plan["fingerprints"][key]:
            raise io.Stop("Prior actual prompt/statement membership changed")
    return old_plan["fingerprints"], meter.spent

def make_plan(config, *, analysis_code=None):
    root,stage,manifest,policy = checked_stage(config,analysis_code=analysis_code)
    pipeline = stage/"data-pipeline"
    rows = intake.read_json(pipeline/"kyoto_raw_statements.json")
    ns = budget.legacy_functions(pipeline/"batch_analyze_council.py",None,
                                 pipeline/"master/councilors_kyoto.json")
    blocks = intake.read_json(config["original_raw"])["tenant_minutes"]
    built = contract.build(rows,blocks,intake.read_json(pipeline/"master/councilors_kyoto.json"),
                           ns["is_procedural_call"])
    selected = [t for t in built["threads"] if not ns["is_procedural_or_voting"](t)]
    if built["holds"]:
        raise io.Stop("Unknown speaker/role held: "+json.dumps(built["holds"],ensure_ascii=False))
    if not selected or len(selected)>budget.MAX_THREADS:
        raise io.Stop("Repair requires 1..100 reviewed threads; no implicit truncation")
    review = {}
    if config.get("prior_content_review"):
        prior_for_review = intake.read_json(config["prior_receipt"])
        review = reviewed_results(config,policy,prior_for_review["selected_keys"])
    for thread in selected:
        note = review.get(contract.thread_key(thread),{}).get("reanalysis_instruction")
        if note:
            # Separate correction guidance from verbatim source; retain the base prompt/model.
            thread["context_log"].append("【再解析時の確認指示（原文ではない）】\n"+note)
    new = {contract.thread_key(t):contract.fingerprint(ns,t) for t in selected}
    reuse,changes,prior_cost = {},[],Decimal("0")
    prior_sha = None
    prior_path = config.get("prior_receipt")
    if prior_path:
        prior = intake.read_json(prior_path)
        prior_sha = io.digest(Path(prior_path).read_bytes())
        if (policy.get("prior_receipt_sha256")!=prior_sha
            or prior.get("model")!=budget.MODEL
            or prior.get("status")!="selected_threads_complete_private_only"
            or prior.get("binding",{}).get("manifest_sha256")!=io.digest(intake.encode(manifest))):
            raise io.Stop("Prior success receipt/input/model binding mismatch")
        if prior.get("binding",{}).get("thread_revision"):
            if not review:
                raise io.Stop("Prior repair requires independent content review")
            old_fps, prior_cost = saved_repair_prior(config,policy,prior,ns,manifest)
        else:
            original_rows = intake.read_json(pipeline/"sagebase_crawled_data.json")
            old = [t for t in ns["build_debate_threads"](original_rows) if not ns["is_procedural_or_voting"](t)][:budget.MAX_THREADS]
            oldkeys = [contract.thread_key(t) for t in old]
            if oldkeys!=prior.get("selected_keys"):
                raise io.Stop("Original thread selection differs from prior receipt")
            recovered = json.loads(json.dumps(prior))
            meter = budget.Meter(policy,None,lambda:None)
            budget.restore_meter(meter,recovered,oldkeys)
            prior_cost = meter.spent
            charged = {a["thread_id"]:a for a in prior["api_attempts"] if a["status"]=="success"}
            old_fps = {contract.thread_key(t):old_fingerprint(ns,t,original_rows) for t in old}
            if any(fp["prompt_sha256"]!=charged[k]["prompt_sha256"] for k,fp in old_fps.items()):
                raise io.Stop("Reconstructed original prompt differs from charged request")
        for key,before in old_fps.items():
            after = new.get(key)
            rejected = review.get(key,{}).get("decision") == "invalidate"
            identical = not rejected and after is not None and same_analysis_input(before,after)
            if identical:
                reuse[key] = prior["results"][key]
            changes.append(dict(key=key,before=before,after=after,reuse=identical,
                disposition="invalidated_content_review" if rejected else "reuse_exact_model_input" if identical else "invalidated_changed_or_removed_thread",
                timeline_only_changed=bool(identical and before["statement_ids"]!=after["statement_ids"])))
    elif policy.get("prior_receipt_sha256") is not None:
        raise io.Stop("Unexpected prior receipt policy")
    plan = dict(schema=1,revision=contract.REVISION,revision_id=policy["revision_id"],
        meeting_key=manifest["meeting_key"],manifest_sha256=io.digest(intake.encode(manifest)),
        input_sha256=manifest["input_sha256"],original_raw_sha256=manifest["original_raw_sha256"],
        code_sha256=analysis_code if analysis_code is not None else code_hashes(),model=budget.MODEL,prior_receipt_sha256=prior_sha,
        prior_estimated_jpy=str(prior_cost),threads=selected,fingerprints=new,roles=built["roles"],
        boundary_positions=built["boundary_positions"],agenda_evidence=built["agenda_evidence"],
        content_review=review,changes=changes,reused_results=reuse,
        selected_keys=list(new),pending_keys=[k for k in new if k not in reuse],
        official_coverage="unknown",meeting_complete=False)
    # Match the on-disk representation (notably role keys) for exact resume checks.
    return json.loads(json.dumps(plan,ensure_ascii=False))

def plan_digest(plan):
    return io.digest(intake.encode(plan))

def output_path(config,plan):
    root = Path(config["private_root"])
    return root/("gemini-repair-"+plan["revision_id"]+"-"+plan_digest(plan)[:16])

def validate_attempts(plan,state,policy):
    if state.get("plan_sha256")!=plan_digest(plan) or state.get("reused_results")!=plan["reused_results"]:
        raise io.Stop("Repair checkpoint binding/reuse changed")
    if state.get("selected_keys")!=plan["selected_keys"]:
        raise io.Stop("Repair selected IDs changed")
    meter = budget.Meter(policy,None,lambda:None)
    meter.cap -= Decimal(plan["prior_estimated_jpy"])
    if meter.cap<=0:
        raise io.Stop("Prior spend exhausted the approved combined budget")
    newstate = dict(api_attempts=state.get("api_attempts",[]),
        results={k:v for k,v in state.get("results",{}).items() if k not in plan["reused_results"]},
        total_estimated_jpy=state["total_estimated_jpy"])
    recovered = budget.restore_meter(meter,newstate,plan["pending_keys"])
    expected = dict(plan["reused_results"],**recovered)
    if any(expected.get(k)!=v for k,v in state.get("results",{}).items()):
        raise io.Stop("Repair result lacks an exact reused or newly charged response")
    for entry in meter.entries:
        if entry["prompt_sha256"]!=plan["fingerprints"][entry["thread_id"]]["prompt_sha256"]:
            raise io.Stop("Charged repair prompt differs from planned prompt")
    return meter,expected

def run(config,*,resume=False):
    if config.get("quality_approval"):
        raise io.Stop("Quality exclusion is projection-only; no API execution")
    plan = make_plan(config)
    policy = intake.read_json(config["api_policy"])
    out = output_path(config,plan)
    if resume:
        if not out.is_dir() or intake.read_json(out/"plan.json")!=plan:
            raise io.Stop("No exact repair revision to resume")
    else:
        out.mkdir()
        io.write_json(out/"plan.json",plan)
    lock = out/"RUNNING.lock"
    with lock.open("xb") as f:f.write(io.utc().encode())
    client = None
    # Validate before replacing any existing receipt.
    try:
        if resume:
            state = intake.read_json(out/"receipt.json")
            meter,recovered = validate_attempts(plan,state,policy)
            state["results"] = recovered
        else:
            meter = budget.Meter(policy,None,lambda:None)
            meter.cap -= Decimal(plan["prior_estimated_jpy"])
            if meter.cap<=0:raise io.Stop("No remaining combined budget")
            state = dict(status="in_progress",model=budget.MODEL,plan_sha256=plan_digest(plan),
                selected_keys=plan["selected_keys"],reused_results=plan["reused_results"],
                results=dict(plan["reused_results"]),api_attempts=[],total_estimated_jpy="0",
                success=len(plan["reused_results"]),failure=0,official_coverage="unknown",
                meeting_complete=False,plan_file=str(out/"plan.json"),
                binding=dict(meeting_key=plan["meeting_key"],manifest_sha256=plan["manifest_sha256"],
                             thread_revision=contract.REVISION,plan_sha256=plan_digest(plan)))
        def persist():
            state.update(api_attempts=meter.entries,total_estimated_jpy=str(meter.spent),
                prior_estimated_jpy=plan["prior_estimated_jpy"],
                combined_estimated_jpy=str(meter.spent+Decimal(plan["prior_estimated_jpy"])),
                success=len(state["results"]))
            io.write_json(out/"receipt.json",state)
        meter.persist = persist
        stage = Path(config["prepared_stage"])
        ns = budget.legacy_functions(stage/"data-pipeline/batch_analyze_council.py",meter,
                                     stage/"data-pipeline/master/councilors_kyoto.json")
        persist()
        pending = [t for t in plan["threads"] if contract.thread_key(t) not in state["results"]]
        if pending:
            meter.send,client = budget.live_sender(policy.get("credential_path"))
        try:
            for thread in pending:
                key = contract.thread_key(thread)
                meter.thread_id = key
                value = budget.validate_result(ns["evaluate_thread_with_gemini"](thread))
                if meter.entries[-1]["prompt_sha256"]!=plan["fingerprints"][key]["prompt_sha256"]:
                    raise budget.BudgetStop("Unexpected emitted prompt")
                state["results"][key] = dict(status="analysis_success",analysis=value)
                meter.first_passed = True
                meter.pilot_passed = len([a for a in meter.entries if a["status"]=="success"])>=budget.PILOT
                persist()
                print("Repair success "+key+"; added estimate JPY "+str(meter.spent),flush=True)
            state["status"] = "selected_threads_complete_private_only"
            state["finished_utc"] = io.utc()
            persist()
            validate_attempts(plan,state,policy)
        except BaseException as exc:
            state.update(status="stopped_incomplete",failure=1,stop_reason=str(exc))
            persist()
            raise
    finally:
        if client is not None:client.close()
        lock.unlink()
    return out

def verified(config,receipt_path):
    plan = make_plan(config)
    return verified_plan(config,receipt_path,plan)


def verified_plan(config,receipt_path,plan):
    out = output_path(config,plan)
    if Path(receipt_path).resolve()!=(out/"receipt.json").resolve():
        raise io.Stop("Receipt outside exact repair revision")
    state = intake.read_json(receipt_path)
    if intake.read_json(out/"plan.json")!=plan or state.get("status")!="selected_threads_complete_private_only":
        raise io.Stop("Incomplete or changed repair")
    validate_attempts(plan,state,intake.read_json(config["api_policy"]))
    if set(state["results"])!=set(plan["selected_keys"]):
        raise io.Stop("Repair does not cover all reviewed threads")
    return plan,state


def quality_selection(approval,plan,state,receipt_sha256):
    """Select only a complete, explicit PM-reviewed partition of immutable results."""
    if (approval.get("scope")!="approved_partial_publication"
            or not approval.get("approval_reference")
            or approval.get("meeting_key")!=plan["meeting_key"]
            or approval.get("analysis_receipt_sha256")!=receipt_sha256
            or approval.get("plan_sha256")!=plan_digest(plan)
            or approval.get("input_sha256")!=plan["input_sha256"]
            or approval.get("original_raw_sha256")!=plan["original_raw_sha256"]):
        raise io.Stop("Quality approval input/meeting/receipt mismatch")
    threads={contract.thread_key(t):t for t in plan["threads"]}
    accepted=approval.get("accepted",{})
    exclusions=approval.get("exclusions",[])
    held={e.get("statement_id"):e for e in exclusions}
    if (not accepted or not held or len(held)!=len(exclusions)
            or set(accepted)&set(held) or set(accepted)|set(held)!=set(threads)):
        raise io.Stop("Unapproved, duplicate or incomplete quality exclusions")
    held_members=set()
    for key,entry in {**accepted,**held}.items():
        if entry.get("analysis_sha256")!=io.digest(intake.encode(state["results"][key]["analysis"])):
            raise io.Stop("Quality review refers to a different analysis result")
        if not entry.get("source_reference"):
            raise io.Stop("Quality review requires source evidence")
        if key in held:
            ids=[r["id"] for r in threads[key]["related_statements"]]
            if (entry.get("meeting_key")!=plan["meeting_key"] or not entry.get("reason")
                    or entry.get("source_statement_ids")!=ids):
                raise io.Stop("Excluded thread source scope/reason mismatch")
            held_members.update(ids)
    for key in accepted:
        if held_members & {r["id"] for r in threads[key]["related_statements"]}:
            raise io.Stop("Held source context contaminates a publishable thread")
    return dict(schema=1,publication_scope="partial",meeting_key=plan["meeting_key"],
                accepted_thread_ids=[k for k in plan["selected_keys"] if k in accepted],
                held_thread_ids=[k for k in plan["selected_keys"] if k in held],
                exclusions=exclusions,input_sha256=plan["input_sha256"],
                analysis_receipt_sha256=receipt_sha256,official_coverage="unknown",meeting_complete=False)


def publication_plan(config,receipt_path):
    if not config.get("quality_approval"):
        plan,state=verified(config,receipt_path)
        return plan,state,None
    path=io.safe_path(config["quality_approval"])
    if (io.digest(path.read_bytes())!=config.get("quality_approval_sha256")
            or config.get("projection_code_sha256")!=code_hashes()):
        raise io.Stop("Quality approval/projection code changed")
    approval=intake.read_json(path)
    # Reconstruct and verify the saved analysis under its immutable code identity.
    # No frozen code is executed and no API method is called. Any plan drift stops.
    runtime=io.safe_path(config["analysis_runtime"])
    identity={name:io.digest((runtime/name).read_bytes()) for name in CODE_FILES}
    if io.digest(Path(config["api_policy"]).read_bytes())!=approval.get("api_policy_sha256"):
        raise io.Stop("Saved analysis policy changed")
    plan=make_plan(config,analysis_code=identity)
    plan,state=verified_plan(config,receipt_path,plan)
    selection=quality_selection(approval,plan,state,io.digest(Path(receipt_path).read_bytes()))
    selection["quality_approval_sha256"]=config["quality_approval_sha256"]
    return plan,state,selection

def project(config,receipt_path):
    # A new immutable private candidate; never overwrite the previous candidate/history.
    import kyoto_continuation as continuation
    plan,state,_ = publication_plan(config,receipt_path)
    return continuation.private_project(config["prepared_stage"],receipt_path,
        config["public_summary"],Path(config["private_root"]),repair_config=config)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation",choices=("plan","run","project"))
    parser.add_argument("--config",required=True)
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--receipt")
    args=parser.parse_args()
    config=intake.read_json(args.config)
    try:
        if args.operation=="plan":
            plan=make_plan(config)
            print(json.dumps(dict(selected=len(plan["selected_keys"]),reuse=len(plan["reused_results"]),
                pending=len(plan["pending_keys"]),plan_sha256=plan_digest(plan)),ensure_ascii=False))
        elif args.operation=="run":print(run(config,resume=args.resume))
        else:print(project(config,args.receipt))
    except (Exception,budget.BudgetStop) as exc:
        print("STOP: "+str(exc));raise SystemExit(1)
