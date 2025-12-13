"""
Code Analysis Capability - Main Entry Point.

This is the capability's own server that builds on the Mission System framework.

See docs/JEEVES_CORE_RUNTIME_CONTRACT.md for the authoritative runtime contract.

**Constitutional Layering:**
```
Code Analysis Capability (this file)  ← TOP (application)
    ↓ imports FROM
Mission System API                     ← Framework
    ↓ imports FROM
Avionics (infrastructure)              ← Implementation
    ↓ imports FROM
Core Engine (contracts)                ← BOTTOM (pure)
```

This capability:
- Imports mission system framework API
- Creates its own service using the framework
- Starts its own gRPC server
- Mission system NEVER imports this file

**Bootstrap Order (per Runtime Contract):**
1. Register capability resources FIRST (register_capability())
2. Import runtime services AFTER registration
3. Start application server

**Constitution R7 Compliance:**
- register_capability() is called at module import time
- This ensures resources are registered BEFORE infrastructure initialization
"""

from __future__ import annotations

# Constitution R7: Register capability resources BEFORE any infrastructure imports
# This must happen at module level to ensure registration before lifespan() queries registry
from jeeves_capability_code_analyser import register_capability
register_capability()

import asyncio
import os
import signal
from typing import Optional

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol


class CodeAnalysisServer:
    """
    gRPC server for Code Analysis Capability.

    This is the capability's main entry point. It builds on the mission
    system framework to create and serve the code analysis pipeline.
    """

    def __init__(self, port: int = 50051, logger: Optional[LoggerProtocol] = None):
        self._logger = logger or get_logger()
        self.port = port
        self.server: Optional[grpc.aio.Server] = None
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self.db = None
        self.tool_registry = None
        self.code_analysis_service = None
        self.code_indexer = None
        self.tool_health_service = None
        self.graph_repository = None

    async def start(self) -> None:
        """Initialize components and start gRPC server."""
        self._logger.info("code_analysis_capability_startup", port=self.port)

        # Import from mission system framework (capability → mission system)
        from jeeves_mission_system.api import create_mission_runtime
        from jeeves_mission_system.adapters import get_settings, create_database_client

        # Import capability's own components
        from tools import initialize_all_tools
        from orchestration.wiring import create_code_analysis_service
        from orchestration.servicer import CodeAnalysisServicer

        settings = get_settings()

        # Initialize database
        self._logger.info("initializing_database")
        self.db = await create_database_client(settings)

        # Verify schema
        try:
            await self.db.fetch_one("SELECT 1 FROM sessions LIMIT 1")
            self._logger.info("schema_verification_passed")
        except Exception as e:
            self._logger.error("schema_verification_failed", error=str(e))
            raise RuntimeError(f"Database schema not initialized: {e}")

        # Initialize L2 EventEmitter for domain events (via adapters)
        from jeeves_mission_system.adapters import (
            create_event_emitter,
            create_graph_repository,
            create_code_indexer,
            create_tool_health_service,
        )
        event_emitter = create_event_emitter(self.db)
        self._logger.info("event_emitter_initialized", l2_enabled=event_emitter.enabled)

        # Initialize L5 GraphRepository for dependency edges (via adapters)
        self.graph_repository = create_graph_repository(self.db)
        await self.graph_repository.ensure_table()
        self._logger.info("graph_repository_initialized")

        # Initialize RAG-based code indexer (via adapters)
        from tools.semantic_tools import set_code_indexer
        self.code_indexer = create_code_indexer(self.db)
        set_code_indexer(self.code_indexer)
        self._logger.info("code_indexer_initialized", semantic_search_enabled=True)

        # Auto-index repository if configured
        repo_path = os.getenv("REPO_PATH")
        auto_index = os.getenv("AUTO_INDEX_ON_STARTUP", "").lower() in ("true", "1", "yes")
        if repo_path and auto_index:
            self._logger.info("auto_indexing_repository", repo_path=repo_path)
            try:
                stats = await self.code_indexer.index_repository(repo_path)
                self._logger.info("auto_indexing_completed", **stats)
            except Exception as e:
                self._logger.warning("auto_indexing_failed", error=str(e))

        # Initialize tools
        self._logger.info("initializing_tools")
        tool_instances = initialize_all_tools(db=self.db)
        self.tool_registry = tool_instances["registry"]

        # Initialize memory services (via adapters)
        self.tool_health_service = create_tool_health_service(self.db)
        await self.tool_health_service.ensure_initialized()

        # Register tool names with health service
        if self.tool_registry and hasattr(self.tool_registry, 'tools'):
            tool_names = list(self.tool_registry.tools.keys())
            self.tool_health_service.set_registered_tools(tool_names)
            self._logger.info("tools_registered_with_health", tool_count=len(tool_names))

        # Build database URL for checkpointing
        database_url = (
            f"postgresql://{os.getenv('POSTGRES_USER', 'assistant')}:"
            f"{os.getenv('POSTGRES_PASSWORD', '')}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DATABASE', 'assistant')}"
        )

        # Create mission runtime (capability imports FROM mission system)
        self._logger.info("creating_mission_runtime")
        use_mock = os.getenv("MOCK_LLM_ENABLED", "").lower() in ("true", "1", "yes")
        runtime = create_mission_runtime(
            tool_registry=self.tool_registry,
            persistence=self.db,
            settings=settings,
            use_mock=use_mock,
        )

        # Create code analysis service using capability's own wiring
        self._logger.info("creating_code_analysis_service")
        self.code_analysis_service = create_code_analysis_service(
            runtime=runtime,
            database_url=database_url,
        )

        # Create gRPC server
        self.server = grpc.aio.server(
            options=[
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 60000),
                ("grpc.keepalive_timeout_ms", 20000),
                ("grpc.keepalive_permit_without_calls", True),
                ("grpc.http2.min_ping_interval_without_data_ms", 30000),
                ("grpc.http2.max_pings_without_data", 2),
            ]
        )

        # Register services
        await self._register_services()

        # Add health service
        health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self.server)
        health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        health_servicer.set("jeeves.v1.JeevesFlowService", health_pb2.HealthCheckResponse.SERVING)
        health_servicer.set("jeeves.v1.GovernanceService", health_pb2.HealthCheckResponse.SERVING)

        # Start server
        listen_addr = f"[::]:{self.port}"
        self.server.add_insecure_port(listen_addr)
        await self.server.start()

        self._logger.info(
            "code_analysis_capability_ready",
            listen_addr=listen_addr,
            tools_registered=len(self.tool_registry.tools),
            status="SERVING",
        )

    async def _register_services(self) -> None:
        """Register gRPC service implementations."""
        try:
            from proto import jeeves_pb2_grpc
        except ImportError:
            self._logger.error(
                "grpc_stubs_not_found",
                hint="Run: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/jeeves.proto"
            )
            raise RuntimeError("gRPC stubs not generated")

        from jeeves_mission_system.orchestrator.flow_service import JeevesFlowServicer
        from jeeves_mission_system.orchestrator.governance_service import GovernanceServicer
        from orchestration.servicer import CodeAnalysisServicer

        # Create code analysis servicer (capability-specific adapter)
        code_analysis_servicer = CodeAnalysisServicer(
            code_analysis_service=self.code_analysis_service,
            db=self.db,
        )

        # Register services
        jeeves_pb2_grpc.add_JeevesFlowServiceServicer_to_server(
            JeevesFlowServicer(
                db=self.db,
                code_analysis_servicer=code_analysis_servicer,
            ),
            self.server
        )
        jeeves_pb2_grpc.add_GovernanceServiceServicer_to_server(
            GovernanceServicer(self.tool_health_service, db=self.db),
            self.server
        )

        self._logger.info("grpc_services_registered", services=[
            "JeevesFlowService",
            "GovernanceService",
        ])

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._logger.info("code_analysis_capability_shutdown")

        if self.server:
            await self.server.stop(5)

        if self.db:
            await self.db.close()

        self._logger.info("code_analysis_capability_stopped")

    async def serve(self) -> None:
        """Run server until shutdown signal."""
        await self.start()

        loop = asyncio.get_running_loop()

        def signal_handler():
            self._logger.info("shutdown_signal_received")
            self._shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        await self._shutdown_event.wait()
        await self.stop()


async def main():
    """Entry point for Code Analysis Capability."""
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = CodeAnalysisServer(port=port)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
