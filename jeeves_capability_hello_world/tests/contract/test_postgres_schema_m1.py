"""Postgres Schema Contract Tests for M1: Canonical State is Ground Truth

Structural tests extracted from airframe contract tests.
These tests query information_schema and are postgres-coupled.

Validates schema structure for:
- semantic_chunks table column requirements
- Referential integrity triggers for canonical sources

Reference: MEMORY_INFRASTRUCTURE_CONTRACT.md, Principle M1

Note: These tests require a postgres test_db fixture (to be set up in a future conftest).
"""

import pytest

# Requires PostgreSQL database
pytestmark = pytest.mark.requires_postgres


@pytest.mark.contract
class TestM1SchemaStructural:
    """Validate M1 schema structure via information_schema queries.

    These are postgres-coupled structural tests that verify the
    semantic_chunks table schema meets M1 contract requirements.
    """

    async def test_semantic_chunks_table_has_required_columns(self, test_db):
        """Semantic chunks table must have all required M1 columns.

        M1 Requirement: source_type, source_id for canonical reference

        Test Strategy:
        1. Query table schema
        2. Verify required columns exist
        """
        # Query table schema
        result = await test_db.fetch_all(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'semantic_chunks'
            ORDER BY ordinal_position
            """
        )

        # Convert to dict for easier assertion
        columns = {row["column_name"]: row for row in result}

        # Verify required M1 columns exist
        assert "source_type" in columns, "M1 violation: source_type column missing"
        assert "source_id" in columns, "M1 violation: source_id column missing"
        assert "embedding" in columns, "M1 violation: embedding column missing"

        # Verify source_type and source_id are NOT NULL
        assert columns["source_type"]["is_nullable"] == "NO", \
            "M1 violation: source_type should be NOT NULL"
        assert columns["source_id"]["is_nullable"] == "NO", \
            "M1 violation: source_id should be NOT NULL"


    async def test_referential_integrity_enforced_for_canonical_sources(self, test_db):
        """Referential integrity must be enforced for canonical source tables.

        M1 Requirement: "Embeddings must reference their source tables"

        Test Strategy:
        1. Check for triggers that enforce referential integrity
           (PostgreSQL doesn't support polymorphic FKs, so we use triggers)
        2. Verify the validation trigger exists on semantic_chunks
        """
        # Query for triggers on semantic_chunks that enforce source validation
        result = await test_db.fetch_all(
            """
            SELECT
                trigger_name,
                event_manipulation,
                action_timing
            FROM information_schema.triggers
            WHERE event_object_table = 'semantic_chunks'
                AND trigger_name LIKE '%check_semantic_chunk_source%'
            """
        )

        # Verify the referential integrity trigger exists
        assert len(result) > 0, \
            "M1 violation: No referential integrity enforcement on semantic_chunks. " \
            "Expected trigger 'trg_check_semantic_chunk_source' for polymorphic FK validation."

        # Also verify CASCADE delete triggers exist on canonical tables
        cascade_triggers = await test_db.fetch_all(
            """
            SELECT
                event_object_table,
                trigger_name
            FROM information_schema.triggers
            WHERE trigger_name LIKE '%cascade_delete%chunks%'
            """
        )

        # Should have cascade triggers for knowledge_facts (facts)
        trigger_tables = [t["event_object_table"] for t in cascade_triggers]
        assert "knowledge_facts" in trigger_tables, \
            "M1 violation: Missing CASCADE delete trigger on knowledge_facts table"
