#requires -Version 5.1
# Synthetic CI harness, not an execution or recovery tool. No OS ACL changes.
param([Parameter(Mandatory=$true)][string]$FixtureRoot,
      [ValidateSet('positive','missing_program','changed_program')][string]$Case='positive')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$base=[IO.Path]::GetFullPath($FixtureRoot).TrimEnd('\')
$stage2SyntheticFixtureBoundary=$base
$request=Get-Content -LiteralPath (Join-Path $base 'restore_request.json') -Raw|ConvertFrom-Json
$journal=Join-Path $base $request.journal_directory
$plan=Join-Path $base $request.plan_file
if(-not (Get-Content -LiteralPath $plan -Raw|ConvertFrom-Json).synthetic){throw 'Synthetic plan only'}
$release=Get-Content -LiteralPath (Join-Path $journal 'operator_release.json') -Raw|ConvertFrom-Json
if($release.synthetic_test_only -ne $true){throw 'Synthetic operator fixture required'}
$observedPath=Join-Path $journal 'observed.json'
if($Case -ne 'positive'){
    $rows=@(foreach($row in (Get-Content -LiteralPath $observedPath -Raw|ConvertFrom-Json)){$row})
    if($Case -eq 'missing_program'){$rows[0].PSObject.Properties.Remove('Program')}
    else{$rows[0].Program='unapproved.exe'}
    $rows|ConvertTo-Json -Depth 10|Set-Content -LiteralPath $observedPath -Encoding UTF8
}
$stage2SyntheticCounters=@{reads=0;writes=0}
function Get-NetFirewallRule {$stage2SyntheticCounters.reads++;throw 'Firewall reads forbidden'}
function Remove-NetFirewallRule {$stage2SyntheticCounters.writes++;throw 'Firewall writes forbidden'}
# Only the private-input ACL observation is synthetic. Execute the unchanged
# product path containment, file locking, held-byte hashes and journal validator.
# Never create/change an OS ACL or claim this fixture proves actual ownership.
function Get-Acl {
    param([string]$LiteralPath)
    $full=[IO.Path]::GetFullPath($LiteralPath)
    if(-not $full.StartsWith($stage2SyntheticFixtureBoundary+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside synthetic fixture'}
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetOwner($sid)
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','Allow')))
    return $acl
}
try {
    $result=& (Join-Path $PSScriptRoot 'Restore-Stage2Firewall.ps1') -PlanPath $plan `
        -ExpectedPlanSha256 $request.plan_sha256 -JournalRoot $journal `
        -ObservedRulesPath $observedPath | ConvertFrom-Json
} catch {
    if($Case -eq 'positive' -or $_.Exception.Message -notmatch 'Program|Observed rule differs') {throw}
    if($stage2SyntheticCounters.reads -ne 0 -or $stage2SyntheticCounters.writes -ne 0){throw 'Firewall access attempted'}
    @{handoff='HOLD';expected_negative=$Case;firewall_reads=0;firewall_writes=0}|ConvertTo-Json -Compress
    return
}
if($Case -ne 'positive'){throw 'Unsafe observed rule accepted'}
if($result.mode -cne 'dry_run' -or @($result.would_remove).Count -ne 2 -or
   $result.firewall_writes -ne 0 -or $result.automatic_restore -ne $false -or
   $stage2SyntheticCounters.reads -ne 0 -or $stage2SyntheticCounters.writes -ne 0){throw 'Offline handoff contract failed'}
@{handoff='PASS';acl_observation='synthetic';firewall_reads=$stage2SyntheticCounters.reads;firewall_writes=$stage2SyntheticCounters.writes}|ConvertTo-Json -Compress
