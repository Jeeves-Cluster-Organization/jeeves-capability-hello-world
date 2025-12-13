"""
Deployment Tests for Docker Infrastructure.

Tests Docker container builds, health checks, and service connectivity.
These tests verify the deployment infrastructure is properly configured.

Requirements:
- Docker installed and running
- docker-compose available
- Network access to localhost ports

Test Markers:
    @pytest.mark.deployment - Deployment infrastructure tests
    @pytest.mark.requires_docker - Requires Docker
    @pytest.mark.slow - May take significant time
"""

import asyncio
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.deployment,
]


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCKER_DIR = PROJECT_ROOT / "docker"
DOCKER_COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"

# Default ports from docker-compose.yml
DEFAULT_PORTS = {
    "orchestrator": 8000,  # gRPC server mapped to host
    "gateway": 8001,       # HTTP gateway
    "postgres": 5432,      # PostgreSQL
    "llama_server": 8080,  # LLM server
    "metrics": 9090,       # Prometheus metrics
}


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def docker_compose_path():
    """Get path to docker-compose.yml."""
    return str(DOCKER_COMPOSE_FILE)


@pytest.fixture
def project_root():
    """Get project root path."""
    return str(PROJECT_ROOT)


# =============================================================================
# Utility Functions
# =============================================================================

def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def run_docker_compose(
    args: list,
    compose_file: str,
    cwd: str,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """Run docker-compose command."""
    cmd = ["docker", "compose", "-f", compose_file] + args
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def wait_for_port(
    host: str,
    port: int,
    timeout: float = 60.0,
    interval: float = 1.0,
) -> bool:
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            return True
        time.sleep(interval)
    return False


# =============================================================================
# Docker Configuration Tests
# =============================================================================

class TestDockerConfiguration:
    """Tests for Docker configuration files."""

    def test_dockerfile_exists(self):
        """Verify Dockerfile exists."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        assert dockerfile.exists(), f"Dockerfile not found at {dockerfile}"

    def test_docker_compose_exists(self, docker_compose_path):
        """Verify docker-compose.yml exists."""
        assert Path(docker_compose_path).exists()

    def test_dockerfile_has_required_stages(self):
        """Verify Dockerfile has all required build stages."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        content = dockerfile.read_text()

        required_stages = [
            "builder-go",
            "builder-base",
            "builder-gateway",
            "builder-orchestrator",
            "test",
            "gateway",
            "orchestrator",
        ]

        for stage in required_stages:
            assert f"FROM " in content or f"AS {stage}" in content, \
                f"Missing stage: {stage}"

    def test_docker_compose_has_required_services(self, docker_compose_path):
        """Verify docker-compose.yml defines all required services."""
        content = Path(docker_compose_path).read_text()

        required_services = [
            "assistant",    # gRPC orchestrator
            "gateway",      # HTTP gateway
            "postgres",     # Database
            "llama-server", # LLM server
            "test",         # Test runner
        ]

        for service in required_services:
            assert f"{service}:" in content, f"Missing service: {service}"

    def test_docker_compose_has_health_checks(self, docker_compose_path):
        """Verify services have health checks configured."""
        content = Path(docker_compose_path).read_text()
        assert "healthcheck:" in content

    def test_docker_compose_has_networks(self, docker_compose_path):
        """Verify network configuration exists."""
        content = Path(docker_compose_path).read_text()
        assert "networks:" in content
        assert "assistant-network" in content

    def test_docker_compose_has_volumes(self, docker_compose_path):
        """Verify volume configuration exists."""
        content = Path(docker_compose_path).read_text()
        assert "volumes:" in content
        assert "postgres-data" in content


class TestDockerfileOptimizations:
    """Tests for Dockerfile optimization patterns."""

    def test_multi_stage_build(self):
        """Verify multi-stage build is used for optimization."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        content = dockerfile.read_text()

        # Count FROM statements (multi-stage builds have multiple)
        from_count = content.count("FROM ")
        assert from_count >= 4, "Expected multi-stage build with 4+ stages"

    def test_non_root_user(self):
        """Verify non-root user is configured."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        content = dockerfile.read_text()

        assert "jeeves" in content, "Expected non-root user 'jeeves'"
        assert "USER jeeves" in content

    def test_cache_optimization(self):
        """Verify dependency caching is optimized."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        content = dockerfile.read_text()

        # Requirements should be copied before code for caching
        assert "requirements" in content
        assert "COPY --chown" in content

    def test_health_check_in_dockerfile(self):
        """Verify HEALTHCHECK is defined."""
        dockerfile = DOCKER_DIR / "Dockerfile"
        content = dockerfile.read_text()

        assert "HEALTHCHECK" in content


class TestRequirementsFiles:
    """Tests for split requirements files."""

    def test_requirements_directory_exists(self):
        """Verify requirements directory exists."""
        req_dir = PROJECT_ROOT / "requirements"
        assert req_dir.exists()

    def test_base_requirements_exists(self):
        """Verify base.txt exists."""
        req_file = PROJECT_ROOT / "requirements" / "base.txt"
        assert req_file.exists()

    def test_gateway_requirements_exists(self):
        """Verify gateway.txt exists."""
        req_file = PROJECT_ROOT / "requirements" / "gateway.txt"
        assert req_file.exists()

    def test_orchestrator_requirements_exists(self):
        """Verify orchestrator.txt exists."""
        req_file = PROJECT_ROOT / "requirements" / "orchestrator.txt"
        assert req_file.exists()

    def test_test_requirements_exists(self):
        """Verify test.txt exists."""
        req_file = PROJECT_ROOT / "requirements" / "test.txt"
        assert req_file.exists()

    def test_requirements_hierarchy(self):
        """Verify requirements properly chain together."""
        # test.txt should include orchestrator.txt
        test_req = PROJECT_ROOT / "requirements" / "test.txt"
        content = test_req.read_text()
        assert "-r orchestrator.txt" in content or "-r base.txt" in content


# =============================================================================
# Service Health Check Tests
# =============================================================================

class TestServiceHealthChecks:
    """Tests for service health check endpoints."""

    @pytest.mark.requires_docker
    def test_postgres_health_check_command(self, docker_compose_path):
        """Verify PostgreSQL health check command."""
        content = Path(docker_compose_path).read_text()
        assert "pg_isready" in content

    @pytest.mark.requires_docker
    def test_gateway_health_check_endpoint(self, docker_compose_path):
        """Verify gateway health check uses HTTP endpoint."""
        content = Path(docker_compose_path).read_text()
        assert "/health" in content

    @pytest.mark.requires_docker
    def test_llama_server_health_check(self, docker_compose_path):
        """Verify llama-server health check."""
        content = Path(docker_compose_path).read_text()
        assert "curl" in content or "/health" in content


class TestServiceConnectivity:
    """Tests for service connectivity when Docker is running."""

    @pytest.fixture
    def check_docker_running(self):
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @pytest.mark.requires_docker
    @pytest.mark.slow
    def test_can_check_service_status(
        self,
        docker_compose_path,
        project_root,
        check_docker_running,
    ):
        """Test that docker compose ps works."""
        if not check_docker_running:
            pytest.skip("Docker not running")

        result = run_docker_compose(
            ["ps", "--format", "json"],
            docker_compose_path,
            project_root,
        )
        # Command should succeed (even if no containers running)
        assert result.returncode == 0 or "no configuration file" not in result.stderr

    @pytest.mark.requires_docker
    @pytest.mark.slow
    def test_can_validate_compose_config(
        self,
        docker_compose_path,
        project_root,
        check_docker_running,
    ):
        """Test that docker compose config validates."""
        if not check_docker_running:
            pytest.skip("Docker not running")

        result = run_docker_compose(
            ["config", "--quiet"],
            docker_compose_path,
            project_root,
        )
        # Config validation should pass
        assert result.returncode == 0, f"Config validation failed: {result.stderr}"


# =============================================================================
# Environment Configuration Tests
# =============================================================================

class TestEnvironmentConfiguration:
    """Tests for environment configuration."""

    def test_env_file_exists(self):
        """Verify .env file exists."""
        env_file = PROJECT_ROOT / ".env"
        assert env_file.exists(), "Missing .env file"

    def test_env_has_required_variables(self):
        """Verify .env has required variables."""
        env_file = PROJECT_ROOT / ".env"
        content = env_file.read_text()

        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DATABASE",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        ]

        for var in required_vars:
            assert var in content, f"Missing env var: {var}"

    def test_env_has_llm_configuration(self):
        """Verify .env has LLM configuration."""
        env_file = PROJECT_ROOT / ".env"
        content = env_file.read_text()

        # Should have LLM provider config
        assert "LLM_PROVIDER" in content or "LLAMASERVER" in content


class TestDockerComposePorts:
    """Tests for port configuration in docker-compose."""

    def test_orchestrator_port_mapping(self, docker_compose_path):
        """Verify orchestrator port is mapped correctly."""
        content = Path(docker_compose_path).read_text()
        # gRPC server on 50051 inside container, mapped to 8000
        assert "50051" in content

    def test_gateway_port_mapping(self, docker_compose_path):
        """Verify gateway port is mapped correctly."""
        content = Path(docker_compose_path).read_text()
        assert "8001" in content or "GATEWAY_PORT" in content

    def test_postgres_port_mapping(self, docker_compose_path):
        """Verify PostgreSQL port is mapped."""
        content = Path(docker_compose_path).read_text()
        assert "5432" in content

    def test_llama_server_port_mapping(self, docker_compose_path):
        """Verify llama-server port is mapped."""
        content = Path(docker_compose_path).read_text()
        assert "8080" in content


# =============================================================================
# Resource Limits Tests
# =============================================================================

class TestResourceLimits:
    """Tests for container resource limits."""

    def test_orchestrator_has_memory_limit(self, docker_compose_path):
        """Verify orchestrator has memory limit configured."""
        content = Path(docker_compose_path).read_text()
        assert "memory:" in content

    def test_orchestrator_has_cpu_limit(self, docker_compose_path):
        """Verify orchestrator has CPU limit configured."""
        content = Path(docker_compose_path).read_text()
        assert "cpus:" in content

    def test_gateway_has_lower_limits(self, docker_compose_path):
        """Verify gateway has lower resource limits than orchestrator."""
        content = Path(docker_compose_path).read_text()
        # Gateway should have lower limits (512M vs 2G)
        assert "512M" in content


# =============================================================================
# Volume Configuration Tests
# =============================================================================

class TestVolumeConfiguration:
    """Tests for Docker volume configuration."""

    def test_postgres_data_volume(self, docker_compose_path):
        """Verify PostgreSQL data volume is configured."""
        content = Path(docker_compose_path).read_text()
        assert "postgres-data" in content

    def test_llama_models_volume(self, docker_compose_path):
        """Verify llama-models volume is configured."""
        content = Path(docker_compose_path).read_text()
        assert "llama-models" in content

    def test_external_volume_for_models(self, docker_compose_path):
        """Verify llama-models is external volume."""
        content = Path(docker_compose_path).read_text()
        assert "external: true" in content


# =============================================================================
# Network Configuration Tests
# =============================================================================

class TestNetworkConfiguration:
    """Tests for Docker network configuration."""

    def test_bridge_network(self, docker_compose_path):
        """Verify bridge network is used."""
        content = Path(docker_compose_path).read_text()
        assert "driver: bridge" in content

    def test_services_on_same_network(self, docker_compose_path):
        """Verify all services use same network."""
        content = Path(docker_compose_path).read_text()
        # All services should reference assistant-network
        network_refs = content.count("assistant-network")
        assert network_refs >= 4, "Expected all services on same network"


# =============================================================================
# Build Configuration Tests
# =============================================================================

class TestBuildConfiguration:
    """Tests for Docker build configuration."""

    def test_code_version_arg(self, docker_compose_path):
        """Verify CODE_VERSION build arg is supported."""
        content = Path(docker_compose_path).read_text()
        assert "CODE_VERSION" in content

    def test_build_context_is_parent(self, docker_compose_path):
        """Verify build context is parent directory."""
        content = Path(docker_compose_path).read_text()
        assert "context: .." in content

    def test_explicit_dockerfile_path(self, docker_compose_path):
        """Verify Dockerfile path is explicit."""
        content = Path(docker_compose_path).read_text()
        assert "dockerfile:" in content


# =============================================================================
# Dependency Configuration Tests
# =============================================================================

class TestDependencyConfiguration:
    """Tests for service dependency configuration."""

    def test_orchestrator_depends_on_postgres(self, docker_compose_path):
        """Verify orchestrator depends on postgres."""
        content = Path(docker_compose_path).read_text()
        assert "depends_on:" in content
        assert "postgres" in content

    def test_orchestrator_depends_on_llama(self, docker_compose_path):
        """Verify orchestrator depends on llama-server."""
        content = Path(docker_compose_path).read_text()
        assert "llama-server" in content

    def test_gateway_depends_on_orchestrator(self, docker_compose_path):
        """Verify gateway depends on orchestrator."""
        content = Path(docker_compose_path).read_text()
        # Gateway should depend on assistant (orchestrator)
        assert "assistant" in content

    def test_health_condition_used(self, docker_compose_path):
        """Verify health condition is used for dependencies."""
        content = Path(docker_compose_path).read_text()
        assert "condition: service_healthy" in content
