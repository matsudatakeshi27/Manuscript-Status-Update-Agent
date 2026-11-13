
$ErrorActionPreference = "Stop"

Write-Host "Configuring ScholarOne Monitor schedule..."

$ProjectDir = $PSScriptRoot
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$MonitorScript = Join-Path $ProjectDir "src\monitor.py"

if (-not (Test-Path $PythonExe)) {
    throw "Python environment not found. Run install_windows.ps1 first."
}

# Locate private configuration file
$ConfigPath = (& $PythonExe -c "import sys; sys.path.insert(0, 'src'); from paths import CONFIG_FILE; print(CONFIG_FILE)").Trim()

if (-not (Test-Path $ConfigPath)) {
    throw "Configuration file not found: $ConfigPath"
}

# Read monitoring interval
$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$Hours = $Config.monitoring_interval_hours

if ($null -eq $Hours -or $Hours -le 0) {
    throw "Invalid monitoring_interval_hours in config.json."
}

$Interval = [TimeSpan]::FromHours($Hours)

if ($Interval.TotalMinutes -lt 1) {
    throw "Minimum monitoring interval is one minute."
}

# Create scheduled task
$TaskName = "ScholarOne Manuscript Monitor"

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$MonitorScript`"" `
    -WorkingDirectory $ProjectDir

$StartTime = (Get-Date).AddMinutes(1)

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $StartTime `
    -RepetitionInterval $Interval `
    -RepetitionDuration (New-TimeSpan -Days 3650)

# Run only while the user is logged in.
# This allows access to the user's browser and credentials.
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings

Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $Task `
    -Force | Out-Null

Write-Host ""
Write-Host "Scheduled task successfully created."
Write-Host "Task: $TaskName"
Write-Host "Interval: Every $Hours hours"
Write-Host "Project: $ProjectDir"
Write-Host ""
Write-Host "The task runs while your Windows account is logged in."
