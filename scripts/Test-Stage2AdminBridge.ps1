#requires -Version 5.1
# Extract only the pure/control functions. Never dot-source the live entry.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$path=Join-Path $PSScriptRoot 'Stage2AdminBridge.ps1'
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('Assert-Binding','Assert-Completion','Invoke-GuardRecovery','Restore-Audit')){
    $nodes=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$false))
    if($nodes.Count -ne 1){throw 'Function boundary'}
    . ([scriptblock]::Create($nodes[0].Extent.Text))
}
$script:Passed=0
function Check($ok,$message){if(-not $ok){throw $message};$script:Passed++}
$script:Binding=@{run_id=('a'*32);runtime_sha256=('b'*64);plan_sha256=('c'*64);nonce=('d'*64)}
Assert-Binding ([pscustomobject]$script:Binding)
Check $true 'binding'
foreach($key in $script:Binding.Keys){
    $bad=@{};foreach($k in $script:Binding.Keys){$bad[$k]=$script:Binding[$k]};$bad[$key]='mismatch'
    $held=$false;try{Assert-Binding ([pscustomobject]$bad)}catch{$held=$true}
    Check $held ('binding mismatch '+$key)
}
# In-memory filesystem/tool/process doubles: no audit/Firewall/process API.
$digest=[Security.Cryptography.SHA256]::Create()
try{$tokenHash=[BitConverter]::ToString($digest.ComputeHash([Text.Encoding]::UTF8.GetBytes('test-capability'))).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
foreach($case in @('valid','token','record_sha','run','deadline','termination')){
    $started=[pscustomobject]@{run_id=$script:Binding.run_id;plan_sha256=$script:Binding.plan_sha256;completion_token_sha256=$tokenHash;total_seconds=10}
    $done=[pscustomobject]@{run_id=$script:Binding.run_id;plan_sha256=$script:Binding.plan_sha256;termination_confirmed=$true;cleanup_complete=$true;elapsed_seconds=2;total_seconds=10}
    $success=[pscustomobject]@{run_id=$script:Binding.run_id;plan_sha256=$script:Binding.plan_sha256;completion_token='test-capability';termination_record_sha256=('e'*64);elapsed_seconds=2}
    switch($case){
        'token' {$success.completion_token='wrong'}
        'record_sha' {$success.termination_record_sha256='wrong'}
        'run' {$done.run_id='wrong'}
        'deadline' {$success.elapsed_seconds=10}
        'termination' {$done.termination_confirmed=$false}
    }
    $held=$false;try{Assert-Completion $started $done $success ('e'*64)}catch{$held=$true}
    Check ($held -eq ($case -ne 'valid')) ('completion '+$case)
}
$script:Connection='{0CCE9226-69AE-11D9-BED3-505054503030}'
$script:OriginalAudit=@{connection=@{success=$false;failure=$false};packet=@{success=$false;failure=$false}}
$script:ToolCalls=@()
function Invoke-FixedTool($Name,$Arguments){$script:ToolCalls+=,@{name=$Name;arguments=$Arguments};if($script:ToolFail){throw 'synthetic tool timeout'}}
function Read-Audit {return $script:Readback}
foreach($case in @('restored','readback_mismatch','tool_timeout')){
    $script:Readback=@{connection=@{success=$false;failure=($case -eq 'readback_mismatch')};packet=@{success=$false;failure=$false}}
    $script:ToolFail=($case -eq 'tool_timeout');$held=$false
    try{$null=Restore-Audit}catch{$held=$true}
    Check ($held -eq ($case -ne 'restored')) ('audit rollback '+$case)
}
Check (@($script:ToolCalls|Where-Object {($_.arguments -join ' ') -match 'success:|5152|failure:enable'}).Count -eq 0) 'Only failure disable'
function Test-Path {param($LiteralPath) return $LiteralPath.EndsWith('audit_intent.json')}
function Save-New($Path,$Value){$script:Saved+=,$Value}
function Restore-Audit { $script:Restores++;if($script:FailRestore){throw 'synthetic restore failure'};return $true }
$script:Box=$PSScriptRoot
foreach($case in @('normal','agent_alive','stop_timeout','stop_throw','restore_failure','identity_mismatch')){
    $script:Saved=@();$script:Restores=0;$script:FailRestore=($case -eq 'restore_failure')
    $stamp=[DateTime]::SpecifyKind([DateTime]'2026-01-01',[DateTimeKind]::Utc)
    $script:Client=@{started=$stamp.ToFileTimeUtc();image='synthetic.exe'}
    $script:GuardClient=[pscustomobject]@{HasExited=$false;StartTime=$stamp;MainModule=[pscustomobject]@{FileName='synthetic.exe'};Case=$case;Kills=0}
    $script:GuardClient|Add-Member ScriptMethod Kill { $this.Kills++;if($this.Case -eq 'stop_throw'){throw 'synthetic kill failure'} }
    $script:GuardClient|Add-Member ScriptMethod WaitForExit {param($ms) return $this.Case -ne 'stop_timeout'}
    $script:GuardAgent=[pscustomobject]@{HasExited=($case -ne 'agent_alive')}
    if($case -eq 'identity_mismatch'){$script:GuardClient.MainModule.FileName='other.exe'}
    $complete=Invoke-GuardRecovery
    Check ($script:Restores -eq 1) ('independent restore '+$case)
    Check ($complete -eq ($case -eq 'normal')) ('guard result '+$case)
    if($case -notin @('normal','agent_alive')){
        Check ($script:Saved.Count -eq 1 -and $script:Saved[0].state -eq 'HOLD' -and -not $script:Saved[0].firewall_removed) ('durable HOLD '+$case)
    }
    if($case -eq 'identity_mismatch'){Check ($script:GuardClient.Kills -eq 0) 'No wrong PID kill'}
}
@{passed=$script:Passed;synthetic=$true;firewall_operations=0;audit_operations=0;native_process_launches=0}|ConvertTo-Json -Compress
