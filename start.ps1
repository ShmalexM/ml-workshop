$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe scripts/launch.py @args
exit $LASTEXITCODE
