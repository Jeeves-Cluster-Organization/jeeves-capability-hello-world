"""
Code Analysis Prompts.

This module contains prompt templates for the code analysis capability.
Prompts are registered with the mission_system PromptRegistry at startup.

Note: Perception and Executor agents have has_llm=False, so no prompts are needed for them.
"""

from .code_analysis import (
    code_analysis_intent,
    code_analysis_planner,
    code_analysis_synthesizer,
    code_analysis_critic,
    code_analysis_integration,
    register_code_analysis_prompts,
)

__all__ = [
    "code_analysis_intent",
    "code_analysis_planner",
    "code_analysis_synthesizer",
    "code_analysis_critic",
    "code_analysis_integration",
    "register_code_analysis_prompts",
]
