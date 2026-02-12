# setup_scheduler.ps1
# Registers a Windows Task Scheduler job that runs the newsletter every Monday at 8:00 AM.
#
# Run once from the project root (requires no elevation):
#   powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1

$TaskName   = "AI Newsletter - Weekly"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile  = Join-Path $ScriptDir "newsletter\run_newsletter.bat"

if (-not (Test-Path $BatchFile)) {
    Write-Error "Batch file not found: $BatchFile"
    exit 1
}

# Remove existing task with the same name (idempotent re-registration)
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

# Trigger: every Monday at 08:00 AM
$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday `
    -At "08:00AM"

# Action: run the batch file via cmd.exe (so the .bat runs in a proper shell)
$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchFile`""

# Settings: run whether or not user is logged on, don't stop if on battery
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -WakeToRun

# Principal: run as current user
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Trigger   $Trigger `
    -Action    $Action `
    -Settings  $Settings `
    -Principal $Principal `
    -Description "Generates and emails the weekly AI & Data Engineering newsletter every Monday at 8:00 AM." | Out-Null

Write-Host ""
Write-Host "[OK] Scheduled task registered: '$TaskName'"
Write-Host "     Runs every Monday at 08:00 AM"
Write-Host "     Batch file: $BatchFile"
Write-Host ""
Write-Host "To verify: open Task Scheduler and look under 'Task Scheduler Library'"
Write-Host "To test immediately: Right-click the task → Run"
