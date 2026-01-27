# Multi-stage Dockerfile for Jeeves FF
# Optimized for Docker deployment with split gateway/orchestrator architecture
#
# OPTIMIZATION: Uses separate requirements files to minimize image sizes
#   - Gateway: ~200MB (fastapi, grpcio only)
#   - Orchestrator: ~2.5GB (includes sentence-transformers, pytorch)
#   - Previous: Both were ~2.5GB due to shared requirements
#
# HYBRID PYTHON-GO: Go binaries built and included for performance-critical ops
#   - go-envelope: Envelope processing (bounds checking, validation)
#   - Go binaries in /app/bin/, called via subprocess
#
# Stages:
#   builder-go         - Go binary compilation
#   builder-base       - Shared proto compilation
#   builder-gateway    - Gateway-specific dependencies (minimal)
#   builder-orchestrator - Full orchestrator dependencies (ML, database)
#   test              - Testing stage with all dependencies
#   gateway           - HTTP gateway only (FastAPI + gRPC client)
#   orchestrator      - gRPC orchestration service
#
# Build examples:
#   Gateway:      docker build -t jeeves-gateway:latest --target gateway .
#   Orchestrator: docker build -t jeeves-orchestrator:latest --target orchestrator .
#   Test:         docker build -t assistant-7agent:test --target test .

# =============================================================================
# Builder Go Stage - Compile Go binaries for hybrid execution
# =============================================================================
FROM docker.io/library/golang:1.24-alpine AS builder-go

WORKDIR /build

# Copy Go module files first (for caching)
# jeeves-core submodule contains go.mod at root level
COPY jeeves-core/go.mod jeeves-core/go.sum* ./

# Download dependencies
RUN go mod download || true

# Copy Go source from submodule
COPY jeeves-core/cmd/ ./cmd/
COPY jeeves-core/commbus/ ./commbus/
COPY jeeves-core/coreengine/ ./coreengine/

# Build binaries
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /build/bin/go-envelope ./cmd/envelope

# =============================================================================
# Builder Base Stage - Proto compilation only
# =============================================================================
FROM docker.io/library/python:3.11-slim AS builder-base

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install grpcio-tools for proto compilation
RUN pip install --no-cache-dir grpcio-tools>=1.60.0

# Compile proto files (located in jeeves-core/mission_system/proto/)
COPY jeeves-core/mission_system/proto/ ./proto/
RUN python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    proto/jeeves.proto && \
    touch proto/__init__.py

# =============================================================================
# Builder Gateway Stage - Minimal dependencies for HTTP gateway
# =============================================================================
FROM docker.io/library/python:3.11-slim AS builder-gateway

WORKDIR /build

# Create virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy split requirements files
COPY requirements/base.txt requirements/gateway.txt ./

# Install gateway dependencies only (minimal: ~150MB vs ~2.5GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r gateway.txt

# =============================================================================
# Builder Orchestrator Stage - Full dependencies for gRPC service
# =============================================================================
FROM docker.io/library/python:3.11-slim AS builder-orchestrator

# Install build dependencies for native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy split requirements files
COPY requirements/base.txt requirements/orchestrator.txt ./

# Install orchestrator dependencies in stages to reduce peak memory
# Heavy ML packages first (sentence-transformers pulls in torch)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir sentence-transformers && \
    pip install --no-cache-dir -r orchestrator.txt

# =============================================================================
# Test Stage - Full dependencies + test packages
# =============================================================================
FROM builder-orchestrator AS test

# Install test dependencies from requirements/test.txt
# Note: test.txt dependencies are already installed from orchestrator stage
COPY requirements/test.txt requirements/base.txt requirements/orchestrator.txt ./
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    pytest-timeout>=2.0.0 \
    pytest-xdist>=3.5.0 \
    pytest-html>=4.1.0 \
    pytest-json-report>=1.5.0 \
    testcontainers[postgres]>=3.7.0 \
    websockets>=12.0 \
    httpx>=0.25.0 \
    asyncpg>=0.29.0 \
    aiohttp>=3.9.0 \
    docker>=7.0.0 \
    hypothesis>=6.92.0

# Set working directory
WORKDIR /app

# Copy compiled proto files from builder-base
COPY --from=builder-base /build/proto/ ./proto/

# Copy Go binaries for hybrid execution testing
COPY --from=builder-go /build/bin/ ./bin/
ENV PATH="/app/bin:$PATH"
ENV GO_BIN_PATH=/app/bin

# Cache-busting: pass git SHA or timestamp to force rebuild when code changes
# Usage: docker compose build --build-arg CODE_VERSION=$(git rev-parse --short HEAD)
ARG CODE_VERSION=dev
RUN echo "Code version: ${CODE_VERSION}" > /app/.code_version

# Copy application code from jeeves-core submodule
# Constitutional dependency hierarchy: protocols/shared → control_tower → avionics → mission_system → capability
COPY --chown=1000:1000 jeeves-core/protocols/ ./protocols/
COPY --chown=1000:1000 jeeves-core/shared/ ./shared/
COPY --chown=1000:1000 jeeves-core/control_tower/ ./control_tower/
COPY --chown=1000:1000 jeeves-core/memory_module/ ./memory_module/
COPY --chown=1000:1000 jeeves-core/avionics/ ./avionics/
COPY --chown=1000:1000 jeeves-core/mission_system/ ./mission_system/

# Copy hello-world capability as Python package
# This enables: from jeeves_capability_hello_world import register_capability
COPY --chown=1000:1000 jeeves_capability_hello_world/ ./jeeves_capability_hello_world/

# Copy hello-world tests
COPY --chown=1000:1000 jeeves_capability_hello_world/tests/ ./hello_world_tests/
COPY --chown=1000:1000 tests/ ./tests/

# Copy Gradio application
COPY --chown=1000:1000 gradio_app.py ./

# Install local packages in editable mode (required for imports)
RUN pip install --no-cache-dir -e ./protocols -e ./shared

# Create cache directories for transformers/huggingface models
RUN mkdir -p /app/data /app/data/.cache/huggingface /app/data/.cache/torch

# Set cache directories for ML models
ENV TRANSFORMERS_CACHE=/app/data/.cache/huggingface
ENV HF_HOME=/app/data/.cache/huggingface
ENV TORCH_HOME=/app/data/.cache/torch
ENV XDG_CACHE_HOME=/app/data/.cache

# Test environment variables
ENV LOG_LEVEL=DEBUG
ENV PYTHONUNBUFFERED=1

# Default test command
CMD ["pytest", "-v", "--tb=short"]

# =============================================================================
# Gateway Stage - HTTP API only (FastAPI + gRPC client)
# Image size: ~200MB (down from ~2.5GB)
# =============================================================================
FROM docker.io/library/python:3.11-slim AS gateway

# Create non-root user
RUN groupadd -r jeeves && useradd -r -g jeeves -u 1000 -m -d /home/jeeves jeeves

# Copy minimal virtual environment from builder-gateway
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder-gateway --chown=jeeves:jeeves "$VIRTUAL_ENV" "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Copy compiled proto files from builder-base
COPY --from=builder-base --chown=jeeves:jeeves /build/proto/ ./proto/

# Cache-busting: pass git SHA or timestamp to force rebuild when code changes
# Usage: docker compose build --build-arg CODE_VERSION=$(git rev-parse --short HEAD)
ARG CODE_VERSION=dev
RUN echo "Code version: ${CODE_VERSION}" > /app/.code_version

# Copy only gateway-related code (minimal footprint) from jeeves-core submodule
# ADR-001: Gateway requires logging module and core protocols for DI pattern
# Create minimal package structure (don't copy full __init__.py which has many dependencies)
RUN mkdir -p avionics protocols shared && \
    echo '"""Minimal avionics for gateway."""' > avionics/__init__.py && \
    echo '"""Minimal protocols for gateway."""' > protocols/__init__.py && \
    echo '"""Minimal shared for gateway."""' > shared/__init__.py && \
    chown -R jeeves:jeeves avionics protocols shared
COPY --chown=jeeves:jeeves jeeves-core/avionics/gateway/ ./avionics/gateway/
COPY --chown=jeeves:jeeves jeeves-core/avionics/logging/ ./avionics/logging/
COPY --chown=jeeves:jeeves jeeves-core/protocols/ ./protocols/
COPY --chown=jeeves:jeeves jeeves-core/shared/ ./shared/
COPY --chown=jeeves:jeeves jeeves-core/mission_system/config/ ./mission_system/config/
# Copy static files to ./static/ (gateway looks for "static" relative to /app)
# Frontend assets are now capability-owned (migrated from jeeves-core)
COPY --chown=jeeves:jeeves frontend/static/ ./static/
# Copy templates to ./gateway/templates/ (primary path gateway checks)
COPY --chown=jeeves:jeeves frontend/templates/ ./gateway/templates/

# Create directories
RUN mkdir -p /app/data && chown -R jeeves:jeeves /app/data /home/jeeves

USER jeeves

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

EXPOSE 8000

ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV ORCHESTRATOR_HOST=orchestrator
ENV ORCHESTRATOR_PORT=50051
ENV LOG_FORMAT=json
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "uvicorn", "avionics.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Orchestrator Stage - gRPC service (agents, tools, database)
# Image size: ~2.5GB (includes sentence-transformers, pytorch)
# =============================================================================
FROM docker.io/library/python:3.11-slim AS orchestrator

# Create non-root user
RUN groupadd -r jeeves && useradd -r -g jeeves -u 1000 -m -d /home/jeeves jeeves

# Copy full virtual environment from builder-orchestrator
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder-orchestrator --chown=jeeves:jeeves "$VIRTUAL_ENV" "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Copy compiled proto files from builder-base
COPY --from=builder-base --chown=jeeves:jeeves /build/proto/ ./proto/

# Copy Go binaries for hybrid Python-Go execution
# These enable performance-critical operations (envelope processing) in Go
COPY --from=builder-go --chown=jeeves:jeeves /build/bin/ ./bin/
ENV PATH="/app/bin:$PATH"
ENV GO_BIN_PATH=/app/bin

# Cache-busting: pass git SHA or timestamp to force rebuild when code changes
# Usage: docker compose build --build-arg CODE_VERSION=$(git rev-parse --short HEAD)
ARG CODE_VERSION=dev
RUN echo "Code version: ${CODE_VERSION}" > /app/.code_version

# Copy all orchestration code from jeeves-core submodule
# Constitutional dependency hierarchy: protocols/shared → control_tower → avionics → mission_system → capability
COPY --chown=jeeves:jeeves jeeves-core/protocols/ ./protocols/
COPY --chown=jeeves:jeeves jeeves-core/shared/ ./shared/
COPY --chown=jeeves:jeeves jeeves-core/control_tower/ ./control_tower/
COPY --chown=jeeves:jeeves jeeves-core/memory_module/ ./memory_module/
COPY --chown=jeeves:jeeves jeeves-core/avionics/ ./avionics/
COPY --chown=jeeves:jeeves jeeves-core/mission_system/ ./mission_system/

# Copy hello-world capability as Python package
# This enables: from jeeves_capability_hello_world import register_capability
COPY --chown=jeeves:jeeves jeeves_capability_hello_world/ ./jeeves_capability_hello_world/

# Copy Gradio application for hello-world chatbot
COPY --chown=jeeves:jeeves gradio_app.py ./

# Install local packages in editable mode
# This makes protocols and shared importable
RUN pip install --no-cache-dir -e ./protocols -e ./shared

# Create directories for cache/data
RUN mkdir -p /app/data /app/data/.cache/huggingface /app/data/.cache/torch && \
    chown -R jeeves:jeeves /app/data /home/jeeves

USER jeeves

# Gradio health check for hello-world chatbot
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

ENV GRADIO_PORT=8000
ENV POSTGRES_HOST=postgres
ENV POSTGRES_PORT=5432
ENV POSTGRES_DATABASE=assistant
ENV LLM_PROVIDER=llamaserver
ENV LLAMASERVER_HOST=http://llama-server:8080
ENV LOG_FORMAT=json
ENV LOG_LEVEL=INFO

# Cache directories for ML models
ENV TRANSFORMERS_CACHE=/app/data/.cache/huggingface
ENV HF_HOME=/app/data/.cache/huggingface
ENV TORCH_HOME=/app/data/.cache/torch
ENV XDG_CACHE_HOME=/app/data/.cache

# Default: start hello-world chatbot with Gradio UI
CMD ["python", "gradio_app.py"]
