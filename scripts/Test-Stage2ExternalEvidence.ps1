#requires -Version 5.1
# Synthetic binary fixtures only. No native identity API, external tools or live entry.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Stage2AdminBridge.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Syntax'}
foreach($name in @('Accept-ExternalEvidence','Copy-ExternalStream','Assert-ExternalSecurity','New-EvidenceSecurity','Assert-EvidenceSecurity','Assert-Binding')){
 $node=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$false))
 if($node.Count -ne 1){throw 'Pure function boundary'}
 . ([scriptblock]::Create($node[0].Extent.Text))
}
$script:ActorSid='S-1-5-21-111-222-333-1004'
$script:Binding=@{run_id=('a'*32);nonce=('b'*64);plan_sha256=('c'*64);runtime_sha256=('d'*64)}
$script:Runtime=[pscustomobject]@{system_tools=[pscustomobject]@{'wevtutil.exe'=('e'*64);'logman.exe'=('f'*64)}}
$root=Join-Path ([IO.Path]::GetTempPath()) ('external-fixture-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root)
$script:Pass=0;$script:Holds=0;$script:Case='';$script:Meta=@{}
function Check($ok,$name){if(-not $ok){throw $name};$script:Pass++}
function Assert-Private([string]$Path){if($script:Case -eq 'parent' -or -not $Path.StartsWith($root,[StringComparison]::Ordinal)){throw 'Parent scope'}}
function Assert-EvidenceFile([string]$Path){Assert-Private $Path;Assert-EvidenceSecurity $script:Meta[$Path].security}
function Open-ExternalEvidence([string]$Path){
 if($script:Case -eq 'busy' -and $Path -ceq $script:Raw){throw 'Writer still open'}
 return [IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
}
function Get-ExternalIdentity($Stream){
 if($Stream.Name -ceq $script:Raw){
  $script:RawIdentityReads++
  if($script:Case -in @('reparse','links','identity_api')){throw 'Unverified native identity'}
  if($script:Case -eq 'changed_id' -and $script:RawIdentityReads -gt 1){return 'different'}
 }
 return $script:Meta[$Stream.Name].id
}
function Get-ExternalSecurity($Stream){return $script:Meta[$Stream.Name].security}
function New-EvidenceStream([string]$Path,$Security){
 if($script:Case -eq 'owner_rejected'){throw 'Owner rejected'}
 $script:Meta[$Path]=@{id=[guid]::NewGuid().ToString();security=$Security}
 return [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
}
function Publish-Evidence([string]$Temporary,[string]$Path){
 if($script:Case -eq 'publication'){throw 'Publication failure'}
 if($script:Case -eq 'race'){[IO.File]::WriteAllText($Path,'preexisting')}
 [IO.File]::Move($Temporary,$Path);$script:Meta[$Path]=$script:Meta[$Temporary]
}
function Save-New([string]$Path,$Value){
 if($script:Case -eq 'provenance'){throw 'Provenance save failed'}
 $bytes=[Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 16))
 $f=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
$script:RealCopy=${function:Copy-ExternalStream}
function Copy-ExternalStream($Source,$Destination,[long]$Limit){
 $script:Copies++
 if($script:Case -eq 'partial' -and $null -ne $Destination){$Destination.WriteByte(1);throw 'Partial write'}
 $v=& $script:RealCopy $Source $Destination $Limit
 if(($script:Case -eq 'raw_hash' -and $script:Copies -eq 2) -or ($script:Case -eq 'derived_hash' -and $script:Copies -eq 3) -or ($script:Case -eq 'final_hash' -and $script:Copies -eq 4)){$v.sha256='bad'}
 return $v
}
try{
 foreach($case in @('evtx_ok','etl_ok','wrong_owner','extra_ace','reparse','links','identity_api','changed_id','busy','parent','owner_rejected','partial','raw_hash','derived_hash','final_hash','publication','race','provenance','bad_pin','bad_binding','incomplete','loss','empty','oversize','scope')){
  $script:Case=$case;$script:Copies=0;$script:RawIdentityReads=0
  $script:Streams=New-Object 'System.Collections.Generic.List[System.IDisposable]'
  $script:Box=Join-Path $root $case;$null=[IO.Directory]::CreateDirectory($script:Box)
  $kind=if($case -in @('etl_ok','loss')){'etl'}else{'evtx'}
  $phase=if($kind -eq 'etl'){'dns'}else{'before'}
  $script:Raw=Join-Path $script:Box ($phase+'.'+$kind)
  $length=if($case -eq 'oversize'){33554433}elseif($case -eq 'empty'){0}elseif($case -eq 'evtx_ok'){3145728}else{32769}
  $f=[IO.File]::Open($script:Raw,[IO.FileMode]::CreateNew);try{$f.SetLength($length)}finally{$f.Dispose()}
  $before=(Get-FileHash -LiteralPath $script:Raw).Hash
  $security=New-EvidenceSecurity;$security.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
  if($case -eq 'wrong_owner'){$security.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-19'))}
  if($case -eq 'extra_ace'){$security.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-1-0'),'Read','Allow'))}
  $script:Meta[$script:Raw]=@{id='raw-'+$case;security=$security}
  $tool=if($kind -eq 'etl'){'logman.exe'}else{'wevtutil.exe'}
  $completion=[pscustomobject]@{binding=[pscustomobject]$script:Binding;tool=$tool;tool_sha256=$script:Runtime.system_tools.$tool;exit_code=0;status=0;missing=$false;stopped=$true;events_lost=0;buffers_lost=0;realtime_lost=0}
  if($case -eq 'bad_pin'){$completion.tool_sha256='wrong'}
  if($case -eq 'bad_binding'){$completion.binding=[pscustomobject]@{run_id='wrong'}}
  if($case -eq 'incomplete'){$completion.exit_code=1}
  if($case -eq 'loss'){$completion.events_lost=1}
  if($case -eq 'scope'){$phase='foreign'}
  $held=$false;$result=$null
  try{$result=Accept-ExternalEvidence $kind $phase $completion}catch{$held=$true}
  finally{foreach($stream in $script:Streams){$stream.Dispose()}}
  if($case.EndsWith('_ok')){
   Check (-not $held) ($case+' unexpectedly HOLD')
   Check ((Get-FileHash -LiteralPath $result).Hash -ceq $before) 'Exact derived bytes'
   $record=Get-Content -Raw -LiteralPath ($result+'.provenance.json')|ConvertFrom-Json
   Check ($record.length -eq $length -and -not $record.raw_modified) 'Provenance'
  }else{Check $held ($case+' must HOLD');$script:Holds++}
  Check ((Get-FileHash -LiteralPath $script:Raw).Hash -ceq $before) 'Original preserved'
 }
}finally{
 foreach($dir in [IO.Directory]::GetDirectories($root)){foreach($file in [IO.Directory]::GetFiles($dir)){[IO.File]::Delete($file)};[IO.Directory]::Delete($dir)}
 [IO.Directory]::Delete($root)
}
@{pass=$script:Pass;expected_hold=$script:Holds;external_tools=0;native_identity_api=0;stage2=0}|ConvertTo-Json -Compress
