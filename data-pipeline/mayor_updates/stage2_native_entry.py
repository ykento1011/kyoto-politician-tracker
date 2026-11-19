"""Native entry assembly. All live source gates must be privately activated.

The representative pre-arms the already open local admin PS5.1 console. It starts
an independent guardian; the non-elevated controller never elevates or impersonates.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time

from . import stage2_acceptance as core
from . import stage2_os_adapter as native
from .launch_contract import FixedLaunch
from .projection import Hold
from .stage2_windows_identity import WindowsIdentity, FixedDnsQuery
from .stage2_guard import _record


def validate_runtime(value):
    required={'schema_version','plan','nonce','private_root','acceptance_root','mailbox_root',
              'code_root','controller_code_pins','native_parameters_path','native_parameters_sha256',
              'controller_image','administrator','dns_image','system_tools','resolvers','interface',
              'recovery_text','wfp_sublayer','preblock_proof'}
    core.require(type(value) is dict and set(value)==required and value['schema_version']==1,
                 'Exact native runtime schema')
    core.require(re.fullmatch('[0-9a-f]{64}',value['nonce']) and
                 re.fullmatch('[0-9a-f]{64}',value['native_parameters_sha256']) and
                 type(value['resolvers']) is list and value['resolvers'], 'Native runtime binding')
    from ipaddress import ip_address
    for server in value['resolvers']:core.require(str(ip_address(server))==server,'Canonical resolver')
    core.require(value['plan']['audit_seconds']==60 and value['plan']['event_limit']==64 and
                 value['plan']['sid'].endswith('-1004'), 'Native acceptance limits')
    core.require(value['controller_image']['path'].casefold()==os.path.realpath(os.sys.executable).casefold(),
                 'Wrong controller interpreter')
    return value


def recovery_text(runtime_path, runtime_sha, runtime, actor):
    """Text only. No policy is executed and no operator acknowledgement invented."""
    script=Path(runtime['code_root'])/'scripts/Stage2AdminBridge.ps1'
    for path in (str(script),str(runtime_path)):
        core.require(not re.search(r"[\r\n\x00']",path),'Fixed recovery quoting')
    return (
        'LOCAL RECOVERY — retain this text on this PC before auditing. No network needed.\n'
        'If Python/WinAPI/broker hangs, the separate admin guardian requests stop at 45s.\n'
        'Do not wait for ChatGPT/GitHub. Use another local administrator PS5.1 console.\n'
        'First, audit-only fallback (original success/failure both OFF):\n'
        "& 'C:\\Windows\\System32\\auditpol.exe' /set '/subcategory:{0CCE9226-69AE-11D9-BED3-505054503030}' /failure:disable\n"
        "& 'C:\\Windows\\System32\\auditpol.exe' /get '/subcategory:{0CCE9226-69AE-11D9-BED3-505054503030}' /r\n"
        "& 'C:\\Windows\\System32\\auditpol.exe' /get '/subcategory:{0CCE9225-69AE-11D9-BED3-505054503030}' /r\n"
        'Both must report NO AUDITING. If a command fails/hangs, restoration is HOLD.\n'
        'Do NOT reset/import all Firewall/audit settings, reboot automatically or leave unattended.\n'
        'Verified parent stop and audit recovery (never blindly kill a PID):\n'
        f"& '{script}' -Mode Recover -RuntimePath '{runtime_path}' -RuntimeSha256 '{runtime_sha}' -StopActor\n"
        f"Controller PID={actor['pid']}; FILETIME start={actor['started']}; image={actor['image']}\n"
        'Parent exit/Job kill-on-close alone is NOT independent proof that every possible\n'
        'unassigned suspended worker or pending DNS operation is gone. Keep the two Block\n'
        'rules on unknown termination. Inspect locally; no automatic Firewall recovery.\n'
        'Only after all target descendants/pending DNS work are independently confirmed stopped:\n'
        f"& '{script}' -Mode Recover -RuntimePath '{runtime_path}' -RuntimeSha256 '{runtime_sha}' -RestoreFirewall\n"
        'That path checks the exact remaining delta, asks EXIT-CONFIRMED and removes\n'
        'Inbound then Outbound. It never removes a changed/foreign rule or a whole group.\n'
    )


def run(runtime_path, runtime_sha):
    # No runtime file, interpreter, PS process, IPC, audit or socket is touched
    # until both *source* gates are true. Runtime JSON cannot enable these gates.
    core.require(native.LIVE_OS_ADAPTER_ENABLED is True and core.LIVE_ACCEPTANCE_ENABLED is True,
                 'Native OS adapter/acceptance source-disabled')
    core.require(os.name=='nt' and re.fullmatch('[0-9a-f]{64}',runtime_sha),'Windows/runtime SHA')
    raw=Path(runtime_path).read_bytes()
    core.require(len(raw)<=65536 and sha256(raw).hexdigest()==runtime_sha,'Runtime bytes differ')
    value=validate_runtime(native.read_json(runtime_path,65536))
    parameters_path=Path(value['native_parameters_path'])
    body=parameters_path.read_bytes()
    core.require(sha256(body).hexdigest()==value['native_parameters_sha256'],'Native parameters PIN')
    parameters=native.read_json(parameters_path,65536)
    core.require(parameters['run_id']==value['plan']['run_id'] and
                 parameters['plan_sha256']==value['plan']['native_plan_sha256'],'Native plan differs')
    spec=FixedLaunch(**{**parameters['worker_spec'],'arguments':tuple(parameters['worker_spec']['arguments'])})
    meta=WindowsIdentity(spec,{'administrator':value['administrator']})
    meta.check_path(runtime_path)
    meta.check_path(parameters_path)
    actor=meta.own()  # exact signed/locked interpreter, non-elevated SID1004
    core.require(actor['sid']==value['plan']['sid'],'Controller actor differs')
    for relative,pin in value['controller_code_pins'].items():
        path=Path(value['code_root'])/relative
        core.require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'Source path')
        meta.check_path(path)
        core.require(sha256(path.read_bytes()).hexdigest()==pin,'Controller dependency PIN')
    state=Path(value['acceptance_root'])
    core.require(state == parameters_path.parent/('integrated_acceptance_'+parameters['run_id']),
                 'Acceptance state outside fixed Stage 2 parent')
    meta.check_path(state.parent)
    core.require(not state.exists(),'Consumed acceptance root; never reset/retry')
    native_root=Path(parameters['run_root'])
    core.require(native_root == parameters_path.parent/'native_run_once','Unexpected native state')
    meta.check_path(native_root)
    core.require(not any(native_root.iterdir()),'Native worker run already consumed')
    state.mkdir(exist_ok=False);meta.check_path(state)
    mailbox=Path(value['mailbox_root'])
    core.require(mailbox.parent==state and mailbox.name=='admin_rpc','Fixed mailbox directory')
    mailbox.mkdir(exist_ok=False);meta.check_path(mailbox)
    transaction=state/'transaction';transaction.mkdir(exist_ok=False)
    binding=dict(run_id=value['plan']['run_id'],runtime_sha256=runtime_sha,
                 plan_sha256=value['plan']['native_plan_sha256'],nonce=value['nonce'])
    _record(mailbox,'client_identity.json',actor)
    _record(state,'controller_intent.json',{'binding':binding,'actor':actor,'native_root':str(native_root)})
    text=recovery_text(runtime_path,runtime_sha,value,actor)
    with (mailbox/'LOCAL_RECOVERY.txt').open('x',encoding='utf-8-sig') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    admin_script=Path(value['code_root'])/'scripts/Stage2AdminBridge.ps1'
    print('Before blocking, open LOCAL_RECOVERY.txt in the existing local administrator console.',flush=True)
    print(f"& '{admin_script}' -Mode Agent -RuntimePath '{runtime_path}' -RuntimeSha256 '{runtime_sha}'",flush=True)
    # This is a local handoff, not online authorization; no connection is needed
    # once the broker/guardian are armed. Setup has no enabled audit/network probe.
    setup_end=time.monotonic()+180
    while not (mailbox/'agent_ready.json').exists():
        core.require(time.monotonic()<setup_end,'Local administrator setup timed out before audit')
        time.sleep(.05)
    rpc=native.Mailbox(mailbox,binding,meta.check_path,meta.peer)
    dns=FixedDnsQuery(meta.api)
    probes=native.FixedProbes(meta.own,dns)
    plan={**value['plan'],'native_root':str(native_root)}
    ports=native.WindowsPorts(rpc,probes,plan,meta.peer,meta.device_to_dos)
    leaf=FixedLaunch(**{**parameters['leaf_spec'],'arguments':tuple(parameters['leaf_spec']['arguments'])})
    args=dict(run_id=parameters['run_id'],expected_plan_sha256=parameters['plan_sha256'],
              restore_script=parameters['restore_script'],expected_restore_sha256=parameters['restore_script_sha256'],
              worker_spec=spec,code_root=parameters['code_root'],code_pins=parameters['code_pins'])
    worker=core.WorkerFlow(native_root,leaf,args)
    try:
        result=core.run(transaction,plan,ports,worker,simulation=False)
        print(json.dumps(result,sort_keys=True),flush=True)
        return result
    finally:
        if dns.pending:
            rpc.restore_audit_out_of_band()
            # Do not tear down Python callback state with a pending native DNS
            # callback. The independent admin guardian stops this exact process.
            while dns.pending:time.sleep(.1)
        try:rpc.call('finish')
        except BaseException:rpc.restore_audit_out_of_band()
