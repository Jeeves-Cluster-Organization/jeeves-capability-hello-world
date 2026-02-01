#!/usr/bin/env python3
"""CI Check: Layer Boundary Enforcement.

This script enforces the Jeeves layer architecture invariants:
- L0 (jeeves_infra.protocols): Zero dependencies, type definitions
- L1 (Go kernel): Process lifecycle, resources - accessed via KernelClient (gRPC)
- L2 (jeeves_infra.memory): Event sourcing, semantic memory - imports L0 only
- L3 (jeeves_infra): Infrastructure - LLM, DB, Gateway - imports L0, L2
- L4 (mission_system): API layer - orchestration, services - imports L0, L2, L3

Note: L1 is implemented in Go (jeeves-core/coreengine/kernel/). Python code
accesses it via jeeves_infra.kernel_client (gRPC bridge), which is part of L3.

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

# =============================================================================
# Layer Definitions
# =============================================================================
# The Jeeves architecture uses a layered approach where higher layers can
# import from lower layers, but not vice versa.
#
# Note: L1 (kernel) is implemented in Go and accessed via gRPC. The Python
# KernelClient is part of L3 (jeeves_infra) and provides the bridge.
# =============================================================================

# Layer definitions (order matters - higher index = higher layer)
# Format: "package_name": layer_number
LAYERS: Dict[str, int] = {
    # L0: Zero dependencies - protocols and shared utilities
    "jeeves_infra.protocols": 0,
    "jeeves_infra.utils": 0,

    # L2: Memory module (L1 is Go kernel, not Python)
    "jeeves_infra.memory": 2,

    # L3: Infrastructure layer
    "jeeves_infra": 3,

    # L4: API/Mission layer
    "mission_system": 4,
}

# Mapping from import prefixes to their layer
# This handles the fact that jeeves_infra has sub-packages at different layers
LAYER_MAPPING: Dict[str, int] = {
    "jeeves_infra.protocols": 0,
    "jeeves_infra.utils": 0,
    "jeeves_infra.memory": 2,
    "jeeves_infra": 3,  # Catch-all for other jeeves_infra imports
    "mission_system": 4,
}

# Allowed imports per layer
LAYER_RULES: Dict[str, List[str]] = {
    # L0: Can import from other L0 packages
    "jeeves_infra.protocols": ["jeeves_infra.utils"],
    "jeeves_infra.utils": ["jeeves_infra.protocols"],

    # L2: Can import from L0
    "jeeves_infra.memory": [
        "jeeves_infra.protocols",
        "jeeves_infra.utils",
    ],

    # L3: Can import from L0, L2
    "jeeves_infra": [
        "jeeves_infra.protocols",
        "jeeves_infra.utils",
        "jeeves_infra.memory",
    ],

    # L4: Can import from L0, L2, L3
    "mission_system": [
        "jeeves_infra.protocols",
        "jeeves_infra.utils",
        "jeeves_infra.memory",
        "jeeves_infra",
    ],
}

# Base directory for Python packages (jeeves-airframe submodule)
JEEVES_AIRFRAME_DIR = Path("jeeves-airframe")

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
        importing_level = get_layer_level(self.importing_layer)
        imported_level = get_layer_level(self.imported_layer)
        return (
            f"{self.file}:{self.line}: [LAYER_VIOLATION] "
            f"{self.importing_layer} (L{importing_level}) "
            f"imports {self.imported_layer} (L{imported_level})"
        )


def get_layer_level(layer_name: str) -> int:
    """Get the layer level for a package name."""
    return LAYERS.get(layer_name, -1)


def get_layer_for_import(module_name: str) -> Optional[str]:
    """Determine which layer an import belongs to.

    Handles nested packages by checking most specific first.
    """
    # Check from most specific to least specific
    for prefix in sorted(LAYER_MAPPING.keys(), key=len, reverse=True):
        if module_name.startswith(prefix):
            return prefix
    return None


def get_layer_for_file(filepath: Path) -> Optional[str]:
    """Determine which layer a file belongs to based on its path."""
    # Try to get path relative to jeeves-airframe
    try:
        relative = filepath.relative_to(JEEVES_AIRFRAME_DIR)
    except ValueError:
        return None

    parts = relative.parts
    if not parts:
        return None

    # Build the module path and find the matching layer
    if parts[0] == "jeeves_infra":
        if len(parts) > 1:
            if parts[1] == "protocols":
                return "jeeves_infra.protocols"
            elif parts[1] == "utils":
                return "jeeves_infra.utils"
            elif parts[1] == "memory":
                return "jeeves_infra.memory"
        return "jeeves_infra"
    elif parts[0] == "mission_system":
        return "mission_system"

    return None


class LayerBoundaryChecker:
    """AST-based checker for layer boundary violations."""

    def __init__(self, filepath: Path, source_layer: str):
        self.filepath = filepath
        self.source_layer = source_layer
        self.violations: List[Violation] = []
        self.allowed_imports = LAYER_RULES.get(source_layer, [])
        self.source_level = get_layer_level(source_layer)

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
        # Only check jeeves_infra and mission_system imports
        if not (module_name.startswith("jeeves_infra") or
                module_name.startswith("mission_system")):
            return

        # Determine the layer of the imported module
        imported_layer = get_layer_for_import(module_name)
        if imported_layer is None:
            return

        # Skip self-imports (same layer)
        if imported_layer == self.source_layer:
            return

        # Skip if importing from a sub-package of the same base layer
        if self.source_layer.startswith(imported_layer) or imported_layer.startswith(self.source_layer):
            # More specific check: is the imported layer level <= source level?
            imported_level = get_layer_level(imported_layer)
            if imported_level <= self.source_level:
                return

        # Check if this import is allowed
        imported_level = get_layer_level(imported_layer)

        # Allow imports from lower layers
        if imported_level < self.source_level:
            return

        # Check explicit allow list
        is_allowed = False
        for allowed in self.allowed_imports:
            if module_name.startswith(allowed) or imported_layer == allowed:
                is_allowed = True
                break

        if not is_allowed and imported_level >= self.source_level:
            self.violations.append(
                Violation(
                    file=self.filepath,
                    line=lineno,
                    import_module=module_name,
                    importing_layer=self.source_layer,
                    imported_layer=imported_layer,
                    message=f"Layer violation: {self.source_layer} cannot import {imported_layer}",
                )
            )


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

    if not JEEVES_AIRFRAME_DIR.exists():
        print(f"Warning: {JEEVES_AIRFRAME_DIR} not found")
        return files

    # Check jeeves_infra
    jeeves_infra_dir = JEEVES_AIRFRAME_DIR / "jeeves_infra"
    if jeeves_infra_dir.exists():
        for filepath in jeeves_infra_dir.rglob("*.py"):
            if should_check_file(filepath, EXCLUDE_PATTERNS):
                layer = get_layer_for_file(filepath)
                if layer:
                    files.append((filepath, layer))

    # Check mission_system
    mission_system_dir = JEEVES_AIRFRAME_DIR / "mission_system"
    if mission_system_dir.exists():
        for filepath in mission_system_dir.rglob("*.py"):
            if should_check_file(filepath, EXCLUDE_PATTERNS):
                layer = get_layer_for_file(filepath)
                if layer:
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
        src_level = get_layer_level(src)
        dst_level = get_layer_level(dst)
        print(f"\n{src} (L{src_level}) -> {dst} (L{dst_level}): {len(pair_violations)} violation(s)")
        for v in pair_violations[:5]:  # Show first 5
            print(f"  - {v.file}:{v.line}: import {v.import_module}")
        if len(pair_violations) > 5:
            print(f"  ... and {len(pair_violations) - 5} more")


def print_layer_diagram() -> None:
    """Print the layer architecture diagram."""
    print("""
Jeeves Layer Architecture:

┌─────────────────────────────────────────────────────────────────┐
│ L4: mission_system (jeeves-airframe/mission_system/)            │
│     API layer - orchestration, services, capabilities           │
├─────────────────────────────────────────────────────────────────┤
│ L3: jeeves_infra (jeeves-airframe/jeeves_infra/)                │
│     Infrastructure - LLM, DB, Gateway, Tools, KernelClient      │
├─────────────────────────────────────────────────────────────────┤
│ L2: jeeves_infra.memory (jeeves-airframe/jeeves_infra/memory/)  │
│     Event sourcing, semantic search, session state              │
├─────────────────────────────────────────────────────────────────┤
│ L1: Go Kernel (jeeves-core/coreengine/kernel/) [NOT PYTHON]     │
│     Process lifecycle, resources, orchestration                 │
│     Python access via: KernelClient (gRPC) in L3                │
├─────────────────────────────────────────────────────────────────┤
│ L0: jeeves_infra.protocols, jeeves_infra.utils                  │
│     Zero dependencies - types, protocols, shared utilities      │
└─────────────────────────────────────────────────────────────────┘

Import Rules:
  - Higher layers may import from lower layers
  - Lower layers MUST NOT import from higher layers
  - Same-layer imports are allowed
  - L1 is Go code, accessed via KernelClient (gRPC bridge in L3)

Legacy naming (deprecated):
  - avionics      -> jeeves_infra
  - control_tower -> Go kernel (jeeves-core/coreengine/kernel/)
  - memory_module -> jeeves_infra.memory
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
    print(f"Checking in: {JEEVES_AIRFRAME_DIR}")

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
    for layer, count in sorted(files_by_layer.items(), key=lambda x: get_layer_level(x[0])):
        level = get_layer_level(layer)
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
  - If jeeves_infra.memory needs DB access, use protocols interfaces

Option 2: Extract to protocols
  - If multiple layers need a type, define it in L0 (jeeves_infra.protocols)

Option 3: Use dependency injection
  - Instead of importing concrete implementations, accept protocols

Example fix for memory importing from infra:
  BEFORE: from jeeves_infra.database import PostgresClient
  AFTER:  from jeeves_infra.protocols import DatabaseClientProtocol
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
