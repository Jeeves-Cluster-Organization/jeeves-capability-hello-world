#!/usr/bin/env python3
"""CI Check: Logging Invariant Enforcement.

This script enforces the Jeeves logging architecture invariants:
1. No print() in production code
2. No bare except: blocks without logging
3. No structlog.get_logger() outside the central logging module

Run as part of CI to prevent logging architecture violations.

Usage:
    python scripts/check_logging_invariants.py
    python scripts/check_logging_invariants.py --fix  # Show suggested fixes

Exit codes:
    0: All checks pass
    1: Violations found
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple

# Directories to check
CHECK_DIRS = [
    "jeeves_core_engine",
    "avionics",
    "mission_system",
    "jeeves-capability-code-analyser",
]

# Files/patterns to exclude
EXCLUDE_PATTERNS = [
    "**/tests/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/conftest.py",
    "**/scripts/**",
    "**/logging/__init__.py",  # Central logging module is allowed
    "**/__pycache__/**",
    "**/migrations/**",
]

# Allowed files for structlog.get_logger()
STRUCTLOG_ALLOWED_FILES = {
    "avionics/logging/__init__.py",
    "jeeves_core_engine/config/logging_config.py",
}


@dataclass
class Violation:
    """A single logging invariant violation."""
    file: Path
    line: int
    rule: str
    message: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: [{self.rule}] {self.message}\n  {self.snippet}"


class LoggingInvariantChecker:
    """AST-based checker for logging invariants."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.violations: List[Violation] = []
        self.source_lines: List[str] = []

    def check(self) -> List[Violation]:
        """Run all checks on the file."""
        try:
            content = self.filepath.read_text()
            self.source_lines = content.split('\n')
            tree = ast.parse(content, filename=str(self.filepath))
        except SyntaxError as e:
            # Skip files with syntax errors
            return []
        except Exception as e:
            return []

        self._check_print_statements(tree)
        self._check_bare_except(tree)
        self._check_structlog_global(content)

        return self.violations

    def _check_print_statements(self, tree: ast.AST) -> None:
        """Check for print() statements in production code."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    # Check if it's in a docstring (we skip those)
                    snippet = self._get_snippet(node.lineno)
                    if '"""' not in snippet and "'''" not in snippet:
                        self.violations.append(Violation(
                            file=self.filepath,
                            line=node.lineno,
                            rule="NO_PRINT",
                            message="print() in production code - use logger.info() instead",
                            snippet=snippet.strip(),
                        ))

    def _check_bare_except(self, tree: ast.AST) -> None:
        """Check for bare except: blocks without logging."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Bare except: has type=None
                if node.type is None:
                    # Check if there's a logger call in the body
                    has_logging = self._has_logging_in_body(node.body)
                    if not has_logging:
                        snippet = self._get_snippet(node.lineno)
                        self.violations.append(Violation(
                            file=self.filepath,
                            line=node.lineno,
                            rule="BARE_EXCEPT",
                            message="Bare except: without logging - specify exception type and log",
                            snippet=snippet.strip(),
                        ))

    def _has_logging_in_body(self, body: List[ast.stmt]) -> bool:
        """Check if an exception handler body contains logging."""
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("debug", "info", "warning", "error", "critical"):
                            return True
        return False

    def _check_structlog_global(self, content: str) -> None:
        """Check for structlog.get_logger() outside central module."""
        relative_path = str(self.filepath.relative_to(Path.cwd()))
        if relative_path in STRUCTLOG_ALLOWED_FILES:
            return

        # Pattern: module-level logger = structlog.get_logger()
        pattern = r"^logger\s*=\s*structlog\.get_logger\(\)"
        for i, line in enumerate(self.source_lines, 1):
            if re.match(pattern, line.strip()):
                self.violations.append(Violation(
                    file=self.filepath,
                    line=i,
                    rule="GLOBAL_STRUCTLOG",
                    message="Module-level structlog.get_logger() - use injected LoggerProtocol",
                    snippet=line.strip(),
                ))

    def _get_snippet(self, lineno: int) -> str:
        """Get source line for a given line number."""
        if 0 < lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""


def should_check_file(filepath: Path, exclude_patterns: List[str]) -> bool:
    """Determine if a file should be checked."""
    if not filepath.suffix == ".py":
        return False

    # Check exclusion patterns
    for pattern in exclude_patterns:
        if filepath.match(pattern):
            return False

    return True


def get_files_to_check(check_dirs: List[str], exclude_patterns: List[str]) -> List[Path]:
    """Get all Python files to check."""
    cwd = Path.cwd()
    files = []

    for dir_name in check_dirs:
        dir_path = cwd / dir_name
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*.py"):
            if should_check_file(filepath, exclude_patterns):
                files.append(filepath)

    return sorted(files)


def print_violation_summary(violations: List[Violation]) -> None:
    """Print summary of violations by rule."""
    by_rule: dict = {}
    for v in violations:
        by_rule.setdefault(v.rule, []).append(v)

    print("\n" + "=" * 60)
    print("VIOLATION SUMMARY")
    print("=" * 60)

    for rule, rule_violations in sorted(by_rule.items()):
        print(f"\n{rule}: {len(rule_violations)} violation(s)")
        for v in rule_violations[:5]:  # Show first 5
            print(f"  - {v.file}:{v.line}")
        if len(rule_violations) > 5:
            print(f"  ... and {len(rule_violations) - 5} more")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check logging invariants")
    parser.add_argument("--fix", action="store_true", help="Show suggested fixes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("Checking logging invariants...")
    print(f"Directories: {', '.join(CHECK_DIRS)}")

    files = get_files_to_check(CHECK_DIRS, EXCLUDE_PATTERNS)
    print(f"Files to check: {len(files)}")

    all_violations: List[Violation] = []

    for filepath in files:
        checker = LoggingInvariantChecker(filepath)
        violations = checker.check()
        all_violations.extend(violations)

        if args.verbose and violations:
            print(f"\n{filepath}: {len(violations)} violation(s)")
            for v in violations:
                print(f"  {v}")

    if all_violations:
        print(f"\n{'=' * 60}")
        print(f"FAILED: {len(all_violations)} logging invariant violation(s) found")
        print_violation_summary(all_violations)

        if args.fix:
            print("\n" + "=" * 60)
            print("SUGGESTED FIXES")
            print("=" * 60)
            print("""
NO_PRINT:
  Replace: print(message)
  With:    logger.info("event_name", message=message)

BARE_EXCEPT:
  Replace: except:
  With:    except (SpecificError1, SpecificError2) as e:
               logger.error("event_name", error=str(e))

GLOBAL_STRUCTLOG:
  Replace: logger = structlog.get_logger()
  With:    from avionics.logging import create_logger
           # In constructor:
           self._logger = logger or create_logger("component_name")
""")

        return 1

    print(f"\n{'=' * 60}")
    print("PASSED: All logging invariants satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
