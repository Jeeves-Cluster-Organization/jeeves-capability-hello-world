"""Tools for Onboarding chatbot capability.

Registration is handled by capability/wiring.py via CapabilityToolCatalog.
"""

from .hello_world_tools import get_time, list_tools

__all__ = ["get_time", "list_tools"]
