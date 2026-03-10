"""Hello World Capability for Jeeves-Core.

Thin capability layer that registers hello-world chatbot with jeeves-core.
Uses service_class + pipeline_config for auto-wiring.

Usage:
    from jeeves_capability_hello_world.capability import register_capability
    register_capability()
"""

from jeeves_capability_hello_world.capability.wiring import (
    register_capability,
    CAPABILITY_ID,
    CAPABILITY_VERSION,
)

__all__ = [
    "register_capability",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
]
