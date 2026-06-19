<#
.SYNOPSIS
    Builds the STS2_MCP mod DLL, with an optional install step.

.DESCRIPTION
    Compiles STS2_MCP.dll against the game's assemblies. By default this only
    builds into out/STS2_MCP/. Use -Install to copy the built DLL and manifest
    into the game's mods/ directory. The install step does not touch
    STS2_MCP.conf.

.PARAMETER GameDir
    Path to the Slay the Spire 2 installation directory.
    Falls back to the STS2_GAME_DIR environment variable if not specified.

.PARAMETER Configuration
    Build configuration (default: Release).

.PARAMETER Install
    Copy STS2_MCP.dll and STS2_MCP.json into the game's mods/ directory after
    a successful build.

.PARAMETER ModsDir
    Optional explicit mods directory. Defaults to <GameDir>/mods when -Install
    is used.

.EXAMPLE
    .\build.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
    .\build.ps1  # uses $env:STS2_GAME_DIR
    .\build.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Slay the Spire 2" -Install
#>
param(
    [string]$GameDir,
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [switch]$Install,
    [string]$ModsDir
)

$ErrorActionPreference = "Stop"

# --- Resolve game directory ---
if (-not $GameDir) {
    $GameDir = $env:STS2_GAME_DIR
}
if (-not $GameDir) {
    Write-Host @"
ERROR: Game directory not specified.

Provide it via parameter or environment variable:
  .\build.ps1 -GameDir "D:\SteamLibrary\steamapps\common\Slay the Spire 2"

Or set it once in your PowerShell profile:
  `$env:STS2_GAME_DIR = "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
"@ -ForegroundColor Red
    exit 1
}

$dllDir = Join-Path $GameDir "data_sts2_windows_x86_64"
if (-not (Test-Path (Join-Path $dllDir "sts2.dll"))) {
    Write-Host "ERROR: Could not find sts2.dll in '$dllDir'." -ForegroundColor Red
    Write-Host "Make sure -GameDir points to the Slay the Spire 2 installation root." -ForegroundColor Red
    exit 1
}

# --- Check prerequisites ---
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Host @"
ERROR: 'dotnet' not found.

Install the .NET 9 SDK from:
  https://dotnet.microsoft.com/download/dotnet/9.0
"@ -ForegroundColor Red
    exit 1
}

# --- Build ---
$scriptDir = $PSScriptRoot
$project = Join-Path $scriptDir "STS2_MCP.csproj"
$outDir = Join-Path (Join-Path $scriptDir "out") "STS2_MCP"
$builtDll = Join-Path $outDir "STS2_MCP.dll"
$manifest = Join-Path $scriptDir "mod_manifest.json"

Write-Host "=== Building STS2_MCP ($Configuration) ===" -ForegroundColor Cyan
Write-Host "Game directory : $GameDir"
Write-Host "Output         : $outDir"
Write-Host ""

dotnet build $project -c $Configuration -o $outDir -p:STS2GameDir="$GameDir"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Build succeeded ===" -ForegroundColor Green

if (-not $Install) {
    Write-Host "To install, copy these files to <game_install>/mods/:"
    Write-Host "  $builtDll"
    Write-Host "  $manifest  ->  mods\STS2_MCP.json"
    Write-Host ""
    Write-Host "Or rerun with -Install to copy them automatically."
    exit 0
}

if (-not $ModsDir) {
    $ModsDir = Join-Path $GameDir "mods"
}

if (-not (Test-Path -LiteralPath $builtDll)) {
    Write-Host "ERROR: Build output missing: $builtDll" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $manifest)) {
    Write-Host "ERROR: Manifest missing: $manifest" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $ModsDir | Out-Null
$installedDll = Join-Path $ModsDir "STS2_MCP.dll"
$installedJson = Join-Path $ModsDir "STS2_MCP.json"
$localConf = Join-Path $ModsDir "STS2_MCP.conf"

Write-Host ""
Write-Host "=== Installing STS2_MCP ===" -ForegroundColor Cyan
Write-Host "Mods directory : $ModsDir"
Write-Host "Copying        : $installedDll"
Write-Host "Copying        : $installedJson"
if (Test-Path -LiteralPath $localConf) {
    Write-Host "Preserving     : $localConf"
}

try {
    Copy-Item -LiteralPath $builtDll -Destination $installedDll -Force
    Copy-Item -LiteralPath $manifest -Destination $installedJson -Force
} catch {
    Write-Host "ERROR: Failed to install the mod. Close Slay the Spire 2 and try again." -ForegroundColor Red
    throw
}

Write-Host ""
Write-Host "=== Install succeeded ===" -ForegroundColor Green
Write-Host "Launch the game, enable the mod if needed, then verify:"
Write-Host "  curl http://localhost:15526/"
