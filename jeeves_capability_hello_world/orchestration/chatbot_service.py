"""ChatbotService — CapabilityService subclass for hello-world chatbot.

Kernel-driven 4-agent pipeline with conditional routing.
Memory is fail-forward: pipeline works without SQLite persistence.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from jeeves_core.runtime import CapabilityService, CapabilityResult
from jeeves_core.pipeline_worker import WorkerResult
from jeeves_core.protocols import Envelope


class ChatbotService(CapabilityService):
    """Kernel-driven chatbot service for hello-world capability.

    Features:
    - 4-agent pipeline with conditional routing (kernel-driven)
    - SQLite-backed session state and message persistence
    - Fail-forward memory: pipeline works without DB
    """

    capability_id = "hello_world"

    def __init__(self, *, db=None, **kwargs):
        from jeeves_capability_hello_world.prompts.registry import PromptRegistry

        self._db = db
        self._session_state = None

        # If no persistence provided but we have a raw DB, wrap it
        if kwargs.get("persistence") is None and db is not None:
            import json
            from jeeves_core.runtime.persistence import DatabasePersistence

            kwargs["persistence"] = DatabasePersistence(
                db, encode=json.dumps, decode=json.loads
            )

        super().__init__(
            prompt_registry=PromptRegistry.get_instance(), **kwargs
        )

    async def _ensure_ready(self):
        """Initialize SQLite schema and session state service (fail-forward)."""
        if self._db is None:
            return
        try:
            from jeeves_capability_hello_world.database.schema import (
                SESSION_STATE_DDL,
                MESSAGES_DDL,
            )
            from jeeves_capability_hello_world.memory.services.session_state_service import (
                SessionStateService,
            )

            await self._db.connect()
            for ddl in [SESSION_STATE_DDL, MESSAGES_DDL]:
                for stmt in ddl.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await self._db.execute(stmt)
            self._session_state = SessionStateService(db=self._db)
            self._logger.info("memory_initialized", backend="sqlite")
        except Exception as e:
            self._logger.error("memory_init_failed", error=str(e))
            self._db = None

    async def _enrich_metadata(self, meta, message, user_id, session_id):
        """Inject session context into envelope metadata."""
        if not self._session_state:
            return
        try:
            await self._session_state.get_or_create(session_id, user_id)
            await self._session_state.on_user_turn(session_id, message)
            meta["session_context"] = (
                await self._session_state.get_context_for_prompt(session_id)
            )
        except Exception as e:
            self._logger.warning("session_state_load_failed", error=str(e))

    async def _on_result(self, worker_result, capability_result, envelope):
        """Persist user and assistant messages to SQLite."""
        if not self._db:
            return
        try:
            session_id = envelope.session_id
            user_message = envelope.raw_input
            assistant_response = capability_result.response or ""
            now = datetime.now(timezone.utc).isoformat()

            await self._db.insert(
                "messages",
                {
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "session_id": session_id,
                    "role": "user",
                    "content": user_message,
                    "created_at": now,
                },
            )
            if assistant_response:
                await self._db.insert(
                    "messages",
                    {
                        "message_id": f"msg_{uuid4().hex[:12]}",
                        "session_id": session_id,
                        "role": "assistant",
                        "content": assistant_response,
                        "created_at": now,
                    },
                )
        except Exception as e:
            self._logger.error(
                "message_persist_failed",
                session_id=envelope.session_id,
                error=str(e),
            )

    def _build_result(self, worker_result, request_id):
        """Convert WorkerResult to CapabilityResult with chatbot-specific metadata."""
        result = super()._build_result(worker_result, request_id)

        final = worker_result.envelope.outputs.get(self.output_key, {})
        if result.status == "success":
            result.metadata["citations"] = final.get("citations") or None
            result.metadata["confidence"] = final.get("confidence", "medium")

        # Bounds exits get low confidence
        reason = worker_result.terminal_reason
        bounds_reasons = {
            "MAX_ITERATIONS_EXCEEDED",
            "MAX_LLM_CALLS_EXCEEDED",
            "MAX_AGENT_HOPS_EXCEEDED",
            "MAX_STAGE_VISITS_EXCEEDED",
        }
        if reason in bounds_reasons and result.status == "success":
            result.metadata["confidence"] = "low"

        return result


__all__ = ["ChatbotService"]
