"""Capability Registration for Hello World Chatbot.

Registers hello-world as a capability with jeeves-core. PipelineConfig is the
deployment spec — agent metadata, LLM configs, and service config are derived.

Usage:
    from jeeves_capability_hello_world.capability.wiring import register_capability
    register_capability()
"""

import logging
from pathlib import Path

from jeeves_core import (
    register_capability as _register,
    ModeConfig,
    ToolsConfig,
    ToolCatalog,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CAPABILITY CONSTANTS
# =============================================================================

CAPABILITY_ID = "hello_world"
_create_from_app_context = None  # Set by register_capability()
CAPABILITY_VERSION = "0.0.1"
CAPABILITY_ROOT = Path(__file__).resolve().parent.parent

# =============================================================================
# TOOL CATALOG (from @tool decorators)
# =============================================================================


def _create_tool_catalog() -> ToolCatalog:
    """Build catalog from @tool-decorated functions."""
    from jeeves_capability_hello_world.tools import hello_world_tools

    return ToolCatalog.from_decorated(CAPABILITY_ID, hello_world_tools)


# =============================================================================
# ONE-CALL REGISTRATION
# =============================================================================


def register_capability() -> None:
    """Register hello-world capability with jeeves-core."""
    global _create_from_app_context
    from jeeves_capability_hello_world.orchestration.chatbot_service import ChatbotService
    from jeeves_capability_hello_world.pipeline_config import ONBOARDING_CHATBOT_PIPELINE
    from jeeves_capability_hello_world.database.sqlite_client import SQLiteClient

    _create_from_app_context = _register(
        CAPABILITY_ID,
        ONBOARDING_CHATBOT_PIPELINE,
        service_class=ChatbotService,
        is_default=True,
        default_session_title="Chat Session",
        capabilities=["query", "chat", "general"],
        mode_config=ModeConfig(
            mode_id=CAPABILITY_ID,
            response_fields=["response", "citations", "confidence"],
        ),
        tools_config=ToolsConfig(
            initializer=_create_tool_catalog,
        ),
        service_kwargs={"db": SQLiteClient()},
    )

    logger.info(
        "hello_world_capability_registered",
        extra={
            "capability_id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
        },
    )


def create_from_app_context(app_context):
    """Create ChatbotService from AppContext (for standalone apps like gradio_app)."""
    if _create_from_app_context is None:
        raise RuntimeError("Call register_capability() first")
    return _create_from_app_context(app_context)


__all__ = [
    "register_capability",
    "create_from_app_context",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "CAPABILITY_ROOT",
]
