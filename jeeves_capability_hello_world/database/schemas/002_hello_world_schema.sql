-- =====================================================================
-- HELLO WORLD CAPABILITY - POSTGRESQL SCHEMA
-- =====================================================================
-- Schema owned by hello_world capability (per Avionics R3/R4).
-- Registered via CapabilityResourceRegistry.register_schema().
-- Dependencies: PostgreSQL 14+, pgvector extension
--
-- IMPORTANT: Run AFTER 001_postgres_schema.sql
-- =====================================================================

-- Enable required extensions (may already exist)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================
-- ADD COLUMNS TO EXISTING TABLES
-- =====================================================================

-- Add state column to sessions for conversation state storage
-- Uses DO block to be idempotent
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sessions' AND column_name = 'state'
    ) THEN
        ALTER TABLE sessions ADD COLUMN state JSONB DEFAULT '{}';
        COMMENT ON COLUMN sessions.state IS 'Conversation state for hello world (L4 working memory)';
    END IF;
END $$;

-- Add sources column to messages for web search citations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'sources'
    ) THEN
        ALTER TABLE messages ADD COLUMN sources JSONB;
        COMMENT ON COLUMN messages.sources IS 'Web search sources [{url, title, snippet}]';
    END IF;
END $$;

-- =====================================================================
-- NEW TABLES FOR HELLO WORLD
-- =====================================================================

-- Hello world event log (separate from main event_log to avoid conflicts)
CREATE TABLE IF NOT EXISTS hello_world_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,  -- References sessions(session_id)
    event_type TEXT NOT NULL,  -- 'tool_call', 'query', 'response'
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hello_world_events_session ON hello_world_events(session_id);
CREATE INDEX IF NOT EXISTS idx_hello_world_events_type ON hello_world_events(event_type);
CREATE INDEX IF NOT EXISTS idx_hello_world_events_created ON hello_world_events(created_at);

-- =====================================================================
-- TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- =====================================================================

-- Function to update updated_at timestamp (may already exist)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- HELPER FUNCTIONS FOR HELLO WORLD
-- =====================================================================

-- Get session state for hello world
CREATE OR REPLACE FUNCTION get_session_state(p_session_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_state JSONB;
BEGIN
    SELECT state INTO v_state
    FROM sessions
    WHERE session_id = p_session_id;

    RETURN COALESCE(v_state, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Save session state for hello world
CREATE OR REPLACE FUNCTION save_session_state(p_session_id UUID, p_state JSONB)
RETURNS VOID AS $$
BEGIN
    UPDATE sessions
    SET state = p_state, last_activity = NOW()
    WHERE session_id = p_session_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Session % not found', p_session_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Log a hello world event
CREATE OR REPLACE FUNCTION log_hello_world_event(
    p_session_id UUID,
    p_event_type TEXT,
    p_payload JSONB
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO hello_world_events (session_id, event_type, payload)
    VALUES (p_session_id, p_event_type, p_payload)
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================================

COMMENT ON TABLE hello_world_events IS 'Event log for hello world operations (L2)';

COMMENT ON FUNCTION get_session_state IS 'Get conversation state for a hello world session';
COMMENT ON FUNCTION save_session_state IS 'Save conversation state for a hello world session';
COMMENT ON FUNCTION log_hello_world_event IS 'Log an event to hello world audit trail';
