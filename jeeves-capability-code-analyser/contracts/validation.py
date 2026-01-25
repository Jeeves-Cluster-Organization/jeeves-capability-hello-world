"""
Tool Result Validation for Code Analysis Vertical.

Light validation hooks that check tool results against contracts.
Designed to be cheap, non-blocking, and informative rather than strict.

Usage:
    from mission_system.contracts.code_analysis import validate_tool_result

    result = await some_tool(...)
    issues = validate_tool_result("some_tool", result)
    if issues:
        for issue in issues:
            logger.warning(issue.message, severity=issue.severity)

Design Principles:
- Lightweight: Quick checks, no deep validation
- Informative: Clear messages about what's wrong
- Non-blocking: Returns issues, doesn't raise by default
- Constitutional: Follows logging patterns (structlog, no globals)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .registry import (
    TOOL_RESULT_SCHEMAS,
    requires_attempt_history,
    get_schema_for_tool,
)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues.

    Following Constitution logging patterns.
    """
    CRITICAL = "critical"  # Contract violation, should never happen
    ERROR = "error"        # Missing required field
    WARNING = "warning"    # Type mismatch, unexpected value
    INFO = "info"          # Suggestion for improvement


@dataclass
class ToolResultValidationIssue:
    """A single validation issue found in a tool result.

    Used for validating tool outputs against their contracts.

    Note: This is distinct from MetaValidationIssue in
    common/models.py which is for hallucination detection.
    """
    field: str
    message: str
    severity: ValidationSeverity
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        d = {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
        }
        if self.expected:
            d["expected"] = self.expected
        if self.actual:
            d["actual"] = self.actual
        return d

    def __str__(self) -> str:
        """Human-readable string representation."""
        parts = [f"[{self.severity.value.upper()}] {self.field}: {self.message}"]
        if self.expected and self.actual:
            parts.append(f" (expected: {self.expected}, got: {self.actual})")
        return "".join(parts)


def validate_tool_result(
    tool_name: str,
    result: Dict[str, Any],
    strict: bool = False,
) -> List[ToolResultValidationIssue]:
    """Validate a tool result against its contract.

    This function performs lightweight validation:
    1. Checks required fields (status, citations)
    2. Validates attempt_history for composite/resilient tools
    3. Checks type correctness for normalized fields (files, counts)

    Args:
        tool_name: Name of the tool that produced the result
        result: The result dictionary to validate
        strict: If True, treat warnings as errors

    Returns:
        List of ToolResultValidationIssue objects. Empty list means valid.
    """
    issues: List[ToolResultValidationIssue] = []

    if not isinstance(result, dict):
        issues.append(ToolResultValidationIssue(
            field="result",
            message="Result must be a dictionary",
            severity=ValidationSeverity.CRITICAL,
            expected="dict",
            actual=type(result).__name__,
        ))
        return issues

    # ─── Check required fields ───
    issues.extend(_validate_required_fields(result))

    # ─── Check attempt_history for composite/resilient tools ───
    if requires_attempt_history(tool_name):
        issues.extend(_validate_attempt_history(tool_name, result))

    # ─── Check normalized fields ───
    issues.extend(_validate_normalized_fields(tool_name, result))

    # ─── Check status value ───
    issues.extend(_validate_status(result))

    # ─── Check citations format ───
    issues.extend(_validate_citations(result))

    return issues


def _validate_required_fields(result: Dict[str, Any]) -> List[ToolResultValidationIssue]:
    """Check that required fields are present."""
    issues = []

    # status is always required
    if "status" not in result:
        issues.append(ToolResultValidationIssue(
            field="status",
            message="Missing required field 'status'",
            severity=ValidationSeverity.ERROR,
        ))

    # citations should be present (can be empty list)
    if "citations" not in result:
        issues.append(ToolResultValidationIssue(
            field="citations",
            message="Missing 'citations' field (should be list, can be empty)",
            severity=ValidationSeverity.WARNING,
        ))

    return issues


def _validate_attempt_history(
    tool_name: str,
    result: Dict[str, Any],
) -> List[ToolResultValidationIssue]:
    """Validate attempt_history for composite/resilient tools.

    Per Amendment XVII and XIX, these tools MUST return attempt_history.
    """
    issues = []

    if "attempt_history" not in result:
        issues.append(ToolResultValidationIssue(
            field="attempt_history",
            message=f"Composite/resilient tool '{tool_name}' missing required 'attempt_history'",
            severity=ValidationSeverity.ERROR,
        ))
        return issues

    attempt_history = result["attempt_history"]

    # Must be a list (not None, not int)
    if attempt_history is None:
        issues.append(ToolResultValidationIssue(
            field="attempt_history",
            message="attempt_history must be a list, not None",
            severity=ValidationSeverity.ERROR,
            expected="List[AttemptHistoryEntry]",
            actual="None",
        ))
    elif not isinstance(attempt_history, list):
        issues.append(ToolResultValidationIssue(
            field="attempt_history",
            message="attempt_history must be a list",
            severity=ValidationSeverity.ERROR,
            expected="List[AttemptHistoryEntry]",
            actual=type(attempt_history).__name__,
        ))

    return issues


def _validate_normalized_fields(
    tool_name: str,
    result: Dict[str, Any],
) -> List[ToolResultValidationIssue]:
    """Validate normalized fields (files as list, counts as int)."""
    issues = []

    # ─── files field: MUST be a list, never an int ───
    if "files" in result:
        files = result["files"]
        if isinstance(files, int):
            issues.append(ToolResultValidationIssue(
                field="files",
                message="'files' should be a list, not a count. Use 'file_count' for the count.",
                severity=ValidationSeverity.ERROR,
                expected="List[str]",
                actual="int",
            ))
        elif not isinstance(files, list):
            issues.append(ToolResultValidationIssue(
                field="files",
                message="'files' should be a list",
                severity=ValidationSeverity.WARNING,
                expected="List[str]",
                actual=type(files).__name__,
            ))

    # ─── symbols field: MUST be a list when present (for symbol tools) ───
    if "symbols" in result and tool_name in ("find_symbol", "get_file_symbols"):
        symbols = result["symbols"]
        if not isinstance(symbols, list):
            issues.append(ToolResultValidationIssue(
                field="symbols",
                message="'symbols' should be a list",
                severity=ValidationSeverity.WARNING,
                expected="List[SymbolInfo]",
                actual=type(symbols).__name__,
            ))

    # ─── matches field: MUST be a list when present ───
    if "matches" in result:
        matches = result["matches"]
        if not isinstance(matches, list):
            issues.append(ToolResultValidationIssue(
                field="matches",
                message="'matches' should be a list",
                severity=ValidationSeverity.WARNING,
                expected="List[GrepMatch]",
                actual=type(matches).__name__,
            ))

    # ─── results field: MUST be a list when present ───
    if "results" in result:
        results = result["results"]
        if not isinstance(results, list):
            issues.append(ToolResultValidationIssue(
                field="results",
                message="'results' should be a list",
                severity=ValidationSeverity.WARNING,
                expected="List[...]",
                actual=type(results).__name__,
            ))

    # ─── Count fields: MUST be int when present ───
    count_fields = ["file_count", "symbol_count", "match_count", "result_count", "usage_count"]
    for field in count_fields:
        if field in result:
            value = result[field]
            if not isinstance(value, int):
                issues.append(ToolResultValidationIssue(
                    field=field,
                    message=f"'{field}' should be an integer",
                    severity=ValidationSeverity.WARNING,
                    expected="int",
                    actual=type(value).__name__,
                ))

    return issues


def _validate_status(result: Dict[str, Any]) -> List[ToolResultValidationIssue]:
    """Validate status field value."""
    issues = []

    if "status" in result:
        status = result["status"]
        valid_statuses = {"success", "partial", "not_found", "error"}
        if status not in valid_statuses:
            issues.append(ToolResultValidationIssue(
                field="status",
                message=f"Invalid status value",
                severity=ValidationSeverity.WARNING,
                expected=str(valid_statuses),
                actual=str(status),
            ))

    return issues


def _validate_citations(result: Dict[str, Any]) -> List[ToolResultValidationIssue]:
    """Validate citations field format."""
    issues = []

    if "citations" in result:
        citations = result["citations"]
        if not isinstance(citations, list):
            issues.append(ToolResultValidationIssue(
                field="citations",
                message="'citations' should be a list",
                severity=ValidationSeverity.WARNING,
                expected="List[str]",
                actual=type(citations).__name__,
            ))
        elif citations:
            # Check format of first few citations
            for i, citation in enumerate(citations[:3]):
                if not isinstance(citation, str):
                    issues.append(ToolResultValidationIssue(
                        field=f"citations[{i}]",
                        message="Citation entries should be strings",
                        severity=ValidationSeverity.WARNING,
                        expected="str",
                        actual=type(citation).__name__,
                    ))
                elif ":" not in citation and not citation.startswith("["):
                    issues.append(ToolResultValidationIssue(
                        field=f"citations[{i}]",
                        message="Citation should be in [file:line] format",
                        severity=ValidationSeverity.INFO,
                        expected="[file:line] or file:line",
                        actual=citation[:50],
                    ))

    return issues


def validate_and_log(
    tool_name: str,
    result: Dict[str, Any],
    logger: Any,
    strict: bool = False,
) -> bool:
    """Validate and log any issues found.

    Convenience function that validates and logs issues using
    the provided logger (following Constitution logging patterns).

    Args:
        tool_name: Name of the tool
        result: Result dictionary
        logger: Logger instance (structlog-compatible)
        strict: If True, return False on any warning+

    Returns:
        True if valid (no errors), False otherwise
    """
    issues = validate_tool_result(tool_name, result, strict=strict)

    if not issues:
        return True

    # Group issues by severity
    errors = [i for i in issues if i.severity in (ValidationSeverity.CRITICAL, ValidationSeverity.ERROR)]
    warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
    infos = [i for i in issues if i.severity == ValidationSeverity.INFO]

    # Log grouped issues
    if errors:
        logger.warning(
            "tool_result_validation_errors",
            tool=tool_name,
            error_count=len(errors),
            errors=[i.to_dict() for i in errors],
        )

    if warnings:
        logger.debug(
            "tool_result_validation_warnings",
            tool=tool_name,
            warning_count=len(warnings),
            warnings=[i.to_dict() for i in warnings],
        )

    if infos:
        logger.debug(
            "tool_result_validation_info",
            tool=tool_name,
            info_count=len(infos),
            infos=[i.to_dict() for i in infos],
        )

    # Return False if any errors (or warnings in strict mode)
    if strict:
        return len(errors) == 0 and len(warnings) == 0
    return len(errors) == 0
