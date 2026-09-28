[CmdletBinding()]
param(
    [string]$MinecraftVersion = "1.20.1",
    [string]$MmvDevKit = "$PSScriptRoot\mmv-devkit-windows-amd64-v2.3.0.exe",
    [string]$OutputRoot = "$env:USERPROFILE\Downloads\MMV-Minecraft-$MinecraftVersion-Client-Assets",
    [ValidateRange(1,64)]
    [int]$Workers = 24,
    [switch]$PackageForDrive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-ExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $MmvDevKit -PathType Leaf)) {
    throw "mmv-devkit was not found at '$MmvDevKit'. Download mmv-devkit-windows-amd64-v2.3.0.exe, put it next to this script, or pass -MmvDevKit with its full path."
}

$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$MetadataDir = Join-Path $OutputRoot "metadata"
$AssetsDir = Join-Path $OutputRoot "assets"
New-Item -ItemType Directory -Force -Path $MetadataDir, $AssetsDir | Out-Null

$ManifestUrl = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
Write-Host "[1/5] Resolving Minecraft $MinecraftVersion from Mojang..."
$Manifest = Invoke-RestMethod -Uri $ManifestUrl -Method Get
$VersionEntry = $Manifest.versions | Where-Object { $_.id -eq $MinecraftVersion } | Select-Object -First 1
if ($null -eq $VersionEntry) {
    throw "Minecraft $MinecraftVersion was not found in Mojang's version manifest."
}

$VersionJson = Join-Path $MetadataDir "$MinecraftVersion.json"
Write-Host "[2/5] Downloading official version metadata..."
Invoke-WebRequest -UseBasicParsing -Uri $VersionEntry.url -OutFile $VersionJson
$VersionMeta = Get-Content -LiteralPath $VersionJson -Raw | ConvertFrom-Json
if ($null -eq $VersionMeta.assetIndex -or [string]::IsNullOrWhiteSpace([string]$VersionMeta.assetIndex.url)) {
    throw "The Minecraft version metadata did not contain a valid assetIndex."
}
Write-Host ("      Asset index: {0}  expected external bytes: {1:N0}" -f $VersionMeta.assetIndex.id, [int64]$VersionMeta.assetIndex.totalSize)

$DownloadReport = Join-Path $OutputRoot "client-assets-download.json"
Write-Host "[3/5] Downloading and SHA-1 verifying Mojang asset objects..."
& $MmvDevKit client-assets --version-json $VersionJson --assets-dir $AssetsDir --mc $MinecraftVersion --workers $Workers --json | Tee-Object -FilePath $DownloadReport
Assert-ExitCode "mmv-devkit client-assets"

$VerifyReport = Join-Path $OutputRoot "client-assets-verify.json"
Write-Host "[4/5] Re-verifying the complete cache without network access..."
& $MmvDevKit client-assets --version-json $VersionJson --assets-dir $AssetsDir --mc $MinecraftVersion --workers $Workers --verify-only --json | Tee-Object -FilePath $VerifyReport
Assert-ExitCode "mmv-devkit client-assets --verify-only"

if ($PackageForDrive) {
    Write-Host "[5/5] Packaging and splitting into Drive/connector-safe 85 MiB parts..."
    $Archive = Join-Path $OutputRoot "minecraft-$MinecraftVersion-client-assets.zip"
    $SplitDir = Join-Path $OutputRoot "minecraft-$MinecraftVersion-client-assets-SPLIT"
    if (Test-Path -LiteralPath $Archive) { Remove-Item -LiteralPath $Archive -Force }
    if (Test-Path -LiteralPath $SplitDir) { Remove-Item -LiteralPath $SplitDir -Recurse -Force }

    $Tar = Get-Command tar.exe -ErrorAction Stop
    Push-Location $OutputRoot
    try {
        & $Tar.Source -a -cf $Archive "assets" "metadata" "client-assets-download.json" "client-assets-verify.json"
        Assert-ExitCode "tar.exe ZIP packaging"
    }
    finally {
        Pop-Location
    }

    & $MmvDevKit archive-split --file $Archive --out-dir $SplitDir --part-mib 85 --json | Tee-Object -FilePath (Join-Path $OutputRoot "archive-split.json")
    Assert-ExitCode "mmv-devkit archive-split"

    Write-Host ""
    Write-Host "DONE. Upload every file inside this folder to Minecraft Dev Kit:" -ForegroundColor Green
    Write-Host "  $SplitDir"
}
else {
    Write-Host "[5/5] Packaging skipped. Re-run with -PackageForDrive when you want upload-safe parts."
}

Write-Host ""
Write-Host "Verified Minecraft client asset cache:" -ForegroundColor Green
Write-Host "  $AssetsDir"
Write-Host "Download report: $DownloadReport"
Write-Host "Verify report:   $VerifyReport"
