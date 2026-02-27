"""
Session State Service for In-Dialogue Working Memory.

Manages session state with direct SQLite access:
- Session lifecycle management
- Focus tracking across conversations
- Entity reference management
- Short-term memory coordination
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import UUID
import json

from jeeves_core.protocols import LoggerProtocol, DatabaseClientProtocol


class SessionState:
    """Represents the current state of a user session."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        focus_type: Optional[str] = None,
        focus_id: Optional[str] = None,
        focus_context: Optional[Dict[str, Any]] = None,
        referenced_entities: Optional[List[Dict[str, str]]] = None,
        short_term_memory: Optional[str] = None,
        turn_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.focus_type = focus_type
        self.focus_id = focus_id
        self.focus_context = focus_context or {}
        self.referenced_entities = referenced_entities or []
        self.short_term_memory = short_term_memory
        self.turn_count = turn_count
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "focus_type": self.focus_type,
            "focus_id": self.focus_id,
            "focus_context": self.focus_context,
            "referenced_entities": self.referenced_entities,
            "short_term_memory": self.short_term_memory,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse a datetime value from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    return None


def _row_to_session_state(row: Dict[str, Any]) -> SessionState:
    """Convert a database row to SessionState."""
    focus_context = row.get("focus_context")
    if isinstance(focus_context, str):
        focus_context = json.loads(focus_context) if focus_context else {}

    referenced_entities = row.get("referenced_entities")
    if isinstance(referenced_entities, str):
        referenced_entities = json.loads(referenced_entities) if referenced_entities else []

    session_id = row["session_id"]
    if isinstance(session_id, UUID):
        session_id = str(session_id)

    user_id = row["user_id"]
    if isinstance(user_id, UUID):
        user_id = str(user_id)

    return SessionState(
        session_id=session_id,
        user_id=user_id,
        focus_type=row.get("focus_type"),
        focus_id=row.get("focus_id"),
        focus_context=focus_context,
        referenced_entities=referenced_entities,
        short_term_memory=row.get("short_term_memory"),
        turn_count=row.get("turn_count", 0),
        created_at=_parse_datetime(row.get("created_at")),
        updated_at=_parse_datetime(row.get("updated_at")),
    )


class SessionStateService:
    """Service for managing session state with direct DB access."""

    _GET_QUERY = """
        SELECT session_id, user_id, focus_type, focus_id,
               focus_context, referenced_entities, short_term_memory,
               turn_count, created_at, updated_at
        FROM session_state
        WHERE session_id = ?
    """

    def __init__(
        self,
        db: DatabaseClientProtocol,
        logger: Optional[LoggerProtocol] = None,
    ):
        self.db = db
        self._logger = logger

    async def get(self, session_id: str) -> Optional[SessionState]:
        row = await self.db.fetch_one(self._GET_QUERY, (session_id,))
        if not row:
            return None
        return _row_to_session_state(row)

    async def _upsert(self, state: SessionState) -> SessionState:
        state.updated_at = datetime.now(timezone.utc)
        data = {
            "session_id": state.session_id,
            "user_id": state.user_id,
            "focus_type": state.focus_type,
            "focus_id": state.focus_id,
            "focus_context": json.dumps(state.focus_context) if state.focus_context else None,
            "referenced_entities": json.dumps(state.referenced_entities) if state.referenced_entities else None,
            "short_term_memory": state.short_term_memory,
            "turn_count": state.turn_count,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }
        await self.db.upsert("session_state", data, key_columns=["session_id"])
        return state

    async def get_or_create(self, session_id: str, user_id: str) -> SessionState:
        existing = await self.get(session_id)
        if existing:
            return existing
        new_state = SessionState(
            session_id=session_id,
            user_id=user_id,
            focus_type="general",
            turn_count=0,
        )
        await self._upsert(new_state)
        return new_state

    async def on_user_turn(self, session_id: str, user_message: str) -> Optional[SessionState]:
        state = await self.get(session_id)
        if not state:
            return None
        state.turn_count += 1
        return await self._upsert(state)

    async def get_context_for_prompt(self, session_id: str) -> Dict[str, Any]:
        state = await self.get(session_id)
        if not state:
            return {}
        context: Dict[str, Any] = {
            "turn_count": state.turn_count,
            "focus": {
                "type": state.focus_type,
                "id": state.focus_id,
                "context": state.focus_context,
            } if state.focus_type else None,
        }
        if state.referenced_entities:
            context["recent_entities"] = state.referenced_entities[-5:]
        if state.short_term_memory:
            context["conversation_summary"] = state.short_term_memory
        return context

    async def delete(self, session_id: str) -> bool:
        result = await self.db.execute(
            "DELETE FROM session_state WHERE session_id = ?", (session_id,)
        )
        return result is not None


__all__ = ["SessionStateService", "SessionState"]
