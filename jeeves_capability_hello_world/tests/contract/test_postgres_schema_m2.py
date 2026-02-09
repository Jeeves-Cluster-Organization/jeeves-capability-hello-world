"""Postgres Schema Contract Tests for M2: Events Are Immutable History

Structural tests extracted from airframe contract tests.
These tests query information_schema and are postgres-coupled.

Validates schema structure for:
- domain_events table existence and column requirements
- Primary key constraints
- Timestamp defaults

Reference: MEMORY_INFRASTRUCTURE_CONTRACT.md, Principle M2

Note: These tests require a postgres test_db fixture (to be set up in a future conftest).
"""

import pytest

# Requires PostgreSQL database
pytestmark = pytest.mark.requires_postgres


@pytest.mark.contract
class TestM2SchemaStructural:
    """Validate M2 schema structure via information_schema queries.

    These are postgres-coupled structural tests that verify the
    domain_events table schema meets M2 contract requirements.
    """

    async def test_domain_events_table_exists(self, test_db):
        """domain_events table must exist for event sourcing.

        M2 Requirement: "Event log is append-only"

        Test Strategy:
        1. Query table existence
        2. Verify table has required columns
        """
        # Query table existence
        result = await test_db.fetch_one(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'domain_events'
            """
        )

        assert result is not None, \
            "M2 violation: domain_events table does not exist"


    async def test_domain_events_have_immutable_timestamps(self, test_db):
        """Events must have TIMESTAMPTZ for ordering.

        M2 Requirement: "Events have immutable timestamps"

        Test Strategy:
        1. Query column schema
        2. Verify timestamp column is TIMESTAMPTZ (not TIMESTAMP)
        """
        # Query timestamp column type
        result = await test_db.fetch_one(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'domain_events'
                AND column_name IN ('occurred_at', 'timestamp', 'event_timestamp')
            """
        )

        # Verify timestamp column exists and is TIMESTAMPTZ
        assert result is not None, \
            "M2 violation: domain_events table missing timestamp column"

        # PostgreSQL reports 'timestamp with time zone' for TIMESTAMPTZ
        assert "time zone" in result["data_type"].lower(), \
            f"M2 violation: Timestamp column is {result['data_type']}, should be TIMESTAMPTZ"


    async def test_domain_events_has_required_columns(self, test_db):
        """domain_events table must have all required M2 columns.

        M2 Requirements:
        - event_id (unique identifier)
        - event_type (what happened)
        - aggregate_id (which entity)
        - aggregate_type (entity type)
        - occurred_at (TIMESTAMPTZ)
        - user_id (who triggered)
        - payload (event data)

        Test Strategy:
        1. Query table schema
        2. Verify required columns exist
        """
        # Query table schema
        result = await test_db.fetch_all(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'domain_events'
            ORDER BY ordinal_position
            """
        )

        # Convert to dict for easier assertion
        columns = {row["column_name"]: row for row in result}

        # Verify required M2 columns exist
        required_columns = [
            "event_id", "event_type", "aggregate_id",
            "aggregate_type", "user_id", "payload"
        ]

        for col in required_columns:
            assert col in columns, f"M2 violation: {col} column missing from domain_events"

        # Verify timestamp column exists (may be named occurred_at, timestamp, etc.)
        timestamp_cols = [c for c in columns.keys()
                         if "timestamp" in c.lower() or "occurred" in c.lower()]
        assert len(timestamp_cols) > 0, \
            "M2 violation: domain_events missing timestamp column"


    async def test_event_id_is_primary_key(self, test_db):
        """event_id must be primary key for uniqueness.

        M2 Requirement: Events are uniquely identifiable

        Test Strategy:
        1. Query constraint metadata
        2. Verify event_id is primary key
        """
        # Query primary key constraints
        result = await test_db.fetch_all(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'domain_events'
                AND tc.constraint_type = 'PRIMARY KEY'
            """
        )

        # Verify event_id is in primary key
        pk_columns = [row["column_name"] for row in result]
        assert "event_id" in pk_columns, \
            "M2 violation: event_id is not primary key"


    async def test_occurred_at_has_default_now(self, test_db):
        """occurred_at should default to NOW() for automatic timestamping.

        M2 Requirement: Immutable timestamps

        Test Strategy:
        1. Query column default
        2. Verify default is NOW() or CURRENT_TIMESTAMP
        """
        # Query column default
        result = await test_db.fetch_one(
            """
            SELECT column_name, column_default
            FROM information_schema.columns
            WHERE table_name = 'domain_events'
                AND column_name IN ('occurred_at', 'timestamp', 'event_timestamp')
            """
        )

        if result is not None:
            # Check if default is NOW() or CURRENT_TIMESTAMP
            default = result.get("column_default", "")
            if default:
                default_lower = default.lower()
                has_default = "now()" in default_lower or "current_timestamp" in default_lower
                assert has_default, \
                    f"M2 warning: occurred_at default is '{default}', consider NOW() or CURRENT_TIMESTAMP"
