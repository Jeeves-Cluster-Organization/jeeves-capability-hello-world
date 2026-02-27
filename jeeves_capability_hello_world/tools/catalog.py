"""
Tool Catalog for Onboarding Capability.

Constitution R7 compliant tool catalog with metadata.
Provides typed tool identifiers, categories, and risk classification.

Architecture:
    Tools are registered with the catalog at initialization time.
    The catalog provides metadata for tool access control and routing.
"""

from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, Optional


class ToolId(str, Enum):
    """Typed tool identifiers for Onboarding capability."""

    GET_TIME = "get_time"
    LIST_TOOLS = "list_tools"


class ToolCategory(str, Enum):
    """Tool categories for routing and access control."""

    UTILITY = "utility"  # General utilities
    INTROSPECTION = "introspection"  # Self-inspection


class RiskSemantic(str, Enum):
    """Risk semantic for tool execution behavior."""

    READ_ONLY = "read_only"  # Safe, no side effects
    WRITE = "write"  # Modifies state
    DESTRUCTIVE = "destructive"  # Irreversible changes


class RiskSeverity(str, Enum):
    """Risk severity for tool execution impact."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Exposed tools available to agents
EXPOSED_TOOL_IDS: FrozenSet[str] = frozenset([
    ToolId.GET_TIME.value,
    ToolId.LIST_TOOLS.value,
])


class CapabilityToolCatalog:
    """
    Tool catalog for Onboarding capability.

    Maintains registry of tools with metadata including:
    - Function reference
    - Description
    - Category
    - Risk semantic and severity
    - Parameters schema
    - Async flag

    Example:
        catalog = CapabilityToolCatalog()
        catalog.register(
            tool_id=ToolId.GET_TIME.value,
            func=get_time,
            description="Get current time",
            category=ToolCategory.UTILITY.value,
            risk_semantic=RiskSemantic.READ_ONLY.value,
            risk_severity=RiskSeverity.LOW.value,
        )
    """

    def __init__(
        self,
        capability_id: str = "hello_world",
        description: str = "Hello World capability tools",
    ):
        self.capability_id = capability_id
        self.description = description
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        *,
        tool_id: str,
        func: Callable,
        description: str,
        category: str,
        risk_semantic: str,
        risk_severity: str,
        parameters: Optional[Dict[str, Any]] = None,
        is_async: bool = False,
    ) -> None:
        """
        Register a tool with the catalog.

        Args:
            tool_id: Unique tool identifier
            func: Tool function reference
            description: Human-readable description
            category: Tool category (from ToolCategory)
            risk_semantic: Risk semantic (from RiskSemantic)
            risk_severity: Risk severity (from RiskSeverity)
            parameters: Optional parameters schema
            is_async: Whether the tool is async
        """
        self._tools[tool_id] = {
            "id": tool_id,
            "func": func,
            "description": description,
            "category": category,
            "risk_semantic": risk_semantic,
            "risk_severity": risk_severity,
            "parameters": parameters or {},
            "is_async": is_async,
        }

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool by ID."""
        return self._tools.get(tool_id)

    def has_tool(self, tool_id: str) -> bool:
        """Check if tool exists."""
        return tool_id in self._tools

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        return self._tools.copy()

    def get_tools_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get tools by category."""
        return {
            tid: info
            for tid, info in self._tools.items()
            if info["category"] == category
        }

    def get_exposed_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get only exposed tools (available to agents)."""
        return {
            tid: info
            for tid, info in self._tools.items()
            if tid in EXPOSED_TOOL_IDS
        }

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)


# Global tool catalog instance for this capability
tool_catalog = CapabilityToolCatalog(
    capability_id="hello_world",
    description="Onboarding capability tools for Jeeves ecosystem explanation",
)


__all__ = [
    "ToolId",
    "ToolCategory",
    "RiskSemantic",
    "RiskSeverity",
    "EXPOSED_TOOL_IDS",
    "CapabilityToolCatalog",
    "tool_catalog",
]
