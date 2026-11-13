
$ErrorActionPreference = "Stop"

Write-Host "ScholarOne Monitor - Windows Setup"

$ProjectDir = $PSScriptRoot
$VenvDir = Join-Path $ProjectDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

# Find Python
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $Python) {
    throw "Python 3 is required. Install it from https://www.python.org/downloads/"
}

# Create virtual environment
if (-not (Test-Path $PythonExe)) {
    & $Python.Source -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

# Install dependencies
& $PythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Pip upgrade failed." }

& $PythonExe -m pip install -r (Join-Path $ProjectDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

# Install Playwright Chromium
& $PythonExe -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Playwright installation failed." }

# Set Python import path
$env:PYTHONPATH = Join-Path $ProjectDir "src"

# Initialize private data directory
& $PythonExe -c "from paths import DATA_DIR, CONFIG_FILE, ENV_FILE; print(DATA_DIR)"
if ($LASTEXITCODE -ne 0) { throw "Data directory initialization failed." }

# Copy example configuration if no configuration exists
$ConfigExample = Join-Path $ProjectDir "config.example.json"
& $PythonExe -c "from paths import CONFIG_FILE; print(CONFIG_FILE)"
$ConfigPath = (& $PythonExe -c "from paths import CONFIG_FILE; print(CONFIG_FILE)").Trim()

if (-not (Test-Path $ConfigPath)) {
    Copy-Item $ConfigExample $ConfigPath
}

# Create email configuration template if needed
$EnvPath = (& $PythonExe -c "from paths import ENV_FILE; print(ENV_FILE)").Trim()
$EnvExample = Join-Path $ProjectDir ".env.example"

if (-not (Test-Path $EnvPath) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvPath
}

# Save journal credentials
Write-Host "`nEnter your ScholarOne credentials:"
& $PythonExe (Join-Path $ProjectDir "src\setup_credentials.py")
if ($LASTEXITCODE -ne 0) { throw "Credential setup failed." }

Write-Host "`nPython setup completed."
Write-Host "Project: $ProjectDir"
Write-Host "Private data: $ConfigPath"
Write-Host "Email settings: $EnvPath"
Write-Host ""
Write-Host "Email settings must be completed before monitoring."
Write-Host "OpenClaw and the Windows scheduled task still need configuration."
