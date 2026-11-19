#requires -Version 5.1
[CmdletBinding()]
param([ValidateSet('Agent','Guard','Recover','SelfTest')][string]$Mode='Agent',
      [string]$RuntimePath,[string]$RuntimeSha256,[switch]$StopActor,[switch]$RestoreFirewall)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:LiveOsBridgeEnabled=$false # private activation/re-PIN only; no CLI override
$script:Connection='{0CCE9226-69AE-11D9-BED3-505054503030}'
$script:Packet='{0CCE9225-69AE-11D9-BED3-505054503030}'
$script:Streams=New-Object 'System.Collections.Generic.List[System.IDisposable]'

function Initialize-NativeTypes {
    if('Stage2TraceControl' -as [type]){return}
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Security.Principal;
[StructLayout(LayoutKind.Sequential)] public struct Stage2Wnode {
 public UInt32 BufferSize,ProviderId; public UInt64 HistoricalContext,TimeStamp;
 public Guid Guid; public UInt32 ClientContext,Flags;
}
[StructLayout(LayoutKind.Sequential)] public struct Stage2TraceProperties {
 public Stage2Wnode Wnode;
 public UInt32 BufferSize,MinimumBuffers,MaximumBuffers,MaximumFileSize,LogFileMode,FlushTimer,EnableFlags;
 public Int32 AgeLimit; public UInt32 NumberOfBuffers,FreeBuffers,EventsLost,BuffersWritten,LogBuffersLost,RealTimeBuffersLost;
 public IntPtr LoggerThreadId; public UInt32 LogFileNameOffset,LoggerNameOffset;
}
public sealed class Stage2Loss { public UInt32 Status,EventsLost,LogBuffersLost,RealTimeBuffersLost; public bool Missing; }
public static class Stage2TraceControl {
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,EntryPoint="ControlTraceW")]
 static extern UInt32 Control(UInt64 handle,string name,IntPtr props,UInt32 code);
 public static Stage2Loss Stop(string name,string expectedPath) {
  if(!System.Text.RegularExpressions.Regex.IsMatch(name,@"^GikaiMikata-Stage2DNS-[0-9a-f]{32}$"))throw new Exception("Trace scope");
  int size=Marshal.SizeOf(typeof(Stage2TraceProperties)); IntPtr p=Marshal.AllocHGlobal(size+8192);
  try {
   Marshal.Copy(new byte[size+8192],0,p,size+8192);
   Stage2TraceProperties v=new Stage2TraceProperties(); v.Wnode.BufferSize=(UInt32)(size+8192);
   v.LoggerNameOffset=(UInt32)size; v.LogFileNameOffset=(UInt32)(size+4096);
   Marshal.StructureToPtr(v,p,false);
   UInt32 status=Control(0,name,p,0);
   if(status==4201)return new Stage2Loss{Status=0,Missing=true};
   if(status!=0)return new Stage2Loss{Status=status};
   v=(Stage2TraceProperties)Marshal.PtrToStructure(p,typeof(Stage2TraceProperties));
   if(v.LogFileNameOffset< size || v.LogFileNameOffset>=size+8192)throw new Exception("Trace logfile offset");
   string path=Marshal.PtrToStringUni(IntPtr.Add(p,(int)v.LogFileNameOffset));
   if(!String.Equals(System.IO.Path.GetFullPath(path),System.IO.Path.GetFullPath(expectedPath),StringComparison.OrdinalIgnoreCase))throw new Exception("Not owned trace");
   status=Control(0,name,p,1);
   v=(Stage2TraceProperties)Marshal.PtrToStructure(p,typeof(Stage2TraceProperties));
   return new Stage2Loss{Status=status,EventsLost=v.EventsLost,LogBuffersLost=v.LogBuffersLost,RealTimeBuffersLost=v.RealTimeBuffersLost};
  } finally {Marshal.FreeHGlobal(p);}
 }
 [DllImport("advapi32.dll",SetLastError=true)]static extern bool OpenProcessToken(IntPtr process,UInt32 access,out IntPtr token);
 [DllImport("advapi32.dll",SetLastError=true)]static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr data,UInt32 size,out UInt32 returned);
 [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr h);
 public static bool Elevated(IntPtr process) {
  IntPtr token; if(!OpenProcessToken(process,8,out token))throw new Exception("Token query failed");
  IntPtr p=Marshal.AllocHGlobal(4);try {UInt32 n;if(!GetTokenInformation(token,20,p,4,out n))throw new Exception("Elevation query failed");return Marshal.ReadInt32(p)!=0;}
  finally{Marshal.FreeHGlobal(p);CloseHandle(token);}
 }
}
'@
}
function Assert-Binding($Value){
    if(@($Value.PSObject.Properties).Count -ne 4){throw 'Binding fields'}
    foreach($key in @('run_id','runtime_sha256','plan_sha256','nonce')){
        if($Value.PSObject.Properties[$key].Value -isnot [string] -or $Value.PSObject.Properties[$key].Value -cne $script:Binding[$key]){throw 'Binding substitution'}
    }
}
function Assert-Completion($Started,$Done,$Success,[string]$DoneSha){
    foreach($row in @($Started,$Done,$Success)){
        if($row.run_id -cne $script:Binding.run_id -or $row.plan_sha256 -cne $script:Binding.plan_sha256){throw 'Journal identity'}
        if($null -ne $row.PSObject.Properties['auto_restore'] -and $row.auto_restore -ne $false){throw 'Automatic restore forbidden'}
    }
    $sha=[Security.Cryptography.SHA256]::Create()
    try{$tokenHash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Success.completion_token))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
    if($tokenHash -cne $Started.completion_token_sha256 -or $Success.termination_record_sha256 -cne $DoneSha -or
       $Done.termination_confirmed -isnot [bool] -or -not $Done.termination_confirmed -or
       $Done.cleanup_complete -isnot [bool] -or -not $Done.cleanup_complete -or
       $Success.elapsed_seconds -lt 0 -or $Success.elapsed_seconds -ge $Started.total_seconds -or
       $Done.elapsed_seconds -lt 0 -or $Done.elapsed_seconds -ge $Done.total_seconds){throw 'Uncommitted completion capability'}
}

function Save-New([string]$Path,$Value){
    $enc=New-Object Text.UTF8Encoding($true,$true)
    $json=ConvertTo-Json -InputObject $Value -Depth 24
    $null=ConvertFrom-Json -InputObject $json
    $body=$enc.GetPreamble()+$enc.GetBytes($json)
    # Same-directory rename publishes only a closed, fully flushed record.
    # File.Move's two-argument overload refuses an existing destination.
    $temporary=Join-Path ([IO.Path]::GetDirectoryName($Path)) ('.stage2-'+[Guid]::NewGuid().ToString('N')+'.tmp')
    $created=$false
    try{
        $s=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $created=$true
        try{$s.Write($body,0,$body.Length);$s.Flush($true)}finally{$s.Dispose()}
        [IO.File]::Move($temporary,$Path)
        $created=$false
    }finally{if($created){[IO.File]::Delete($temporary)}}
}
function Assert-Private([string]$Path){
    $p=[IO.Path]::GetFullPath($Path)
    if($p -cne $script:PrivateRoot -and -not $p.StartsWith($script:PrivateRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside fixed private root'}
    $item=Get-Item -LiteralPath $p -Force
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse refused'}
    $acl=Get-Acl -LiteralPath $p
    if($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $script:ActorSid){throw 'Owner SID mismatch'}
    foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
        if($ace.AccessControlType -eq 'Allow' -and -not $ace.IsInherited -and $ace.IdentityReference.Value -cne $script:ActorSid){throw 'Non-owner grant'}
        if($ace.AccessControlType -eq 'Allow' -and -not ($ace.PropagationFlags -band 2) -and $ace.IdentityReference.Value -cne $script:ActorSid){throw 'Effective non-owner grant'}
    }
    if($p -cne $script:PrivateRoot){Assert-Private ([IO.Path]::GetDirectoryName($p))}
}
function Read-FixedJson([string]$Path,[int]$Limit=2097152){
    Assert-Private $Path
    $s=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try{
        if($s.Length -gt $Limit){throw 'JSON bound'}
        $r=New-Object IO.StreamReader($s,(New-Object Text.UTF8Encoding($false,$true)),$true)
        try{return ($r.ReadToEnd()|ConvertFrom-Json)}finally{$r.Dispose()}
    }finally{$s.Dispose()}
}
function Invoke-FixedTool([string]$Name,[string[]]$Arguments,[int]$Milliseconds=2000){
    # Exact Windows tools only. No shell, environment expansion or arbitrary argv.
    $allowed=@('auditpol.exe','wevtutil.exe','netsh.exe','logman.exe')
    if($Name -cnotin $allowed){throw 'Tool not allowed'}
    $path=Join-Path $env:SystemRoot ('System32\'+$Name)
    $pin=$script:Runtime.system_tools.PSObject.Properties[$Name]
    if($null -eq $pin -or (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $pin.Value){throw 'System tool PIN differs'}
    foreach($arg in $Arguments){if($arg -match '[\r\n"\x00]'){throw 'Unsafe tool argument'}}
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$path;$info.Arguments=(@($Arguments|ForEach-Object {'"'+$_+'"'}) -join ' ')
    $info.UseShellExecute=$false;$info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
    $info.StandardOutputEncoding=[Console]::OutputEncoding;$info.StandardErrorEncoding=[Console]::OutputEncoding
    $proc=New-Object Diagnostics.Process;$proc.StartInfo=$info
    try{
        if(-not $proc.Start()){throw 'Tool did not start'}
        $stdout=$proc.StandardOutput.ReadToEndAsync();$stderr=$proc.StandardError.ReadToEndAsync()
        if(-not $proc.WaitForExit($Milliseconds)){
            $proc.Kill();if(-not $proc.WaitForExit(1000)){throw 'Tool termination unknown'}
            throw 'Tool timeout; no retry'
        }
        $a=$stdout.GetAwaiter().GetResult();$b=$stderr.GetAwaiter().GetResult()
        if($proc.ExitCode -ne 0){throw ('Tool HOLD '+$Name+': '+$b)}
        return $a
    }finally{$proc.Dispose()}
}
function Read-Audit {
    $result=[ordered]@{}
    foreach($g in @($script:Connection,$script:Packet)){
        $csv=Invoke-FixedTool 'auditpol.exe' @('/get',('/subcategory:'+$g),'/r')
        $rows=@($csv -split '\r?\n'|Where-Object {$_ -match [regex]::Escape($g)})
        if($rows.Count -ne 1){throw 'Audit row ambiguous'}
        $row=$rows[0]|ConvertFrom-Csv -Header computer,target,name,guid,inclusion,exclusion
        if($row.exclusion){throw 'Unknown exclusion'}
        switch -Exact ($row.inclusion){
            '監査なし' {$v=@{success=$false;failure=$false}}
            '失敗' {$v=@{success=$false;failure=$true}}
            '成功' {$v=@{success=$true;failure=$false}}
            '成功および失敗' {$v=@{success=$true;failure=$true}}
            default {throw 'Unexpected success audit or locale'}
        }
        $result[$g.Trim('{}').ToLowerInvariant()]=$v
    }
    return $result
}
function Restore-Audit {
    $null=Invoke-FixedTool 'auditpol.exe' @('/set',('/subcategory:'+$script:Connection),'/failure:disable')
    $state=Read-Audit
    foreach($key in $script:OriginalAudit.Keys){
        if($state[$key].success -ne $script:OriginalAudit[$key].success -or $state[$key].failure -ne $script:OriginalAudit[$key].failure){throw 'Audit restoration/readback HOLD'}
    }
    return $state
}
function Process-Identity([int]$Number,[string]$ExpectedSid,[string]$ExpectedImage,[string]$ExpectedSha){
    $p=[Diagnostics.Process]::GetProcessById($Number)
    $null=$p.Handle # retain, do not just trust PID or a stale CIM lookup
    $script:Streams.Add($p)
    $cim=Get-CimInstance Win32_Process -Filter ('ProcessId='+$Number)
    $owner=Invoke-CimMethod -InputObject $cim -MethodName GetOwnerSid
    if($p.HasExited -or $cim.CreationDate.ToUniversalTime().ToFileTimeUtc() -ne $p.StartTime.ToUniversalTime().ToFileTimeUtc() -or
       $owner.ReturnValue -ne 0 -or $owner.Sid -cne $ExpectedSid -or
       $p.MainModule.FileName -ine $ExpectedImage -or
       (Get-FileHash -LiteralPath $ExpectedImage).Hash.ToLowerInvariant() -cne $ExpectedSha){throw 'Retained process identity differs'}
    return @{pid=$Number;started=$p.StartTime.ToUniversalTime().ToFileTimeUtc();image=$p.MainModule.FileName;
        sid=$owner.Sid;retained_process_handle=$true;image_verified=$true}
}
function Dns-Identity {
    if($script:Runtime.dns_image.path -ine (Join-Path $env:SystemRoot 'System32\svchost.exe')){throw 'Fixed DNS service image required'}
    $s=Get-CimInstance Win32_Service -Filter "Name='Dnscache'"
    if($s.State -ne 'Running'){throw 'DNS service not running'}
    return Process-Identity ([int]$s.ProcessId) 'S-1-5-20' $script:Runtime.dns_image.path $script:Runtime.dns_image.sha256
}
function Log-Boundary {
    $l=Get-WinEvent -ListLog Security
    $first=Get-WinEvent -LogName Security -Oldest -MaxEvents 1
    $last=Get-WinEvent -LogName Security -MaxEvents 1
    return @{enabled=$l.IsEnabled;maximum_bytes=$l.MaximumSizeInBytes;oldest=$first.RecordId;latest=$last.RecordId;
        cleared=($last.RecordId -lt $script:StartBoundary.latest);evidence_missing=($first.RecordId -gt $script:StartBoundary.latest+1)}
}
function Export-Security([string]$Phase){
    if($Phase -cnotin @('before','after')){throw 'Export phase'}
    $path=Join-Path $script:Box ($Phase+'.evtx')
    if(Test-Path -LiteralPath $path){throw 'Existing EVTX; no overwrite'}
    $null=Invoke-FixedTool 'wevtutil.exe' @('epl','Security',$path,'/ow:false') 5000
    Assert-Private $path
    $first=Get-WinEvent -Path $path -Oldest -MaxEvents 1
    $last=Get-WinEvent -Path $path -MaxEvents 1
    # Actual exported RecordId continuity, not file size/metadata alone. The full
    # 20MiB archive remains private. Never upload/clear/resize the Security log.
    $previous=$null;$missing=New-Object 'System.Collections.Generic.List[long]'
    foreach($e in Get-WinEvent -Path $path -Oldest){
        if($null -ne $previous -and $e.RecordId -ne $previous+1){$missing.Add($previous+1)}
        $previous=$e.RecordId
    }
    return @{sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();readback=$true;owner_only=$true;
        complete=($missing.Count -eq 0);first_record=$first.RecordId;last_record=$last.RecordId;missing_records=@($missing.ToArray())}
}
function Snapshot-Firewall {
    $state=[ordered]@{}
    foreach($store in @('ActiveStore','PersistentStore')){
        $baseRules=@(NetSecurity\Get-NetFirewallRule -PolicyStore $store|Where-Object {$_.Name -cnotin $script:RuleNames})
        foreach($kind in @('Rule','ApplicationFilter','AddressFilter','InterfaceFilter','InterfaceTypeFilter','PortFilter','SecurityFilter','ServiceFilter','Profile')){
            $command='Get-NetFirewall'+$kind
            if($kind -ceq 'Rule'){$items=$baseRules}
            elseif($kind -ceq 'Profile'){$items=@(NetSecurity\Get-NetFirewallProfile -PolicyStore $store)}
            else{$items=@($baseRules| & ('NetSecurity\'+$command))}
            $rows=@($items | Sort-Object InstanceID,Name | ForEach-Object {
                $v=[ordered]@{}
                foreach($prop in $_.PSObject.Properties|Where-Object {$_.Name -notmatch '^Cim'}|Sort-Object Name){
                    $v[$prop.Name]=(@($prop.Value|ForEach-Object {[string]$_}) -join [char]31)
                }
                $v
            })
            $state[$store+'/'+$kind]=$rows
        }
    }
    return ($state|ConvertTo-Json -Depth 8 -Compress)
}
function Load-RuleValidator {
    $path=$script:Runtime.recovery_text.path
    Assert-Private $path
    if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $script:Runtime.recovery_text.sha256){throw 'Recovery text PIN'}
    $t=$null;$e=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$t,[ref]$e)
    if($e.Count){throw 'Recovery parser HOLD'}
    $fn=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Confirm-ExactRule'},$true))
    if($fn.Count -ne 1){throw 'Fixed accepted validator not found'}
    # Import ONLY the accepted verifier, never its removal/acknowledgement block.
    return [scriptblock]::Create($fn[0].Extent.Text)
}
function Assert-Rules {
    $prefix='GikaiMikata-Stage2-'+$script:Binding.run_id
    . (Load-RuleValidator)
    Confirm-ExactRule 'Inbound';Confirm-ExactRule 'Outbound'
}
function Apply-Rules {
    foreach($name in $script:RuleNames){
        foreach($store in @('ActiveStore','PersistentStore')){
            if(@(NetSecurity\Get-NetFirewallRule -PolicyStore $store|Where-Object Name -CEQ $name).Count){throw 'Existing rule collision'}
        }
    }
    foreach($direction in @('Inbound','Outbound')){
        $name='GikaiMikata-Stage2-'+$script:Binding.run_id+'-'+$direction
        $null=NetSecurity\New-NetFirewallRule -PolicyStore PersistentStore -Name $name -DisplayName $name `
            -Group ('GikaiMikata-Stage2-'+$script:Binding.run_id) -Direction $direction -Action Block -Enabled True `
            -Profile Any -Program Any -Service Any -Protocol Any -LocalAddress Any -RemoteAddress Any
    }
    Assert-Rules
    if((Snapshot-Firewall) -cne $script:FirewallBefore){throw 'Non-delta Firewall settings changed; no probes'}
    # Exact rule label AND approved Windows Firewall sublayer, never fuzzy name
    # matching. Unknown netsh XML versions stop before any probe.
    $path=Join-Path $script:Box 'filters.xml'
    $null=Invoke-FixedTool 'netsh.exe' @('wfp','show','filters',('file='+$path),'verbose=on') 5000
    [xml]$xml=Get-Content -LiteralPath $path -Raw -Encoding UTF8
    $rows=@(foreach($item in $xml.SelectNodes('//*[filterId and displayData/name and subLayerKey]')){
        $label=[string]$item.displayData.name
        if($label -cin $script:RuleNames){
            if(([string]$item.subLayerKey).ToLowerInvariant() -cne $script:Runtime.wfp_sublayer.ToLowerInvariant()){throw 'Unexpected WFP sublayer'}
            @{id=[long]$item.filterId;rule=$label;origin=$label;snapshot_unchanged=$true}
        }
    })
    if(@($rows|Where-Object rule -CEQ $script:RuleNames[0]).Count -eq 0 -or
       @($rows|Where-Object rule -CEQ $script:RuleNames[1]).Count -eq 0){throw 'Rule/filter mapping unavailable'}
    $script:FilterMap=@{};foreach($row in $rows){if($script:FilterMap.ContainsKey($row.id)){throw 'Duplicate filter ID'};$script:FilterMap[$row.id]=$row.rule}
    return ,$rows
}
function Read-Denials([long]$After,[int]$Limit){
    if($Limit -lt 0 -or $Limit -gt 64){throw 'Event cap'}
    $left=64-$script:RawRecords.Count
    if($left -gt 0){
        $from=[long]$script:StartBoundary.latest
        if($script:RawRecords.Count){$from=($script:RawRecords.Keys|Measure-Object -Maximum).Maximum}
        $query='*[System[(EventID=5157) and (EventRecordID > '+$from+')]]'
        $fresh=@()
        try{$fresh=@(Get-WinEvent -LogName Security -FilterXPath $query -Oldest -MaxEvents $left)}
        catch{if($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'){throw}}
        foreach($e in $fresh){
            $xml=$e.ToXml()
            Save-New (Join-Path $script:Box ('5157-'+$e.RecordId+'.json')) @{xml=$xml;record_id=$e.RecordId}
            $script:RawRecords[[long]$e.RecordId]=$e
        }
    }
    $rows=@(foreach($number in @($script:RawRecords.Keys|Sort-Object)){
        if($number -le $After){continue}
        $e=$script:RawRecords[$number]
        [xml]$x=$e.ToXml();$d=@{};foreach($v in $x.Event.EventData.Data){if($d.ContainsKey($v.Name)){throw 'Duplicate event field'};$d[$v.Name]=[string]$v.'#text'}
        if(-not $d.ContainsKey('ProcessID') -or -not $d.ContainsKey('FilterOrigin')){throw 'Unsupported 5157 schema'}
        $processNumber=if($d.ProcessID -match '^0x'){[Convert]::ToInt32($d.ProcessID.Substring(2),16)}else{[int]$d.ProcessID}
        if($processNumber -eq $script:Client.pid){$owner=$script:Client}else{
            $owner=Dns-Identity
            if($processNumber -ne $owner.pid){throw 'Unattributable background process; raw XML preserved; HOLD'}
        }
        if(-not $script:FilterMap.ContainsKey([long]$d.FilterRTID) -or
           $d.FilterOrigin -cne $script:FilterMap[[long]$d.FilterRTID]){throw 'Filter origin changed/unproven'}
        $xml=$e.ToXml();$hash=[Security.Cryptography.SHA256]::Create()
        try{$xmlSha=[BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
        @{xml=$xml;xml_sha256=$xmlSha;owner=$owner;filter_origin=$d.FilterOrigin;fields=$d;event_id=$e.Id;
          provider=$e.ProviderName;record_id=$e.RecordId;utc_tick=$e.TimeCreated.ToUniversalTime().ToFileTimeUtc()}
    })
    $boundary=Log-Boundary
    return @{events=@($rows|Select-Object -First $Limit);truncated=($script:RawRecords.Count -ge 64 -or $rows.Count -gt $Limit);
        lost=[int]($boundary.evidence_missing -or $boundary.cleared);boundary=$boundary}
}
function Start-DnsTrace {
    $name='GikaiMikata-Stage2DNS-'+$script:Binding.run_id
    $existing=Invoke-FixedTool 'logman.exe' @('query','-ets')
    if($existing -match [regex]::Escape($name)){throw 'Existing ETW session; no takeover'}
    $script:TraceName=$name
    $pf=Join-Path $script:Box 'dns-providers.txt'
    $lines=@('{1c95126e-7eea-49a9-a3fe-a378b03ddb4d} 0xffffffffffffffff 5',
             'Microsoft-Windows-Kernel-Network 0xffffffffffffffff 5')
    $f=[IO.File]::Open($pf,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$b=[Text.Encoding]::ASCII.GetBytes(($lines -join "`r`n"));$f.Write($b,0,$b.Length);$f.Flush($true)}finally{$f.Dispose()}
    $null=Invoke-FixedTool 'logman.exe' @('create','trace',$name,'-pf',$pf,
        '-o',(Join-Path $script:Box 'dns.etl'),'-f','bin','-max','16','-ct','system','-ets')
}
function Stop-DnsTrace {
    if(-not $script:TraceName){return}
    # logman query provides buffer-loss status; unsupported/localized output is
    # not silently treated as zero. Raw query/ETL stay in private storage.
    $query=Invoke-FixedTool 'logman.exe' @('query',$script:TraceName,'-ets')
    Save-New (Join-Path $script:Box 'dns-trace-before-stop.json') @{query=$query}
    $loss=[Stage2TraceControl]::Stop($script:TraceName,(Join-Path $script:Box 'dns.etl'))
    if($loss.Status -ne 0){throw 'ETW native stop failed'}
    $script:TraceName=$null
    Save-New (Join-Path $script:Box 'dns-trace-final-loss.json') $loss
    $after=Invoke-FixedTool 'logman.exe' @('query','-ets')
    if($after -match [regex]::Escape('GikaiMikata-Stage2DNS-'+$script:Binding.run_id)){throw 'ETW stop unconfirmed'}
    $script:TraceLossProven=(-not $loss.Missing -and $loss.EventsLost -eq 0 -and $loss.LogBuffersLost -eq 0 -and $loss.RealTimeBuffersLost -eq 0 -and
        (Get-Item -LiteralPath (Join-Path $script:Box 'dns.etl')).Length -lt 16777216)
}
function Read-DnsTransport($Event,$Data){
    # Classify service ownership BEFORE schema filtering; unknown versions must
    # never vanish from the independent send counter in a mixed-version trace.
    if(-not $Data.ContainsKey('PID')){throw 'Transport owner missing'}
    if([int]$Data.PID -ne $script:Dns.pid){return $null}
    if($Event.Id -cnotin @(42,58) -or $Event.Version -ne 0){throw 'Unsupported DNS service transport schema'}
    if($Event.Id -eq 42){
        $remote=[Net.IPAddress]::new([BitConverter]::GetBytes([uint32]$Data.daddr)).ToString()
    }else{
        $hex=$Data.daddr -replace '[^0-9a-fA-F]',''
        if($hex.Length -ne 32){throw 'Unknown IPv6 ETW encoding'}
        $bytes=New-Object byte[] 16;for($i=0;$i -lt 16;$i++){$bytes[$i]=[Convert]::ToByte($hex.Substring($i*2,2),16)}
        $remote=[Net.IPAddress]::new($bytes).ToString()
    }
    $networkPort=[BitConverter]::ToInt16([BitConverter]::GetBytes([uint16]$Data.dport),0)
    return @{remote=$remote;port=([Net.IPAddress]::NetworkToHostOrder($networkPort) -band 65535)}
}
function Dns-Evidence($Receipt){
    Stop-DnsTrace
    $rows=@(Get-WinEvent -Path (Join-Path $script:Box 'dns.etl') -Oldest)
    $matched=@();$other=@()
    $sends=@();$responses=@()
    foreach($e in $rows){
        [xml]$x=$e.ToXml();$d=@{};foreach($v in $x.Event.EventData.Data){$d[$v.Name]=[string]$v.'#text'}
        $tick=$e.TimeCreated.ToUniversalTime().ToFileTimeUtc()
        if($tick -lt $Receipt.start_tick -or $tick -gt $Receipt.end_tick){continue}
        if($e.ProviderName -ceq 'Microsoft-Windows-Kernel-Network'){
            $transport=Read-DnsTransport $e $d
            if($null -eq $transport){continue}
            if($transport.remote -cnotin $script:Runtime.resolvers -or $transport.port -ne 53){$other+=@($e)}else{$sends+=@($e)}
            continue
        }
        if($e.ProviderName -cne 'Microsoft-Windows-DNS-Client'){continue}
        if([int]$x.Event.System.Execution.ProcessID -ne $script:Dns.pid){continue}
        if($e.Id -eq 3011 -and $d.QueryName -ceq $Receipt.query -and $d.ResponseStatus -notin @('10013','5','1460')){$responses+=@($e)}
        if($e.Id -ne 3010){continue}
        if($d.QueryName -ceq $Receipt.query -and [int]$d.ClientPID -eq $script:Client.pid -and
           $d.DnsServerIpAddress -cin $script:Runtime.resolvers){$matched+=@($e)}else{$other+=@($e)}
    }
    $dnsAfter=Dns-Identity
    # DNS-provider sends alone are not a packet/retry counter. Require actual
    # transport send events with the retained service PID as well. If blocked
    # below this trace point, there is no proof: HOLD, never invent zero sends.
    return @{service_before=$script:Dns;service_after=$dnsAfter;service_send_count=$sends.Count;
        service_send_count_verified=($script:TraceLossProven -and $other.Count -eq 0 -and $responses.Count -eq 0 -and
            $matched.Count -eq $sends.Count -and $sends.Count -ge 1 -and $sends.Count -le 8)}
}
function Invoke-Operation([string]$Operation,$Payload){
    switch -Exact ($Operation){
        'preflight' {return $script:Preflight}
        'read_audit' {return Read-Audit}
        'set_failure' {
            if($Payload.guid -cne $script:Connection.Trim('{}').ToLowerInvariant() -or $Payload.value -isnot [bool]){throw 'Only 5157 failure'}
            if($Payload.value){
                if($script:AuditConsumed){throw 'Audit already consumed'}
                $script:AuditConsumed=$true
                Save-New (Join-Path $script:Box 'audit_intent.json') @{binding=$script:Binding;utc=[DateTime]::UtcNow.ToString('o');original=$script:OriginalAudit}
                Start-DnsTrace
                $null=Invoke-FixedTool 'auditpol.exe' @('/set',('/subcategory:'+$script:Connection),'/failure:enable')
            }else{try{Stop-DnsTrace}finally{$null=Restore-Audit}}
            return $true
        }
        'log_boundary' {return Log-Boundary}
        'export_security' {return Export-Security $Payload.phase}
        'apply_rules' {return Apply-Rules}
        'read_denials' {return Read-Denials $Payload.after $Payload.limit}
        'dns_evidence' {return Dns-Evidence $Payload.receipt}
        'confirm_exit' {
            $c=$Payload.completion
            if($c.run_id -cne $script:Binding.run_id -or $c.plan_sha256 -cne $script:Binding.plan_sha256 -or
               -not $c.termination_confirmed -or -not $c.cleanup_complete -or -not $c.all_descendants_exited){throw 'Termination proof missing'}
            $parametersPath=$script:Runtime.native_parameters_path
            Assert-Private $parametersPath
            if((Get-FileHash -LiteralPath $parametersPath).Hash.ToLowerInvariant() -cne $script:Runtime.native_parameters_sha256){throw 'Native parameters PIN changed'}
            $parameters=Read-FixedJson $parametersPath
            $journal=Join-Path (Join-Path ([IO.Path]::GetDirectoryName($parametersPath)) 'native_run_once') 'journal'
            if([IO.Path]::GetFullPath($parameters.run_root) -ine [IO.Path]::GetDirectoryName($journal)){throw 'Native journal location'}
            if(Test-Path -LiteralPath (Join-Path $journal 'HOLD.json')){throw 'Native persistent HOLD'}
            $donePath=Join-Path $journal 'termination_confirmed.json'
            $done=Read-FixedJson $donePath
            Assert-Completion (Read-FixedJson (Join-Path $journal 'run_started.json')) $done `
                (Read-FixedJson (Join-Path $journal 'supervisor_success.json')) (Get-FileHash -LiteralPath $donePath).Hash.ToLowerInvariant()
            $ack='EXIT-CONFIRMED '+$script:Binding.run_id
            if((Read-Host ('Independently check all target descendants exited; type '+$ack)) -cne $ack){throw 'No operator acknowledgement'}
            $script:ExitConfirmed=$true
            return @{run_id=$script:Binding.run_id;onsite_exit_confirmed=$true}
        }
        'restore_rules' {
            if(-not $script:ExitConfirmed){throw 'Keep isolation; no independent exit confirmation'}
            Assert-Rules
            foreach($name in $script:RuleNames){
                Assert-RulesRemaining
                NetSecurity\Remove-NetFirewallRule -PolicyStore PersistentStore -Name $name -Confirm:$false
                foreach($store in @('ActiveStore','PersistentStore')){if(@(NetSecurity\Get-NetFirewallRule -PolicyStore $store|Where-Object Name -CEQ $name).Count){throw 'Removal unconfirmed'}}
            }
            $same=(Snapshot-Firewall) -ceq $script:FirewallBefore
            return @{removed=$script:RuleNames;both_stores_absent=$true;baseline_unchanged=$same}
        }
        'audit_unchanged' {
            $v=Invoke-FixedTool 'auditpol.exe' @('/get','/category:*','/r')
            return $v -ceq $script:AllAuditBefore
        }
        'finish' {$script:Finished=$true;return $true}
        default {throw 'Unknown privileged operation'}
    }
}
function Invoke-GuardRecovery {
    # One local recovery attempt. Audit rollback is independent of actor stop.
    # Any failure is durable HOLD, never permission to remove Firewall rules.
    $stopped=$false;$restored=$false;$problems=@()
    try {
        if(-not $script:GuardClient.HasExited){
            if($script:GuardClient.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $script:Client.started -or
               $script:GuardClient.MainModule.FileName -ine $script:Client.image){throw 'STOP actor identity changed'}
            $script:GuardClient.Kill()
            if(-not $script:GuardClient.WaitForExit(2000)){throw 'Actor exit unknown; keep Firewall'}
        }
        $stopped=$true
    }catch{$problems+=('stop: '+$_.Exception.Message)}
    try {
        if(Test-Path -LiteralPath (Join-Path $script:Box 'audit_intent.json')){$null=Restore-Audit}
        $restored=$true
    }catch{$problems+=('audit: '+$_.Exception.Message)}
    if($problems.Count){
        $hold=Join-Path $script:Box 'guardian_hold.json'
        if(-not(Test-Path -LiteralPath $hold)){
            Save-New $hold @{binding=$script:Binding;state='HOLD';errors=$problems;
                actor_stopped=$stopped;audit_restored=$restored;firewall_removed=$false}
        }
        Write-Warning 'LOCAL RECOVERY HOLD: retain Firewall; use independent recovery console'
    }
    return ($stopped -and $restored -and $script:GuardAgent.HasExited)
}
function Assert-RulesRemaining {
    # Recovery permits an exact partial delta, but never a changed/foreign rule.
    $prefix='GikaiMikata-Stage2-'+$script:Binding.run_id
    . (Load-RuleValidator)
    foreach($direction in @('Inbound','Outbound')){
        $name=$prefix+'-'+$direction
        $present=@(NetSecurity\Get-NetFirewallRule -PolicyStore PersistentStore|Where-Object Name -CEQ $name)
        if($present.Count -gt 1){throw 'Duplicate rule'}
        if($present.Count -eq 1){Confirm-ExactRule $direction}
    }
}

if($Mode -eq 'SelfTest'){
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile($PSCommandPath,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'PS5.1 syntax'}
    @{mode='syntax_only';passed=1;firewall_operations=0;audit_operations=0;process_launches=0}|ConvertTo-Json -Compress
    return
}
if(-not $script:LiveOsBridgeEnabled){throw 'OS bridge source-disabled; no live operation'}
if($RuntimeSha256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Fixed runtime SHA required'}
$raw=[IO.File]::ReadAllBytes($RuntimePath)
$hash=[Security.Cryptography.SHA256]::Create()
try{$actual=[BitConverter]::ToString($hash.ComputeHash($raw)).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
if($actual -cne $RuntimeSha256){throw 'Runtime SHA differs'}
$script:Runtime=(New-Object Text.UTF8Encoding($false,$true)).GetString($raw).TrimStart([char]0xfeff)|ConvertFrom-Json
$script:ActorSid=$script:Runtime.plan.sid;$script:PrivateRoot=[IO.Path]::GetFullPath($script:Runtime.private_root)
Assert-Private $RuntimePath
$id=[Security.Principal.WindowsIdentity]::GetCurrent()
if($id.User.Value -cne $script:ActorSid -or -not ([Security.Principal.WindowsPrincipal]::new($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'SID1004 local administrator console required'}
$script:Box=[IO.Path]::GetFullPath($script:Runtime.mailbox_root);Assert-Private $script:Box
$script:Binding=[ordered]@{run_id=$script:Runtime.plan.run_id;runtime_sha256=$RuntimeSha256;
    plan_sha256=$script:Runtime.plan.native_plan_sha256;nonce=$script:Runtime.nonce}
if($script:Binding.run_id -cnotmatch '^[0-9a-f]{32}$' -or $script:Binding.nonce -cnotmatch '^[0-9a-f]{64}$'){throw 'Fixed run/nonce'}
foreach($entry in $script:Runtime.controller_code_pins.PSObject.Properties){
    if($entry.Name -match '(^|[/\\])\.\.([/\\]|$)' -or [IO.Path]::IsPathRooted($entry.Name)){throw 'Source PIN path'}
    $path=Join-Path $script:Runtime.code_root $entry.Name;Assert-Private $path
    if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Source PIN mismatch'}
}
$expectedPins=@('__init__','projection','launch_contract','native_launch','stage2_guard','stage2_flow','worker_ipc',
    'stage2_acceptance','stage2_os_adapter','stage2_windows_identity','stage2_native_entry'|ForEach-Object {'data-pipeline/mayor_updates/'+$_+'.py'})
$expectedPins+=@('scripts/Run-Stage2Acceptance.py','scripts/Stage2Worker.py','scripts/Stage2AdminBridge.ps1')
if(@(Compare-Object ($expectedPins|Sort-Object) (@($script:Runtime.controller_code_pins.PSObject.Properties.Name)|Sort-Object) -CaseSensitive).Count -ne 0 -or
   [IO.Path]::GetFullPath($PSCommandPath) -ine [IO.Path]::GetFullPath((Join-Path $script:Runtime.code_root 'scripts\Stage2AdminBridge.ps1'))){throw 'Exact controller PIN set/bridge location required'}
Initialize-NativeTypes
$script:RuleNames=@('Inbound','Outbound'|ForEach-Object {'GikaiMikata-Stage2-'+$script:Binding.run_id+'-'+$_})
$script:RawRecords=@{};$script:TraceName=$null;$script:TraceLossProven=$false;$script:Finished=$false;$script:AuditConsumed=$false;$script:ExitConfirmed=$false
$script:OriginalAudit=Read-Audit
if($Mode -eq 'Recover'){
    $intent=Read-FixedJson (Join-Path $script:Box 'audit_intent.json');Assert-Binding $intent.binding
    foreach($v in $intent.original.PSObject.Properties){if($v.Value.success -or $v.Value.failure){throw 'Recovery original not approved'}}
    $script:OriginalAudit=[ordered]@{($script:Connection.Trim('{}').ToLowerInvariant())=@{success=$false;failure=$false};($script:Packet.Trim('{}').ToLowerInvariant())=@{success=$false;failure=$false}}
}elseif(@($script:OriginalAudit.Values|Where-Object {$_.success -or $_.failure}).Count){throw 'Audit original differs'}
$script:Client=Read-FixedJson (Join-Path $script:Box 'client_identity.json')
Import-Module (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules\NetSecurity\NetSecurity.psd1')
if($Mode -eq 'Recover'){
    # Do this BEFORE any process/service inspection, even if the client is gone.
    $null=Restore-Audit
    if($StopActor){
        $live=@(Get-Process -Id $script:Client.pid -ErrorAction SilentlyContinue)
        if($live.Count){
            $p=$live[0];$null=$p.Handle
            if($p.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $script:Client.started -or $p.MainModule.FileName -ine $script:Client.image){throw 'Unverified process; keep isolation'}
            $p.Kill();if(-not $p.WaitForExit(2000)){throw 'Process exit unconfirmed'}
        }
    }
    if($RestoreFirewall){
        Assert-RulesRemaining
        $ack='EXIT-CONFIRMED '+$script:Binding.run_id
        if((Read-Host ('Check every target descendant AND pending DNS work; type '+$ack)) -cne $ack){throw 'Keep isolation'}
        foreach($name in $script:RuleNames){
            Assert-RulesRemaining
            if(@(NetSecurity\Get-NetFirewallRule -PolicyStore PersistentStore|Where-Object Name -CEQ $name).Count){NetSecurity\Remove-NetFirewallRule -PolicyStore PersistentStore -Name $name -Confirm:$false}
            foreach($store in @('ActiveStore','PersistentStore')){
                if(@(NetSecurity\Get-NetFirewallRule -PolicyStore $store|Where-Object Name -CEQ $name).Count){throw 'Exact removal not confirmed'}
            }
        }
    }
    return
}
$claimed=$script:Client
$script:Client=Process-Identity $script:Client.pid $script:ActorSid $script:Runtime.controller_image.path $script:Runtime.controller_image.sha256
if($claimed.started -ne $script:Client.started){throw 'Client PID reused'}
$clientHandle=[Diagnostics.Process]::GetProcessById($script:Client.pid);$null=$clientHandle.Handle;$script:Streams.Add($clientHandle)
if([Stage2TraceControl]::Elevated($clientHandle.Handle)){throw 'Elevated client refused'}
$script:Dns=Dns-Identity
if($Mode -eq 'Guard'){
    $parentNumber=(Get-CimInstance Win32_Process -Filter ('ProcessId='+$PID)).ParentProcessId
    $agent=[Diagnostics.Process]::GetProcessById($parentNumber);$null=$agent.Handle;$script:Streams.Add($agent)
    if($agent.MainModule.FileName -ine $script:Runtime.administrator.path -or -not [Stage2TraceControl]::Elevated($agent.Handle)){throw 'Guardian parent mismatch'}
    $me=[Diagnostics.Process]::GetCurrentProcess()
    Save-New (Join-Path $script:Box 'guard_ready.json') @{binding=$script:Binding;identity=@{pid=$me.Id;started=$me.StartTime.ToUniversalTime().ToFileTimeUtc();image=$me.MainModule.FileName;sid=$script:ActorSid}}
    # Independent physical console/process. Never auto-remove Firewall rules.
    $script:GuardClient=$clientHandle;$script:GuardAgent=$agent
    $guardComplete=$false
    while(-not(Test-Path -LiteralPath (Join-Path $script:Box 'finished.json'))){
        $intent=Join-Path $script:Box 'audit_intent.json';$stop=Join-Path $script:Box 'STOP.json'
        if($clientHandle.HasExited -or (Test-Path -LiteralPath $stop) -or ((Test-Path -LiteralPath $intent) -and
           ([DateTime]::UtcNow-[DateTime](Read-FixedJson $intent).utc).TotalSeconds -ge 45)){
            if(-not(Test-Path -LiteralPath $stop)){Save-New $stop @{binding=$script:Binding;reason='independent_guard_stop'}}
            $guardComplete=Invoke-GuardRecovery
            if($guardComplete){Save-New (Join-Path $script:Box 'guard_restored.json') @{audit_restored=$true;firewall_removed=$false;agent_exited=$true}}
        }
        if($guardComplete){break}
        Start-Sleep -Milliseconds 100
    }
    return
}
# Start a fixed independent guardian process BEFORE accepting any audit request.
# It is management infrastructure, never the worker/leaf or part of their Job.
$guardPath=Join-Path $script:Box 'guard_ready.json'
if(Test-Path -LiteralPath $guardPath){throw 'Guardian collision'}
$exe=$script:Runtime.administrator.path
if($exe -ine (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -or
   (Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant() -cne $script:Runtime.administrator.sha256){throw 'Fixed guardian host PIN'}
foreach($value in @($PSCommandPath,$RuntimePath)){if($value -match '[\r\n"\x00]'){throw 'Unsafe fixed guardian path'}}
$info=New-Object Diagnostics.ProcessStartInfo
$info.FileName=$exe
$info.Arguments='-NoProfile -NonInteractive -File "'+$PSCommandPath+'" -Mode Guard -RuntimePath "'+$RuntimePath+'" -RuntimeSha256 '+$RuntimeSha256
$info.UseShellExecute=$false;$info.CreateNoWindow=$true
$guardProcess=[Diagnostics.Process]::Start($info);$script:Streams.Add($guardProcess)
$wait=[Diagnostics.Stopwatch]::StartNew()
while(-not(Test-Path -LiteralPath $guardPath)){
    if($guardProcess.HasExited -or $wait.Elapsed.TotalSeconds -ge 10){throw 'Guardian failed to arm'}
    Start-Sleep -Milliseconds 20
}
$guard=Read-FixedJson (Join-Path $script:Box 'guard_ready.json');Assert-Binding $guard.binding
if($guard.identity.pid -ne $guardProcess.Id -or $guard.identity.started -ne $guardProcess.StartTime.ToUniversalTime().ToFileTimeUtc() -or
   $guardProcess.MainModule.FileName -ine $exe -or -not [Stage2TraceControl]::Elevated($guardProcess.Handle)){throw 'Guardian process/token mismatch'}
$script:StartBoundary=@{latest=0};$script:StartBoundary=Log-Boundary
$script:AllAuditBefore=Invoke-FixedTool 'auditpol.exe' @('/get','/category:*','/r')
$script:FirewallBefore=Snapshot-Firewall
$proofPath=$script:Runtime.preblock_proof.path;Assert-Private $proofPath
if((Get-FileHash -LiteralPath $proofPath).Hash.ToLowerInvariant() -cne $script:Runtime.preblock_proof.sha256){throw 'Accepted preblock proof PIN'}
$proof=Read-FixedJson $proofPath
$policyKey=Get-Item -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa'
$gpoOk=($proof.gpresult_exit -eq 0 -and $proof.errors.Count -eq 0 -and -not $proof.computer.PartOfDomain -and
    -not (Get-CimInstance Win32_ComputerSystem).PartOfDomain -and $proof.local_audit_csv.Count -eq 0 -and
    $policyKey.GetValue('SCENoApplyLegacyAuditPolicy',$null) -eq $proof.force_subcategory_value -and
    -not (Test-Path -LiteralPath (Join-Path $env:SystemRoot 'System32\GroupPolicy\Machine\Microsoft\Windows NT\Audit\audit.csv')) -and
    -not (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\PolicyManager\current\device\Audit'))
if(-not $gpoOk){throw 'GPO/MDM state unproven or changed'}
$handoff='RECOVERY-READY '+$script:Binding.run_id
if((Read-Host ('Open LOCAL_RECOVERY.txt; confirm local attendance, business window and no unknown bypass; type '+$handoff)) -cne $handoff){throw 'Local recovery handoff absent'}
Save-New (Join-Path $script:Box 'operator_setup.json') @{binding=$script:Binding;typed_input=$handoff;is_approval_signature=$false}
$addresses=@(Get-DnsClientServerAddress|Where-Object {$_.InterfaceAlias -ceq $script:Runtime.interface}|ForEach-Object {$_.ServerAddresses}|Sort-Object -Unique)
if(($addresses -join ',') -cne (@($script:Runtime.resolvers|Sort-Object -Unique) -join ',')){throw 'Resolver snapshot changed'}
if(@(NetSecurity\Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True|Where-Object OverrideBlockRules -EQ True).Count){throw 'Authenticated bypass'}
if(@(NetSecurity\Get-NetIPsecMainModeSA).Count -or @(NetSecurity\Get-NetIPsecQuickModeSA).Count){throw 'IPsec path not excluded'}
foreach($name in $script:RuleNames){if(@(NetSecurity\Get-NetFirewallRule -PolicyStore ActiveStore|Where-Object Name -CEQ $name).Count){throw 'Rule collision'}}
$script:Preflight=@{owner_only=$true;recovery_local=$true;source_pins_valid=$true;existing_rules_absent=$true;
    gpo_audit_unmanaged=$gpoOk;bypass_paths_excluded=$true;
    resolvers=$addresses;dns=$script:Dns;restore_watchdog_ready=$true;guardian=$guard.identity}
$me=[Diagnostics.Process]::GetCurrentProcess()
Save-New (Join-Path $script:Box 'agent_ready.json') @{binding=$script:Binding;identity=@{pid=$me.Id;started=$me.StartTime.ToUniversalTime().ToFileTimeUtc();image=$me.MainModule.FileName;sid=$script:ActorSid}}
$sequence=1
try{
    while(-not $script:Finished){
        if(Test-Path -LiteralPath (Join-Path $script:Box 'STOP.json')){throw 'Independent STOP'}
        $path=Join-Path $script:Box ('request-{0:d4}.json' -f $sequence)
        if(-not(Test-Path -LiteralPath $path)){Start-Sleep -Milliseconds 20;continue}
        $r=Read-FixedJson $path 65536
        Assert-Binding $r.binding
        if($r.sequence -ne $sequence){throw 'Request sequence'}
        $reply=@{binding=$script:Binding;sequence=$sequence;operation=$r.operation;ok=$false}
        try{$reply.result=Invoke-Operation $r.operation $r.payload;$reply.ok=$true}catch{$reply.error=$_.Exception.Message}
        Save-New (Join-Path $script:Box ('response-{0:d4}.json' -f $sequence)) $reply
        $sequence++
    }
}finally{
    # Stop/restore are independent. A trace-stop error cannot skip audit rollback.
    try{Stop-DnsTrace}finally{if($script:AuditConsumed){$null=Restore-Audit}}
    if($script:Finished){Save-New (Join-Path $script:Box 'finished.json') @{binding=$script:Binding;audit_restored=$true}}
    foreach($s in $script:Streams){$s.Dispose()}
}
