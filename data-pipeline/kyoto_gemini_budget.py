"""Private one-meeting Gemini budget boundary; no API calls on import.
Legacy prompts/classifiers are extracted unchanged; the old analyzer main is never run.
Requires a committed kyoto_new_meetings.prepare stage and explicit runtime evidence.
"""
import argparse
import ast
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

import kyoto_council_list_guard as files
from kyoto_new_meetings import PINNED_CODE, encode, _private_root, read_json

MODEL = "gemini-3.5-flash-lite"
MAX_THREADS = 100
PILOT = 10
CAP = Decimal("1000")
INPUT_BOUND = 1048576
OUTPUT_BOUND = 65536
# Conservative reserve allows the full output bound separately for thoughts too.
GENERATED_BOUND = 2 * OUTPUT_BOUND


class BudgetStop(BaseException):
    """Must bypass legacy except Exception/retry/failure-as-procedural behavior."""


def decimal(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise BudgetStop("Unknown/nonexact price or currency conversion")
    d = Decimal(value)
    if not d.is_finite() or d <= 0:
        raise BudgetStop("Invalid price or conversion")
    return d


def policy_check(policy):
    if policy.get("api_go") is not True or policy.get("model") != MODEL:
        raise BudgetStop("Model/API GO mismatch")
    if policy.get("target_confirmed") is not True:
        raise BudgetStop("New analysis target is not confirmed")
    if (policy.get("trial_mode") not in ("retrospective_private", "new_meeting_private")
            or policy.get("official_coverage") != "unknown"
            or policy.get("estimated_budget_accepted") is not True):
        raise BudgetStop("PM-approved retrospective scope and estimate policy required")
    for field in ("target_review", "price_reference", "fx_reference", "sdk_reference"):
        if not isinstance(policy.get(field), str) or not policy[field].strip():
            raise BudgetStop("Missing runtime evidence: " + field)
    if decimal(policy.get("budget_stop_jpy")) > CAP:
        raise BudgetStop("Stop target exceeds approved trial budget")
    if policy.get("sdk_usage_supported") is not True:
        raise BudgetStop("SDK cannot preserve required usage fields")
    stamp = datetime.fromisoformat(policy.get("pricing_checked_utc", ""))
    if stamp.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-stamp).total_seconds() <= 86400:
        raise BudgetStop("Runtime rates must be checked within 24 hours")
    inp, out, fx = (decimal(policy.get(k)) for k in
                   ("input_usd_per_million", "output_usd_per_million", "jpy_per_usd_upper"))
    return inp, out, fx


def usage_counts(usage):
    fields = ("prompt_token_count", "candidates_token_count", "thoughts_token_count", "total_token_count")
    values = {k: usage.get(k) for k in fields}
    total = values["total_token_count"]
    if type(total) is not int or total <= 0:
        raise BudgetStop("Total usage missing; monitoring cannot continue")
    parts = [values[k] for k in fields[:3]]
    if any(v is not None and (type(v) is not int or v < 0) for v in parts):
        raise BudgetStop("Invalid usage breakdown")
    if sum(v for v in parts if v is not None) > total:
        raise BudgetStop("Usage breakdown exceeds total")
    complete = all(v is not None for v in parts)
    if complete and total != sum(parts):
        raise BudgetStop("Usage total inconsistent")
    if total > INPUT_BOUND + GENERATED_BOUND or (complete and
            (parts[0] > INPUT_BOUND or parts[1] + parts[2] > GENERATED_BOUND)):
        raise BudgetStop("Usage exceeded reserved model bounds")
    values.update(cost_basis="measured_breakdown" if complete else "total_at_highest_rate",
                  billable_input_tokens=parts[0] if complete else 0,
                  billable_generated_tokens=parts[1]+parts[2] if complete else total)
    return values


def validate_result(value):
    if not isinstance(value, dict):
        raise BudgetStop("Analysis response is not an object")
    for k in ("category", "summary", "reasoning"):
        if not isinstance(value.get(k), str) or not value[k].strip():
            raise BudgetStop("Missing analysis field: " + k)
    if not isinstance(value.get("keywords"), list) or any(not isinstance(k, str) for k in value["keywords"]):
        raise BudgetStop("Invalid keywords")
    scores = value.get("scores")
    if not isinstance(scores, dict) or set(scores) != {"evidence","solution","local_focus","constructive"}:
        raise BudgetStop("Invalid score schema")
    if any(type(s) is not int or not 0 <= s <= 5 for s in scores.values()):
        raise BudgetStop("Invalid score values")
    return value


class Meter:
    def __init__(self, policy, send, persist):
        self.inp, self.out, self.fx = policy_check(policy)
        self.send, self.persist = send, persist
        self.cap = min(CAP, decimal(policy["budget_stop_jpy"]))
        self.spent = Decimal("0")
        self.entries = []
        self.halted = False
        self.thread_id = None
        self.threads = set()
        self.pilot_passed = False
        self.first_passed = False

    def cost(self, inp, output, thoughts):
        return (Decimal(inp)*self.inp + Decimal(output+thoughts)*self.out)/Decimal(1000000)*self.fx

    def estimate(self, n):
        reserve=self.cost(INPUT_BOUND,OUTPUT_BOUND,OUTPUT_BOUND)
        return {"threads":n,"next_call_upper_estimate_jpy":str(reserve),
                "all_calls_worst_case_jpy":str(reserve*n),
                "policy":"reserve next call before sending; actual totals settle after each response",
                "invoice_guarantee":False,"currency_note":"Planning conversion, not an invoice exchange rate"}

    def generate_content(self, prompt, generation_config):
        if self.halted:
            raise BudgetStop("Previous failure/unknown usage prohibits additional calls")
        if not isinstance(prompt,str) or not prompt or self.thread_id is None:
            raise BudgetStop("Invalid prompt/thread")
        new_thread=self.thread_id not in self.threads
        if new_thread and len(self.threads)>=1 and not self.first_passed:
            raise BudgetStop("First-response JSON/usage gate")
        if new_thread and (len(self.threads)>=MAX_THREADS or
                           len(self.threads)>=PILOT and not self.pilot_passed):
            raise BudgetStop("Pilot gate or 100-thread cap")
        reserve=self.cost(INPUT_BOUND,OUTPUT_BOUND,OUTPUT_BOUND)
        if self.spent+reserve>self.cap:
            self.halted=True
            self.persist()
            raise BudgetStop("Next request could exceed remaining budget")
        attempt=sum(e["thread_id"]==self.thread_id for e in self.entries)+1
        if attempt>4:
            raise BudgetStop("Attempt cap")
        self.threads.add(self.thread_id)
        entry=dict(thread_id=self.thread_id,attempt=attempt,status="reserved",
                   prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                   rates=dict(input_usd_per_million=str(self.inp),output_usd_per_million=str(self.out),
                              jpy_per_usd_upper=str(self.fx)),
                   reserved_jpy=str(reserve),started_utc=files.utc())
        self.entries.append(entry)
        self.persist() # If persistence fails, the API is not called.
        try:
            response=self.send(prompt, generation_config)
        except BaseException:
            entry.update(status="api_failed_usage_unknown",usage=None,cost_jpy=None)
            self.halted=True
            self.persist()
            raise BudgetStop("API failed; billing unknown, no retries") from None
        try:
            entry.update(response_model=response.get("model"),finish_reason=response.get("finish_reason"),
                         raw_usage=response.get("usage"))
            usage=usage_counts(response["usage"])
            cost=self.cost(usage["billable_input_tokens"],usage["billable_generated_tokens"],0)
            self.spent+=cost
            entry.update(usage=usage,cost_jpy=str(cost),cumulative_jpy=str(self.spent),status="usage_recorded")
            self.persist()
            if (response.get("model")!=MODEL or response.get("finish_reason")!="STOP"
                    or self.spent>self.cap):
                raise BudgetStop("Unexpected model/finish reason/cost")
            result=validate_result(json.loads(response["text"]))
            # Save result and charged usage together before returning to the caller.
            # A restart can recover this successful call without sending it again.
            entry.update(status="success",analysis=result,completed_utc=files.utc())
            self.persist()
            return SimpleNamespace(text=json.dumps(result,ensure_ascii=False))
        except BaseException:
            entry["status"]="invalid_response_or_usage"
            self.halted=True
            self.persist()
            raise BudgetStop("Invalid response/usage; no further calls") from None


def legacy_functions(path, model, master):
    raw=path.read_bytes()
    lf=raw.replace(b"\r\n",b"\n")
    blob=hashlib.sha1(b"blob "+str(len(lf)).encode()+b"\0"+lf).hexdigest()
    if blob!=PINNED_CODE["batch_analyze_council.py"]:
        raise BudgetStop("Legacy analyzer differs from accepted code")
    tree=ast.parse(raw.decode("utf-8-sig"))
    names={"get_official_councilors","clean_name","find_meeting_chair","is_procedural_call",
           "build_debate_threads","is_procedural_or_voting","evaluate_thread_with_gemini"}
    body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in body}!=names: raise BudgetStop("Legacy function set mismatch")
    ns=dict(os=os,re=re,json=json,MASTER_JSON=str(master),model=model,
            genai=SimpleNamespace(GenerationConfig=lambda **kw:kw),
            time=SimpleNamespace(sleep=lambda n: (_ for _ in ()).throw(BudgetStop("Legacy retry blocked"))))
    exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),str(path),"exec"),ns)
    ns["VALID_COUNCILORS"]=ns["get_official_councilors"]()
    if not ns["VALID_COUNCILORS"]: raise BudgetStop("Empty private master")
    return ns


def live_sender(credential_path=None):
    # Created only after target, stage, pricing and billing gates pass.
    # Existing installed SDK; no installation, model substitution or legacy main.
    from google import genai
    from google.genai import types
    if "thoughts_token_count" not in types.GenerateContentResponseUsageMetadata.model_fields:
        raise BudgetStop("Installed SDK lacks thought usage")
    key=os.environ.get("GEMINI_API_KEY")
    if not key and credential_path:
        # Use the existing credential only in memory; never copy .env or log values.
        from dotenv import dotenv_values
        key=dotenv_values(credential_path).get("GEMINI_API_KEY")
    if not key: raise BudgetStop("API credential is not present in process environment")
    client=genai.Client(api_key=key,vertexai=False,http_options=types.HttpOptions(
        timeout=60000,retry_options=types.HttpRetryOptions(attempts=1),
        client_args={"follow_redirects":False,"trust_env":False}))
    def send(prompt, config):
        response=client.models.generate_content(model=MODEL,contents=prompt,
            config=types.GenerateContentConfig(**config,max_output_tokens=OUTPUT_BOUND))
        usage=response.usage_metadata
        return {"text":response.text,"model":response.model_version,
                "finish_reason":str(response.candidates[0].finish_reason.value) if response.candidates else None,
                "usage":usage.model_dump() if usage else {}}
    return send,client


def restore_meter(meter, state, selected_keys, retry_failed=False):
    """Recover only accounted attempts. An interrupted/unknown bill stops closed."""
    if set(state.get("results", {})) - set(selected_keys):
        raise BudgetStop("Checkpoint contains another input/thread")
    entries = state.get("api_attempts", [])
    results = {}
    spent = Decimal("0")
    counts = {}
    failed = set()
    for entry in entries:
        key = entry.get("thread_id")
        if key not in selected_keys or key in results:
            raise BudgetStop("Unknown thread or success was resubmitted")
        counts[key] = counts.get(key, 0) + 1
        if entry.get("attempt") != counts[key] or counts[key] > 4:
            raise BudgetStop("Attempt history mismatch")
        if entry.get("status") not in ("success", "invalid_response_or_usage"):
            raise BudgetStop("Reserved/interrupted/API-error billing unknown; manual reconciliation required")
        usage=usage_counts(entry.get("raw_usage") or {})
        rates=entry.get("rates",{})
        inp,out,fx=(decimal(rates.get(k)) for k in
                    ("input_usd_per_million","output_usd_per_million","jpy_per_usd_upper"))
        cost = decimal(entry.get("cost_jpy"))
        expected=(Decimal(usage["billable_input_tokens"])*inp+
                  Decimal(usage["billable_generated_tokens"])*out)*fx/Decimal(1000000)
        if cost!=expected or entry.get("usage")!=usage:
            raise BudgetStop("Receipt cost differs from measured usage and rates")
        spent += cost
        if Decimal(entry.get("cumulative_jpy", "-1")) != spent:
            raise BudgetStop("Cumulative cost mismatch")
        if entry["status"] == "success":
            value = entry.get("analysis")
            if value is None:
                value = state.get("results", {}).get(key, {}).get("analysis")
            validate_result(value)
            results[key] = dict(status="analysis_success", analysis=value)
            failed.discard(key)
        else:
            failed.add(key)
    if any(state["results"].get(k) != v for k,v in results.items() if k in state["results"]):
        raise BudgetStop("Checkpoint result differs from durable response")
    if set(state.get("results", {})) - set(results):
        raise BudgetStop("Success lacks a charged API receipt")
    if spent != Decimal(state.get("total_estimated_jpy", "-1")) or spent > meter.cap:
        raise BudgetStop("Checkpoint cost/cap mismatch")
    if failed and not retry_failed:
        raise BudgetStop("Known-cost failures need explicit retry_failed; successful threads will be skipped")
    meter.entries, meter.spent, meter.threads = entries, spent, set(counts)
    meter.first_passed = bool(results)
    meter.pilot_passed = len(results) >= PILOT
    state["results"] = results
    state["success"] = len(results)
    return results


def run(stage,policy_path,public_summary,private_root,*,resume=False,retry_failed=False):
    root=_private_root(private_root,public_summary)
    if not root.resolve().is_relative_to(files.ARTIFACT.resolve()):
        raise BudgetStop("Output must stay in Codex A's existing private root")
    stage=files.safe_path(stage)
    if stage.parent.resolve()!=root.resolve() or not stage.name.startswith("ready-"):
        raise BudgetStop("Input must be a committed private prepare stage")
    manifest=read_json(stage/"manifest.json")
    ready=read_json(stage/"READY.json")
    if ready!={"status":"prepared_only","manifest_sha256":hashlib.sha256(encode(manifest)).hexdigest()}:
        raise BudgetStop("Invalid prepared stage")
    policy=read_json(policy_path)
    policy_check(policy)
    modes={"approved_retrospective_trial":"retrospective_private","confirmed_new_meeting":"new_meeting_private"}
    if (manifest.get("decision") not in modes
            or policy.get("trial_mode")!=modes.get(manifest.get("decision"))
            or policy.get("meeting_key")!=manifest.get("meeting_key")
            or policy.get("input_sha256")!=manifest.get("input_sha256")
            or policy.get("manifest_sha256")!=ready["manifest_sha256"]):
        raise BudgetStop("Policy not bound to accepted one-meeting input")
    for name,h in manifest["files"].items():
        p=files.safe_path(stage/name)
        if not p.resolve().is_relative_to(stage.resolve()) or files.digest(p.read_bytes())!=h:
            raise BudgetStop("Input/master/code hash mismatch")
    pipeline=stage/"data-pipeline"
    rows=read_json(pipeline/"sagebase_crawled_data.json")
    binding=dict(meeting_key=manifest["meeting_key"],input_sha256=manifest["input_sha256"],
                 manifest_sha256=ready["manifest_sha256"],model=MODEL,
                 files=manifest["files"],budget_stop_jpy=policy["budget_stop_jpy"])
    output=root/("gemini-resumable-"+files.digest(encode(binding))[:20])
    if resume:
        if not output.is_dir(): raise BudgetStop("No prior execution for this exact binding")
    else:
        output.mkdir(exist_ok=False)
    # No concurrent callers can spend against the same receipt. A stale lock is held.
    lock=output/"RUNNING.lock"
    with lock.open("xb") as f: f.write(files.utc().encode())
    state=dict(status="in_progress",model=MODEL,api_attempts=[],results={},skipped={},
               success=0,failure=0,total_estimated_jpy="0",publish=False,pilot_passed=False,
               first_passed=False,official_coverage="unknown",trial_mode=policy["trial_mode"],
               binding=binding)
    meter=None
    def persist():
        if meter is not None:
            state.update(api_attempts=meter.entries,total_estimated_jpy=str(meter.spent),
                         pilot_passed=meter.pilot_passed,first_passed=meter.first_passed)
        files.write_json(output/"receipt.json",state)
        files.write_json(output/"checkpoint.json",state["results"])
    client=None
    try:
        meter=Meter(policy,None,persist)
        ns=legacy_functions(pipeline/"batch_analyze_council.py",meter,pipeline/"master/councilors_kyoto.json")
        all_threads=ns["build_debate_threads"](rows)
        selected=[]
        for thread in all_threads:
            mid=thread["main_statement"]
            key=str(mid["meeting_id"])+"_"+str(mid["sequence_number"])
            if key in state["skipped"] or key in {k for k,t in selected}:
                raise BudgetStop("Duplicate thread identity")
            if ns["is_procedural_or_voting"](thread):
                state["skipped"][key]="non_question_by_existing_rules"
            else: selected.append((key,thread))
        state["deferred_threads"]=max(0,len(selected)-MAX_THREADS)
        selected=selected[:MAX_THREADS]
        selected_keys=[k for k,t in selected]
        if resume:
            saved=read_json(output/"receipt.json")
            if saved.get("binding")!=binding or saved.get("selected_keys")!=selected_keys:
                raise BudgetStop("Resume input/code/model/selected-thread binding mismatch")
            # Do not overwrite any receipt until its full history has been validated.
            restore_meter(meter,saved,selected_keys,retry_failed)
            state=saved
            state["status"]="in_progress"
            state.pop("stop_reason",None)
        state["selected_keys"]=selected_keys
        state["selected_threads"]=len(selected)
        state["estimate"]=meter.estimate(len(selected))
        persist()
        pending=[(k,t) for k,t in selected if k not in state["results"]]
        if pending:
            meter.send,client=live_sender(policy.get("credential_path"))
        for key,thread in pending:
            meter.thread_id=key
            try:
                result=ns["evaluate_thread_with_gemini"](thread)
                validate_result(result)
            except BaseException:
                state["failure"]+=1
                raise BudgetStop("Analysis failed; entire trial is incomplete") from None
            state["results"][key]=dict(status="analysis_success",analysis=result)
            state["success"]+=1
            if state["success"]==1:
                if meter.halted or meter.entries[-1]["status"]!="success":
                    raise BudgetStop("First response validation failed")
                meter.first_passed=True
                print("First response PASS; usage recorded",flush=True)
            if state["success"]==PILOT:
                if meter.halted or any(k not in state["results"] for k in selected_keys[:PILOT]):
                    raise BudgetStop("Pilot usage/result check failed")
                meter.pilot_passed=True
                print("Pilot 10 PASS; cumulative estimate JPY "+str(meter.spent),flush=True)
            persist()
            print("Completed "+str(state["success"])+"/"+str(len(selected))+"; estimate JPY "+str(meter.spent),flush=True)
        state["status"]="selected_threads_complete_private_only"
        state["accepted_input_analysis_complete"]=state["deferred_threads"]==0
        state["meeting_complete"]=False # Official source completeness remains unknown.
        # No generator, timeline writer, assemble or publication is invoked here.
    except BaseException as exc:
        state["status"]="stopped_incomplete"
        state["stop_reason"]=str(exc)
        raise
    finally:
        state["finished_utc"]=files.utc()
        try:
            # A rejected resume must not replace the original evidence with empty state.
            if not resume or state.get("selected_keys") is not None: persist()
        finally:
            if client is not None: client.close()
            lock.unlink()
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for option in ("stage","policy","public-summary","private-root"):
        p.add_argument("--"+option,required=True)
    p.add_argument("--resume",action="store_true")
    p.add_argument("--retry-failed",action="store_true")
    a=p.parse_args()
    try: print(run(a.stage,a.policy,a.public_summary,a.private_root,resume=a.resume,retry_failed=a.retry_failed))
    except (BudgetStop,Exception) as exc:
        print("STOP: "+str(exc))
        raise SystemExit(1)
