# Install DataMind Context as a Codex plugin (Windows / PowerShell version).
#
# OpenAI Codex's plugin model on Windows is the same as on macOS/Linux:
#   * marketplaces are directories registered in %USERPROFILE%\.codex\config.toml
#     under [marketplaces.<name>] with `source = "<absolute path>"`.
#   * each marketplace contains:
#       <root>\.agents\plugins\marketplace.json   (catalogue)
#       <root>\plugins\<plugin>\.codex-plugin\plugin.json
#       <root>\plugins\<plugin>\...               (the plugin)
#   * plugins are enabled via [plugins."<plugin>@<marketplace>"] enabled = true.
#
# Usage (PowerShell):
#   .\install.ps1
#   .\install.ps1 -Force
#   .\install.ps1 -SkipDeps
#   .\install.ps1 -RepoRoot C:\path\to\DataMind
#   .\install.ps1 -PythonExe C:\Python311\python.exe
#   .\install.ps1 -MarketplaceName mycustom

[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$Force,
    [switch]$SkipDeps,
    [string]$PythonExe = 'python',
    [string]$MarketplaceName = 'datamind'
)

$ErrorActionPreference = 'Stop'

$PluginName = 'datamind-context'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MarketplaceRoot = Join-Path $env:USERPROFILE ".codex\marketplaces\$MarketplaceName"
$TargetDir = Join-Path $MarketplaceRoot "plugins\$PluginName"
$MarketplaceJson = Join-Path $MarketplaceRoot ".agents\plugins\marketplace.json"
$CodexConfig = Join-Path $env:USERPROFILE ".codex\config.toml"

function Resolve-BundledRepo($base) {
    if ((Test-Path (Join-Path $base 'pyproject.toml')) -and (Test-Path (Join-Path $base 'datamind'))) {
        return (Resolve-Path $base).Path
    }
    return $null
}

# --- Resolve DataMind runtime root ---
if (-not $RepoRoot) {
    $RepoRoot = Resolve-BundledRepo $ScriptDir
}

if (-not $RepoRoot) {
    $Candidate = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
    if (Resolve-BundledRepo $Candidate) {
        $RepoRoot = $Candidate
    }
}

if (-not $RepoRoot) {
    Write-Error "Missing DataMind runtime. Use -RepoRoot C:\path\to\DataMind, or run this script from a DataMind checkout."
    exit 1
}

$RepoRoot = (Resolve-Path $RepoRoot).Path
if (-not (Test-Path (Join-Path $RepoRoot 'pyproject.toml')) -or -not (Test-Path (Join-Path $RepoRoot 'datamind'))) {
    Write-Error "Not a DataMind repository root: $RepoRoot"
    exit 1
}

if (-not (Test-Path (Join-Path $ScriptDir '.codex-plugin\plugin.json'))) {
    Write-Error "Cannot find plugin manifest in $ScriptDir"
    exit 1
}

# --- Sanity: do we have a Codex install? ---
if (-not (Test-Path (Join-Path $env:USERPROFILE '.codex'))) {
    Write-Warning "$($env:USERPROFILE)\.codex does not exist. Make sure OpenAI Codex desktop is installed and run at least once."
    New-Item -ItemType Directory -Force -Path (Join-Path $env:USERPROFILE '.codex') | Out-Null
}

# --- Stage the marketplace + plugin ---
New-Item -ItemType Directory -Force -Path (Join-Path $MarketplaceRoot '.agents\plugins') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $MarketplaceRoot 'plugins') | Out-Null

if ($ScriptDir -ne $TargetDir) {
    if ((Test-Path $TargetDir) -and -not $Force) {
        Write-Error "Target already exists: $TargetDir`nRerun with -Force to replace it."
        exit 1
    }
    if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

    $exclusions = @('.DS_Store', '.datamind-repo-root', '__pycache__', '.pytest_cache', '.venv')
    Get-ChildItem -Path $ScriptDir -Force | Where-Object {
        $exclusions -notcontains $_.Name
    } | ForEach-Object {
        Copy-Item -Recurse -Force -Path $_.FullName -Destination $TargetDir
    }

    if ($RepoRoot.StartsWith($ScriptDir, [StringComparison]::OrdinalIgnoreCase)) {
        $bundled = Resolve-BundledRepo $TargetDir
        if ($bundled) { $RepoRoot = $bundled }
    }
}

Set-Content -Path (Join-Path $TargetDir '.datamind-repo-root') -Value $RepoRoot

# --- Activate Windows MCP config ---
$WinMcp = Join-Path $TargetDir '.mcp.windows.json'
$Mcp = Join-Path $TargetDir '.mcp.json'
if (Test-Path $WinMcp) {
    Copy-Item -Force $WinMcp $Mcp
    Write-Host "Activated Windows MCP config: $Mcp"
}

# --- Bootstrap .env + venv ---
if (-not (Test-Path (Join-Path $RepoRoot '.env.datamind')) -and (Test-Path (Join-Path $RepoRoot '.env.datamind.example'))) {
    Copy-Item -Force (Join-Path $RepoRoot '.env.datamind.example') (Join-Path $RepoRoot '.env.datamind')
    Write-Host "Created $RepoRoot\.env.datamind from .env.datamind.example. Edit it with your LLM and embedding credentials."
}

if (-not $SkipDeps) {
    $venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPy)) {
        & $PythonExe -m venv (Join-Path $RepoRoot '.venv')
    }
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install --prefer-binary -e $RepoRoot
}

# --- Write marketplace.json + patch config.toml ---
$pyScript = @"
import json, pathlib, re, sys, datetime as dt

mp_path = pathlib.Path(sys.argv[1])
mname = sys.argv[2]
mroot = sys.argv[3]
config_path = pathlib.Path(sys.argv[4])

# 1. marketplace.json
entry = {
    'name': 'datamind-context',
    'source': {'source': 'local', 'path': './plugins/datamind-context'},
    'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'},
    'category': 'Productivity',
}
if mp_path.exists():
    payload = json.loads(mp_path.read_text(encoding='utf-8'))
else:
    payload = {'name': mname, 'interface': {'displayName': 'DataMind'}, 'plugins': []}
payload.setdefault('name', mname)
payload.setdefault('interface', {}).setdefault('displayName', 'DataMind')
plugins = payload.setdefault('plugins', [])
for i, p in enumerate(plugins):
    if isinstance(p, dict) and p.get('name') == entry['name']:
        plugins[i] = entry; break
else:
    plugins.append(entry)
mp_path.parent.mkdir(parents=True, exist_ok=True)
mp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# 2. config.toml
config_path.parent.mkdir(parents=True, exist_ok=True)
text = config_path.read_text(encoding='utf-8') if config_path.exists() else ''
now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def patch(text, header, body):
    pat = re.compile(r'(?ms)^' + re.escape(header) + r'\n(?:(?!^\[).*\n?)*')
    block = header + '\n' + (body if body.endswith('\n') else body + '\n')
    if pat.search(text):
        return pat.sub(block, text, count=1)
    if text and not text.endswith('\n'): text += '\n'
    if text and not text.endswith('\n\n'): text += '\n'
    return text + block

mroot_toml = mroot.replace('\\', '\\\\')
text = patch(text, f'[marketplaces.{mname}]',
             f'last_updated = \"{now}\"\nsource_type = \"local\"\nsource = \"{mroot_toml}\"\n')
text = patch(text, f'[plugins.\"datamind-context@{mname}\"]', 'enabled = true\n')
config_path.write_text(text, encoding='utf-8')
print(f'Wrote {mp_path}'); print(f'Patched {config_path}')
"@

& $PythonExe -c $pyScript $MarketplaceJson $MarketplaceName $MarketplaceRoot $CodexConfig

# --- Friendly summary ---
Write-Host ""
Write-Host "Installed $PluginName for Codex (OpenAI desktop app)."
Write-Host "Marketplace name:    $MarketplaceName"
Write-Host "Marketplace root:    $MarketplaceRoot"
Write-Host "Plugin source:       $TargetDir"
Write-Host "DataMind repo root:  $RepoRoot"
Write-Host "Codex config:        $CodexConfig"
Write-Host ""
if (Test-Path (Join-Path $RepoRoot '.env')) {
    Write-Host "Before first use, make sure $RepoRoot\.env contains valid LLM and embedding credentials."
}
Write-Host ""
Write-Host "Next step: fully quit Codex and reopen it. The plugin should appear in"
Write-Host "          Codex's plugin list and start automatically."
