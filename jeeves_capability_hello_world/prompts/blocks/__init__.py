"""
Core prompt building blocks for agent pipelines.

Blocks:
- identity_block: Agent identity and persona
- style_block: Response voice and formatting rules
- role_invariants: Universal constraints for all agents
- safety_block: Safety guardrails (mode-aware)
"""

from .identity_block import IDENTITY_BLOCK, get_identity_block
from .style_block import STYLE_BLOCK
from .role_invariants import ROLE_INVARIANTS
from .safety_block import SAFETY_BLOCK, get_safety_block

__all__ = [
    "IDENTITY_BLOCK",
    "get_identity_block",
    "STYLE_BLOCK",
    "ROLE_INVARIANTS",
    "SAFETY_BLOCK",
    "get_safety_block",
]
