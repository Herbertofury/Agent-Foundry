# Private first-run Python bootstrap. Never installs globally or changes user/system PATH.
$ErrorActionPreference = 'Stop'
$ForwardArgs = @($args)
$Root = $PSScriptRoot
$Scripts = Join-Path $Root 'scripts'
if (Test-Path (Join-Path $Root 'worker/scripts/devkit.py')) { $Scripts = Join-Path $Root 'worker/scripts' }
$Entry = Join-Path $Scripts 'devkit.py'
if (-not (Test-Path $Entry)) { throw "Dev Kit entry point is missing: $Entry. Extract the complete package first." }
function Get-DevKitHash([string]$Path) {
    $Stream = [IO.File]::OpenRead($Path)
    $Algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($Algorithm.ComputeHash($Stream))).Replace('-','').ToLowerInvariant() }
    finally { $Algorithm.Dispose(); $Stream.Dispose() }
}
function Invoke-DevKit([string]$Executable) {
    if ($ForwardArgs.Count -eq 0) { & $Executable $Entry wizard }
    else { & $Executable $Entry @ForwardArgs }
    exit $LASTEXITCODE
}
if ($env:DEVKIT_BOOTSTRAP_FORCE -ne '1') {
    foreach ($Name in @('python3', 'python')) {
        $Command = Get-Command $Name -ErrorAction SilentlyContinue
        if ($Command -and $Command.Source -notmatch 'WindowsApps') {
            & $Command.Source -c 'import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { Invoke-DevKit $Command.Source }
        }
    }
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        $Found = & $Launcher.Source -3 -c 'import sys;print(sys.executable) if sys.version_info >= (3,12) else sys.exit(1)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $Found -and (Test-Path $Found)) { Invoke-DevKit $Found }
    }
}
$Version = '3.13.15'
$Architecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { 'arm64' } else { 'amd64' }
$Checksum = if ($Architecture -eq 'arm64') { 'cd992cbfb33be433ff20f150691595efb2862e56f4f1bec684c6077d4775af8e' } else { 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf' }
$Bytes = [Text.Encoding]::UTF8.GetBytes([IO.Path]::GetFullPath($Scripts).ToLowerInvariant())
$SHA = [Security.Cryptography.SHA256]::Create()
try { $Identity = ([BitConverter]::ToString($SHA.ComputeHash($Bytes))).Replace('-','').Substring(0,16) } finally { $SHA.Dispose() }
$Cache = if ($env:DEVKIT_BOOTSTRAP_CACHE) { [IO.Path]::GetFullPath($env:DEVKIT_BOOTSTRAP_CACHE) } else { Join-Path $env:LOCALAPPDATA 'MinecraftDevKit' }
[IO.Directory]::CreateDirectory($Cache) | Out-Null
$RuntimeHome = Join-Path $Cache "python-$Version-$Architecture-$Identity"
$Python = Join-Path $RuntimeHome 'python.exe'
$Mutex = [Threading.Mutex]::new($false, "Local\EnderloomDevKitPython-$Identity-$Architecture")
$Held = $false
try {
    try { $Held = $Mutex.WaitOne(120000) } catch [Threading.AbandonedMutexException] { $Held = $true }
    if (-not $Held) { throw 'Another setup is still running. Its files were left intact; retry after it finishes.' }
    $Valid = $false
    $Receipt = Join-Path $RuntimeHome 'devkit-python-install.json'
    if (Test-Path $Receipt) {
        try {
            $Record = Get-Content $Receipt -Raw | ConvertFrom-Json
            $Valid = $Record.version -eq $Version -and $Record.archive_sha256 -eq $Checksum -and $Record.script_directory -eq $Scripts
            foreach ($File in $Record.files) {
                $Path = [IO.Path]::GetFullPath((Join-Path $RuntimeHome $File.path))
                if (-not $Path.StartsWith($RuntimeHome + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid bootstrap receipt path' }
                if (-not (Test-Path -LiteralPath $Path) -or (Get-DevKitHash $Path) -ne $File.sha256) { $Valid = $false; break }
            }
            if ($Valid) { & $Python -c 'import sys,ssl,hashlib;sys.exit(0 if sys.version_info[:3] == (3,13,15) else 1)' 2>$null; $Valid = $LASTEXITCODE -eq 0 }
        } catch { $Valid = $false }
    }
    if (-not $Valid) {
        if ($env:DEVKIT_OFFLINE -eq '1') { throw 'Private Python is not cached. Run this launcher once online; no administrator rights are needed.' }
        Write-Host 'Setting up the private Dev Kit Python runtime from python.org...'
        $Archive = Join-Path $Cache "python-$Version-$Architecture.zip"
        if (-not (Test-Path $Archive) -or (Get-DevKitHash $Archive) -ne $Checksum) {
            $Partial = $Archive + '.' + [Guid]::NewGuid().ToString('N') + '.partial'
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/$Version/python-$Version-embed-$Architecture.zip" -OutFile $Partial
                if ((Get-DevKitHash $Partial) -ne $Checksum) { throw 'The Python download did not match the official checksum. Nothing was installed.' }
                Move-Item -Force $Partial $Archive
            } finally { if (Test-Path $Partial) { Remove-Item $Partial } }
        }
        $Stage = Join-Path $Cache ('python-stage-' + [Guid]::NewGuid().ToString('N'))
        [IO.Directory]::CreateDirectory($Stage) | Out-Null
        try {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $Zip = [IO.Compression.ZipFile]::OpenRead($Archive)
            try {
                foreach ($Item in $Zip.Entries) {
                    $Target = [IO.Path]::GetFullPath((Join-Path $Stage $Item.FullName))
                    if ($Item.FullName -match ':' -or -not $Target.StartsWith($Stage + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe Python archive path' }
                }
            } finally { $Zip.Dispose() }
            [IO.Compression.ZipFile]::ExtractToDirectory($Archive, $Stage)
            [IO.File]::WriteAllText((Join-Path $Stage 'python313._pth'), "python313.zip`n.`n$Scripts`n", [Text.UTF8Encoding]::new($false))
            & (Join-Path $Stage 'python.exe') -c 'import ssl,hashlib,sys;import northpoint_execution;sys.exit(0 if sys.version_info[:3] == (3,13,15) else 1)'
            if ($LASTEXITCODE -ne 0) { throw 'Private Python or Dev Kit imports failed their setup check' }
            $Files = @(Get-ChildItem $Stage -Recurse -File | ForEach-Object {
                @{path=$_.FullName.Substring($Stage.Length+1); sha256=(Get-DevKitHash $_.FullName)}
            })
            @{version=$Version;archive_sha256=$Checksum;script_directory=$Scripts;files=$Files} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Stage 'devkit-python-install.json') -Encoding UTF8
            if (Test-Path $RuntimeHome) { Move-Item $RuntimeHome ($RuntimeHome + '.previous-' + [Guid]::NewGuid().ToString('N')) }
            Move-Item $Stage $RuntimeHome
        } finally { if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force } }
    }
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($Held) { $Mutex.ReleaseMutex() }
    $Mutex.Dispose()
}
Invoke-DevKit $Python
