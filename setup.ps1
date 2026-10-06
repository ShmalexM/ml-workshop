$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python scripts/setup.py @args
} else {
    & py -3 scripts/setup.py @args
}
exit $LASTEXITCODE
