"""Code Analysis Capability Configuration.

Domain-specific configuration for the code analysis vertical.
Generic config types are in jeeves_mission_system.config.

Exports:
- Context bounds (CodeAnalysisBounds - domain-specific resource limits)
- Language config (LanguageId, LanguageSpec, LanguageConfig)
- Tool access matrix (AgentToolAccess, TOOL_CATEGORIES)
- Agent list (CODE_ANALYSIS_AGENTS)
- Product identity (PRODUCT_NAME, etc.)

Note: Deployment profiles (NodeProfile, PROFILES) extracted to k8s/ manifests.
Note: Pipeline modes now defined in pipeline_config.py as PipelineConfig variants.
"""

from jeeves_capability_code_analyser.config.context_bounds import (
    CodeAnalysisBounds,
    DEFAULT_CODE_ANALYSIS_BOUNDS,
    get_code_analysis_bounds,
    set_code_analysis_bounds,
    reset_code_analysis_bounds,
)

from jeeves_capability_code_analyser.config.language_config import (
    LanguageId,
    LanguageSpec,
    LanguageConfig,
    LANGUAGE_SPECS,
    COMMON_EXCLUDE_DIRS,
    get_language_config,
    set_language_config,
    detect_repo_languages,
)

from jeeves_capability_code_analyser.config.tool_access import (
    AgentToolAccess,
    TOOL_CATEGORIES,
    get_agent_access,
    can_agent_use_tool,
    get_agents_for_tool,
    get_tools_by_category,
)
# Re-export ToolAccess from jeeves_protocols for convenience
from jeeves_protocols import ToolAccess

from jeeves_capability_code_analyser.config.deployment import (
    CODE_ANALYSIS_AGENTS,
)

from jeeves_capability_code_analyser.config.identity import (
    PRODUCT_NAME,
    PRODUCT_NAME_FULL,
    PRODUCT_DESCRIPTION,
    PRODUCT_VERSION,
    PRODUCT_SERVICE_NAME,
    AGENT_ARCHITECTURE,
    AGENT_COUNT,
)

__all__ = [
    # Context bounds (domain-specific resource limits)
    "CodeAnalysisBounds",
    "DEFAULT_CODE_ANALYSIS_BOUNDS",
    "get_code_analysis_bounds",
    "set_code_analysis_bounds",
    "reset_code_analysis_bounds",
    # Language config
    "LanguageId",
    "LanguageSpec",
    "LanguageConfig",
    "LANGUAGE_SPECS",
    "COMMON_EXCLUDE_DIRS",
    "get_language_config",
    "set_language_config",
    "detect_repo_languages",
    # Tool access
    "ToolAccess",
    "AgentToolAccess",
    "TOOL_CATEGORIES",
    "get_agent_access",
    "can_agent_use_tool",
    "get_agents_for_tool",
    "get_tools_by_category",
    # Agent list
    "CODE_ANALYSIS_AGENTS",
    # Identity
    "PRODUCT_NAME",
    "PRODUCT_NAME_FULL",
    "PRODUCT_DESCRIPTION",
    "PRODUCT_VERSION",
    "PRODUCT_SERVICE_NAME",
    "AGENT_ARCHITECTURE",
    "AGENT_COUNT",
]
