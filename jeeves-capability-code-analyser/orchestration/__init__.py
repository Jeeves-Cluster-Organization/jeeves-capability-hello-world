"""
Code Analysis Orchestration Package.

Centralized Architecture (v4.0):
- CodeAnalysisService wraps UnifiedRuntime + CODE_ANALYSIS_PIPELINE
- CodeAnalysisResult is the output container
- Factory functions in wiring.py for proper dependency injection

See docs/JEEVES_CORE_RUNTIME_CONTRACT.md for the authoritative contract.

Exports:
- CodeAnalysisService: Main service for code analysis queries
- CodeAnalysisResult: Result container
- create_code_analysis_service: Factory function for service creation
"""

from orchestration.service import CodeAnalysisService
from orchestration.types import CodeAnalysisResult
from orchestration.wiring import (
    create_code_analysis_service,
    create_code_analysis_service_from_components,
)

__all__ = [
    "CodeAnalysisService",
    "CodeAnalysisResult",
    "create_code_analysis_service",
    "create_code_analysis_service_from_components",
]
