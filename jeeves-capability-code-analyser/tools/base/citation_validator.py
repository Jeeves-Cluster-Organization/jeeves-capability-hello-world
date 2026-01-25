"""Citation Validator - Verify code citations in responses.

This utility validates that file:line citations in code analysis responses
actually exist and match the content claimed.

Constitutional Compliance:
- P2 (Reliability): Verify claims are backed by actual code
- P6 (Observable): Provide detailed validation reports
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from protocols import LoggerProtocol
import structlog
get_logger = structlog.get_logger
from tools.base.path_helpers import get_repo_path, resolve_path


@dataclass
class Citation:
    """Represents a single file:line citation."""

    file: str
    line: int
    end_line: Optional[int] = None
    description: Optional[str] = None
    raw_match: str = ""

    @property
    def line_range(self) -> Tuple[int, int]:
        """Get line range as (start, end) tuple."""
        return (self.line, self.end_line or self.line)


@dataclass
class CitationValidationResult:
    """Result of validating a single citation."""

    citation: Citation
    valid: bool
    file_exists: bool
    line_exists: bool
    actual_content: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report for a response."""

    total_citations: int
    valid_citations: int
    invalid_citations: int
    missing_files: List[str] = field(default_factory=list)
    invalid_lines: List[str] = field(default_factory=list)
    results: List[CitationValidationResult] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        """Calculate citation accuracy as percentage."""
        if self.total_citations == 0:
            return 1.0  # No citations = nothing to invalidate
        return self.valid_citations / self.total_citations

    @property
    def is_valid(self) -> bool:
        """Check if all citations are valid."""
        return self.invalid_citations == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_citations": self.total_citations,
            "valid_citations": self.valid_citations,
            "invalid_citations": self.invalid_citations,
            "accuracy": self.accuracy,
            "is_valid": self.is_valid,
            "missing_files": self.missing_files,
            "invalid_lines": self.invalid_lines,
            "results": [
                {
                    "file": r.citation.file,
                    "line": r.citation.line,
                    "valid": r.valid,
                    "file_exists": r.file_exists,
                    "line_exists": r.line_exists,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class CitationValidator:
    """Validates file:line citations in code analysis responses.

    Supports multiple citation formats:
    - `file.py:123` (backtick enclosed)
    - file.py:123 (plain text)
    - `file.py:10-20` (line range)
    - {"file": "path", "line": 123} (JSON format)
    """

    # Regex patterns for different citation formats
    PATTERNS = [
        # Backtick enclosed: `file.py:123` or `file.py:10-20`
        re.compile(r"`([a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+):(\d+)(?:-(\d+))?`"),
        # Plain text: file.py:123 (word boundary)
        re.compile(r"\b([a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+):(\d+)(?:-(\d+))?\b"),
        # Parenthetical: (file.py:123)
        re.compile(r"\(([a-zA-Z0-9_/\-\.]+\.[a-zA-Z0-9]+):(\d+)(?:-(\d+))?\)"),
    ]

    # JSON citation pattern
    JSON_PATTERN = re.compile(
        r'\{\s*"file"\s*:\s*"([^"]+)"\s*,\s*"line"\s*:\s*(\d+)'
        r'(?:\s*,\s*"end_line"\s*:\s*(\d+))?'
    )

    def __init__(self, repo_path: Optional[str] = None, logger: Optional[LoggerProtocol] = None):
        """Initialize citation validator.

        Args:
            repo_path: Repository root path. If None, uses configured repo path.
            logger: Optional logger instance.
        """
        self.repo_path = repo_path or get_repo_path()
        self._logger = logger or get_logger()

    def extract_citations(self, text: str) -> List[Citation]:
        """Extract all citations from text.

        Args:
            text: Response text containing citations

        Returns:
            List of Citation objects
        """
        citations = []
        seen = set()  # Dedupe by (file, line)

        # Try each pattern
        for pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                file_path = match.group(1)
                line = int(match.group(2))
                end_line = int(match.group(3)) if match.group(3) else None

                key = (file_path, line)
                if key not in seen:
                    seen.add(key)
                    citations.append(
                        Citation(
                            file=file_path,
                            line=line,
                            end_line=end_line,
                            raw_match=match.group(0),
                        )
                    )

        # Try JSON pattern
        for match in self.JSON_PATTERN.finditer(text):
            file_path = match.group(1)
            line = int(match.group(2))
            end_line = int(match.group(3)) if match.group(3) else None

            key = (file_path, line)
            if key not in seen:
                seen.add(key)
                citations.append(
                    Citation(
                        file=file_path,
                        line=line,
                        end_line=end_line,
                        raw_match=match.group(0),
                    )
                )

        return citations

    def validate_citation(self, citation: Citation) -> CitationValidationResult:
        """Validate a single citation.

        Args:
            citation: Citation to validate

        Returns:
            CitationValidationResult with validation details
        """
        # Resolve file path
        resolved = resolve_path(citation.file, self.repo_path)

        if resolved is None:
            return CitationValidationResult(
                citation=citation,
                valid=False,
                file_exists=False,
                line_exists=False,
                error=f"Path '{citation.file}' is outside repository bounds",
            )

        if not resolved.exists():
            return CitationValidationResult(
                citation=citation,
                valid=False,
                file_exists=False,
                line_exists=False,
                error=f"File not found: {citation.file}",
            )

        if not resolved.is_file():
            return CitationValidationResult(
                citation=citation,
                valid=False,
                file_exists=False,
                line_exists=False,
                error=f"Not a file: {citation.file}",
            )

        # Read file and check line
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            start_line, end_line = citation.line_range

            # Check if lines exist
            if start_line < 1 or start_line > total_lines:
                return CitationValidationResult(
                    citation=citation,
                    valid=False,
                    file_exists=True,
                    line_exists=False,
                    error=f"Line {start_line} out of range (file has {total_lines} lines)",
                )

            if end_line > total_lines:
                return CitationValidationResult(
                    citation=citation,
                    valid=False,
                    file_exists=True,
                    line_exists=False,
                    error=f"End line {end_line} out of range (file has {total_lines} lines)",
                )

            # Get actual content at cited lines
            actual_lines = lines[start_line - 1 : end_line]
            actual_content = "\n".join(actual_lines)

            return CitationValidationResult(
                citation=citation,
                valid=True,
                file_exists=True,
                line_exists=True,
                actual_content=actual_content,
            )

        except Exception as e:
            self._logger.error(
                "citation_validation_error",
                file=citation.file,
                line=citation.line,
                error=str(e),
            )
            return CitationValidationResult(
                citation=citation,
                valid=False,
                file_exists=True,
                line_exists=False,
                error=f"Failed to read file: {e}",
            )

    def validate_response(self, response: str) -> ValidationReport:
        """Validate all citations in a response.

        Args:
            response: Full response text containing citations

        Returns:
            ValidationReport with all validation results
        """
        citations = self.extract_citations(response)

        results = []
        missing_files = []
        invalid_lines = []
        valid_count = 0

        for citation in citations:
            result = self.validate_citation(citation)
            results.append(result)

            if result.valid:
                valid_count += 1
            else:
                if not result.file_exists:
                    missing_files.append(citation.file)
                elif not result.line_exists:
                    invalid_lines.append(f"{citation.file}:{citation.line}")

        return ValidationReport(
            total_citations=len(citations),
            valid_citations=valid_count,
            invalid_citations=len(citations) - valid_count,
            missing_files=missing_files,
            invalid_lines=invalid_lines,
            results=results,
        )

    def validate_citations_list(
        self, citations: List[Dict[str, Any]]
    ) -> ValidationReport:
        """Validate a list of citation dictionaries.

        Args:
            citations: List of dicts with 'file' and 'line' keys

        Returns:
            ValidationReport with all validation results
        """
        citation_objs = []
        for c in citations:
            citation_objs.append(
                Citation(
                    file=c.get("file", ""),
                    line=c.get("line", 0),
                    end_line=c.get("end_line"),
                    description=c.get("description"),
                )
            )

        results = []
        missing_files = []
        invalid_lines = []
        valid_count = 0

        for citation in citation_objs:
            result = self.validate_citation(citation)
            results.append(result)

            if result.valid:
                valid_count += 1
            else:
                if not result.file_exists:
                    missing_files.append(citation.file)
                elif not result.line_exists:
                    invalid_lines.append(f"{citation.file}:{citation.line}")

        return ValidationReport(
            total_citations=len(citation_objs),
            valid_citations=valid_count,
            invalid_citations=len(citation_objs) - valid_count,
            missing_files=missing_files,
            invalid_lines=invalid_lines,
            results=results,
        )


# Convenience functions for direct use


def extract_citations(text: str, repo_path: Optional[str] = None) -> List[Citation]:
    """Extract citations from text.

    Args:
        text: Text containing citations
        repo_path: Optional repository path

    Returns:
        List of Citation objects
    """
    validator = CitationValidator(repo_path)
    return validator.extract_citations(text)


def validate_response(
    response: str, repo_path: Optional[str] = None
) -> ValidationReport:
    """Validate all citations in a response.

    Args:
        response: Response text
        repo_path: Optional repository path

    Returns:
        ValidationReport
    """
    validator = CitationValidator(repo_path)
    return validator.validate_response(response)


def validate_citations(
    citations: List[Dict[str, Any]], repo_path: Optional[str] = None
) -> ValidationReport:
    """Validate a list of citation dictionaries.

    Args:
        citations: List of citation dicts
        repo_path: Optional repository path

    Returns:
        ValidationReport
    """
    validator = CitationValidator(repo_path)
    return validator.validate_citations_list(citations)
