"""Future weekly HTML+PDF entry; refuses activation before HTML autorun proof.

Uses two existing phase states. No publishing, retry, or scheduler mutation.
"""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from . import weekly, pdf_watch
from .acquire import assert_owner_only
from .engine import PrivateOutput
from .operations import load
from .projection import Hold


def verify_autorun(receipt, now=None):
    """Require pinned scheduler proof, not a manual run or a calendar date.

    The controlled one-time proof disables demand starts before the trigger.
    Unchanged task XML and the scheduler observation bind its result to that
    trigger. Missing history is never replaced by a successful manual run.
    """
    now=now or datetime.now(timezone.utc)
    try:
        due=datetime.fromisoformat(receipt['scheduled_for'])
        started=datetime.fromisoformat(receipt['started_at'])
        finished=datetime.fromisoformat(receipt['finished_at'])
        evidence=receipt['scheduler_evidence']
        before=weekly.pinned_input(evidence['task_before']).read_text(encoding='utf-8-sig')
        after=weekly.pinned_input(evidence['task_after']).read_text(encoding='utf-8-sig')
        observation=load(weekly.pinned_input(evidence['observation']))
        task=ET.fromstring(before)
        ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
        value=lambda path: task.findtext(path, namespaces=ns)
        triggers=task.findall('t:Triggers/*',ns)
        selected=[t for t in triggers if t.get('id')==receipt['trigger_id']]
        trigger=selected[0] if len(selected)==1 else None
        task_name='GikaiMikata-Kyoto-Mayor-Weekly'
        valid=(before==after and receipt['state']=='scheduled_run_verified'
               and receipt['task_name']==task_name and observation['task_name']==task_name
               and value('t:RegistrationInfo/t:URI')=='\\'+task_name
               and value('t:Settings/t:AllowStartOnDemand')=='false'
               and value('t:Principals/t:Principal/t:LogonType')=='InteractiveToken'
               and task.find('t:Settings/t:RestartOnFailure',ns) is None
               and trigger is not None and trigger.tag.endswith('}TimeTrigger')
               and datetime.fromisoformat(trigger.findtext('t:StartBoundary',namespaces=ns))==due
               and trigger.find('t:Repetition',ns) is None
               and all(t is trigger or (t.tag.endswith('}CalendarTrigger') and
                   datetime.fromisoformat(t.findtext('t:StartBoundary',namespaces=ns))>finished) for t in triggers)
               and datetime.fromisoformat(observation['registered_at'])<due
               and datetime.fromisoformat(observation['last_run'])==started
               and datetime.fromisoformat(observation['checked_at'])>=finished
               and datetime.fromisoformat(observation['checked_at'])<=now
               and observation['last_result']==0 and observation['state']=='Ready'
               and receipt['task_last_result']==0 and due<=started<=due+timedelta(minutes=2)
               and started<=finished<=started+timedelta(minutes=5) and finished<=now
               and receipt['html_get_requests']==3 and receipt['public_writes']==0
               and receipt['cas_integrity_pass'] is True and receipt['state_consistent'] is True)
    except (KeyError,TypeError,ValueError,OSError,ET.ParseError): valid=False
    if not valid: raise Hold('Scheduled HTML run proof missing or inconsistent; keep existing task unchanged')


def validate_combined(html_runtime,pdf_runtime,html_config,pdf_plan):
    sources=weekly.validate_plan(html_config)
    if Path(html_runtime['state_root']).resolve()==Path(pdf_runtime['state_root']).resolve():
        raise Hold('HTML and PDF state must be separate')
    if Path(html_runtime['snapshot_root']).resolve()!=Path(pdf_runtime['snapshot_root']).resolve():
        raise Hold('Use the existing shared P1 CAS')
    if html_runtime['baseline']['sha256']!=pdf_runtime['baseline']['sha256']:
        raise Hold('Phase public baselines differ')
    if len(sources)+pdf_plan['max_requests']>6 or sum(s['max_bytes'] for s in sources)+pdf_plan['max_received_bytes']>31457280:
        raise Hold('Combined 6 GET / 30 MiB cap exceeded')


def execute(root,html_runtime,pdf_runtime,*,day=None):
    """One durable daily intent; uncertain/failed runs cannot automatically retry."""
    day=day or datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    # Reject arbitrary path components in a manually supplied/test day.
    if datetime.strptime(day,'%Y-%m-%d').date().isoformat()!=day: raise Hold('Invalid daily slot')
    with weekly.single_run(root):
        runs=root/'runs'; runs.mkdir(exist_ok=True); output=runs/day
        try: output.mkdir()
        except FileExistsError as exc: raise Hold('Daily combined run already attempted; no retry') from exc
        out=PrivateOutput(output)
        out.json('intent.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'max_get':6,'max_bytes':31457280})
        results={}
        try:
            results['html']=weekly.run(html_runtime)
            if not results['html']['state_advanced']: raise Hold('HTML phase stopped; PDF not attempted')
            results['pdf']=pdf_watch.run(pdf_runtime)
            if results['pdf']['state']=='stopped': raise Hold('PDF phase stopped; successful HTML state retained')
            result={'state':'success','finished_at':datetime.now(timezone.utc).isoformat(),'phases':results,'public_writes':0}
            out.json('result.json',result)
            weekly.atomic_json(root/'last_success.json',result)
            return result
        except Exception as exc:
            out.json('failure.json',{'state':'stopped','reason':str(exc),'phases':results,
                'html_success_retained':bool(results.get('html',{}).get('state_advanced')),'public_writes':0})
            raise


def run(runtime):
    root=PrivateOutput(runtime['state_root']).root; assert_owner_only(root)
    gate=load(weekly.pinned_input(runtime['autorun_verification'])); verify_autorun(gate)
    html_runtime=load(weekly.pinned_input(runtime['html_runtime']))
    pdf_runtime=load(weekly.pinned_input(runtime['pdf_runtime']))
    for spec in runtime['code_files']: weekly.pinned_input(spec)
    if not any(Path(s['path']).resolve()==Path(__file__).resolve() for s in runtime['code_files']): raise Hold('Bundle entry must be pinned')
    _,_,html_config=weekly.validate_runtime(html_runtime,reuse_saved=False)
    _,_,_,pdf_plan=pdf_watch.validate_runtime(pdf_runtime,reuse_saved=False)
    validate_combined(html_runtime,pdf_runtime,html_config,pdf_plan)
    return execute(root,html_runtime,pdf_runtime)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--runtime',required=True); a=p.parse_args(); runtime=load(a.runtime)
    if os.name=='nt': os.environ['MAYOR_PWSH_EXE']=runtime['powershell_exe']
    assert_owner_only(a.runtime); print(json.dumps(run(runtime),ensure_ascii=False))

if __name__=='__main__': main()
