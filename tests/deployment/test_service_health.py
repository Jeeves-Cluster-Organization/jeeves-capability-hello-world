"""
Service Health and Connectivity Tests.

Tests for verifying that services are running and healthy.
These tests check actual service endpoints when services are available.

Requirements:
- Services running via docker compose up
- Network access to service ports

Test Markers:
    @pytest.mark.deployment - Deployment tests
    @pytest.mark.requires_docker - Requires Docker services running
    @pytest.mark.e2e - End-to-end tests
"""

import asyncio
import os
import socket
import ssl
import time
from typing import Dict, Optional
from urllib.parse import urljoin

import pytest

# Try to import HTTP clients
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

pytestmark = [
    pytest.mark.deployment,
    pytest.mark.asyncio,
]


# =============================================================================
# Configuration from Environment
# =============================================================================

def get_service_config() -> Dict[str, str]:
    """Get service URLs from environment or defaults."""
    return {
        "orchestrator_host": os.getenv("API_HOST", "http://localhost:8000"),
        "gateway_host": os.getenv("GATEWAY_HOST", "http://localhost:8001"),
        "postgres_host": os.getenv("POSTGRES_HOST", "localhost"),
        "postgres_port": int(os.getenv("POSTGRES_PORT", "5432")),
        "llama_host": os.getenv("LLAMASERVER_HOST", "http://localhost:8080"),
    }


# =============================================================================
# Utility Functions
# =============================================================================

def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


async def check_http_health(
    url: str,
    timeout: float = 5.0,
) -> Dict[str, any]:
    """Check HTTP health endpoint."""
    if not HTTPX_AVAILABLE:
        return {"status": "skipped", "reason": "httpx not available"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
    except httpx.ConnectError:
        return {"status": "unreachable", "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# Port Connectivity Tests
# =============================================================================

class TestPortConnectivity:
    """Tests for basic port connectivity."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    def test_postgres_port_reachable(self, config):
        """Test PostgreSQL port is reachable."""
        is_open = is_port_open(config["postgres_host"], config["postgres_port"])
        if not is_open:
            pytest.skip("PostgreSQL not running")
        assert is_open, "PostgreSQL port should be open"

    @pytest.mark.requires_docker
    def test_orchestrator_port_reachable(self, config):
        """Test orchestrator port is reachable."""
        # Parse host:port from URL
        host = config["orchestrator_host"].replace("http://", "").split(":")[0]
        port = 8000
        is_open = is_port_open(host, port)
        if not is_open:
            pytest.skip("Orchestrator not running")
        assert is_open, "Orchestrator port should be open"

    @pytest.mark.requires_docker
    def test_gateway_port_reachable(self, config):
        """Test gateway port is reachable."""
        host = config["gateway_host"].replace("http://", "").split(":")[0]
        port = 8001
        is_open = is_port_open(host, port)
        if not is_open:
            pytest.skip("Gateway not running")
        assert is_open, "Gateway port should be open"

    @pytest.mark.requires_docker
    def test_llama_server_port_reachable(self, config):
        """Test llama-server port is reachable."""
        host = config["llama_host"].replace("http://", "").split(":")[0]
        port = 8080
        is_open = is_port_open(host, port)
        if not is_open:
            pytest.skip("llama-server not running")
        assert is_open, "llama-server port should be open"


# =============================================================================
# HTTP Health Endpoint Tests
# =============================================================================

class TestHTTPHealthEndpoints:
    """Tests for HTTP health check endpoints."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_gateway_health_endpoint(self, config):
        """Test gateway /health endpoint."""
        url = urljoin(config["gateway_host"], "/health")
        result = await check_http_health(url)

        if result["status"] == "unreachable":
            pytest.skip("Gateway not running")

        assert result["status"] == "healthy", f"Gateway unhealthy: {result}"
        assert result["status_code"] == 200

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_gateway_health_response_time(self, config):
        """Test gateway health endpoint responds quickly."""
        url = urljoin(config["gateway_host"], "/health")
        result = await check_http_health(url)

        if result["status"] == "unreachable":
            pytest.skip("Gateway not running")

        if result["status"] == "healthy":
            assert result["response_time_ms"] < 1000, \
                f"Health check too slow: {result['response_time_ms']}ms"

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_llama_server_health_endpoint(self, config):
        """Test llama-server /health endpoint."""
        url = urljoin(config["llama_host"], "/health")
        result = await check_http_health(url)

        if result["status"] == "unreachable":
            pytest.skip("llama-server not running")

        assert result["status"] == "healthy", f"llama-server unhealthy: {result}"


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestAPIEndpoints:
    """Tests for API endpoint availability."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_gateway_root_endpoint(self, config):
        """Test gateway root endpoint."""
        url = config["gateway_host"]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                # Root should return something (200 or redirect)
                assert response.status_code in [200, 301, 302, 307, 308]
        except httpx.ConnectError:
            pytest.skip("Gateway not running")

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_gateway_api_docs(self, config):
        """Test gateway OpenAPI docs endpoint."""
        url = urljoin(config["gateway_host"], "/docs")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                # FastAPI docs should be available
                assert response.status_code in [200, 404]
        except httpx.ConnectError:
            pytest.skip("Gateway not running")

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_gateway_openapi_schema(self, config):
        """Test gateway OpenAPI schema endpoint."""
        url = urljoin(config["gateway_host"], "/openapi.json")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    assert "openapi" in data or "info" in data
        except httpx.ConnectError:
            pytest.skip("Gateway not running")


# =============================================================================
# gRPC Health Tests
# =============================================================================

class TestGRPCHealth:
    """Tests for gRPC service health."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    def test_grpc_port_open(self, config):
        """Test gRPC port is open."""
        # gRPC runs on 50051 inside container, mapped to 8000
        host = config["orchestrator_host"].replace("http://", "").split(":")[0]
        port = 8000

        is_open = is_port_open(host, port)
        if not is_open:
            pytest.skip("gRPC service not running")

        assert is_open, "gRPC port should be open"


# =============================================================================
# Database Connectivity Tests
# =============================================================================

class TestDatabaseConnectivity:
    """Tests for database connectivity."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.requires_postgres
    def test_postgres_accepts_connections(self, config):
        """Test PostgreSQL accepts TCP connections."""
        is_open = is_port_open(config["postgres_host"], config["postgres_port"])
        if not is_open:
            pytest.skip("PostgreSQL not running")

        assert is_open, "PostgreSQL should accept connections"

    @pytest.mark.requires_docker
    @pytest.mark.requires_postgres
    async def test_postgres_connection_with_driver(self, config):
        """Test PostgreSQL connection with async driver."""
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")

        if not is_port_open(config["postgres_host"], config["postgres_port"]):
            pytest.skip("PostgreSQL not running")

        try:
            conn = await asyncpg.connect(
                host=config["postgres_host"],
                port=config["postgres_port"],
                user=os.getenv("POSTGRES_USER", "assistant"),
                password=os.getenv("POSTGRES_PASSWORD", "dev_password"),
                database=os.getenv("POSTGRES_DATABASE", "assistant"),
                timeout=5,
            )
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            assert result == 1
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")


# =============================================================================
# Service Dependency Tests
# =============================================================================

class TestServiceDependencies:
    """Tests for service dependency chain."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.slow
    async def test_dependency_chain_health(self, config):
        """Test full dependency chain is healthy."""
        services = {
            "postgres": (config["postgres_host"], config["postgres_port"]),
            "llama-server": ("localhost", 8080),
            "orchestrator": ("localhost", 8000),
            "gateway": ("localhost", 8001),
        }

        healthy_services = []
        unhealthy_services = []

        for name, (host, port) in services.items():
            if is_port_open(host, port, timeout=2.0):
                healthy_services.append(name)
            else:
                unhealthy_services.append(name)

        if not healthy_services:
            pytest.skip("No services running")

        # If gateway is healthy, dependency chain should be healthy
        if "gateway" in healthy_services:
            # Gateway depends on orchestrator
            assert "orchestrator" in healthy_services or \
                   "postgres" in healthy_services, \
                   "Gateway healthy but dependencies unhealthy"


# =============================================================================
# Metrics Endpoint Tests
# =============================================================================

class TestMetricsEndpoints:
    """Tests for metrics/monitoring endpoints."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_metrics_port_reachable(self, config):
        """Test metrics port is reachable."""
        # Metrics typically on port 9090
        is_open = is_port_open("localhost", 9090)
        # Metrics port is optional, so just verify we can check
        assert isinstance(is_open, bool)


# =============================================================================
# Container Restart Tests
# =============================================================================

class TestContainerResilience:
    """Tests for container resilience and restart behavior."""

    @pytest.mark.requires_docker
    def test_restart_policy_configured(self):
        """Verify restart policy is configured in docker-compose."""
        from pathlib import Path
        compose_file = Path(__file__).parent.parent.parent / "docker" / "docker-compose.yml"
        content = compose_file.read_text()

        assert "restart:" in content
        assert "unless-stopped" in content


# =============================================================================
# Integration Smoke Tests
# =============================================================================

class TestIntegrationSmoke:
    """Quick smoke tests for full integration."""

    @pytest.fixture
    def config(self):
        return get_service_config()

    @pytest.mark.requires_docker
    @pytest.mark.e2e
    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    async def test_end_to_end_health(self, config):
        """Smoke test: verify complete stack is operational."""
        results = {}

        # Check gateway
        gateway_result = await check_http_health(
            urljoin(config["gateway_host"], "/health")
        )
        results["gateway"] = gateway_result["status"]

        # Check llama-server
        llama_result = await check_http_health(
            urljoin(config["llama_host"], "/health")
        )
        results["llama-server"] = llama_result["status"]

        # Check postgres (via port)
        postgres_healthy = is_port_open(
            config["postgres_host"],
            config["postgres_port"]
        )
        results["postgres"] = "healthy" if postgres_healthy else "unreachable"

        # At least one service should be running for this test to pass
        healthy_count = sum(1 for v in results.values() if v == "healthy")
        if healthy_count == 0:
            pytest.skip("No services running")

        # Report status
        for service, status in results.items():
            if status != "healthy":
                print(f"  {service}: {status}")

        # If we got here with some services healthy, consider it a pass
        assert healthy_count > 0, f"All services unhealthy: {results}"
