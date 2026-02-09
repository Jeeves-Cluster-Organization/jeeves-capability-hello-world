# PowerShell Test Runner
# Usage: .\test.ps1 <command>
# Example: .\test.ps1 ci
#          .\test.ps1 fast

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "PowerShell Test Runner" -ForegroundColor Cyan
    Write-Host "=====================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\test.ps1 <command>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fast Tests (No External Dependencies):" -ForegroundColor Green
    Write-Host "  ci             - CI test suite (Capability tests) - < 10s" -ForegroundColor White
    Write-Host "  fast           - Same as ci (Tier 1 tests)" -ForegroundColor White
    Write-Host "  contract       - Constitutional contract tests - < 5s" -ForegroundColor White
    Write-Host ""
    Write-Host "Integration Tests (Requires Docker):" -ForegroundColor Green
    Write-Host "  tier2          - Database integration tests" -ForegroundColor White
    Write-Host "  tier3          - Integration with real LLM" -ForegroundColor White
    Write-Host "  tier4          - E2E tests (full stack)" -ForegroundColor White
    Write-Host "  full           - Run ALL tiers (complete flow)" -ForegroundColor White
    Write-Host "  mission        - Mission system (lightweight)" -ForegroundColor White
    Write-Host "  mission-full   - Mission system (with services)" -ForegroundColor White
    Write-Host ""
    Write-Host "Utility:" -ForegroundColor Green
    Write-Host "  light          - All lightweight tests" -ForegroundColor White
    Write-Host "  services       - Check if services are running" -ForegroundColor White
    Write-Host "  help           - Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\test.ps1 ci              # Run CI tests (fastest)" -ForegroundColor Gray
    Write-Host "  .\test.ps1 full            # Run complete test flow (all tiers)" -ForegroundColor Gray
    Write-Host "  .\test.ps1 mission         # Test mission system (lightweight)" -ForegroundColor Gray
    Write-Host ""
}

function Test-CI {
    Write-Host ""
    Write-Host "🤖 Running CI test suite (fast, no external dependencies)" -ForegroundColor Cyan
    Write-Host "   - Capability tests" -ForegroundColor Gray
    Write-Host ""

    python -m pytest -c pytest-light.ini `
        jeeves_capability_hello_world/tests `
        -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ CI test suite complete" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ CI test suite failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Contract {
    Write-Host ""
    Write-Host "📜 Running constitutional contract tests" -ForegroundColor Cyan
    Write-Host "   - Import boundary validation" -ForegroundColor Gray
    Write-Host "   - Layer boundary enforcement" -ForegroundColor Gray
    Write-Host "   - Evidence chain integrity (P1)" -ForegroundColor Gray

    python -m pytest jeeves-airframe/mission_system/tests/contract -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Contract tests complete" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Contract tests failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Mission {
    Write-Host ""
    Write-Host "🎯 Testing mission system (contract + unit tests)" -ForegroundColor Cyan

    python -m pytest `
        jeeves-airframe/mission_system/tests/contract `
        jeeves-airframe/mission_system/tests/unit `
        -m "not requires_llamaserver and not requires_postgres" `
        -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Mission system tests complete (lightweight)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Mission system tests failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-MissionFull {
    Write-Host ""
    Write-Host "🎯 Testing mission system (full - requires Docker services)" -ForegroundColor Cyan
    Write-Host "Prerequisites: docker compose up -d postgres llama-server" -ForegroundColor Yellow
    Write-Host ""

    python -m pytest jeeves-airframe/mission_system/tests -m "not e2e and not heavy" -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Mission system tests complete (full)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Mission system tests failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Tier2 {
    Write-Host ""
    Write-Host "🐳 Running Tier 2: Integration tests (requires Docker)" -ForegroundColor Cyan
    Write-Host "   - Infra: Unit tests" -ForegroundColor Gray
    Write-Host "   - Mission System: Unit tests without LLM" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Prerequisites: docker compose up -d postgres" -ForegroundColor Yellow
    Write-Host ""

    python -m pytest `
        jeeves-airframe/jeeves_infra/tests/unit `
        jeeves-airframe/mission_system/tests/unit `
        -m "not requires_llamaserver and not requires_ml" `
        -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Tier 2 complete (expected: 10-30 seconds)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Tier 2 failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Tier3 {
    Write-Host ""
    Write-Host "🧠 Running Tier 3: Integration tests with real LLM" -ForegroundColor Cyan
    Write-Host "   - Mission System: Integration tests" -ForegroundColor Gray
    Write-Host "   - Mission System: API endpoint tests" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Prerequisites: docker compose up -d postgres llama-server" -ForegroundColor Yellow
    Write-Host ""

    python -m pytest `
        jeeves-airframe/mission_system/tests/integration `
        -m "not e2e and not heavy" `
        -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Tier 3 complete (expected: 30-60 seconds)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Tier 3 failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Tier4 {
    Write-Host ""
    Write-Host "🎯 Running Tier 4: End-to-end tests (full stack)" -ForegroundColor Cyan
    Write-Host "   - Mission System: E2E tests with real LLM" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Prerequisites: docker compose up -d (all services)" -ForegroundColor Yellow
    Write-Host ""

    python -m pytest `
        jeeves-airframe/mission_system/tests `
        -m e2e `
        -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Tier 4 complete (expected: 60+ seconds)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Tier 4 failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Light {
    Write-Host ""
    Write-Host "🪶 Running lightweight tests (no ML models, no Docker)" -ForegroundColor Cyan

    python -m pytest -c pytest-light.ini -v

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Lightweight tests complete" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Lightweight tests failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Test-Full {
    Write-Host ""
    Write-Host "🚀 Running FULL test flow (all tiers)" -ForegroundColor Cyan
    Write-Host "Prerequisites: docker compose up -d (all services)" -ForegroundColor Yellow
    Write-Host ""

    # Tier 1: Fast tests
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "TIER 1: Fast Tests (No Dependencies)" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Test-CI

    # Tier 2: Database integration
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "TIER 2: Database Integration" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Test-Tier2

    # Tier 3: LLM integration
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "TIER 3: LLM Integration" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Test-Tier3

    # Tier 4: E2E
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "TIER 4: End-to-End" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Test-Tier4

    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "✅ FULL TEST FLOW COMPLETE" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
}

function Check-Services {
    Write-Host ""
    Write-Host "🔍 Checking required services..." -ForegroundColor Cyan
    Write-Host ""

    Write-Host "PostgreSQL:" -ForegroundColor Yellow
    $pgStatus = docker compose ps postgres 2>$null
    if ($pgStatus) {
        Write-Host "  ✅ Running" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Not running (docker compose up -d postgres)" -ForegroundColor Red
    }
    Write-Host ""

    Write-Host "llama-server:" -ForegroundColor Yellow
    $llamaStatus = docker compose ps llama-server 2>$null
    if ($llamaStatus) {
        Write-Host "  ✅ Running" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Not running (docker compose up -d llama-server)" -ForegroundColor Red
    }
    Write-Host ""

    Write-Host "llamaserver health:" -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ Healthy" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Not reachable" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ❌ Not reachable" -ForegroundColor Red
    }
    Write-Host ""
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "ci"           { Test-CI }
    "fast"         { Test-CI }
    "contract"     { Test-Contract }
    "mission"      { Test-Mission }
    "mission-full" { Test-MissionFull }
    "tier2"        { Test-Tier2 }
    "tier3"        { Test-Tier3 }
    "tier4"        { Test-Tier4 }
    "full"         { Test-Full }
    "light"        { Test-Light }
    "services"     { Check-Services }
    "help"         { Show-Help }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
