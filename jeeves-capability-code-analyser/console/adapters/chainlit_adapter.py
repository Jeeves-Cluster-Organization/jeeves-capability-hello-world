"""Chainlit adapter - subscribes to CommBus, renders in Chainlit UI.

This adapter uses only Chainlit's public API:
- cl.Step for agent lifecycle
- cl.Message for responses
- cl.AskUserMessage for clarifications

No Chainlit internals are accessed or modified.
"""

from typing import Dict
import chainlit as cl

from control_tower.ipc import get_commbus
from console.messages import ProcessQuery, SubmitClarification, GetSystemStatus, ConsoleEvent


class ChainlitAdapter:
    """Thin adapter between CommBus and Chainlit UI."""

    def __init__(self):
        self.bus = get_commbus()
        self.active_steps: Dict[str, cl.Step] = {}
        self.session_id: str = ""

    async def start(self, session_id: str):
        """Subscribe to console events for this session."""
        self.session_id = session_id
        await self.bus.subscribe("console.*", self._handle_event)

    async def send_query(self, query: str, user_id: str):
        """Send query via CommBus."""
        await self.bus.query(ProcessQuery(
            query=query,
            session_id=self.session_id,
            user_id=user_id,
        ))

    async def send_clarification(self, thread_id: str, clarification: str):
        """Submit clarification via CommBus."""
        await self.bus.query(SubmitClarification(
            thread_id=thread_id,
            clarification=clarification,
        ))

    async def get_status(self) -> Dict:
        """Get system status via CommBus."""
        return await self.bus.query(GetSystemStatus())

    async def _handle_event(self, event: ConsoleEvent):
        """Render ConsoleEvent in Chainlit UI."""
        # Filter events for this session
        if event.session_id and event.session_id != self.session_id:
            return

        event_type = event.event_type

        # Agent started - create step
        if event_type.endswith(".started"):
            step = cl.Step(name=event.agent_name or "agent", type="run")
            await step.send()
            if event.agent_name:
                self.active_steps[event.agent_name] = step

        # Agent completed - update step
        elif event_type.endswith(".completed") or event_type.endswith(".decision"):
            agent_name = event.agent_name
            if agent_name and agent_name in self.active_steps:
                step = self.active_steps.pop(agent_name)
                step.output = event.content or ""
                await step.update()

        # Tool events
        elif event_type == "console.tool.started":
            tool_name = event.metadata.get("tool_name", "tool")
            step = cl.Step(name=tool_name, type="tool")
            await step.send()
            self.active_steps[f"tool_{tool_name}"] = step

        elif event_type == "console.tool.completed":
            tool_name = event.metadata.get("tool_name", "tool")
            key = f"tool_{tool_name}"
            if key in self.active_steps:
                step = self.active_steps.pop(key)
                step.output = event.content or ""
                await step.update()

        # Final response
        elif event_type == "console.response":
            await cl.Message(content=event.content or "").send()

        # Clarification needed
        elif event_type == "console.clarification":
            thread_id = event.metadata.get("thread_id", "")
            res = await cl.AskUserMessage(
                content=event.content or "Could you clarify?",
                timeout=300,
            ).send()
            if res:
                await self.send_clarification(thread_id, res["output"])

        # Error
        elif event_type == "console.error":
            await cl.Message(
                content=f"Error: {event.content}",
                author="system",
            ).send()


__all__ = ["ChainlitAdapter"]
