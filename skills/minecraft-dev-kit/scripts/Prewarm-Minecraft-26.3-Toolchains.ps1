param(
    [Parameter(Mandatory=$true)][string]$OutputDir
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Get-VerifiedFile {
    param([string]$Url, [string]$Name, [string]$ExpectedSha256 = '', [string]$ChecksumUrl = '')
    $dest = Join-Path $OutputDir $Name
    if (-not $ExpectedSha256 -and $ChecksumUrl) {
        $sumFile = Join-Path $OutputDir ($Name + '.sha256sum.txt')
        Invoke-WebRequest -UseBasicParsing -Uri $ChecksumUrl -OutFile $sumFile
        $ExpectedSha256 = ((Get-Content $sumFile -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
    }
    if (Test-Path $dest) {
        $existing = (Get-FileHash -Algorithm SHA256 $dest).Hash.ToLowerInvariant()
        if ($ExpectedSha256 -and $existing -eq $ExpectedSha256) {
            Write-Host "REUSE $Name $existing"
            return [PSCustomObject]@{ name=$Name; sha256=$existing; status='reused' }
        }
    }
    $part = $dest + '.part'
    Remove-Item -Force -ErrorAction SilentlyContinue $part
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $part
    $actual = (Get-FileHash -Algorithm SHA256 $part).Hash.ToLowerInvariant()
    if ($ExpectedSha256 -and $actual -ne $ExpectedSha256) {
        Remove-Item -Force $part
        throw "Checksum mismatch for $Name expected=$ExpectedSha256 actual=$actual"
    }
    Move-Item -Force $part $dest
    Write-Host "OK $Name $actual"
    return [PSCustomObject]@{ name=$Name; sha256=$actual; status='downloaded' }
}

$results = @()
$results += Get-VerifiedFile `
    'https://aka.ms/download-jdk/microsoft-jdk-25.0.4.1-windows-x64.zip' `
    'microsoft-jdk-25.0.4.1-windows-x64.zip' `
    '' `
    'https://aka.ms/download-jdk/microsoft-jdk-25.0.4.1-windows-x64.zip.sha256sum.txt'
$results += Get-VerifiedFile `
    'https://services.gradle.org/distributions/gradle-9.6.0-bin.zip' `
    'gradle-9.6.0-bin.zip' `
    'bbaeb2fef8710818cf0e261201dab964c572f92b942812df0c3620d62a529a01'
$results += Get-VerifiedFile `
    'https://services.gradle.org/distributions/gradle-9.2.1-bin.zip' `
    'gradle-9.2.1-bin.zip' `
    '72f44c9f8ebcb1af43838f45ee5c4aa9c5444898b3468ab3f4af7b6076c5bc3f'

$manifest = [PSCustomObject]@{
    schema_version = 1
    snapshot_date = '2026-09-17'
    minecraft = '26.3'
    java = 25
    artifacts = $results
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $OutputDir 'MC-26.3-TOOLCHAIN-CACHE-MANIFEST.json')
Write-Host "Minecraft 26.3 Windows toolchain cache ready at $OutputDir"
