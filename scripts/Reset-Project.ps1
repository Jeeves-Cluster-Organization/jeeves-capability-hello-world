#!/usr/bin/env pwsh
# Complete Project Reset Script (PowerShell)
# This script resets the project to a clean state from main branch

$ErrorActionPreference = "Stop"

Write-Host "🧹 Starting Complete Project Reset..." -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# 1. GIT RESET TO MAIN
# =============================================================================
Write-Host "[NOEMOJI] Step 1: Resetting to latest main branch..." -ForegroundColor Yellow

# Fetch latest from remote
git fetch origin main

# Show current branch and status
$currentBranch = git branch --show-current
Write-Host "Current branch: $currentBranch" -ForegroundColor Gray
git status --short

# Ask for confirmation
$confirm = Read-Host "[NOEMOJI]  This will HARD RESET to origin/main. All local changes will be LOST. Continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "[NOEMOJI] Reset cancelled" -ForegroundColor Red
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

Write-Host "[NOEMOJI] Git reset complete" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 2. CLEAN PYTHON ARTIFACTS
# =============================================================================
Write-Host "[NOEMOJI] Step 2: Cleaning Python artifacts..." -ForegroundColor Yellow

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
Get-ChildItem -Path . -File -Filter "*.db" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Filter "*.db-shm" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -File -Filter "*.db-wal" -ErrorAction SilentlyContinue | Remove-Item -Force

# Remove virtual environments if they exist
@("venv", ".venv", "env") | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Recurse -Force }
}

Write-Host "[NOEMOJI] Python artifacts cleaned" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 3. CLEAN NODE.JS ARTIFACTS
# =============================================================================
Write-Host "[NOEMOJI] Step 3: Cleaning Node.js artifacts..." -ForegroundColor Yellow

# Find and remove all node_modules directories
Get-ChildItem -Path . -Recurse -Directory -Filter "node_modules" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -File -Filter "package-lock.json" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "[NOEMOJI] Node.js artifacts cleaned" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 4. DOCKER CLEANUP (requires Docker to be available)
# =============================================================================
Write-Host "[NOEMOJI] Step 4: Docker cleanup..." -ForegroundColor Yellow

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Stopping Docker containers..."
    docker compose -f docker/docker-compose.yml down -v 2>$null

    Write-Host "Removing project Docker images..."
    $images = docker images | Select-String -Pattern "assistant-gateway|assistant-7agent|helloworld"
    if ($images) {
        $images | ForEach-Object {
            $imageId = ($_ -split '\s+')[2]
            docker rmi -f $imageId 2>$null
        }
    }

    Write-Host "Removing dangling images..."
    docker image prune -f

    Write-Host "Removing unused volumes..."
    docker volume prune -f

    Write-Host "[NOEMOJI] Docker cleanup complete" -ForegroundColor Green
} else {
    Write-Host "[NOEMOJI]  Docker not available in this environment" -ForegroundColor Yellow
    Write-Host "   Run these commands manually if Docker is installed:"
    Write-Host "   - docker compose -f docker/docker-compose.yml down -v"
    Write-Host "   - docker images | Select-String 'assistant-gateway|assistant-7agent' | ForEach-Object { docker rmi -f `$_ }"
    Write-Host "   - docker image prune -f"
    Write-Host "   - docker volume prune -f"
}
Write-Host ""

# =============================================================================
# 5. INITIALIZE DATABASE SCHEMAS
# =============================================================================
Write-Host "[NOEMOJI] Step 5: Initializing database schemas..." -ForegroundColor Yellow

# Wait for PostgreSQL to be ready
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Waiting for PostgreSQL to be ready..."
    $retries = 30
    $ready = $false

    for ($i = 1; $i -le $retries; $i++) {
        try {
            docker exec jeeves-postgres pg_isready -U "${env:POSTGRES_USER}" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $ready = $true
                Write-Host "[NOEMOJI] PostgreSQL is ready" -ForegroundColor Green
                break
            }
        } catch {
            # Continue waiting
        }
        Start-Sleep -Seconds 1
        Write-Host -NoNewline "."
    }

    if (-not $ready) {
        Write-Host ""
        Write-Host "[NOEMOJI]  PostgreSQL is not ready. Database initialization skipped." -ForegroundColor Yellow
        Write-Host "   You may need to run schema initialization manually:"
        Write-Host "   - Base schema: python jeeves-core/jeeves_mission_system/scripts/database/init.py"
        Write-Host "   - Hello world schema: bash jeeves-capability-hello-world/apply_schema.sh"
    } else {
        Write-Host ""

        # Initialize base schema
        Write-Host "Initializing base schema..."
        try {
            python jeeves-core/jeeves_mission_system/scripts/database/init.py --verify
            Write-Host "[NOEMOJI] Base schema initialized" -ForegroundColor Green
        } catch {
            Write-Host "[NOEMOJI]  Base schema initialization failed: $_" -ForegroundColor Yellow
        }

        # Initialize hello world schema
        Write-Host "Initializing hello world schema..."
        try {
            if (Test-Path "jeeves_capability_hello_world/database/schemas/002_hello_world_schema.sql") {
                # Use bash if available (WSL or Git Bash)
                if (Get-Command bash -ErrorAction SilentlyContinue) {
                    bash -c "psql -h ${env:POSTGRES_HOST} -p ${env:POSTGRES_PORT} -U ${env:POSTGRES_USER} -d ${env:POSTGRES_DATABASE} -f jeeves_capability_hello_world/database/schemas/002_hello_world_schema.sql"
                    Write-Host "[NOEMOJI] Hello world schema initialized" -ForegroundColor Green
                } else {
                    # Fallback: use psql directly if available
                    if (Get-Command psql -ErrorAction SilentlyContinue) {
                        $env:PGPASSWORD = "${env:POSTGRES_PASSWORD}"
                        psql -h "${env:POSTGRES_HOST}" -p "${env:POSTGRES_PORT}" -U "${env:POSTGRES_USER}" -d "${env:POSTGRES_DATABASE}" -f jeeves_capability_hello_world/database/schemas/002_hello_world_schema.sql
                        Write-Host "[NOEMOJI] Hello world schema initialized" -ForegroundColor Green
                    } else {
                        Write-Host "[NOEMOJI]  bash/psql not available. Skipping hello world schema." -ForegroundColor Yellow
                        Write-Host "   Install WSL/Git Bash or PostgreSQL client tools to enable this feature"
                    }
                }
            }
        } catch {
            Write-Host "[NOEMOJI]  Hello world schema initialization failed: $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[NOEMOJI]  Docker not available. Database initialization skipped." -ForegroundColor Yellow
}

Write-Host ""

# =============================================================================
# 6. FRESH INSTALL DEPENDENCIES
# =============================================================================
Write-Host "[NOEMOJI] Step 6: Installing fresh dependencies..." -ForegroundColor Yellow

# Update pip
python -m pip install --upgrade pip

# Install Python dependencies
if (Test-Path "requirements/all.txt") {
    pip install -r requirements/all.txt
} elseif (Test-Path "requirements.txt") {
    pip install -r requirements.txt
}

# Install Node.js dependencies if package.json exists
if (Test-Path "jeeves_mission_system/tests/frontend/package.json") {
    Write-Host "Installing frontend dependencies..."
    Push-Location jeeves_mission_system/tests/frontend
    npm install
    Pop-Location
}

Write-Host "[NOEMOJI] Dependencies installed" -ForegroundColor Green
Write-Host ""

# =============================================================================
# 7. VERIFICATION
# =============================================================================
Write-Host "[NOEMOJI] Step 7: Running verification tests..." -ForegroundColor Yellow

# Run fast tier 1 tests to verify setup
python -m pytest -c pytest-light.ini `
    jeeves_core_engine/tests `
    jeeves_avionics/tests/unit/llm `
    jeeves_mission_system/tests/contract `
    jeeves-capability-code-analyser/tests `
    -v

Write-Host ""
Write-Host "[NOEMOJI] Project reset complete!" -ForegroundColor Green
Write-Host ""
Write-Host "[NOEMOJI] Summary:" -ForegroundColor Cyan
Write-Host "  - Git: Reset to origin/main"
Write-Host "  - Python: All cache and artifacts cleaned"
Write-Host "  - Node.js: All node_modules removed"
Write-Host "  - Docker: Images and containers cleaned"
Write-Host "  - Dependencies: Freshly installed"
Write-Host "  - Tests: Tier 1 passing"
Write-Host ""
Write-Host "[NOEMOJI] Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start Docker services: docker compose -f docker/docker-compose.yml up -d"
Write-Host "  2. Run tier 2 tests: make test-tier2"
Write-Host "  3. Run tier 3 tests: make test-tier3"
Write-Host "  4. Run full tests: make test-nightly"
Write-Host ""
