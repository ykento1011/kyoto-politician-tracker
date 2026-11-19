#requires -Version 5.1
param([string]$SavedReadiness)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Stage2AdminBridge.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Bridge syntax'}
$nodes=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Convert-AuditCsv'},$false))
if($nodes.Count -ne 1){throw 'Pure parser boundary'}
. ([scriptblock]::Create($nodes[0].Extent.Text))
function Invoke-FixedTool {throw 'OS tool forbidden in CSV test'}
$script:Pass=0;$script:Rejected=0;$script:SavedCount=0
function Check($ok,$message){if(-not $ok){throw $message};$script:Pass++}
function Reject([string]$csv,[string]$guid){$held=$false;try{$null=Convert-AuditCsv $csv $guid}catch{$held=$true};Check $held 'Malformed CSV did not HOLD';$script:Rejected++}
$guid='{0CCE9226-69AE-11D9-BED3-505054503030}'
$header='コンピューター名,ポリシー ターゲット,サブカテゴリ,サブカテゴリ GUID,包含設定,除外設定'
# Saved schema/content, with only the machine name anonymized. Not a new audit.
$row='FIXTURE-PC,システム,フィルタリング プラットフォームの接続,'+$guid+',監査なし,'
$csv=$header+"`r`n`r`n"+$row+"`r`n"
foreach($state in @('監査なし','失敗','成功','成功および失敗')){
    $v=Convert-AuditCsv ($csv.Replace('監査なし',$state)) $guid
    Check ($v.success -eq ($state -in @('成功','成功および失敗')) -and $v.failure -eq ($state -in @('失敗','成功および失敗'))) 'Audit state mapping'
}
$v=Convert-AuditCsv (([string][char]0xfeff)+$csv) $guid;Check (-not $v.success -and -not $v.failure) 'Leading BOM'
$v=Convert-AuditCsv ($csv.Replace('FIXTURE-PC','"FIXTURE,PC"')) $guid;Check (-not $v.failure) 'Quoted field'
Reject ($header+"`r`n"+$row.TrimEnd(',')) $guid
Reject ($header+"`r`n"+$row+',') $guid
foreach($exclusion in @('unknown','0',' ','なし','失敗')){Reject ($csv.Replace('監査なし,','監査なし,'+$exclusion)) $guid}
Reject ($csv.Replace('監査なし','未知')) $guid
Reject ($csv.Replace('監査なし',' 監査なし ')) $guid
Reject ($csv.Replace($guid,' '+$guid+' ')) $guid
Reject ($csv.Replace($guid,'{0CCE9225-69AE-11D9-BED3-505054503030}')) $guid
Reject ($csv+$row+"`r`n") $guid
Reject ($csv.Replace(',',';')) $guid
Reject ($csv.Replace('除外設定','OTHER')) $guid
Reject ($csv.Replace('システム','ユーザー')) $guid
Reject ($csv.Replace('FIXTURE-PC','"unterminated')) $guid
Reject ($csv.Replace('監査なし',[string][char]0xfffd)) $guid
Reject ($csv.Replace('監査なし',[string][char]0xd800)) $guid
Reject ($csv.Replace('監査なし',([string][char]0xfeff)+'監査なし')) $guid
Reject ($csv.Replace('監査なし',([string][char]0)+'監査なし')) $guid
Reject $csv '{00000000-0000-0000-0000-000000000000}'
# Demonstrate the prior structure bug without running Read-Audit or auditpol.
$legacy=$row.TrimEnd(',')|ConvertFrom-Csv -Header computer,target,name,guid,inclusion,exclusion
Check ([string]::IsNullOrEmpty($legacy.exclusion)) 'Legacy missing-column reproduction'
if($SavedReadiness){
    $bytes=[IO.File]::ReadAllBytes($SavedReadiness)
    $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes).TrimStart([char]0xfeff)
    $saved=ConvertFrom-Json -InputObject $text
    foreach($entry in $saved.audit){
        if($entry.exit -ne 0){throw 'Saved command failed'}
        $inputCsv=$entry.csv -join "`r`n"
        $value=Convert-AuditCsv $inputCsv $entry.guid
        $legacyRow=@($entry.csv|Where-Object {$_ -match [regex]::Escape($entry.guid)})|ConvertFrom-Csv -Header computer,target,name,guid,inclusion,exclusion
        Check (-not $value.success -and -not $value.failure -and [string]::IsNullOrEmpty($legacyRow.exclusion)) 'Saved record replay'
        $script:SavedCount++
    }
}
foreach($name in @('Save-New','Save-AuditCapture','Read-SavedAuditCapture','Decode-AuditCapture','Read-Audit','Initialize-AuditCaptureTypes')){
    $n=@($ast.FindAll({param($a) $a -is [Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -ceq $name},$false))
    if($n.Count -ne 1){throw 'Pure evidence boundary'}
    . ([scriptblock]::Create($n[0].Extent.Text))
}
Initialize-AuditCaptureTypes
Add-Type -TypeDefinition @'
using System; using System.IO; using System.Threading.Tasks;
public sealed class AuditPartialFixture : MemoryStream {
 public bool Hang; int calls;
 public override Task<int> ReadAsync(byte[] b,int o,int n,System.Threading.CancellationToken c) {
  if(calls++==0){b[o]=65;return Task.FromResult(1);}
  if(Hang)return new TaskCompletionSource<int>().Task;
  var t=new TaskCompletionSource<int>();t.SetException(new IOException("synthetic read fault"));return t.Task;
 }
}
'@
foreach($hang in @($false,$true)){
    $stream=New-Object AuditPartialFixture;$stream.Hang=$hang;$buffer=New-Object Stage2AuditBuffer
    $task=[Stage2AuditRaw]::Read($stream,$buffer)
    try{$null=$task.Wait(10)}catch{}
    $partial=$buffer.Freeze()
    Check ($partial.Length -eq 1 -and $partial[0] -eq 65 -and $task.Status -ne [Threading.Tasks.TaskStatus]::RanToCompletion) 'Partial bytes survive fault or stalled read'
    $buffer.Append([byte[]]@(66),1)
    Check ($buffer.Freeze().Length -eq 1) 'Frozen evidence cannot change after publication'
    $stream.Dispose()
}
foreach($length in @(0,17,65536,65537,70000)){
    $stream=New-Object IO.MemoryStream(,[byte[]](New-Object byte[] $length))
    try{
        $chunk=[Stage2AuditRaw]::Read($stream).GetAwaiter().GetResult()
        Check ($chunk.Bytes.Length -eq [Math]::Min($length,65537) -and $chunk.Overflow -eq ($length -gt 65536)) 'Raw stream bound'
    }finally{$stream.Dispose()}
}
$script:Connection=$guid;$script:Packet='{0CCE9225-69AE-11D9-BED3-505054503030}'
$script:Binding=@{run_id=('a'*32);runtime_sha256=('b'*64);plan_sha256=('c'*64);nonce=('d'*64)}
$script:Box=Join-Path ([IO.Path]::GetTempPath()) ('audit-csv-fixture-'+[Guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($script:Box)
function Assert-Private([string]$Path){if(-not ([IO.Path]::GetFullPath($Path)).StartsWith($script:Box,[StringComparison]::Ordinal)){throw 'Fixture path'};if($script:DenyAcl){throw 'Synthetic ACL failure'}}
function Assert-Binding($v){foreach($k in $script:Binding.Keys){if($v.$k -cne $script:Binding[$k]){throw 'Fixture binding'}}}
function Read-FixedJson([string]$Path,[int]$Limit){$b=[IO.File]::ReadAllBytes($Path);if($b.Length -gt $Limit){throw 'Fixture bound'};return ((New-Object Text.UTF8Encoding($false,$true)).GetString($b).TrimStart([char]0xfeff)|ConvertFrom-Json)}
$script:DenyAcl=$false
$script:Capture=@{guid=$guid;started_utc='2026-01-01T00:00:00Z';finished_utc='2026-01-01T00:00:01Z';console_code_page=65001;
    stdout=[Text.Encoding]::UTF8.GetBytes($csv);stderr=[byte[]]@();stdout_complete=$true;stderr_complete=$true;overflow=$false;exit_code=0;failure=$null}
try{
    $evidence=Save-AuditCapture $script:Capture $guid
    $savedCapture=Read-FixedJson $evidence 262144
    Check ($savedCapture.stdout_base64 -ceq [Convert]::ToBase64String($script:Capture.stdout)) 'Exact raw byte preservation'
    Check ((Decode-AuditCapture (Read-SavedAuditCapture $evidence $guid)).text -ceq $csv) 'Parse only saved verified bytes'
    $decoded=Decode-AuditCapture $script:Capture
    Check ($decoded.text -ceq $csv) 'UTF8 byte decode'
    foreach($cp in @(932,1200,1201)){
        $cap=$script:Capture.Clone();$enc=[Text.Encoding]::GetEncoding($cp);$cap.console_code_page=$cp
        $cap.stdout=[byte[]]($enc.GetPreamble()+$enc.GetBytes($csv))
        Check ((Decode-AuditCapture $cap).text -ceq $csv) ('Encoding '+$cp)
    }
    foreach($case in @('invalid_utf8','unknown_codepage','stderr','exit','incomplete','overflow')){
        $cap=$script:Capture.Clone()
        switch($case){
            'invalid_utf8' {$cap.stdout=[byte[]]@(255,255,0)}
            'unknown_codepage' {$cap.console_code_page=1252}
            'stderr' {$cap.stderr=[byte[]]@(65)}
            'exit' {$cap.exit_code=1}
            'incomplete' {$cap.stdout_complete=$false}
            'overflow' {$cap.overflow=$true}
        }
        $held=$false;try{$null=Decode-AuditCapture $cap}catch{$held=$true};Check $held ('Decode HOLD '+$case);$script:Rejected++
    }
    $original=Get-Content -Raw -LiteralPath $evidence
    $held=$false;try{Save-New $evidence @{bad=$true}}catch{$held=$true}
    Check ($held -and (Get-Content -Raw -LiteralPath $evidence) -ceq $original) 'Existing evidence collision HOLD'
    $script:Rejected++
    function Invoke-AuditCapture([string]$g){
        $copy=$script:Capture.Clone();$copy.guid=$g
        if($g -ceq $script:Packet){
            $text=[Text.Encoding]::UTF8.GetString($copy.stdout).Replace($script:Connection,$g).Replace('フィルタリング プラットフォームの接続','フィルタリング プラットフォーム パケットのドロップ')
            $copy.stdout=[Text.Encoding]::UTF8.GetBytes($text)
        }
        return $copy
    }
    $states=Read-Audit
    Check ($states.Count -eq 2 -and -not $states[$guid.Trim('{}').ToLowerInvariant()].failure) 'Read-Audit synthetic save then parse'
    # Inject failure at publication. Read-Audit must never decode/return PASS.
    $saveFunction=${function:Save-New};$decodeFunction=${function:Decode-AuditCapture}
    function Invoke-AuditCapture([string]$g){return $script:Capture}
    $script:DecodeCalls=0
    function Decode-AuditCapture($c){$script:DecodeCalls++;throw 'Decode should not be reached'}
    function Save-New([string]$Path,$Value){throw 'Synthetic interrupted write/fsync/collision'}
    $held=$false;try{$null=Read-Audit}catch{$held=$true}
    Check ($held -and $script:DecodeCalls -eq 0) 'Save failure precedes parse';$script:Rejected++
    Set-Item function:Save-New $saveFunction;Set-Item function:Decode-AuditCapture $decodeFunction
    $script:DenyAcl=$true;$held=$false;try{$null=Save-AuditCapture $script:Capture $guid}catch{$held=$true}
    Check $held 'ACL HOLD before publication';$script:Rejected++
}finally{
    # Synthetic test directory only; never a private runtime/run.
    foreach($file in [IO.Directory]::GetFiles($script:Box)){[IO.File]::Delete($file)}
    [IO.Directory]::Delete($script:Box)
}
@{pass=$script:Pass;malformed_hold=$script:Rejected;saved_records=$script:SavedCount;firewall_operations=0;audit_operations=0;controller=0;worker=0}|ConvertTo-Json -Compress
