# Integration, Deployment, and UI/UX Testing Guide

**Version:** 1.0 | **Date:** 2025-12-13

---

## Overview

This document provides comprehensive steps for running integration tests, deployment tests, and UI/UX tests for the Jeeves Code Analysis Capability.

**Reference:** All tests are based on the [JEEVES_CORE_RUNTIME_CONTRACT.md](JEEVES_CORE_RUNTIME_CONTRACT.md) as the source of truth.

---

## Test Categories

| Category | Location | Purpose | Requirements |
|----------|----------|---------|--------------|
| Integration | `tests/integration/` | Service contracts, agent pipeline | None (mocked) |
| Deployment | `tests/deployment/` | Docker, health checks, connectivity | Docker running |
| UI/UX | `tests/ui_ux/` | API formats, WebSocket, response validation | None (format tests) |

---

## Quick Start

### Run All Tests (No External Dependencies)

```bash
# Run all unit and contract tests
pytest tests/ -m "not requires_docker and not requires_postgres"

# Run with verbose output
pytest tests/ -v -m "not requires_docker"
```

### Run With Docker Services

```bash
# Start services first
docker compose -f docker/docker-compose.yml up -d postgres llama-server

# Wait for services to be healthy
sleep 30

# Run integration tests
pytest tests/integration/ -v

# Run deployment tests
pytest tests/deployment/ -m "requires_docker" -v
```

---

## Full Integration Testing Steps

### Step 1: Environment Setup

```bash
# 1. Clone repository (if not already done)
git clone <repo-url>
cd jeeves-capability-code-analysis

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate  # Windows

# 3. Install test dependencies
pip install -r requirements/test.txt
```

### Step 2: Run Contract Tests

Contract tests validate that implementations follow the runtime contract.

```bash
# Run all contract tests
pytest tests/integration/test_service_contracts.py -v

# Run specific contract test class
pytest tests/integration/test_service_contracts.py::TestLLMProviderContract -v
pytest tests/integration/test_service_contracts.py::TestToolExecutorContract -v
pytest tests/integration/test_service_contracts.py::TestStandardToolResultContract -v
```

**Expected Output:**
- All protocol implementations should pass
- Contract compliance should be 100%

### Step 3: Run Agent Pipeline Tests

```bash
# Run agent pipeline tests
pytest tests/integration/test_agent_pipeline.py -v

# Run specific agent tests
pytest tests/integration/test_agent_pipeline.py::TestAgentPipelineFlow -v
pytest tests/integration/test_agent_pipeline.py::TestConstitutionalCompliance -v
```

---

## Full Deployment Testing Steps

### Step 1: Verify Docker Configuration

```bash
# Test without Docker running (config validation only)
pytest tests/deployment/test_docker_infrastructure.py::TestDockerConfiguration -v
pytest tests/deployment/test_docker_infrastructure.py::TestRequirementsFiles -v
```

### Step 2: Start Docker Services

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Check service status
docker compose -f docker/docker-compose.yml ps

# View logs
docker compose -f docker/docker-compose.yml logs -f
```

### Step 3: Run Health Check Tests

```bash
# Wait for services to be healthy (important!)
sleep 60

# Run health check tests
pytest tests/deployment/test_service_health.py -v -m "requires_docker"
```

### Step 4: Run Full Deployment Tests

```bash
# Run all deployment tests
pytest tests/deployment/ -v -m "requires_docker"

# Run with detailed output
pytest tests/deployment/ -v --tb=long -m "requires_docker"
```

### Step 5: Stop Services

```bash
docker compose -f docker/docker-compose.yml down
```

---

## Full UI/UX Testing Steps

### Step 1: Run API Format Tests

```bash
# Run all API format tests (no services needed)
pytest tests/ui_ux/test_api_endpoints.py -v

# Run specific format tests
pytest tests/ui_ux/test_api_endpoints.py::TestRequestFormats -v
pytest tests/ui_ux/test_api_endpoints.py::TestResponseFormats -v
pytest tests/ui_ux/test_api_endpoints.py::TestErrorHandling -v
```

### Step 2: Run WebSocket Event Tests

```bash
# Run WebSocket format tests (no services needed)
pytest tests/ui_ux/test_websocket.py -v

# Run specific WebSocket tests
pytest tests/ui_ux/test_websocket.py::TestWebSocketEventFormats -v
pytest tests/ui_ux/test_websocket.py::TestStreamingResponses -v
```

### Step 3: Run Live API Tests (Requires Services)

```bash
# Start services
docker compose -f docker/docker-compose.yml up -d

# Run live API tests
pytest tests/ui_ux/ -v -m "requires_docker"
```

---

## Complete Test Flow

### Tier 1: Fast Tests (< 1 minute)

```bash
# All contract and format tests
pytest tests/ -v -m "not requires_docker and not requires_postgres and not slow"
```

### Tier 2: Integration Tests (1-5 minutes)

```bash
# Start PostgreSQL only
docker compose -f docker/docker-compose.yml up -d postgres
sleep 30

# Run database-dependent tests
pytest tests/ -v -m "requires_postgres and not requires_llamaserver"
```

### Tier 3: Full Stack Tests (5-15 minutes)

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d
sleep 60

# Run all tests including E2E
pytest tests/ -v -m "requires_docker or e2e"
```

### Tier 4: Complete Validation

```bash
# Run complete test suite with coverage
pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# Generate test report
pytest tests/ -v --html=reports/test_report.html --json-report --json-report-file=reports/test_results.json
```

---

## Test Commands Reference

### By Test Type

```bash
# Contract tests only
pytest tests/integration/test_service_contracts.py -v

# Deployment tests only
pytest tests/deployment/ -v

# UI/UX tests only
pytest tests/ui_ux/ -v

# Pipeline tests only
pytest tests/integration/test_agent_pipeline.py -v
```

### By Marker

```bash
# All contract tests
pytest tests/ -m contract -v

# All deployment tests
pytest tests/ -m deployment -v

# All UI/UX tests
pytest tests/ -m ui_ux -v

# All WebSocket tests
pytest tests/ -m websocket -v

# All E2E tests
pytest tests/ -m e2e -v
```

### With Coverage

```bash
# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html

# Coverage with minimum threshold
pytest tests/ --cov=. --cov-fail-under=80
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Auto-detect number of workers
pytest tests/ -n auto
```

---

## Docker Commands Reference

### Build Images

```bash
# Build all images
docker compose -f docker/docker-compose.yml build

# Build specific image
docker compose -f docker/docker-compose.yml build test

# Build with cache busting
docker compose -f docker/docker-compose.yml build --no-cache
```

### Run Tests in Docker

```bash
# Run unit tests in container
docker compose -f docker/docker-compose.yml --profile test run --rm test pytest tests/ -v

# Run specific test file
docker compose -f docker/docker-compose.yml --profile test run --rm test pytest tests/integration/test_service_contracts.py -v

# Run with coverage
docker compose -f docker/docker-compose.yml --profile test run --rm test pytest tests/ --cov=. --cov-report=term
```

### Service Health Checks

```bash
# Check PostgreSQL
docker compose -f docker/docker-compose.yml exec postgres pg_isready

# Check llama-server
curl http://localhost:8080/health

# Check gateway
curl http://localhost:8001/health

# Check all services
docker compose -f docker/docker-compose.yml ps
```

---

## PowerShell Commands (Windows)

```powershell
# Run CI tests
.\scripts\test.ps1 ci

# Run full test flow
.\scripts\test.ps1 full

# Check services
.\scripts\test.ps1 services

# Run specific tier
.\scripts\test.ps1 tier2
.\scripts\test.ps1 tier3
.\scripts\test.ps1 tier4
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker compose -f docker/docker-compose.yml logs llama-server

# Check resource usage
docker stats

# Restart services
docker compose -f docker/docker-compose.yml restart
```

### Tests Timing Out

```bash
# Increase timeout
pytest tests/ -v --timeout=300

# Run single test with verbose output
pytest tests/deployment/test_service_health.py::TestServiceConnectivity::test_postgres_port_reachable -v -s
```

### Port Conflicts

```bash
# Check what's using port
lsof -i :8000
netstat -tlnp | grep 8000

# Use different ports in .env
API_PORT=8002
GATEWAY_PORT=8003
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker compose -f docker/docker-compose.yml exec postgres pg_isready -U assistant

# Reset database
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements/test.txt
      - run: pytest tests/ -v -m "not requires_docker"

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: assistant
          POSTGRES_USER: assistant
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements/test.txt
      - run: pytest tests/ -v -m "requires_postgres"
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DATABASE: assistant
          POSTGRES_USER: assistant
          POSTGRES_PASSWORD: test_password
```

---

## Test File Structure

```
tests/
├── __init__.py
├── integration/
│   ├── __init__.py
│   ├── test_agent_pipeline.py      # 7-agent pipeline tests
│   └── test_service_contracts.py   # Contract compliance tests
├── deployment/
│   ├── __init__.py
│   ├── test_docker_infrastructure.py  # Docker config tests
│   └── test_service_health.py         # Health check tests
└── ui_ux/
    ├── __init__.py
    ├── test_api_endpoints.py       # API format tests
    └── test_websocket.py           # WebSocket event tests
```

---

*Last Updated: 2025-12-13*
