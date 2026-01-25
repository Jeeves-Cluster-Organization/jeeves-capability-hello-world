"""Tests for jeeves-capability-code-analyser app.

This test suite is organized by layer:
- tests/unit/ - Unit tests for app components (agents, tools)
- tests/integration/ - Integration tests for app workflows
- tests/fixtures/ - Shared test fixtures

Constitutional compliance:
- All tests import from mission_system.contracts (not jeeves_core_engine)
- Tests use mission_system.adapters for infrastructure access
- No tests bypass layer boundaries
"""
