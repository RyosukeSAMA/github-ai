# Native Windows bootstrap. Run in a normal PowerShell session.
$ErrorActionPreference = "Stop"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Install Git first: winget install --id Git.Git -e --source winget. Then open a new PowerShell window."
}
$Python = $null
foreach ($version in @("3.12", "3.11", "3.10")) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try { $candidate = & py "-$version" -c "import sys; print(sys.executable)" 2>$null }
        catch { continue }
        if ($LASTEXITCODE -eq 0) { $Python = $candidate.Trim(); break }
    }
}
if (-not $Python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try { $candidate = & python -c "import sys; print(sys.executable if (3,10) <= sys.version_info[:2] <= (3,12) else '')" 2>$null }
    catch { $candidate = $null }
    if ($LASTEXITCODE -eq 0 -and $candidate) { $Python = $candidate.Trim() }
}
if (-not $Python) { throw "Install Python 3.12 first: winget install --id Python.Python.3.12 -e --scope user. Then open a new PowerShell window." }
$Bootstrap = Join-Path ([IO.Path]::GetTempPath()) ("pantheon-install-" + [guid]::NewGuid() + ".py")
try {
    $Local = if ($PSCommandPath -and ([IO.Path]::GetFileName($PSCommandPath) -eq 'install.ps1')) { Join-Path $PSScriptRoot "../pantheon/installer.py" } else { $null }
    if ($Local -and (Test-Path $Local)) { Copy-Item $Local $Bootstrap }
    elseif ($env:PANTHEON_REPO_URL -and (Test-Path (Join-Path $env:PANTHEON_REPO_URL "pantheon/installer.py"))) {
        Copy-Item (Join-Path $env:PANTHEON_REPO_URL "pantheon/installer.py") $Bootstrap
    } else {
        Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/pantheon/installer.py" -OutFile $Bootstrap
    }
    & $Python $Bootstrap @args
    if ($LASTEXITCODE -ne 0) { throw "Pantheon installation failed; check the error above. The previous version was preserved." }
    if ($env:PANTHEON_SKIP_PATH -ne '1') {
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    }
} finally {
    Remove-Item $Bootstrap -ErrorAction SilentlyContinue
}
