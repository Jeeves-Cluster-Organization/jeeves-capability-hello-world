"""
Agent Tool Access Matrix for Code Analysis Capability.

Runtime-enforced tool access control with typed ToolIds.
Only executor agent can execute tools.

Centralized Architecture (v4.0):
- Agent names use simple form: "perception", "intent", "planner", etc.
- Imports ToolId from capability's own catalog (not contracts_core)
"""

from typing import Dict, List, FrozenSet
import logging

from protocols import ToolAccess

# Import ToolId from capability's own catalog (layer-compliant)
from tools.catalog import ToolId

# Module logger (standard library - no avionics dependency)
_logger = logging.getLogger(__name__)


class AgentToolAccess:
    """Runtime-enforced tool access configuration.

    This class provides the access control matrix that ToolExecutor
    uses to validate tool execution requests at runtime.

    Agent names use simple form per centralized architecture v4.0.
    """

    _ACCESS_MATRIX: Dict[str, FrozenSet[ToolId]] = {
        # Agent 1: Perception - Pure LLM reasoning
        "perception": frozenset(),

        # Agent 2: Intent - Pure LLM reasoning
        "intent": frozenset(),

        # Agent 3: Planner - No execution, only reads tool registry
        "planner": frozenset(),

        # Agent 4: Executor - ONLY agent that can execute tools
        "executor": frozenset({
            # COMPOSITE TOOLS
            ToolId.LOCATE,
            ToolId.EXPLORE_SYMBOL_USAGE,
            ToolId.MAP_MODULE,
            ToolId.TRACE_ENTRY_POINT,
            ToolId.EXPLAIN_CODE_HISTORY,
            # RESILIENT OPS
            ToolId.READ_CODE,
            ToolId.FIND_RELATED,
            # STANDALONE
            ToolId.GIT_STATUS,
            ToolId.LIST_TOOLS,
        }),

        # Agent 5: Synthesizer - Pure LLM reasoning
        "synthesizer": frozenset(),

        # Agent 6: Critic - Pure LLM validation
        "critic": frozenset(),

        # Agent 7: Integration - Pure LLM reasoning
        "integration": frozenset(),
    }

    PLANNER_VISIBLE_TOOLS: FrozenSet[ToolId] = _ACCESS_MATRIX["executor"]

    @classmethod
    def get_allowed_tools(cls, agent_name: str) -> FrozenSet[ToolId]:
        """Get set of tools an agent is allowed to execute."""
        return cls._ACCESS_MATRIX.get(agent_name, frozenset())

    @classmethod
    def is_tool_allowed(cls, agent_name: str, tool_id: ToolId) -> bool:
        """Check if an agent can execute a specific tool."""
        return tool_id in cls.get_allowed_tools(agent_name)

    @classmethod
    def get_rejection_message(cls, agent_name: str, tool_id: ToolId) -> str:
        """Get rejection message for unauthorized access attempt."""
        return (
            f"Tool access denied: {agent_name} cannot execute {tool_id.value}. "
            f"Only executor agent can execute tools."
        )

    @classmethod
    def get_agent_access_level(cls, agent_name: str) -> ToolAccess:
        """Get access level for an agent."""
        allowed = cls.get_allowed_tools(agent_name)
        if not allowed:
            return ToolAccess.NONE
        return ToolAccess.READ


TOOL_CATEGORIES: Dict[str, List[ToolId]] = {
    "composite": [
        ToolId.LOCATE,
        ToolId.EXPLORE_SYMBOL_USAGE,
        ToolId.MAP_MODULE,
        ToolId.TRACE_ENTRY_POINT,
        ToolId.EXPLAIN_CODE_HISTORY,
    ],
    "resilient": [
        ToolId.READ_CODE,
        ToolId.FIND_RELATED,
    ],
    "standalone": [
        ToolId.GIT_STATUS,
        ToolId.LIST_TOOLS,
    ],
    "_internal_base": [
        ToolId.READ_FILE,
        ToolId.GLOB_FILES,
        ToolId.GREP_SEARCH,
        ToolId.TREE_STRUCTURE,
        ToolId.FIND_SYMBOL,
        ToolId.GET_FILE_SYMBOLS,
        ToolId.GET_IMPORTS,
        ToolId.GET_IMPORTERS,
        ToolId.SEMANTIC_SEARCH,
        ToolId.FIND_SIMILAR_FILES,
    ],
    "_internal_git": [
        ToolId.GIT_LOG,
        ToolId.GIT_BLAME,
        ToolId.GIT_DIFF,
    ],
}


def get_agent_access(agent_name: str) -> Dict:
    """Get tool access configuration for an agent."""
    allowed = AgentToolAccess.get_allowed_tools(agent_name)
    level = AgentToolAccess.get_agent_access_level(agent_name)

    return {
        "level": level,
        "allowed_tools": [tid.value for tid in allowed],
        "allowed_tool_ids": allowed,
    }


def can_agent_use_tool(agent_name: str, tool_name: str) -> bool:
    """Check if an agent can use a specific tool (by string name)."""
    try:
        tool_id = ToolId(tool_name)
        return AgentToolAccess.is_tool_allowed(agent_name, tool_id)
    except ValueError:
        _logger.debug(
            "unknown_tool_name_in_access_check",
            tool_name=tool_name,
            agent_name=agent_name,
        )
        return False


def get_agents_for_tool(tool_name: str) -> List[str]:
    """Get list of agents that can use a specific tool."""
    try:
        tool_id = ToolId(tool_name)
    except ValueError:
        _logger.debug(
            "unknown_tool_name_in_agent_lookup",
            tool_name=tool_name,
        )
        return []

    agents = []
    for agent_name in AgentToolAccess._ACCESS_MATRIX:
        if tool_id in AgentToolAccess._ACCESS_MATRIX[agent_name]:
            agents.append(agent_name)
    return agents


def get_tools_by_category(category: str) -> List[str]:
    """Get tool names in a specific category."""
    tool_ids = TOOL_CATEGORIES.get(category, [])
    return [tid.value for tid in tool_ids]
