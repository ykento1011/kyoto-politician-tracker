# Exports a DISABLED task definition. Does not register, enable or modify any task.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$PythonExe,
    [Parameter(Mandatory)][string]$DataPipelineRoot,
    [Parameter(Mandatory)][string]$RuntimeFile,
    [Parameter(Mandatory)][string]$OutputXml
)
$ErrorActionPreference = 'Stop'
if ((Get-TimeZone).Id -ne 'Tokyo Standard Time') { throw 'This job requires the Windows JST time zone' }
$pythonPath = (Resolve-Path -LiteralPath $PythonExe).Path
$pipelinePath = (Resolve-Path -LiteralPath $DataPipelineRoot).Path
$runtimePath = (Resolve-Path -LiteralPath $RuntimeFile).Path
$target = [IO.Path]::GetFullPath($OutputXml)
if (Test-Path -LiteralPath $target) { throw 'Choose a new task definition output file' }
$parent = Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($target))
for ($node=$parent; $null -ne $node; $node=$node.Parent) {
    if ((Test-Path -LiteralPath (Join-Path $node.FullName '.git')) -or $node.Name -eq 'public') {
        throw 'Task definitions with private paths must stay outside repositories/public directories'
    }
}
$actor=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=Get-Acl -LiteralPath $parent.FullName
$owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
$foreign=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | Where-Object { $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Value -ne $owner })
if ($owner -ne $actor -or $foreign.Count) { throw 'Owner-only destination required' }
$runtime=Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
if ($runtime.network_enabled -ne $false) { throw 'Prepare the disabled job before separately approving live activation' }
function XmlText([string]$value) { [Security.SecurityElement]::Escape($value) }
$start=[DateTime]::Today.AddHours(9)
$days=(8-[int]$start.DayOfWeek)%7
$start=$start.AddDays($days)
if ($start -le (Get-Date)) { $start=$start.AddDays(7) }
$boundary=$start.ToString('yyyy-MM-ddTHH:mm:ss')+'+09:00'
$arguments='-B -m mayor_updates.weekly --runtime "'+$runtimePath+'"'
$xml=@"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Kyoto mayor tracker: private HTML monitoring only. Publication is separate.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>$boundary</StartBoundary><Enabled>true</Enabled><ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><Monday /></DaysOfWeek></ScheduleByWeek></CalendarTrigger></Triggers>
  <Principals><Principal id="Owner"><UserId>$actor</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable><Enabled>false</Enabled><ExecutionTimeLimit>PT5M</ExecutionTimeLimit></Settings>
  <Actions Context="Owner"><Exec><Command>$(XmlText $pythonPath)</Command><Arguments>$(XmlText $arguments)</Arguments><WorkingDirectory>$(XmlText $pipelinePath)</WorkingDirectory></Exec></Actions>
</Task>
"@
[void][xml]$xml
[IO.File]::WriteAllText($target,$xml,[Text.Encoding]::Unicode)
Write-Output "Exported disabled weekly task: $target"
