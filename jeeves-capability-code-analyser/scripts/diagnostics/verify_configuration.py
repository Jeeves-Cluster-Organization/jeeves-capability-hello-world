#!/usr/bin/env python3
"""
Verify Code Analysis Capability configuration settings.

This script verifies that agents are properly configured with correct settings
including temperature, models, providers, and other configuration parameters.

Layer Extraction Compliant (Avionics R4):
    This script imports capability-specific code (agents.*, tools.*)
    and therefore belongs in jeeves-capability-code-analyser, not jeeves_mission_system.

Usage:
    python scripts/diagnostics/verify_configuration.py [--check CHECK_TYPE]

Examples:
    # Verify all configuration
    python scripts/diagnostics/verify_configuration.py

    # Verify temperature settings only
    python scripts/diagnostics/verify_configuration.py --check temperature

    # Verify LLM provider configuration
    python scripts/diagnostics/verify_configuration.py --check providers
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path (3 levels up from capability/scripts/diagnostics/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Add jeeves-core submodule to Python path for core packages
JEEVES_CORE_PATH = PROJECT_ROOT / "jeeves-core"
if JEEVES_CORE_PATH.exists():
    sys.path.insert(0, str(JEEVES_CORE_PATH))


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70 + "\n")


def print_success(text: str):
    """Print success message."""
    print(f"  ✓ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"  ✗ {text}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


async def verify_temperature_configuration() -> Tuple[bool, List[str]]:
    """Verify that all agents correctly handle temperature configuration."""
    from jeeves_avionics.settings import get_settings
    from jeeves_avionics.database.client import DatabaseClient
    from tools.registry import ToolRegistry
    from jeeves_avionics.llm.factory import create_agent_provider

    print_header("AGENT TEMPERATURE CONFIGURATION VERIFICATION")

    settings = get_settings()
    db = DatabaseClient(settings.database_path)
    await db.connect()

    agents_to_test = [
        ("planner", "PlannerAgent"),
        ("validator", "ValidatorAgent"),
        ("critic", "CriticAgent"),
        ("meta_validator", "MetaValidatorAgent"),
    ]

    print_info(f"Global Setting: DISABLE_TEMPERATURE = {settings.disable_temperature}")
    print()

    all_passed = True
    errors = []

    for agent_name, agent_class in agents_to_test:
        try:
            # Get the temperature setting for this agent
            temp_attr = f"{agent_name}_temperature"
            if hasattr(settings, temp_attr):
                temp_value = getattr(settings, temp_attr)
                if settings.disable_temperature:
                    expected = None
                else:
                    expected = temp_value
            else:
                expected = None

            print(f"[{agent_class}]")
            print_info(f"Expected temperature: {expected}")

            # Create the agent
            provider = create_agent_provider(settings, agent_name)

            # Import and instantiate the agent to check its temperature attribute
            if agent_name == "planner":
                from agents.planner import PlannerAgent
                tool_registry = ToolRegistry(db)
                agent = PlannerAgent(db, tool_registry, provider)
            elif agent_name == "validator":
                from agents.validator import ValidatorAgent
                agent = ValidatorAgent(db, provider)
            elif agent_name == "critic":
                from agents.critic import CriticAgent
                agent = CriticAgent(db, provider)
            elif agent_name == "meta_validator":
                from agents.meta_validator import MetaValidatorAgent
                agent = MetaValidatorAgent(db, provider)

            actual = agent.temperature if hasattr(agent, 'temperature') else "NOT SET"

            print_info(f"Actual temperature: {actual}")

            if actual == expected:
                print_success("PASS")
            else:
                print_error(f"FAIL (expected {expected}, got {actual})")
                errors.append(f"{agent_class}: expected {expected}, got {actual}")
                all_passed = False

            print()

        except Exception as e:
            print_error(f"ERROR - {e}")
            errors.append(f"{agent_class}: {str(e)}")
            all_passed = False
            print()

    await db.disconnect()

    return all_passed, errors


async def verify_provider_configuration() -> Tuple[bool, List[str]]:
    """Verify LLM provider configuration."""
    from jeeves_avionics.settings import get_settings

    print_header("LLM PROVIDER CONFIGURATION VERIFICATION")

    settings = get_settings()
    all_passed = True
    errors = []

    # Check global provider
    print("[Global Configuration]")
    print_info(f"LLM Provider: {settings.llm_provider}")
    print_info(f"Default Model: {settings.default_model}")
    print()

    # Check per-agent configuration
    agents = ['planner', 'validator', 'meta_validator', 'critic']

    for agent_name in agents:
        print(f"[{agent_name.capitalize()}]")

        # Get provider
        provider_attr = f"{agent_name}_llm_provider"
        if hasattr(settings, provider_attr):
            provider = getattr(settings, provider_attr)
            print_info(f"Provider: {provider}")
        else:
            print_info(f"Provider: {settings.llm_provider} (default)")

        # Get model
        try:
            model_method = f"get_{agent_name}_model"
            if hasattr(settings, model_method):
                model = getattr(settings, model_method)()
                print_info(f"Model: {model}")
            else:
                print_info(f"Model: {settings.default_model} (default)")

            print_success("Configuration OK")
        except Exception as e:
            print_error(f"Configuration error: {e}")
            errors.append(f"{agent_name}: {str(e)}")
            all_passed = False

        print()

    return all_passed, errors


async def verify_feature_flags() -> Tuple[bool, List[str]]:
    """Verify feature flag configuration."""
    from config.feature_flags import get_feature_flags

    print_header("FEATURE FLAGS VERIFICATION")

    flags = get_feature_flags()
    all_passed = True
    errors = []

    flag_list = [
        ('use_llm_gateway', 'LLM Gateway'),
        ('use_redis_state', 'Redis State'),
        ('use_graph_engine', 'Graph Engine'),
        ('enable_checkpoints', 'Checkpoints'),
        ('enable_distributed_mode', 'Distributed Mode'),
    ]

    for flag_name, description in flag_list:
        if hasattr(flags, flag_name):
            value = getattr(flags, flag_name)
            status = "ENABLED" if value else "DISABLED"
            print_info(f"{description}: {status}")
        else:
            print_error(f"{description}: NOT FOUND")
            errors.append(f"Missing flag: {flag_name}")
            all_passed = False

    print()
    return all_passed, errors


async def verify_database_configuration() -> Tuple[bool, List[str]]:
    """Verify PostgreSQL database configuration and connectivity."""
    from jeeves_avionics.settings import get_settings
    from jeeves_avionics.database.postgres_client import PostgreSQLClient

    print_header("DATABASE CONFIGURATION VERIFICATION")

    settings = get_settings()
    all_passed = True
    errors = []

    print_info(f"PostgreSQL Host: {settings.postgres_host}:{settings.postgres_port}")
    print_info(f"PostgreSQL Database: {settings.postgres_database}")

    # Try to connect
    try:
        client = PostgreSQLClient(
            database_url=settings.get_postgres_url(),
            pool_size=2,
            max_overflow=0,
        )
        await client.connect()

        # Check some tables exist
        result = await client.fetch_one(
            "SELECT COUNT(*) AS count FROM pg_tables WHERE schemaname = 'public'"
        )
        table_count = result.get('count', 0) if result else 0

        if table_count > 0:
            print_success(f"Connected successfully ({table_count} tables)")
        else:
            print_error("No tables found - run init_db.py")
            errors.append("No tables in database")
            all_passed = False

        await client.disconnect()
    except Exception as e:
        print_error(f"Connection failed: {e}")
        errors.append(f"Database connection error: {str(e)}")
        all_passed = False

    print()
    return all_passed, errors


async def verify_all_configuration() -> bool:
    """Run all configuration verifications."""
    all_results = []
    all_errors = []

    # Temperature configuration
    passed, errors = await verify_temperature_configuration()
    all_results.append(("Temperature Configuration", passed))
    all_errors.extend(errors)

    # Provider configuration
    passed, errors = await verify_provider_configuration()
    all_results.append(("Provider Configuration", passed))
    all_errors.extend(errors)

    # Feature flags
    passed, errors = await verify_feature_flags()
    all_results.append(("Feature Flags", passed))
    all_errors.extend(errors)

    # Database configuration
    passed, errors = await verify_database_configuration()
    all_results.append(("Database Configuration", passed))
    all_errors.extend(errors)

    # Print summary
    print_header("VERIFICATION SUMMARY")

    all_passed = True
    for check_name, passed in all_results:
        if passed:
            print_success(f"{check_name}")
        else:
            print_error(f"{check_name}")
            all_passed = False

    if all_passed:
        print()
        print("=" * 70)
        print("✓ ALL CONFIGURATION CHECKS PASSED")
        print("=" * 70)
    else:
        print()
        print("=" * 70)
        print("✗ SOME CONFIGURATION CHECKS FAILED")
        print("=" * 70)
        print("\nErrors:")
        for error in all_errors:
            print(f"  - {error}")

    return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Code Analysis Capability configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--check',
        choices=['temperature', 'providers', 'flags', 'database', 'all'],
        default='all',
        help='Type of configuration to verify (default: all)'
    )

    args = parser.parse_args()

    if args.check == 'temperature':
        success, _ = asyncio.run(verify_temperature_configuration())
    elif args.check == 'providers':
        success, _ = asyncio.run(verify_provider_configuration())
    elif args.check == 'flags':
        success, _ = asyncio.run(verify_feature_flags())
    elif args.check == 'database':
        success, _ = asyncio.run(verify_database_configuration())
    else:  # all
        success = asyncio.run(verify_all_configuration())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
