#requires -Version 5.1
# Preparation only: emits console text, never imports NetSecurity or runs it.
[CmdletBinding()]
param([string]$RunId,[string]$ObservedRulesPath,[string]$ExpectedSnapshotSha256,[switch]$SelfTest)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Assert-RecoverySnapshot {
    param([string]$Id,$Rows)
    if($Id -cnotmatch '^[0-9a-f]{32}$'){throw 'Fixed run ID required'}
    if(@($Rows).Count -ne 2){throw 'Exact two-rule snapshot required'}
    $prefix='GikaiMikata-Stage2-'+$Id
    foreach($direction in @('Inbound','Outbound')){
        $row=@($Rows|Where-Object {$_.Name -ceq ($prefix+'-'+$direction)})
        if($row.Count -ne 1){throw 'Missing/duplicate/foreign rule'}
        $expected=@{Name=$prefix+'-'+$direction;Group=$prefix;Direction=$direction;Action='Block';
            Enabled='True';Profile='Any';Program='Any';Service='Any';Protocol='Any';
            LocalAddress='Any';RemoteAddress='Any';LocalPort='Any';RemotePort='Any';
            LocalUser='Any';RemoteUser='Any';OverrideBlockRules='False'}
        if(@($row[0].PSObject.Properties).Count -ne $expected.Count){throw 'Unexpected rule snapshot structure'}
        foreach($key in $expected.Keys){
            $property=$row[0].PSObject.Properties[$key]
            if($null -eq $property -or $property.Value -isnot [string] -or $property.Value -cne $expected[$key]){
                throw ('Recovery filter differs: '+$key)
            }
        }
    }
}

function New-ManualRecoveryText {
    param([string]$Id,[string]$SnapshotSha)
    if($Id -cnotmatch '^[0-9a-f]{32}$' -or $SnapshotSha -cnotmatch '^[0-9a-f]{64}$'){throw 'Fixed recovery identity required'}
    # Only validated hex is substituted. This is never Invoke-Expression'd here.
    $template=@'
# MANUAL CONSOLE TEXT ONLY. Requires separate PM/representative Stage 2 GO.
# Use local administrator Windows PowerShell 5.1 -NoProfile; no network required.
# Expected approved saved-snapshot SHA256: __SNAPSHOT__
# If Job/descendant exit is unknown: KEEP BLOCKING. Do not execute this program.
# A locally verified reboot is the contingency only if separately approved.
& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference='Stop'
    $id='__RUN__';$prefix='GikaiMikata-Stage2-'+$id
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    if(-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Local administrator required'}
    Import-Module 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules\NetSecurity\NetSecurity.psd1' -ErrorAction Stop
    if((Get-Module NetSecurity).Path -ine 'C:\Windows\System32\WindowsPowerShell\v1.0\Modules\NetSecurity\NetSecurity.psd1'){throw 'Fixed local NetSecurity module required'}
    function Confirm-ExactRule([string]$Direction){
        $name=$prefix+'-'+$Direction
        foreach($store in @('ActiveStore','PersistentStore')){
        $r=@(NetSecurity\Get-NetFirewallRule -PolicyStore $store -Name $name -ErrorAction Stop)
        if($r.Count -ne 1 -or $r[0].PolicyStoreSourceType.ToString() -cne 'Local'){throw 'Exact local rule required'}
        $r=$r[0]
        $a=$r|NetSecurity\Get-NetFirewallApplicationFilter
        $s=$r|NetSecurity\Get-NetFirewallServiceFilter
        $p=$r|NetSecurity\Get-NetFirewallPortFilter
        $d=$r|NetSecurity\Get-NetFirewallAddressFilter
        $u=$r|NetSecurity\Get-NetFirewallSecurityFilter
        $i=$r|NetSecurity\Get-NetFirewallInterfaceFilter
        $t=$r|NetSecurity\Get-NetFirewallInterfaceTypeFilter
        if($r.Name -cne $name -or $r.Group -cne $prefix -or $r.Direction.ToString() -cne $Direction -or
           $r.Action.ToString() -cne 'Block' -or $r.Enabled.ToString() -cne 'True' -or $r.Profile.ToString() -cne 'Any' -or
           $a.Program -cne 'Any' -or ($a.Package -and $a.Package -cne 'Any') -or $s.Service -cne 'Any' -or
           $p.Protocol.ToString() -cne 'Any' -or (@($p.LocalPort)-join ',') -cne 'Any' -or (@($p.RemotePort)-join ',') -cne 'Any' -or
           (@($d.LocalAddress)-join ',') -cne 'Any' -or (@($d.RemoteAddress)-join ',') -cne 'Any' -or
           $u.LocalUser -cne 'Any' -or $u.RemoteUser -cne 'Any' -or $r.OverrideBlockRules.ToString() -cne 'False' -or
           (@($i.InterfaceAlias)-join ',') -cne 'Any' -or $t.InterfaceType.ToString() -cnotin @('Any','0')){
            throw 'Observed recovery rule differs; keep isolation for local handling'
        }
        }
    }
    # Review BOTH rules before touching either. No wildcard/group/reset/import.
    Confirm-ExactRule 'Inbound';Confirm-ExactRule 'Outbound'
    if((Read-Host ('After independently verifying all target processes exited, type EXIT-CONFIRMED '+$id)) -cne ('EXIT-CONFIRMED '+$id)){throw 'Manual acknowledgement absent'}
    foreach($direction in @('Inbound','Outbound')){
        Confirm-ExactRule $direction
        $name=$prefix+'-'+$direction
        NetSecurity\Remove-NetFirewallRule -PolicyStore PersistentStore -Name $name -Confirm:$false -ErrorAction Stop
        if(@(NetSecurity\Get-NetFirewallRule -PolicyStore PersistentStore -ErrorAction Stop|Where-Object {$_.Name -ceq $name}).Count -ne 0 -or
           @(NetSecurity\Get-NetFirewallRule -PolicyStore ActiveStore -ErrorAction Stop|Where-Object {$_.Name -ceq $name}).Count -ne 0){throw 'Removal not confirmed; no broad fallback'}
    }
    'Exact Stage 2 delta removed; compare the saved baseline before resuming work.'
}
'@
    return $template.Replace('__RUN__',$Id).Replace('__SNAPSHOT__',$SnapshotSha)
}

if($SelfTest){
    function Get-NetFirewallRule {throw 'Real Firewall read forbidden'}
    function Remove-NetFirewallRule {throw 'Real Firewall mutation forbidden'}
    $id='a'*32;$prefix='GikaiMikata-Stage2-'+$id
    $rows=@(foreach($direction in @('Inbound','Outbound')){[pscustomobject]@{
        Name=$prefix+'-'+$direction;Group=$prefix;Direction=$direction;Action='Block';Enabled='True';Profile='Any';
        Program='Any';Service='Any';Protocol='Any';LocalAddress='Any';RemoteAddress='Any';LocalPort='Any';RemotePort='Any';
        LocalUser='Any';RemoteUser='Any';OverrideBlockRules='False'}})
    Assert-RecoverySnapshot $id $rows
    $passed=1
    foreach($case in @('foreign','duplicate','program','missing','protocol','bypass','scope')){
        $copy=@(foreach($row in $rows){$row|ConvertTo-Json|ConvertFrom-Json})
        switch($case){'foreign'{$copy[0].Name='foreign'};'duplicate'{$copy[1]=$copy[0]};
            'program'{$copy[0].Program='other.exe'};'missing'{$copy[0].PSObject.Properties.Remove('Program')};
            'protocol'{$copy[0].Protocol='TCP'};'bypass'{$copy[0].OverrideBlockRules='True'};'scope'{$copy[0].RemoteAddress='1.1.1.1'}}
        $blocked=$false;try{Assert-RecoverySnapshot $id $copy}catch{$blocked=$true}
        if(-not $blocked){throw ('Unsafe recovery snapshot accepted: '+$case)};$passed++
    }
    $program=New-ManualRecoveryText $id ('b'*64)
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseInput($program,[ref]$tokens,[ref]$errors)
    if(@($errors).Count -ne 0){throw 'Generated PS5.1 recovery text has syntax errors'}
    if($program -notmatch 'EXIT-CONFIRMED' -or $program -match 'Invoke-Expression|netsh|Reset-Net'){throw 'Unsafe manual program'}
    @{mode='synthetic_preparation_only';passed=($passed+1);firewall_reads=0;firewall_writes=0;generated_program_executions=0}|ConvertTo-Json -Compress
    return
}
if(-not $ObservedRulesPath -or $ExpectedSnapshotSha256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Approved saved two-rule snapshot SHA required'}
$stream=[IO.File]::Open($ObservedRulesPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{
    if($stream.Length -gt 16384){throw 'Snapshot size outside bound'}
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try{$actual=[BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
    if($actual -cne $ExpectedSnapshotSha256){throw 'Saved snapshot SHA differs'}
    $stream.Position=0;$reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true,1024,$true)
    try{$rows=@(foreach($row in ($reader.ReadToEnd()|ConvertFrom-Json)){$row})}finally{$reader.Dispose()}
    Assert-RecoverySnapshot $RunId $rows
    New-ManualRecoveryText $RunId $actual  # plain text only; never executed
}finally{$stream.Dispose()}
