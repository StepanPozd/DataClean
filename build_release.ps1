[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements-build.txt (or requirements-build-lock.txt) first.'
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit Windows installation is required.' }

Push-Location -LiteralPath $projectRoot
$savedBuildPath = $env:PATH
try {
    $env:TMP = Join-Path $projectRoot '.cache\tmp'
    $env:TEMP = $env:TMP
    $env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot '.cache\pyinstaller'
    # Avoid DLL collisions from unrelated tools (e.g. Poppler/Conda ICU on PATH).
    $env:PATH = ((Join-Path $projectRoot '.venv\Scripts'), (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    foreach ($cachePath in @($env:TMP, $env:PIP_CACHE_DIR, $env:PYINSTALLER_CONFIG_DIR)) {
        New-Item -ItemType Directory -Force -Path $cachePath | Out-Null
    }
    if (-not $SkipTests) {
        & $pythonPath -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw 'pytest failed.' }
        & $pythonPath -m ruff check .
        if ($LASTEXITCODE -ne 0) { throw 'Ruff failed.' }
        & $pythonPath -m ruff format --check .
        if ($LASTEXITCODE -ne 0) { throw 'Formatting check failed.' }
        & $pythonPath -m compileall -q app main.py tests examples tools
        if ($LASTEXITCODE -ne 0) { throw 'Byte compilation failed.' }
        & $pythonPath -m pip check
        if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
    }
    & $pythonPath tools/generate_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $pythonPath -c "from pathlib import Path; root=Path.cwd().resolve(); assert all((root/p).resolve().is_relative_to(root) for p in ('build','dist','release')), 'Build targets must stay inside the project'"
    if ($LASTEXITCODE -ne 0) { throw 'Unsafe output target.' }
    # Only PyInstaller-owned build/dist targets inside this project are replaced.
    & $pythonPath -m PyInstaller --noconfirm --clean --distpath dist --workpath build DataClean.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    & $pythonPath tools/finalize_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Release finalization failed.' }
}
finally {
    $env:PATH = $savedBuildPath
    Pop-Location
}
