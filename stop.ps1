$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe scripts/stop.py @args
exit $LASTEXITCODE
