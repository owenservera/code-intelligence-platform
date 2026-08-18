#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Run the CIP Web Console in dev mode with hot reload (frontend + backend).
.DESCRIPTION
  - Backend:  FastAPI app via uvicorn with --reload (watches lib/)
  - Frontend: Vite dev server (HMR) in web/, proxying /api and /ws to the backend
  Ctrl+C in this window stops the frontend and the spawned backend process.
  Run from the repo root:  .\dev.ps1
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8090,
    [int]$FrontendPort = 5173,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$webDir = Join-Path $root "web"
$libDir = Join-Path $root "lib"

if (-not (Test-Path (Join-Path $webDir "package.json"))) {
    throw "web/ not found at $webDir. Run this from the repo root."
}

# Prefer a repo-local venv if present; otherwise real python, else py launcher.
$venvPy = Join-Path $root "venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $python = $venvPy
}
else {
    $cmd = (Get-Command python -ErrorAction SilentlyContinue)
    if (-not $cmd) {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if (-not $py) { throw "No Python interpreter found (python or py)." }
        $cmd = $py
    }
    $python = $cmd.Source
}

if (Get-Command bun -ErrorAction SilentlyContinue) { $runner = "bun" }
elseif (Get-Command npm -ErrorAction SilentlyContinue) { $runner = "npm" }
else { throw "No package manager found (bun or npm) for the web frontend." }

Write-Host ""
Write-Host "  CIP Web Console - dev hot reload" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:$BackendPort  (uvicorn, reload=$(-not $NoReload))"
Write-Host "  Frontend: http://localhost:$FrontendPort  (vite, HMR)"
Write-Host "  Press Ctrl+C to stop both" -ForegroundColor Yellow
Write-Host ""

# ── Backend: uvicorn on lib/cipkg/web_bridge.py ──────────────────────────────
$env:PYTHONPATH = $libDir
$backendArgs = @(
    "-m", "uvicorn", "cipkg.web_bridge:app",
    "--host", "localhost",
    "--port", "$BackendPort",
    "--log-level", "info"
)
if (-not $NoReload) {
    $backendArgs += @("--reload", "--reload-dir", $libDir)
}
$backend = Start-Process -FilePath $python -ArgumentList $backendArgs -PassThru -WorkingDirectory $root -WindowStyle Normal

try {
    # ── Frontend: Vite dev server (foreground so Ctrl+C reaches it) ────────
    Push-Location $webDir
    try {
        if ($runner -eq "bun") {
            & bun run dev --port $FrontendPort --strictPort
        }
        else {
            & npm run dev -- --port $FrontendPort --strictPort
        }
        if ($LASTEXITCODE -ne 0) { throw "Frontend dev server exited with code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($backend -and -not $backend.HasExited) {
        Write-Host "`nStopping backend (PID $($backend.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}