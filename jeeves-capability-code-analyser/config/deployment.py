"""
Code Analysis Capability - Agent List.

Defines the canonical list of agents in the code analysis pipeline.
For deployment configuration, see k8s/ manifests.

Constitutional Reference:
- Capability owns domain-specific configuration (Constitution R6)
- Deployment profiles extracted to k8s/ manifests (infrastructure-as-code)
"""

from typing import List


# Canonical list of agents in the code analysis pipeline
# Order matters: this is the pipeline execution order
CODE_ANALYSIS_AGENTS: List[str] = [
    "perception",
    "intent",
    "planner",
    "traverser",
    "synthesizer",
    "critic",
    "integration",
]


__all__ = [
    "CODE_ANALYSIS_AGENTS",
]
