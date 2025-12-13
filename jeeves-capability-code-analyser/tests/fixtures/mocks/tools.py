"""Mock tool registry and executor for testing.

Provides mock implementations of the tool system without
requiring real file system access or external services.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from jeeves_protocols import RiskLevel


@dataclass
class MockToolDefinition:
    """Mock tool definition for testing."""
    name: str
    description: str
    parameters: Dict[str, str]
    risk_level: RiskLevel = RiskLevel.LOW
    handler: Optional[Callable] = None

    @property
    def is_read_only(self) -> bool:
        return self.risk_level == RiskLevel.LOW

    @property
    def is_destructive(self) -> bool:
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "risk_level": self.risk_level.value,
        }


class MockToolRegistry:
    """Mock tool registry for testing.

    Pre-registers common code analysis tools with mock responses.
    """

    def __init__(self):
        self._tools: Dict[str, MockToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default code analysis tools."""
        self._tools["read_file"] = MockToolDefinition(
            name="read_file",
            description="Read a file with line numbers",
            parameters={"path": "string", "start_line": "int", "end_line": "int"},
            risk_level=RiskLevel.LOW,
        )
        self._tools["glob_files"] = MockToolDefinition(
            name="glob_files",
            description="Find files matching a pattern",
            parameters={"pattern": "string", "max_results": "int"},
            risk_level=RiskLevel.LOW,
        )
        self._tools["grep_search"] = MockToolDefinition(
            name="grep_search",
            description="Search file contents",
            parameters={"pattern": "string", "path": "string"},
            risk_level=RiskLevel.LOW,
        )
        self._tools["tree_structure"] = MockToolDefinition(
            name="tree_structure",
            description="Get directory tree structure",
            parameters={"path": "string", "depth": "int"},
            risk_level=RiskLevel.LOW,
        )
        self._tools["find_symbol"] = MockToolDefinition(
            name="find_symbol",
            description="Find symbol definitions",
            parameters={"name": "string", "kind": "string"},
            risk_level=RiskLevel.LOW,
        )
        self._tools["locate"] = MockToolDefinition(
            name="locate",
            description="Locate code elements",
            parameters={"query": "string", "scope": "string"},
            risk_level=RiskLevel.LOW,
        )

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, str],
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> Callable:
        """Decorator to register a tool."""
        def decorator(func: Callable) -> Callable:
            self._tools[name] = MockToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                risk_level=risk_level,
                handler=func,
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[MockToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists."""
        return name in self._tools

    def list_tools(self, risk_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered tools."""
        tools = []
        for tool in self._tools.values():
            if risk_filter is None or tool.risk_level.value == risk_filter:
                tools.append(tool.to_dict())
        return tools

    def get_read_only_tools(self) -> List[str]:
        """Get names of read-only tools."""
        return [
            name for name, tool in self._tools.items()
            if tool.is_read_only
        ]

    def get_destructive_tools(self) -> List[str]:
        """Get names of destructive tools."""
        return [
            name for name, tool in self._tools.items()
            if tool.is_destructive
        ]

    def is_destructive_tool(self, name: str) -> bool:
        """Check if a tool is destructive."""
        tool = self._tools.get(name)
        return tool.is_destructive if tool else False


class MockToolExecutor:
    """Mock tool executor for testing.

    Returns configurable mock results for tool executions.
    """

    def __init__(self, responses: Optional[Dict[str, Dict[str, Any]]] = None):
        """Initialize executor with optional custom responses."""
        self.responses = responses or {}
        self.executions: List[Dict[str, Any]] = []
        self._default_responses = self._get_default_responses()

    def _get_default_responses(self) -> Dict[str, Dict[str, Any]]:
        """Get default responses for common tools."""
        return {
            "read_file": {
                "status": "success",
                "content": "# Mock file content\nclass Agent:\n    pass",
                "path": "mock/file.py",
                "total_lines": 3,
            },
            "glob_files": {
                "status": "success",
                "files": ["agents/base.py", "agents/perception.py"],
                "count": 2,
            },
            "grep_search": {
                "status": "success",
                "matches": [
                    {"file": "agents/base.py", "line": 10, "content": "class Agent:"}
                ],
                "count": 1,
            },
            "tree_structure": {
                "status": "success",
                "tree": "agents/\n  base.py\n  perception.py",
                "dir_count": 1,
                "file_count": 2,
            },
            "find_symbol": {
                "status": "success",
                "symbols": [
                    {"name": "Agent", "file": "agents/base.py", "line": 10, "kind": "class"}
                ],
            },
            "locate": {
                "status": "success",
                "matches": [
                    {"file": "agents/base.py", "line": 10, "content": "class Agent:"}
                ],
                "attempts": [("find_symbol", {"found": True})],
            },
        }

    async def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return mock result."""
        self.executions.append({"name": name, "params": params})

        # Check custom responses
        if name in self.responses:
            return self.responses[name]

        # Check default responses
        if name in self._default_responses:
            result = self._default_responses[name].copy()
            # Update path if provided
            if "path" in params:
                result["path"] = params["path"]
            return result

        # Fallback
        return {"status": "success", "data": {"result": f"executed {name}"}}

    def set_response(self, tool_name: str, response: Dict[str, Any]):
        """Set custom response for a tool."""
        self.responses[tool_name] = response

    def reset(self):
        """Reset execution tracking."""
        self.executions = []
