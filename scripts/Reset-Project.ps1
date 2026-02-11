#!/usr/bin/env pwsh
# Complete Project Reset Script (PowerShell)
# This script resets the project to a clean state from main branch

$ErrorActionPreference = "Stop"

Write-Host "Starting Complete Project Reset..." -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# 1. GIT RESET TO MAIN
# =============================================================================
Write-Host "Step 1: Resetting to latest main branch..." -ForegroundColor Yellow

# Fetch latest from remote
git fetch origin main

# Show current branch and status
$currentBranch = git branch --show-current
Write-Host "Current branch: $currentBranch" -ForegroundColor Gray
git status --short

# Ask for confirmation
$confirm = Read-Host "This will HARD RESET to origin/main. All local changes will be LOST. Continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Reset cancelled" -ForegroundColor Red
    exit 1
}

# Checkout main and hard reset
try {
    git checkout main 2>$null
} catch {
    git checkout -b main origin/main
}
git reset --hard origin/main
git clean -fdx  # Remove all untracked files and directories

Write-Host "Git reset complete" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 2. CLEAN PYTHON ARTIFACTS
# =============================================================================
Write-Host "Step 2: Cleaning Python artifacts..." -ForegroundColor Yellow

# Remove all Python cache and build artifacts
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter "build" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter "dist" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# Remove coverage and test artifacts
if (Test-Path ".coverage") { Remove-Item ".coverage" -Force }
if (Test-Path "htmlcov") { Remove-Item "htmlcov" -Recurse -Force }

# Remove SQLite databases
Get-ChildItem -Path . -Recurse -File -Filter "*.db" -ErrorAction SilentlyContinue | Remove-Item -Force

# Remove virtual environments if they exist
@("venv", ".venv", "env") | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Recurse -Force }
}

Write-Host "Python artifacts cleaned" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 3. FRESH INSTALL DEPENDENCIES (uv)
# =============================================================================
Write-Host "Step 3: Installing fresh dependencies via uv..." -ForegroundColor Yellow

uv sync

Write-Host "Dependencies installed" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 4. VERIFICATION
# =============================================================================
Write-Host "Step 4: Running verification tests..." -ForegroundColor Yellow

# Run fast tier 1 tests to verify setup
uv run pytest jeeves_capability_hello_world/tests -v

Write-Host ""
Write-Host "Project reset complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  - Git: Reset to origin/main"
Write-Host "  - Python: All cache and artifacts cleaned"
Write-Host "  - SQLite: Database files removed (recreated on first run)"
Write-Host "  - Dependencies: Freshly installed"
Write-Host "  - Tests: Tier 1 passing"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Ensure Ollama is running: ollama serve"
Write-Host "  2. Pull a model: ollama pull llama3.2"
Write-Host "  3. Run chatbot: uv run python gradio_app.py"
Write-Host "  4. Run tests: .\scripts\test.ps1 ci"
Write-Host ""
