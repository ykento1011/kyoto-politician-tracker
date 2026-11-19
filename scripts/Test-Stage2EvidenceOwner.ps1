#requires -Version 5.1
# Pure descriptor + injected file-port tests; no native bridge/OS tool entry.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Stage2AdminBridge.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Syntax'}
foreach($name in @('New-EvidenceSecurity','Assert-EvidenceSecurity','Save-EvidenceBytes','Save-New','Read-EvidenceBytes','Publish-Evidence',
    'Save-AuditCapture','Read-SavedAuditCapture','Decode-AuditCapture','Convert-AuditCsv','Read-Audit','Assert-Binding')){
    $n=@($ast.FindAll({param($a) $a -is [Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -ceq $name},$false))
    if($n.Count -ne 1){throw 'Pure boundary'}
    . ([scriptblock]::Create($n[0].Extent.Text))
}
$script:ActorSid='S-1-5-21-111-222-333-1004'
$script:Pass=0;$script:Holds=0
function Check($v,$m){if(-not $v){throw $m};$script:Pass++}
function Hold([scriptblock]$Action){$h=$false;try{& $Action}catch{$h=$true};Check $h 'Expected HOLD';$script:Holds++}
$good=New-EvidenceSecurity
Assert-EvidenceSecurity $good
Check ($good.GetOwner([Security.Principal.SecurityIdentifier]).Value -ceq $script:ActorSid) 'Explicit owner'
foreach($case in @('wrong_owner','extra_ace','inherited_dacl','deny','wrong_rights')){
    $s=New-EvidenceSecurity
    switch($case){
        wrong_owner {$s.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))}
        extra_ace {$s.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-5-18'),'Read','Allow'))}
        inherited_dacl {$s.SetAccessRuleProtection($false,$true)}
        deny {$s.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($script:ActorSid),'Read','Deny'))}
        wrong_rights {$s.SetAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($script:ActorSid),'Read','Allow'))}
    }
    Hold {Assert-EvidenceSecurity $s}
}
$script:Root=Join-Path ([IO.Path]::GetTempPath()) ('stage2-owner-fixture-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($script:Root)
$script:Case='normal';$script:Descriptors=@{};$script:DefaultOwner='S-1-5-32-544'
$script:Box=$script:Root
$script:Connection='{0CCE9226-69AE-11D9-BED3-505054503030}';$script:Packet='{0CCE9225-69AE-11D9-BED3-505054503030}'
$script:Binding=@{run_id=('a'*32);runtime_sha256=('b'*64);plan_sha256=('c'*64);nonce=('d'*64)}
function Read-FixedJson([string]$Path,[int]$Limit=2097152){
    Assert-EvidenceFile $Path;$b=[IO.File]::ReadAllBytes($Path)
    if($b.Length -gt $Limit){throw 'Bound'}
    return (([Text.UTF8Encoding]::new($false,$true)).GetString($b).TrimStart([char]0xfeff)|ConvertFrom-Json)
}
function Invoke-AuditCapture([string]$Guid){
    $name=if($Guid -ceq $script:Connection){'フィルタリング プラットフォームの接続'}else{'フィルタリング プラットフォーム パケットのドロップ'}
    $text="コンピューター名,ポリシー ターゲット,サブカテゴリ,サブカテゴリ GUID,包含設定,除外設定`r`nFIXTURE-PC,システム,$name,$Guid,監査なし,"+$script:Exclusion
    return @{guid=$Guid;started_utc='2026-01-01T00:00:00Z';finished_utc='2026-01-01T00:00:01Z';console_code_page=65001;
        stdout=[Text.Encoding]::UTF8.GetBytes($text);stderr=[byte[]]@();stdout_complete=$true;stderr_complete=$true;overflow=$false;exit_code=0;failure=$null}
}
function Assert-Private([string]$Path){
    if(-not ([IO.Path]::GetFullPath($Path)).StartsWith($script:Root,[StringComparison]::Ordinal) -or $script:Case -eq 'parent' -or $script:Case -eq 'reparse'){throw 'Synthetic parent/reparse HOLD'}
}
function Assert-EvidenceFile([string]$Path){Assert-Private $Path;Assert-EvidenceSecurity $script:Descriptors[$Path]}
function New-EvidenceStream([string]$Path,$Security){
    if($script:Case -eq 'owner_rejected'){throw 'Synthetic OS owner rejected'}
    # Model an elevated default owner; only the explicit descriptor overrides it.
    Assert-EvidenceSecurity $Security
    $script:Descriptors[$Path]=$Security
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $o=[pscustomobject]@{Stream=$stream;Security=$Security}
    $o|Add-Member ScriptMethod GetAccessControl {if($script:Case -eq 'wrong_handle_owner'){$s=New-EvidenceSecurity;$s.SetOwner([Security.Principal.SecurityIdentifier]::new($script:DefaultOwner));return $s};return $this.Security}
    $o|Add-Member ScriptMethod Write {param($b,$off,$len) if($script:Case -eq 'partial'){$this.Stream.Write($b,$off,1);throw 'Partial write'};$this.Stream.Write($b,$off,$len)}
    $o|Add-Member ScriptMethod Flush {param($disk) if($script:Case -eq 'fsync'){throw 'Fsync'};$this.Stream.Flush($disk)}
    $o|Add-Member ScriptMethod Dispose {$this.Stream.Dispose()}
    return $o
}
function Read-EvidenceBytes([string]$Path){
    if($script:Case -eq 'hash' -or ($script:Case -eq 'final_hash' -and -not $Path.EndsWith('.tmp'))){return ,([byte[]]@(1))}
    return ,([IO.File]::ReadAllBytes($Path))
}
function Publish-Evidence([string]$Temporary,[string]$Path){
    if($script:Case -eq 'publish'){throw 'Interrupted before publication'}
    if($script:Case -eq 'race_collision'){[IO.File]::WriteAllText($Path,'existing')}
    [IO.File]::Move($Temporary,$Path);$script:Descriptors[$Path]=$script:Descriptors[$Temporary]
}
try{
    foreach($name in @('agent_ready','guard_ready','response','HOLD','finished','audit-capture')){
        $path=Join-Path $script:Root ($name+'.json');Save-New $path @{binding='synthetic';state=$name}
        $v=[IO.File]::ReadAllText($path)|ConvertFrom-Json
        Check ($v.state -ceq $name -and $script:Descriptors[$path].GetOwner([Security.Principal.SecurityIdentifier]).Value -ceq $script:ActorSid) 'Admin default owner overridden by descriptor'
    }
    $existing=Join-Path $script:Root 'HOLD.json';$original=[IO.File]::ReadAllBytes($existing)
    Hold {Save-New $existing @{bad=$true}}
    Check ([Convert]::ToBase64String([IO.File]::ReadAllBytes($existing)) -ceq [Convert]::ToBase64String($original)) 'No overwrite'
    foreach($case in @('owner_rejected','wrong_handle_owner','partial','fsync','parent','reparse','hash','final_hash','publish','race_collision')){
        $script:Case=$case;$path=Join-Path $script:Root ($case+'.json')
        Hold {Save-New $path @{state='synthetic'}}
        if($case -notin @('final_hash','race_collision')){Check (-not [IO.File]::Exists($path)) 'No incomplete final record'}
        if($case -eq 'race_collision'){Check ([IO.File]::ReadAllText($path) -ceq 'existing') 'Race no overwrite'}
    }
    $script:Case='normal';Hold {Save-EvidenceBytes (Join-Path $script:Root 'large') ([byte[]]::new(2097153))}
    $script:Exclusion='';$audit=Read-Audit
    Check ($audit.Count -eq 2) 'Secure publication through saved CSV PASS'
    $script:Exclusion='unknown';Hold {$null=Read-Audit}
    Check (@([IO.Directory]::GetFiles($script:Root,'*.hold.json')).Count -eq 1) 'Malformed CSV kept as owner-guaranteed HOLD evidence'
}finally{
    foreach($file in [IO.Directory]::GetFiles($script:Root)){[IO.File]::Delete($file)}
    [IO.Directory]::Delete($script:Root)
}
@{pass=$script:Pass;expected_hold=$script:Holds;native_owner_creation=0;admin_processes=0;auditpol=0;firewall=0;stage2=0}|ConvertTo-Json -Compress
