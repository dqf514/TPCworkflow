# Publish Windows client: single-file + setup alias + version manifest
$ErrorActionPreference = 'Stop'
$clientRoot = $PSScriptRoot
$repoRoot = Split-Path $clientRoot -Parent

$iconScript = Join-Path $clientRoot 'scripts\build-icon.ps1'
if (Test-Path $iconScript) {
    & $iconScript
}

$csproj = Join-Path $clientRoot 'TPCWorkflow.Client.csproj'
$version = '1.0.0'
if (Test-Path $csproj) {
    $xml = [xml](Get-Content $csproj)
    $verNode = $xml.Project.PropertyGroup.Version
    if ($verNode) { $version = [string]$verNode }
}

$outDir = Join-Path $clientRoot 'publish\win-x64'
if (Test-Path $outDir) {
    Remove-Item $outDir -Recurse -Force
}

Write-Host "Publishing v$version ..."
dotnet publish $clientRoot\TPCWorkflow.Client.csproj -c Release -r win-x64 `
    -p:PublishSingleFile=true `
    -p:SelfContained=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:EnableCompressionInSingleFile=true `
    -p:DebugType=None `
    -p:DebugSymbols=false `
    -o $outDir

$exe = Join-Path $outDir 'TPCWorkflow.Client.exe'
if (-not (Test-Path $exe)) {
    Write-Error "Missing publish output: $exe"
}

$deployDir = Join-Path $repoRoot 'deploy\downloads'
New-Item -ItemType Directory -Force -Path $deployDir | Out-Null

$deployExe = Join-Path $deployDir 'TPCWorkflow.Client.exe'
$deploySetup = Join-Path $deployDir 'TPCWorkflow-Setup.exe'
Copy-Item $exe $deployExe -Force
Copy-Item $exe $deploySetup -Force

$deployZip = Join-Path $deployDir 'TPCWorkflow-Client.zip'
if (Test-Path $deployZip) { Remove-Item $deployZip -Force }
Compress-Archive -Path $deploySetup -DestinationPath $deployZip -CompressionLevel Optimal -Force

$versionJson = Join-Path $deployDir 'client-version.json'
$publishedAt = Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'
$releaseNotes = "v$version - 修复更新下载后未启动安装"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$json = (@{
    version = $version
    release_notes = $releaseNotes
    mandatory = $false
    package_type = 'setup_exe'
    published_at = $publishedAt
} | ConvertTo-Json -Compress)
[System.IO.File]::WriteAllText($versionJson, $json, $utf8NoBom)

$exeMb = [math]::Round((Get-Item $deployExe).Length / 1MB, 1)
$zipMb = [math]::Round((Get-Item $deployZip).Length / 1MB, 1)
Write-Host "Done: $exe"
Write-Host ('  exe:   {0} ({1} MB)' -f $deployExe, $exeMb)
Write-Host ('  setup: {0} ({1} MB)' -f $deploySetup, $exeMb)
Write-Host ('  zip:   {0} ({1} MB)' -f $deployZip, $zipMb)
Write-Host ('  meta:  {0} (v{1})' -f $versionJson, $version)
