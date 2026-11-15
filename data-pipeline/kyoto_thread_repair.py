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

def checked_stage(config):
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
        or policy.get("thread_code_sha256")!=code_hashes()
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

def make_plan(config):
    root,stage,manifest,policy = checked_stage(config)
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
        for thread in old:
            key = contract.thread_key(thread)
            before = old_fingerprint(ns,thread,original_rows)
            after = new.get(key)
            if before["prompt_sha256"]!=charged[key]["prompt_sha256"]:
                raise io.Stop("Reconstructed original prompt differs from charged request")
            identical = after is not None and same_analysis_input(before,after)
            if identical:
                reuse[key] = prior["results"][key]
            changes.append(dict(key=key,before=before,after=after,reuse=identical,
                disposition="reuse_exact_model_input" if identical else "invalidated_changed_or_removed_thread",
                timeline_only_changed=bool(identical and before["statement_ids"]!=after["statement_ids"])))
    elif policy.get("prior_receipt_sha256") is not None:
        raise io.Stop("Unexpected prior receipt policy")
    plan = dict(schema=1,revision=contract.REVISION,revision_id=policy["revision_id"],
        meeting_key=manifest["meeting_key"],manifest_sha256=io.digest(intake.encode(manifest)),
        input_sha256=manifest["input_sha256"],original_raw_sha256=manifest["original_raw_sha256"],
        code_sha256=code_hashes(),model=budget.MODEL,prior_receipt_sha256=prior_sha,
        prior_estimated_jpy=str(prior_cost),threads=selected,fingerprints=new,roles=built["roles"],
        boundary_positions=built["boundary_positions"],changes=changes,reused_results=reuse,
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

def project(config,receipt_path):
    # A new immutable private candidate; never overwrite the previous candidate/history.
    import kyoto_continuation as continuation
    plan,state = verified(config,receipt_path)
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
