"""
Stub adapter for OpenAI Chat Completions wire-compat.

TODO: implement when needed.
"""
from __future__ import annotations

from typing import AsyncIterator

from airframe.adapters.base import BackendAdapter
from airframe.endpoints import EndpointSpec
from airframe.types import InferenceRequest, InferenceStreamEvent


class OpenAIChatAdapter(BackendAdapter):
    async def stream_infer(
        self, endpoint: EndpointSpec, request: InferenceRequest
    ) -> AsyncIterator[InferenceStreamEvent]:
        raise NotImplementedError("OpenAIChatAdapter is not implemented yet")
