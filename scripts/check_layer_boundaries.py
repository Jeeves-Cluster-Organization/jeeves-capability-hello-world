#!/usr/bin/env python3
"""CI Check: Layer Boundary Enforcement.

This script enforces the Jeeves layer architecture invariants:
- L0 (jeeves_protocols, jeeves_shared): imports nothing from higher layers
- L1 (jeeves_control_tower): imports only from L0
- L2 (jeeves_memory_module): imports only from L0
- L3 (jeeves_avionics): imports from L0, L1, L2
- L4 (jeeves_mission_system): imports from L0, L1, L2, L3

See jeeves-core/docs/CONTRACTS.md for layer architecture diagram.

Run as part of CI to prevent layer violations.

Usage:
    python scripts/check_layer_boundaries.py
    python scripts/check_layer_boundaries.py --verbose  # Show all imports
    python scripts/check_layer_boundaries.py --fix      # Show suggested fixes

Exit codes:
    0: All checks pass
    1: Violations found
"""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

# Layer definitions (order matters - higher index = higher layer)
LAYERS: Dict[str, int] = {
    "jeeves_protocols": 0,
    "jeeves_shared": 0,
    "jeeves_control_tower": 1,
    "jeeves_memory_module": 2,
    "jeeves_avionics": 3,
    "jeeves_mission_system": 4,
}

# Allowed imports per layer (can only import from layers with LOWER or EQUAL numbers)
# Exception: L0 packages (jeeves_protocols, jeeves_shared) can import from each other
LAYER_RULES: Dict[str, List[str]] = {
    "jeeves_protocols": ["jeeves_shared"],  # L0: can use shared utilities
    "jeeves_shared": ["jeeves_protocols"],  # L0: can use protocols
    "jeeves_control_tower": ["jeeves_protocols", "jeeves_shared"],  # L1
    "jeeves_memory_module": ["jeeves_protocols", "jeeves_shared"],  # L2
    "jeeves_avionics": [
        "jeeves_protocols",
        "jeeves_shared",
        "jeeves_control_tower",
        "jeeves_memory_module",
    ],  # L3
    "jeeves_mission_system": [
        "jeeves_protocols",
        "jeeves_shared",
        "jeeves_control_tower",
        "jeeves_memory_module",
        "jeeves_avionics",
    ],  # L4
}

# Base directory for jeeves-core packages
JEEVES_CORE_DIR = Path("jeeves-core")

# Files/patterns to exclude
EXCLUDE_PATTERNS = [
    "**/tests/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/conftest.py",
    "**/__pycache__/**",
]


@dataclass
class Violation:
    """A single layer boundary violation."""
    file: Path
    line: int
    import_module: str
    importing_layer: str
    imported_layer: str
    message: str

    def __str__(self) -> str:
        return (
            f"{self.file}:{self.line}: [LAYER_VIOLATION] "
            f"{self.importing_layer} (L{LAYERS.get(self.importing_layer, '?')}) "
            f"imports {self.imported_layer} (L{LAYERS.get(self.imported_layer, '?')})"
        )


class LayerBoundaryChecker:
    """AST-based checker for layer boundary violations."""

    def __init__(self, filepath: Path, source_layer: str):
        self.filepath = filepath
        self.source_layer = source_layer
        self.violations: List[Violation] = []
        self.allowed_imports = LAYER_RULES.get(source_layer, [])

    def check(self) -> List[Violation]:
        """Run layer boundary check on the file."""
        try:
            content = self.filepath.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(self.filepath))
        except SyntaxError:
            return []
        except Exception:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import(alias.name, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import(node.module, node.lineno)

        return self.violations

    def _check_import(self, module_name: str, lineno: int) -> None:
        """Check if an import violates layer boundaries."""
        # Extract the base package (e.g., "jeeves_avionics" from "jeeves_avionics.tools")
        base_package = module_name.split(".")[0]

        # Only check jeeves_* imports
        if not base_package.startswith("jeeves_"):
            return

        # Skip self-imports
        if base_package == self.source_layer:
            return

        # Check if this import is allowed
        if base_package in LAYERS and base_package not in self.allowed_imports:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=lineno,
                    import_module=module_name,
                    importing_layer=self.source_layer,
                    imported_layer=base_package,
                    message=f"Layer violation: {self.source_layer} cannot import {base_package}",
                )
            )


def get_layer_for_file(filepath: Path) -> Optional[str]:
    """Determine which layer a file belongs to."""
    # Get path relative to jeeves-core
    try:
        relative = filepath.relative_to(JEEVES_CORE_DIR)
    except ValueError:
        # File not under jeeves-core
        return None

    # First part of path is the package
    parts = relative.parts
    if not parts:
        return None

    package = parts[0]
    if package in LAYERS:
        return package

    return None


def should_check_file(filepath: Path, exclude_patterns: List[str]) -> bool:
    """Determine if a file should be checked."""
    if not filepath.suffix == ".py":
        return False

    # Check exclusion patterns
    for pattern in exclude_patterns:
        if filepath.match(pattern):
            return False

    return True


def get_files_to_check() -> List[tuple]:
    """Get all Python files to check with their layer."""
    files = []

    if not JEEVES_CORE_DIR.exists():
        print(f"Warning: {JEEVES_CORE_DIR} not found, checking current directory")
        base_dir = Path.cwd()
    else:
        base_dir = JEEVES_CORE_DIR

    for layer in LAYERS.keys():
        layer_dir = base_dir / layer
        if not layer_dir.exists():
            continue

        for filepath in layer_dir.rglob("*.py"):
            if should_check_file(filepath, EXCLUDE_PATTERNS):
                files.append((filepath, layer))

    return sorted(files, key=lambda x: (x[1], x[0]))


def print_violation_summary(violations: List[Violation]) -> None:
    """Print summary of violations by layer pair."""
    by_pair: Dict[tuple, List[Violation]] = {}
    for v in violations:
        pair = (v.importing_layer, v.imported_layer)
        by_pair.setdefault(pair, []).append(v)

    print("\n" + "=" * 70)
    print("VIOLATION SUMMARY")
    print("=" * 70)

    for (src, dst), pair_violations in sorted(by_pair.items()):
        src_level = LAYERS.get(src, "?")
        dst_level = LAYERS.get(dst, "?")
        print(f"\n{src} (L{src_level}) -> {dst} (L{dst_level}): {len(pair_violations)} violation(s)")
        for v in pair_violations[:5]:  # Show first 5
            print(f"  - {v.file}:{v.line}: import {v.import_module}")
        if len(pair_violations) > 5:
            print(f"  ... and {len(pair_violations) - 5} more")


def print_layer_diagram() -> None:
    """Print the layer architecture diagram."""
    print("""
Layer Architecture (see docs/CONTRACTS.md):

+-------------------------------------------------------------------+
| L4: jeeves_mission_system                                         |
|     (API layer - orchestration, services, adapters)               |
+-------------------------------------------------------------------+
| L3: jeeves_avionics                                               |
|     (Infrastructure - LLM, DB, Gateway, Observability)            |
+-------------------------------------------------------------------+
| L2: jeeves_memory_module                                          |
|     (Event sourcing, semantic memory, repositories)               |
+-------------------------------------------------------------------+
| L1: jeeves_control_tower                                          |
|     (OS-like kernel - process lifecycle, resources, IPC)          |
+-------------------------------------------------------------------+
| L0: jeeves_shared, jeeves_protocols                               |
|     (Zero dependencies - types, utilities, protocols)             |
+-------------------------------------------------------------------+

Import Rules:
  - Higher layers may import from lower layers
  - Lower layers MUST NOT import from higher layers
  - Same-layer imports are allowed
""")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check layer boundary violations in Jeeves codebase"
    )
    parser.add_argument("--fix", action="store_true", help="Show suggested fixes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--diagram", action="store_true", help="Show layer diagram")
    args = parser.parse_args()

    if args.diagram:
        print_layer_diagram()
        return 0

    print("Checking layer boundaries...")
    print(f"Layers: {', '.join(LAYERS.keys())}")

    files = get_files_to_check()
    print(f"Files to check: {len(files)}")

    all_violations: List[Violation] = []
    files_by_layer: Dict[str, int] = {}

    for filepath, layer in files:
        files_by_layer[layer] = files_by_layer.get(layer, 0) + 1
        checker = LayerBoundaryChecker(filepath, layer)
        violations = checker.check()
        all_violations.extend(violations)

        if args.verbose and violations:
            print(f"\n{filepath}:")
            for v in violations:
                print(f"  Line {v.line}: imports {v.import_module}")

    print("\nFiles by layer:")
    for layer, count in sorted(files_by_layer.items()):
        level = LAYERS.get(layer, "?")
        print(f"  L{level} {layer}: {count} files")

    if all_violations:
        print(f"\n{'=' * 70}")
        print(f"FAILED: {len(all_violations)} layer boundary violation(s) found")
        print_violation_summary(all_violations)

        if args.fix:
            print("\n" + "=" * 70)
            print("SUGGESTED FIXES")
            print("=" * 70)
            print("""
Option 1: Move the import to an allowed layer
  - If jeeves_control_tower needs DB access, use jeeves_protocols interfaces

Option 2: Extract to jeeves_protocols
  - If multiple layers need a type, define it in L0 (jeeves_protocols)

Option 3: Use dependency injection
  - Instead of importing concrete implementations, accept protocols

Example fix for ControlTower importing from Avionics:
  BEFORE: from avionics.database import PostgresClient
  AFTER:  from protocols import DatabaseClientProtocol
          # Inject concrete client at runtime
""")

        # Print all violations for debugging
        print("\nAll violations:")
        for v in all_violations:
            print(f"  {v}")

        return 1

    print(f"\n{'=' * 70}")
    print("PASSED: All layer boundaries respected")
    return 0


if __name__ == "__main__":
    sys.exit(main())

