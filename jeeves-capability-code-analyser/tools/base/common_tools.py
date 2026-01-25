"""Common utility tools for debugging and system operations.

Tool Result Contract (jeeves-core v1.2+):
    {
        "status": "success" | "error" | "not_found" | "partial",
        "data": {...},
        "error": "...",
        "error_type": "...",
        "citations": [...],
        "execution_time_ms": 123
    }
"""

from typing import Dict, Any, Optional

from protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
# Constitutional imports - from mission_system contracts layer
from mission_system.contracts import PersistenceProtocol
from tools.registry import tool_registry, RiskLevel


class CommonTools:
    """Common utility tools."""

    def __init__(self, db: PersistenceProtocol, logger: Optional[LoggerProtocol] = None):
        self.db = db
        self._logger = logger or get_logger()

    async def echo(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Echo back the input (for testing and debugging).

        Args:
            **kwargs: Any parameters

        Returns:
            Tool result dict with the echoed payload
        """
        self._logger.info("echo", payload=kwargs)

        return {
            "status": "success",
            "data": {"payload": kwargs},
        }

    async def health_check(
        self
    ) -> Dict[str, Any]:
        """
        Perform a health check (database connectivity, etc.).

        Returns:
            Tool result dict with health status
        """
        try:
            # Check database connectivity
            result = await self.db.fetch_one("SELECT 1 as test")

            if result and result.get("test") == 1:
                db_status = "healthy"
            else:
                db_status = "unhealthy"

        except Exception as e:
            db_status = "error"
            self._logger.error("health_check_db_failed", error=str(e))

        self._logger.info("health_check", db_status=db_status)

        return {
            "status": "success",
            "data": {"database": db_status},
        }

    async def get_system_info(
        self
    ) -> Dict[str, Any]:
        """
        Get system information (tables, counts, etc.).

        Returns:
            Tool result dict with system stats
        """
        try:
            # Get table counts
            tasks_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM tasks")
            kv_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM kv_store")
            journal_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM journal_entries")
            requests_count = await self.db.fetch_one("SELECT COUNT(*) as count FROM requests")

            self._logger.info("system_info_retrieved")

            return {
                "status": "success",
                "data": {
                    "tables": {
                        "tasks": tasks_count.get("count", 0) if tasks_count else 0,
                        "kv_store": kv_count.get("count", 0) if kv_count else 0,
                        "journal_entries": journal_count.get("count", 0) if journal_count else 0,
                        "requests": requests_count.get("count", 0) if requests_count else 0
                    }
                },
            }

        except Exception as e:
            self._logger.error("system_info_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }


# Register tools with the registry
def register_common_tools(db: PersistenceProtocol, registry=None):
    """Register all common tools with the specified or global tool registry."""
    target_registry = registry if registry is not None else tool_registry
    tools = CommonTools(db)

    @target_registry.register(
        name="echo",
        description="Echo back the input (for testing and debugging)",
        parameters={
            "**kwargs": "Any parameters (all will be echoed back)"
        },
        risk_level=RiskLevel.READ_ONLY
    )
    async def echo(**kwargs):
        return await tools.echo(**kwargs)

    @target_registry.register(
        name="health_check",
        description="Perform a health check on the system",
        parameters={},
        risk_level=RiskLevel.READ_ONLY
    )
    async def health_check(**kwargs):
        return await tools.health_check()

    @target_registry.register(
        name="system_info",
        description="Get system information (table counts, stats)",
        parameters={},
        risk_level=RiskLevel.READ_ONLY
    )
    async def system_info(**kwargs):
        return await tools.get_system_info()

    return tools
