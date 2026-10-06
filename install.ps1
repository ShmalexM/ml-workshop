# Install, update or remove Engineering Workshop on Windows 10 or 11.
#
#   Install or update (paste into PowerShell):
#     irm https://raw.githubusercontent.com/ShmalexM/ml-workshop/main/install.ps1 | iex
#   Remove the app and keep your progress:
#     & ([scriptblock]::Create((irm https://raw.githubusercontent.com/ShmalexM/ml-workshop/main/install.ps1))) -Uninstall
#   Remove everything, including your progress: add -Purge after -Uninstall.
#
# Everything goes into %LOCALAPPDATA%\EngineeringWorkshop. No admin rights are needed, and
# system settings are not changed.
#   app\      the app; each update replaces it
#   data\     your progress; updates and -Uninstall keep it
#   runtime\  uv, Python 3.12, Node.js (when needed) and the download cache
#
# Settings for testing: EW_HOME (install folder), EW_ARCHIVE (local release .zip; a SHA256SUMS
# file next to it is checked), EW_LIGHT=1 (skip the ML libraries), EW_NO_LAUNCH=1 (do not
# start the app), EW_NO_SHORTCUTS=1 (no Start menu or desktop shortcut).
# Written for Windows PowerShell 5.1. Settings and functions stay inside this script.

param([switch]$Uninstall, [switch]$Purge)

& {
    $ErrorActionPreference = 'Stop'
    # The progress bar makes downloads very slow in Windows PowerShell 5.1.
    $ProgressPreference = 'SilentlyContinue'
    $ReleaseUrl = 'https://github.com/ShmalexM/ml-workshop/releases/latest/download'
    $UvVersion = '0.12.23'  # Keep in step with install.sh.
    $NodeMajor = 24  # Same major version as .nvmrc.
    $MlNote = 'The PyTorch, TensorFlow, Modern AI stack and CUDA lessons need them; all other lessons work.'
    $S = @{ SavedEnv = @{}; Log = $null; Shortcuts = $false; NodePlan = 'keep' }

    function Say([string]$Text) { Write-Host $Text }

    function Write-Log([string]$Text) {
        if ($S.Log) { Add-Content -LiteralPath $S.Log -Value $Text -Encoding UTF8 }
    }

    function Fail([string]$Message) { throw (New-Object System.Exception $Message) }

    # A $null value removes the variable. ([Environment]::SetEnvironmentVariable would get "".)
    function Set-EnvValue([string]$Name, $Value) {
        if ($null -eq $Value) {
            Remove-Item -LiteralPath "env:$Name" -ErrorAction SilentlyContinue
        } else {
            Set-Item -LiteralPath "env:$Name" -Value $Value
        }
    }

    # Change environment variables for this process only; they are restored at the end.
    function Set-ProcessEnv([hashtable]$Values) {
        foreach ($name in @($Values.Keys)) {
            if (-not $S.SavedEnv.ContainsKey($name)) {
                $S.SavedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
            }
            Set-EnvValue $name $Values[$name]
        }
    }

    # Run a program with its output in the log. Returns $true when it succeeds.
    function Invoke-Logged([string]$File, [string[]]$Arguments) {
        Write-Log "+ $File $($Arguments -join ' ')"
        if (-not $File -or -not (Test-Path -LiteralPath $File)) { return $false }
        # Windows PowerShell 5.1 turns a program's error output into errors, which 'Stop' would throw.
        $ErrorActionPreference = 'Continue'
        & $File @Arguments 2>&1 | ForEach-Object { "$_" } | Out-File -LiteralPath $S.Log -Append -Encoding UTF8
        return $LASTEXITCODE -eq 0
    }

    # Returns the last line a program prints, or $null when it fails.
    function Get-Output([string]$File, [string[]]$Arguments) {
        if (-not $File -or -not (Test-Path -LiteralPath $File)) { return $null }
        $ErrorActionPreference = 'Continue'
        $lines = & $File @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return ($lines | Select-Object -Last 1)
    }

    function Save-Url([string]$Url, [string]$Path) {
        Write-Log "+ download $Url"
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            try {
                $client = New-Object System.Net.WebClient
                if ($client.Proxy) { $client.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials }
                $client.DownloadFile($Url, $Path)
                return $true
            } catch {
                Write-Log "  attempt ${attempt}: $($_.Exception.Message)"
            }
        }
        return $false
    }

    # Check $File against the checksum listed for $Name in $SumsFile.
    function Test-Checksum([string]$File, [string]$Name, [string]$SumsFile) {
        $expected = $null
        foreach ($line in Get-Content -LiteralPath $SumsFile) {
            $parts = $line.Trim() -split '\s+', 2
            if ($parts.Count -eq 2 -and $parts[1].TrimStart('*') -eq $Name) {
                $expected = $parts[0].ToLowerInvariant()
                break
            }
        }
        $actual = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-Log "sha256 ${Name}: expected $expected, got $actual"
        return [bool]($expected -and $expected -eq $actual)
    }

    function Expand-Zip([string]$Zip, [string]$Destination) {
        Write-Log "+ unzip $Zip"
        try {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory($Zip, $Destination)
            return $true
        } catch {
            Write-Log "  $($_.Exception.Message)"
            return $false
        }
    }

    # Delete a folder. Returns $true when it is gone.
    function Remove-Tree([string]$Path) {
        if (-not (Test-Path -LiteralPath $Path)) { return $true }
        try {
            [System.IO.Directory]::Delete($Path, $true)
        } catch {
            Write-Log "  delete ${Path}: $($_.Exception.Message)"
            # robocopy can empty folders whose paths exceed 260 characters, as some Python packages do.
            $empty = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
            New-Folder $empty
            $ErrorActionPreference = 'Continue'
            & (Join-Path $env:SystemRoot 'System32\robocopy.exe') $empty $Path /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP 2>&1 |
                ForEach-Object { "$_" } | Out-File -LiteralPath $S.Log -Append -Encoding UTF8
            $ErrorActionPreference = 'Stop'
            [System.IO.Directory]::Delete($empty)
            try { [System.IO.Directory]::Delete($Path, $true) } catch { Write-Log "  delete ${Path}: $($_.Exception.Message)" }
        }
        return -not (Test-Path -LiteralPath $Path)
    }

    # Antivirus scans can hold new files open for a moment, so retry for a few seconds.
    function Move-Tree([string]$From, [string]$To) {
        for ($attempt = 1; ; $attempt++) {
            try {
                [System.IO.Directory]::Move($From, $To)
                return
            } catch {
                Write-Log "  move ${From}: $($_.Exception.Message)"
                if ($attempt -ge 20) {
                    Fail "Could not move $From. Close any program that uses files in $($S.Root), then run the command again."
                }
                Start-Sleep -Milliseconds 500
            }
        }
    }

    function New-Folder([string]$Path) { [System.IO.Directory]::CreateDirectory($Path) | Out-Null }

    function Initialize-Platform {
        $arch = $null
        try { $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() } catch { }
        if (-not $arch) {
            $arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
        }
        switch ($arch) {
            { $_ -in 'X64', 'AMD64' } { $S.UvTarget = 'x86_64-pc-windows-msvc'; $S.NodeTarget = 'win-x64' }
            { $_ -in 'Arm64', 'ARM64' } { $S.UvTarget = 'aarch64-pc-windows-msvc'; $S.NodeTarget = 'win-arm64' }
            default { Fail "This computer's processor type ($arch) is not supported." }
        }
        $S.Arch = $arch
        $root = if ($env:EW_HOME) {
            $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($env:EW_HOME)
        } else {
            Join-Path $env:LOCALAPPDATA 'EngineeringWorkshop'
        }
        $S.Root = $root.TrimEnd('\')
        $S.App = Join-Path $S.Root 'app'
        $S.Data = Join-Path $S.Root 'data'
        $S.Runtime = Join-Path $S.Root 'runtime'
        $S.Marker = Join-Path $S.Root '.engineering-workshop'
        $S.Stage = Join-Path $S.Root '.app-new'
        $S.Old = Join-Path $S.Root '.app-old'
        $S.Work = Join-Path $S.Root '.download'
    }

    function Initialize-Root {
        if (((Test-Path -LiteralPath $S.App) -or (Test-Path -LiteralPath $S.Runtime) -or (Test-Path -LiteralPath $S.Data)) -and -not (Test-Path -LiteralPath $S.Marker)) {
            Fail "$($S.Root) has files that this installer did not create. Set EW_HOME to another folder."
        }
        foreach ($folder in $S.Root, $S.Data, $S.Runtime) { New-Folder $folder }
        Set-Content -LiteralPath $S.Marker -Value 'Created by the Engineering Workshop installer.'
        $S.Log = Join-Path $S.Root 'install.log'
        Set-Content -LiteralPath $S.Log -Value "Engineering Workshop installer, $(Get-Date -Format o), $($S.Arch)" -Encoding UTF8
        # Finish an update that stopped after moving the old app out.
        if ((Test-Path -LiteralPath $S.Old) -and -not (Test-Path -LiteralPath $S.App)) { Move-Tree $S.Old $S.App }
        foreach ($folder in $S.Old, $S.Stage, $S.Work) {
            if (-not (Remove-Tree $folder)) { Fail "Could not remove $folder. Close any program that uses it, then run the command again." }
        }
        New-Folder $S.Work
    }

    function Get-AppArchive {
        if ($env:EW_ARCHIVE) {
            $archive = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($env:EW_ARCHIVE)
            if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) { Fail "EW_ARCHIVE points to a missing file: $archive" }
            $sums = Join-Path (Split-Path -Parent $archive) 'SHA256SUMS'
            Say "Using $archive"
        } else {
            Say 'Downloading Engineering Workshop...'
            $archive = Join-Path $S.Work 'engineering-workshop.zip'
            $sums = Join-Path $S.Work 'SHA256SUMS'
            if (-not (Save-Url "$ReleaseUrl/engineering-workshop.zip" $archive) -or -not (Save-Url "$ReleaseUrl/SHA256SUMS" $sums)) {
                Fail 'Could not download Engineering Workshop. Check your internet connection and try again.'
            }
        }
        if (Test-Path -LiteralPath $sums) {
            if (-not (Test-Checksum $archive (Split-Path -Leaf $archive) $sums)) { Fail 'The download is damaged. Run the command again.' }
        } else {
            Write-Log "No SHA256SUMS next to $archive, so it was not checked."
        }
        $unpacked = Join-Path $S.Work 'app'
        if (-not (Expand-Zip $archive $unpacked)) { Fail "Could not unpack $archive." }
        $folder = Join-Path $unpacked 'engineering-workshop'
        if (-not (Test-Path -LiteralPath (Join-Path $folder 'dist\index.html'))) { Fail 'The download is incomplete. Run the command again.' }
        Move-Tree $folder $S.Stage
    }

    function Get-Uv {
        $uv = Join-Path $S.Runtime 'uv\uv.exe'
        if ((Get-Output $uv @('--version')) -like "uv $UvVersion *") { return $uv }
        $name = "uv-$($S.UvTarget).zip"
        $zip = Join-Path $S.Work $name
        $url = "https://github.com/astral-sh/uv/releases/download/$UvVersion/$name"
        if (-not (Save-Url $url $zip) -or -not (Save-Url "$url.sha256" "$zip.sha256")) {
            Fail 'Could not download uv, which installs Python. Check your internet connection and try again.'
        }
        if (-not (Test-Checksum $zip $name "$zip.sha256")) { Fail 'The uv download is damaged. Run the command again.' }
        $folder = Join-Path $S.Work 'uv'
        if (-not (Expand-Zip $zip $folder)) { Fail 'Could not unpack uv.' }
        New-Folder (Split-Path -Parent $uv)
        Copy-Item -LiteralPath (Join-Path $folder 'uv.exe') -Destination $uv -Force
        return $uv
    }

    function Install-Python {
        Say 'Installing Python 3.12...'
        # Keep Python, packages and the download cache in the install folder. The new app\.venv
        # is built in a staging folder and moved into place, so it must be relocatable.
        Set-ProcessEnv @{
            UV_PYTHON_INSTALL_DIR = Join-Path $S.Runtime 'python'
            UV_CACHE_DIR = Join-Path $S.Runtime 'cache'
            UV_MANAGED_PYTHON = '1'
            UV_NO_CONFIG = '1'
            UV_VENV_RELOCATABLE = '1'
            PYTHONHOME = $null
            PYTHONPATH = $null
            VIRTUAL_ENV = $null
        }
        $S.Uv = Get-Uv
        Set-ProcessEnv @{ PATH = (Split-Path -Parent $S.Uv) + ';' + $env:PATH }
        if (-not (Invoke-Logged $S.Uv @('python', 'install', '3.12', '--no-bin', '--no-registry'))) {
            Fail 'Could not install Python 3.12. Check your internet connection and try again.'
        }
        $S.Python = Get-Output $S.Uv @('python', 'find', '3.12')
        if (-not $S.Python) { Fail 'Could not find the Python 3.12 that was just installed.' }
    }

    # scripts\setup.py creates app\.venv with this Python and installs the requirements with uv.
    function Install-Requirements([string[]]$Extra) {
        return Invoke-Logged $S.Python (@((Join-Path $S.Stage 'scripts\setup.py'), '--no-build', '--no-launch') + $Extra)
    }

    function Install-Packages {
        $light = $env:EW_LIGHT -eq '1'
        if ($light) {
            Say 'Skipping the ML libraries (EW_LIGHT=1).'
        } else {
            if (Test-Path -LiteralPath (Join-Path $S.App '.venv\Lib\site-packages\torch')) {
                Say 'Updating the ML libraries...'
            } else {
                Say 'Downloading ML libraries (about 2 GB, this can take a while)...'
            }
            if (-not (Install-Requirements @())) {
                Say 'Could not install the ML libraries, so they were skipped. Run this command again later to retry.'
                if (-not (Remove-Tree (Join-Path $S.Stage '.venv'))) { Fail 'Could not remove the unfinished Python environment.' }
                $light = $true
            }
        }
        if ($light) {
            Say $MlNote
            if (-not (Install-Requirements @('--no-ml'))) {
                Fail 'Could not install the Python packages. Check your internet connection and try again.'
            }
        }
    }

    # True when $Path runs and is Node.js 22.13 or newer, the minimum in package.json.
    function Test-Node([string]$Path) {
        if ((Get-Output $Path @('--version')) -notmatch '^v(\d+)\.(\d+)\.') { return $false }
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        return ($major -gt 22) -or ($major -eq 22 -and $minor -ge 13)
    }

    # Choose how the app gets Node.js. Nothing in runtime\ changes until the app is stopped.
    function Get-NodeRuntime {
        $system = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($system -and -not $system.Source.StartsWith($S.Runtime, [StringComparison]::OrdinalIgnoreCase) -and (Test-Node $system.Source)) {
            # Shortcuts get the same PATH from Windows, so the app finds it there.
            Write-Log "Using $($system.Source)"
            return
        }
        $current = Join-Path $S.Runtime 'node\node.exe'
        if (-not (Test-Node $current)) { $current = $null }
        $base = "https://nodejs.org/dist/latest-v$NodeMajor.x"
        $sums = Join-Path $S.Work 'SHASUMS256.txt'
        $name = $null
        if (Save-Url "$base/SHASUMS256.txt" $sums) {
            $name = Get-Content -LiteralPath $sums | ForEach-Object { ($_.Trim() -split '\s+')[-1] } |
                Where-Object { $_ -match "^node-v[\d.]+-$($S.NodeTarget)\.zip$" } | Select-Object -First 1
        }
        if ($name) {
            if ($current -and (Get-Output $current @('--version')) -eq ($name -split '-')[1]) { return }
            Say 'Installing Node.js for the JavaScript lessons...'
            $zip = Join-Path $S.Work $name
            $folder = Join-Path $S.Work 'node'
            $S.NodeNew = Join-Path $folder ($name -replace '\.zip$', '')
            if ((Save-Url "$base/$name" $zip) -and (Test-Checksum $zip $name $sums) -and (Expand-Zip $zip $folder) -and
                (Test-Node (Join-Path $S.NodeNew 'node.exe'))) {
                $S.NodePlan = 'replace'
                return
            }
        }
        if ($current) {
            Write-Log "Kept Node.js $(Get-Output $current @('--version'))."
        } else {
            Say 'Could not install Node.js, so the JavaScript lessons will not run. Run this command again later to retry.'
        }
    }

    function Stop-App {
        $python = Join-Path $S.App '.venv\Scripts\python.exe'
        $script = Join-Path $S.App 'scripts\installed.py'
        if ((Test-Path -LiteralPath $python) -and (Test-Path -LiteralPath $script)) {
            if (-not (Invoke-Logged $python @($script, '--stop'))) { Write-Log 'Could not stop the running app.' }
        }
    }

    function Install-NewFiles {
        if ($S.NodePlan -eq 'replace') {
            $node = Join-Path $S.Runtime 'node'
            if (-not (Remove-Tree $node)) { Fail "Could not replace $node. Close any program that uses it, then run the command again." }
            Move-Tree $S.NodeNew $node
        }
        if (Test-Path -LiteralPath $S.App) { Move-Tree $S.App $S.Old }
        try {
            Move-Tree $S.Stage $S.App
        } catch {
            if (Test-Path -LiteralPath $S.Old) { [System.IO.Directory]::Move($S.Old, $S.App) }
            throw
        }
        if (-not (Remove-Tree $S.Old)) { Write-Log "Could not remove $($S.Old); the next update removes it." }
    }

    function Get-ShortcutPaths {
        foreach ($folder in [Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop')) {
            if ($folder) { Join-Path $folder 'Engineering Workshop.lnk' }
        }
    }

    function New-Shortcuts {
        if ($env:EW_NO_SHORTCUTS -eq '1') { return }
        Say 'Adding Engineering Workshop to the Start menu and the desktop...'
        # pythonw starts the app without a console window.
        $target = Join-Path $S.App '.venv\Scripts\pythonw.exe'
        if (-not (Test-Path -LiteralPath $target)) { $target = Join-Path $S.App '.venv\Scripts\python.exe' }
        $shell = New-Object -ComObject WScript.Shell
        foreach ($path in Get-ShortcutPaths) {
            try {
                New-Folder (Split-Path -Parent $path)
                $shortcut = $shell.CreateShortcut($path)
                $shortcut.TargetPath = $target
                $shortcut.Arguments = '"' + (Join-Path $S.App 'scripts\installed.py') + '"'
                $shortcut.WorkingDirectory = $S.App
                $shortcut.IconLocation = (Join-Path $S.App 'assets\Workshop.ico') + ',0'
                $shortcut.Description = 'Practice ML and software engineering'
                $shortcut.Save()
                $S.Shortcuts = $true
            } catch {
                Write-Log "Could not create ${path}: $($_.Exception.Message)"
            }
        }
    }

    function Remove-Shortcuts {
        $shell = New-Object -ComObject WScript.Shell
        foreach ($path in Get-ShortcutPaths) {
            if ((Test-Path -LiteralPath $path) -and
                $shell.CreateShortcut($path).TargetPath.StartsWith($S.App + '\', [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $path -Force
            }
        }
    }

    function Complete-Install {
        Remove-Tree $S.Work | Out-Null
        $python = Join-Path $S.App '.venv\Scripts\python.exe'
        $script = Join-Path $S.App 'scripts\installed.py'
        if ($env:EW_NO_LAUNCH -eq '1') {
            Say 'Done. Engineering Workshop is installed.'
        } else {
            Say 'Starting Engineering Workshop...'
            $ErrorActionPreference = 'Continue'
            $output = & $python $script 2>&1
            $started = $LASTEXITCODE -eq 0
            $ErrorActionPreference = 'Stop'
            $errors = @($output | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" })
            $url = $output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | Select-Object -Last 1
            if (-not $started) {
                Write-Log ($errors -join [Environment]::NewLine)
                Fail ('Engineering Workshop is installed but did not start.' + [Environment]::NewLine + ($errors -join ' '))
            }
            Say "Done. Engineering Workshop is open in your browser at $url"
        }
        Say "Your progress is saved in $($S.Data)."
        if ($S.Shortcuts) {
            Say 'To open it later, use the Engineering Workshop shortcut in the Start menu or on the desktop.'
        } else {
            Say "To open it later, run: & '$python' '$script'"
        }
        Say 'To update, run the install command again.'
    }

    function Install-App {
        Say "Installing Engineering Workshop in $($S.Root)"
        Initialize-Root
        Get-AppArchive
        Install-Python
        Install-Packages
        Get-NodeRuntime
        Stop-App
        Install-NewFiles
        New-Shortcuts
        Complete-Install
    }

    function Uninstall-App {
        if (-not (Test-Path -LiteralPath $S.Marker)) {
            Say "Engineering Workshop is not installed in $($S.Root)."
            return
        }
        $S.Log = Join-Path $S.Root 'install.log'
        Set-Content -LiteralPath $S.Log -Value "Engineering Workshop uninstall, $(Get-Date -Format o)" -Encoding UTF8
        Say 'Removing Engineering Workshop...'
        Stop-App
        Remove-Shortcuts
        foreach ($folder in $S.App, $S.Runtime, $S.Stage, $S.Old, $S.Work) {
            if (-not (Remove-Tree $folder)) { Fail "Could not remove $folder. Close any program that uses it, then run the command again." }
        }
        if ($Purge) {
            if (-not (Remove-Tree $S.Data)) { Fail "Could not remove $($S.Data). Close any program that uses it, then run the command again." }
            Remove-Item -LiteralPath $S.Marker, $S.Log -Force
            try { [System.IO.Directory]::Delete($S.Root) } catch { }
            Say 'Removed Engineering Workshop and your progress.'
        } else {
            Remove-Item -LiteralPath $S.Log -Force
            Say "Removed Engineering Workshop. Your progress is still in $($S.Data)."
            Say 'To delete it too, run the uninstall command again with -Purge at the end.'
        }
    }

    $failed = $false
    # Windows cannot delete a folder that is the current folder, so work from the user profile.
    $savedDirectory = [Environment]::CurrentDirectory
    Push-Location -LiteralPath $env:USERPROFILE
    [Environment]::CurrentDirectory = $env:USERPROFILE
    try {
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor [System.Net.SecurityProtocolType]::Tls12
        if ($Purge -and -not $Uninstall) { Fail '-Purge only works together with -Uninstall.' }
        Initialize-Platform
        if ($Uninstall) { Uninstall-App } else { Install-App }
    } catch {
        $failed = $true
        Write-Host $_.Exception.Message -ForegroundColor Red
        if ($S.Log -and (Test-Path -LiteralPath $S.Log)) {
            Write-Log "$($_.ScriptStackTrace)"
            Write-Host "Details: $($S.Log)"
        }
    } finally {
        foreach ($name in @($S.SavedEnv.Keys)) { Set-EnvValue $name $S.SavedEnv[$name] }
        [Environment]::CurrentDirectory = $savedDirectory
        Pop-Location
    }
    # Tools such as robocopy return nonzero codes on success; do not leave one behind after a good run.
    if (-not $failed) { $global:LASTEXITCODE = 0 }
    # Set an exit code when run as a file. With irm | iex, exit would close the PowerShell window.
    if ($failed -and $PSCommandPath) { exit 1 }
}
