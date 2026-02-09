# Multi-stage Dockerfile for Jeeves Hello World
# Optimized for Docker deployment with split gateway/orchestrator architecture
#
# OPTIMIZATION: Uses separate requirements files to minimize image sizes
#   - Gateway: ~200MB (fastapi, grpcio only)
#   - Orchestrator: ~2.5GB (includes sentence-transformers, pytorch)
#
# Architecture:
#   jeeves-core    = Rust micro-kernel (gRPC server, not used in Docker build)
#   jeeves-airframe = Python infrastructure (jeeves_infra + mission_system)
#   capability     = Application code (jeeves_capability_hello_world)
#
# Stages:
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

# Compile proto files from jeeves-airframe
COPY jeeves-airframe/jeeves_infra/gateway/proto/ ./proto/
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

# Cache-busting: pass git SHA or timestamp to force rebuild when code changes
# Usage: docker compose build --build-arg CODE_VERSION=$(git rev-parse --short HEAD)
ARG CODE_VERSION=dev
RUN echo "Code version: ${CODE_VERSION}" > /app/.code_version

# Copy Python infrastructure from jeeves-airframe submodule
# Dependency hierarchy: jeeves_infra.protocols → jeeves_infra → mission_system → capability
COPY --chown=1000:1000 jeeves-airframe/jeeves_infra/ ./jeeves_infra/
COPY --chown=1000:1000 jeeves-airframe/mission_system/ ./mission_system/

# Copy hello-world capability as Python package
# This enables: from jeeves_capability_hello_world import register_capability
COPY --chown=1000:1000 jeeves_capability_hello_world/ ./jeeves_capability_hello_world/

# Copy hello-world tests
COPY --chown=1000:1000 jeeves_capability_hello_world/tests/ ./hello_world_tests/
COPY --chown=1000:1000 tests/ ./tests/

# Copy Gradio application
COPY --chown=1000:1000 gradio_app.py ./

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

# Copy gateway-related code from jeeves-airframe submodule
COPY --chown=jeeves:jeeves jeeves-airframe/jeeves_infra/ ./jeeves_infra/
COPY --chown=jeeves:jeeves jeeves-airframe/mission_system/ ./mission_system/

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

CMD ["python", "-m", "uvicorn", "mission_system.app_server:app", "--host", "0.0.0.0", "--port", "8000"]

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

# Cache-busting: pass git SHA or timestamp to force rebuild when code changes
# Usage: docker compose build --build-arg CODE_VERSION=$(git rev-parse --short HEAD)
ARG CODE_VERSION=dev
RUN echo "Code version: ${CODE_VERSION}" > /app/.code_version

# Copy Python infrastructure from jeeves-airframe submodule
# Dependency hierarchy: jeeves_infra.protocols → jeeves_infra → mission_system → capability
COPY --chown=jeeves:jeeves jeeves-airframe/jeeves_infra/ ./jeeves_infra/
COPY --chown=jeeves:jeeves jeeves-airframe/mission_system/ ./mission_system/

# Copy hello-world capability as Python package
# This enables: from jeeves_capability_hello_world import register_capability
COPY --chown=jeeves:jeeves jeeves_capability_hello_world/ ./jeeves_capability_hello_world/

# Copy Gradio application for hello-world chatbot
COPY --chown=jeeves:jeeves gradio_app.py ./

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
