"""ChatbotService — CapabilityService subclass for hello-world chatbot.

Kernel-driven 4-agent pipeline with conditional routing.
Memory is fail-forward: pipeline works without SQLite persistence.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from jeeves_core.runtime import CapabilityService, CapabilityResult
from jeeves_core.pipeline_worker import WorkerResult


class ChatbotService(CapabilityService):
    """Kernel-driven chatbot service for hello-world capability.

    Features:
    - 4-agent pipeline with conditional routing (kernel-driven)
    - SQLite-backed session state and message persistence
    - Fail-forward memory: pipeline works without DB
    """

    capability_id = "hello_world"

    def __init__(self, *, db=None, **kwargs):
        from jeeves_capability_hello_world.prompts import prompt_registry

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
            prompt_registry=prompt_registry, **kwargs
        )

    async def _ensure_ready(self):
        """Initialize SQLite schema and session state service (fail-forward)."""
        if self._db is None:
            return
        try:
            from jeeves_capability_hello_world.database.schema import (
                SESSION_STATE_DDL,
                MESSAGES_DDL,
                PIPELINE_SNAPSHOTS_DDL,
            )
            from jeeves_capability_hello_world.memory.services.session_state_service import (
                SessionStateService,
            )

            await self._db.connect()
            for ddl in [SESSION_STATE_DDL, MESSAGES_DDL, PIPELINE_SNAPSHOTS_DDL]:
                for stmt in ddl.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await self._db.execute(stmt)
            self._session_state = SessionStateService(db=self._db)
            self._snapshot_task = asyncio.create_task(self._snapshot_listener())
            self._logger.info("memory_initialized", backend="sqlite")
        except Exception as e:
            self._logger.error("memory_init_failed", error=str(e))
            self._db = None

    async def _snapshot_listener(self):
        """Subscribe to envelope.snapshot and persist."""
        try:
            async for event in self._kernel_client.subscribe_events(
                ["envelope.snapshot"], subscriber_id="hello-world-snapshots"
            ):
                await self._handle_snapshot(event)
        except asyncio.CancelledError:
            pass

    async def _handle_snapshot(self, event: dict):
        """Persist envelope snapshot to SQLite."""
        if self._db is None:
            return
        try:
            payload = event.get("payload", event)
            if isinstance(payload, str):
                payload = json.loads(payload)
            pid = payload.get("pid", "")
            trigger = payload.get("trigger", "")
            envelope = payload.get("envelope", {})
            await self._db.execute(
                "INSERT OR REPLACE INTO pipeline_snapshots (pid, trigger, snapshot, created_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (pid, trigger, json.dumps(envelope)),
            )
        except Exception as e:
            self._logger.error("snapshot_persist_failed", error=str(e))

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

    async def _on_result(self, worker_result, capability_result, *, raw_input="", session_id=""):
        """Persist user and assistant messages to SQLite."""
        if not self._db:
            return
        try:
            assistant_response = capability_result.response or ""
            now = datetime.now(timezone.utc).isoformat()

            await self._db.insert(
                "messages",
                {
                    "message_id": f"msg_{uuid4().hex[:12]}",
                    "session_id": session_id,
                    "role": "user",
                    "content": raw_input,
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
                session_id=session_id,
                error=str(e),
            )

    def _build_result(self, worker_result, request_id):
        """Convert WorkerResult to CapabilityResult with chatbot-specific metadata."""
        result = super()._build_result(worker_result, request_id)

        final = worker_result.outputs.get(self.output_key, {})
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
