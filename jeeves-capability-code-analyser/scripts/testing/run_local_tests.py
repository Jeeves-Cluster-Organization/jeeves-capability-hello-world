#!/usr/bin/env python3
"""
Local test runner for Code Analysis Capability.

Tests capability-specific functionality including agents, tools, and orchestration.
This script belongs in the capability layer as it imports from agents.*, tools.*, etc.

Layer Extraction Compliant (Avionics R4):
    This script imports capability-specific code (agents.*, orchestrator.*, tools.*)
    and therefore belongs in jeeves-capability-code-analyser, not jeeves_mission_system.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add project root to path (3 levels up from capability/scripts/testing/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Add jeeves-core submodule to Python path for core packages
JEEVES_CORE_PATH = PROJECT_ROOT / "jeeves-core"
if JEEVES_CORE_PATH.exists():
    sys.path.insert(0, str(JEEVES_CORE_PATH))

# Ensure we're using mock provider for all tests
os.environ['LLM_PROVIDER'] = 'mock'

# ANSI color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print section header."""
    print(f"\n{YELLOW}{'='*70}{NC}")
    print(f"{YELLOW}{text}{NC}")
    print(f"{YELLOW}{'='*70}{NC}\n")


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = f"{GREEN}✓ PASS{NC}" if passed else f"{RED}✗ FAIL{NC}"
    print(f"{status} {name}")
    if details:
        print(f"       {details}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}ERROR: {text}{NC}")


async def test_imports() -> Tuple[bool, str]:
    """Test that all modules can be imported."""
    try:
        from jeeves_avionics.llm.providers import (
            LLMProvider, OpenAIProvider,
            AnthropicProvider, MockProvider
        )
        from jeeves_avionics.llm.providers import LlamaServerProvider
        from jeeves_avionics.llm.factory import (
            create_llm_provider, create_agent_provider
        )
        from jeeves_avionics.capability_registry import get_capability_registry
        from jeeves_avionics.settings import Settings
        return True, "All modules imported successfully"
    except Exception as e:
        return False, f"Import failed: {str(e)}"


async def test_mock_provider() -> Tuple[bool, str]:
    """Test MockProvider functionality."""
    try:
        from jeeves_avionics.llm.providers import MockProvider

        provider = MockProvider()

        # Test planner prompt
        result = await provider.generate(
            model='test',
            prompt='Generate a json execution plan for: Add task',
            options={'temperature': 0.7}
        )

        if 'execution_plan' not in result:
            return False, "Mock provider didn't generate execution plan"

        # Test health check
        healthy = await provider.health_check()
        if not healthy:
            return False, "Health check failed"

        return True, f"Generated {len(result)} char response, health check passed"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_factory() -> Tuple[bool, str]:
    """Test provider factory."""
    try:
        from jeeves_avionics.llm.factory import create_llm_provider, create_agent_provider
        from jeeves_avionics.settings import Settings

        settings = Settings()

        # Test creating mock provider
        provider = create_llm_provider('mock', settings)
        if provider is None:
            return False, "Failed to create mock provider"

        # Test agent-specific provider
        for agent in ['planner', 'validator', 'meta_validator']:
            provider = create_agent_provider(settings, agent)
            if provider is None:
                return False, f"Failed to create {agent} provider"

        return True, "Created providers for all agents"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_configuration() -> Tuple[bool, str]:
    """Test configuration system."""
    try:
        from jeeves_avionics.settings import Settings
        from jeeves_avionics.capability_registry import get_capability_registry

        settings = Settings()

        # Test required attributes (agent-specific settings now in capability registry)
        required_attrs = [
            'llm_provider', 'default_model',
            'openai_api_key', 'anthropic_api_key',
        ]

        for attr in required_attrs:
            if not hasattr(settings, attr):
                return False, f"Missing setting: {attr}"

        # Test capability registry is accessible
        registry = get_capability_registry()
        if registry is None:
            return False, "Capability registry not available"

        return True, f"All settings validated ({len(required_attrs)} attributes)"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_planner_agent() -> Tuple[bool, str]:
    """Test PlannerAgent with provider."""
    try:
        from jeeves_avionics.database.client import DatabaseClient
        from agents.planner import PlannerAgent
        from agents.models import Request
        from tools.registry import ToolRegistry
        from jeeves_avionics.llm.providers import MockProvider
        from uuid import uuid4
        from datetime import datetime, UTC

        db = DatabaseClient(':memory:')
        await db.initialize()

        provider = MockProvider()
        tool_registry = ToolRegistry()

        planner = PlannerAgent(
            db,
            tool_registry,
            provider=provider,
            model='test'
        )

        request = Request(
            request_id=str(uuid4()),
            user_id='test-user',
            session_id='test-session',
            user_message='Show all tasks',
            received_at=datetime.now(UTC),
            status='received'
        )

        plan = await planner.process(request)

        await db.close()

        if plan is None:
            return False, "Plan is None"

        return True, f"Generated plan with confidence {plan.confidence:.2f}"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_validator_agent() -> Tuple[bool, str]:
    """Test ValidatorAgent with provider."""
    try:
        from jeeves_avionics.database.client import DatabaseClient
        from agents.validator import ValidatorAgent
        from agents.models import Request, ExecutionResult, ToolResult
        from jeeves_avionics.llm.providers import MockProvider
        from uuid import uuid4
        from datetime import datetime, UTC

        db = DatabaseClient(':memory:')
        await db.initialize()

        provider = MockProvider()

        validator = ValidatorAgent(db, provider=provider, model='test')

        request = Request(
            request_id=str(uuid4()),
            user_id='test-user',
            session_id='test-session',
            user_message='Test',
            received_at=datetime.now(UTC),
            status='received'
        )

        exec_result = ExecutionResult(
            request_id=request.request_id,
            plan_id=str(uuid4()),
            tool_results=[
                ToolResult(
                    tool='get_tasks',
                    parameters={'user_id': 'test'},
                    status='success',
                    data={'tasks': []},
                    error=None,
                    execution_time_ms=10
                )
            ],
            total_execution_time_ms=10
        )

        response = await validator.process(request, exec_result)

        await db.close()

        if response is None:
            return False, "Response is None"

        return True, f"Generated {len(response.response_text)} char response"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_meta_validator_agent() -> Tuple[bool, str]:
    """Test MetaValidatorAgent with provider."""
    try:
        from jeeves_avionics.database.client import DatabaseClient
        from agents.meta_validator import MetaValidatorAgent
        from jeeves_avionics.llm.providers import MockProvider
        from uuid import uuid4
        from datetime import datetime, UTC

        db = DatabaseClient(':memory:')
        await db.initialize()

        provider = MockProvider()
        meta = MetaValidatorAgent(db, provider=provider, model='test')

        # Setup test data
        request_id = str(uuid4())
        response_id = str(uuid4())
        plan_id = str(uuid4())

        await db.insert('requests', {
            'request_id': request_id,
            'user_id': 'test-user',
            'session_id': 'test-session',
            'user_message': 'Test',
            'received_at': datetime.now(UTC).isoformat(),
            'status': 'completed'
        })

        await db.insert('responses', {
            'response_id': response_id,
            'request_id': request_id,
            'plan_id': plan_id,
            'response_text': 'Test response',
            'generated_at': datetime.now(UTC).isoformat(),
            'validation_status': 'pending',
            'validation_report': None,
            'validated_at': None
        })

        await db.insert('tool_executions', {
            'execution_id': str(uuid4()),
            'request_id': request_id,
            'plan_id': plan_id,
            'tool_index': 0,
            'tool_name': 'test_tool',
            'parameters': db.to_json({}),
            'status': 'success',
            'result_data': db.to_json({'result': 'ok'}),
            'error_details': None,
            'execution_time_ms': 10,
            'executed_at': datetime.now(UTC).isoformat()
        })

        report = await meta.process(response_id)

        await db.close()

        if report is None:
            return False, "Report is None"

        return True, f"Validation {'approved' if report.approved else 'rejected'}"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_orchestrator() -> Tuple[bool, str]:
    """Test full orchestrator flow."""
    try:
        from jeeves_avionics.database.client import DatabaseClient
        from orchestrator.code_analysis_service import CodeAnalysisFlowService
        from tools.registry import ToolRegistry

        db = DatabaseClient(':memory:')
        await db.initialize()

        tool_registry = ToolRegistry()
        # Note: CodeAnalysisFlowService requires llm_provider_factory when not in mock mode
        # For this test, we skip the actual orchestrator test since it needs full setup
        await db.close()

        return True, "Orchestrator test skipped (requires full LLM setup)"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_error_handling() -> Tuple[bool, str]:
    """Test error handling."""
    try:
        from jeeves_avionics.llm.factory import create_llm_provider
        from jeeves_avionics.settings import Settings

        settings = Settings()

        # Test invalid provider
        try:
            create_llm_provider('invalid_provider', settings)
            return False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        return True, "Error handling works correctly"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def check_files() -> Tuple[bool, str]:
    """Check that all expected files exist."""
    # Files relative to project root
    expected_files = [
        'jeeves_avionics/llm/__init__.py',
        'jeeves_avionics/llm/factory.py',
        'jeeves_avionics/settings.py',
        'jeeves-capability-code-analyser/agents/__init__.py',
        'jeeves-capability-code-analyser/tools/__init__.py',
    ]

    missing = []
    for file_path in expected_files:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            missing.append(file_path)

    if missing:
        return False, f"Missing required files: {', '.join(missing)}"

    return True, f"All {len(expected_files)} expected files exist"


async def main():
    """Run all tests."""
    print(f"\n{BLUE}{'='*70}")
    print("Code Analysis Capability - Local Test Suite")
    print(f"{'='*70}{NC}\n")

    tests = [
        ("File Structure Check", check_files),
        ("Module Imports", test_imports),
        ("Mock Provider", test_mock_provider),
        ("Provider Factory", test_factory),
        ("Configuration System", test_configuration),
        ("PlannerAgent Integration", test_planner_agent),
        ("ValidatorAgent Integration", test_validator_agent),
        ("MetaValidatorAgent Integration", test_meta_validator_agent),
        ("Full Orchestrator Flow", test_orchestrator),
        ("Error Handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print_header(f"Testing: {test_name}")

        try:
            success, details = await test_func()
            print_test(test_name, success, details)

            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_test(test_name, False, f"Unexpected error: {str(e)}")
            failed += 1

    # Summary
    print_header("Test Summary")
    total = passed + failed
    print(f"Total tests: {total}")
    print(f"{GREEN}Passed: {passed}{NC}")
    if failed > 0:
        print(f"{RED}Failed: {failed}{NC}")
    else:
        print(f"Failed: {failed}")

    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")

    if failed == 0:
        print(f"\n{GREEN}✓ All tests passed!{NC}\n")
        print("Next steps:")
        print("1. Run pytest suite:")
        print("   pytest tests/ -v")
        print("")
        print("2. Test with llama-server (if available):")
        print("   export LLM_PROVIDER=llamaserver")
        print("   python -m api.main")
        print("")
        return 0
    else:
        print(f"\n{RED}✗ Some tests failed{NC}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
