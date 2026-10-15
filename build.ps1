# Builds dist\KeyGlow.exe (single file, no console window).
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install --quiet -r requirements.txt pyinstaller

.\.venv\Scripts\python -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

.\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed `
    --name KeyGlow `
    --icon "$PSScriptRoot\assets\keyglow.ico" `
    --add-data "$PSScriptRoot\keyglow\web;keyglow\web" `
    --workpath "$env:TEMP\keyglow-build" `
    --specpath "$env:TEMP\keyglow-build" `
    --distpath "$PSScriptRoot\dist" `
    "$PSScriptRoot\keyglow_app.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "Built dist\KeyGlow.exe"
