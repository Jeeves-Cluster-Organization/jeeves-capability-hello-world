"""SQLite schema definitions for hello-world capability.

Two tables: session_state (L4 working memory) and messages (conversation persistence).
"""

SESSION_STATE_DDL = """
CREATE TABLE IF NOT EXISTS session_state (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    focus_type TEXT,
    focus_id TEXT,
    focus_context TEXT,
    referenced_entities TEXT,
    short_term_memory TEXT,
    turn_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_session_state_user ON session_state(user_id);
"""

MESSAGES_DDL = """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""
