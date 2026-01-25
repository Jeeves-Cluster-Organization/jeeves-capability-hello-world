-- =====================================================================
-- CODE ANALYSIS CAPABILITY - POSTGRESQL SCHEMA
-- =====================================================================
-- Schema owned by code_analysis capability (per Avionics R3/R4).
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

-- Add state column to sessions for TraversalState storage
-- Uses DO block to be idempotent
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sessions' AND column_name = 'state'
    ) THEN
        ALTER TABLE sessions ADD COLUMN state JSONB DEFAULT '{}';
        COMMENT ON COLUMN sessions.state IS 'TraversalState for code analysis (L4 working memory)';
    END IF;
END $$;

-- Add citations column to messages for code analysis
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'citations'
    ) THEN
        ALTER TABLE messages ADD COLUMN citations JSONB;
        COMMENT ON COLUMN messages.citations IS 'Code citations [{file_path, start_line, end_line}]';
    END IF;
END $$;

-- =====================================================================
-- NEW TABLES FOR CODE ANALYSIS
-- =====================================================================

-- Code index for RAG search
CREATE TABLE IF NOT EXISTS code_index (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    language TEXT,
    size_bytes INTEGER,
    line_count INTEGER,
    last_indexed TIMESTAMPTZ DEFAULT NOW(),
    embedding vector(384),
    user_id TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_code_index_path ON code_index(file_path);
CREATE INDEX IF NOT EXISTS idx_code_index_hash ON code_index(content_hash);
CREATE INDEX IF NOT EXISTS idx_code_index_language ON code_index(language);

-- Vector index for code search
CREATE INDEX IF NOT EXISTS idx_code_index_embedding_cosine
ON code_index USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON TABLE code_index IS 'Code file index for RAG-based semantic search';

-- Code understanding cache - stores LLM-generated insights
CREATE TABLE IF NOT EXISTS code_understanding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_path TEXT NOT NULL,
    pattern_key TEXT NOT NULL,  -- 'architecture', 'test_style', 'api_patterns', etc.
    understanding TEXT,         -- LLM-generated description
    confidence FLOAT,           -- Confidence score 0-1
    evidence JSONB,             -- File paths and excerpts supporting this understanding
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_path, pattern_key)
);

CREATE INDEX IF NOT EXISTS idx_code_understanding_repo ON code_understanding(repo_path);
CREATE INDEX IF NOT EXISTS idx_code_understanding_pattern ON code_understanding(pattern_key);

-- Code analysis event log (separate from main event_log to avoid conflicts)
CREATE TABLE IF NOT EXISTS code_analysis_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,  -- References sessions(session_id)
    event_type TEXT NOT NULL,  -- 'tool_call', 'traversal_step', 'query', 'response'
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_code_analysis_events_session ON code_analysis_events(session_id);
CREATE INDEX IF NOT EXISTS idx_code_analysis_events_type ON code_analysis_events(event_type);
CREATE INDEX IF NOT EXISTS idx_code_analysis_events_created ON code_analysis_events(created_at);

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

-- Apply trigger to code_understanding table
DROP TRIGGER IF EXISTS update_code_understanding_updated_at ON code_understanding;
CREATE TRIGGER update_code_understanding_updated_at
    BEFORE UPDATE ON code_understanding
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================================
-- HELPER FUNCTIONS FOR CODE ANALYSIS
-- =====================================================================

-- Get session state for code analysis
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

-- Save session state for code analysis
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

-- Log a code analysis event
CREATE OR REPLACE FUNCTION log_code_analysis_event(
    p_session_id UUID,
    p_event_type TEXT,
    p_payload JSONB
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO code_analysis_events (session_id, event_type, payload)
    VALUES (p_session_id, p_event_type, p_payload)
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================================

COMMENT ON TABLE code_index IS 'Code file index for RAG-based semantic search';
COMMENT ON TABLE code_understanding IS 'LLM-generated code insights cache';
COMMENT ON TABLE code_analysis_events IS 'Event log for code analysis operations (L2)';

COMMENT ON FUNCTION get_session_state IS 'Get TraversalState for a code analysis session';
COMMENT ON FUNCTION save_session_state IS 'Save TraversalState for a code analysis session';
COMMENT ON FUNCTION log_code_analysis_event IS 'Log an event to code analysis audit trail';
