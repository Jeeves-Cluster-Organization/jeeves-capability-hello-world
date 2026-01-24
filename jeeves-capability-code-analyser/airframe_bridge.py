"""
Airframe bridge for the code analysis capability.

This keeps capability ownership of selection policy while reusing the
jeezes-airframe platform for endpoint representation and invocation.
"""

from typing import Callable, Optional

from airframe import (
    AirframeClient,
    InferenceRequest,
    InferenceStreamEvent,
    Message,
    StaticRegistry,
    EndpointSpec,
    BackendKind,
    StreamEventType,
)
import structlog
from airframe_settings import is_airframe_debug


class AirframeLLMProvider:
    """
    Minimal LLM provider wrapper that matches the runtime's expected interface:
    async generate(model: str, prompt: str, options: dict) -> str
    """

    def __init__(
        self,
        client: AirframeClient,
        registry: StaticRegistry,
        agent_role: str,
        endpoint_selector: Optional[Callable[[str], EndpointSpec]] = None,
    ):
        self.client = client
        self.registry = registry
        self.agent_role = agent_role
        self.endpoint_selector = endpoint_selector or self._default_selector
        self._logger = structlog.get_logger()

    def _default_selector(self, agent_role: str) -> EndpointSpec:
        endpoints = self.registry.list_endpoints()
        if not endpoints:
            raise RuntimeError("Airframe registry returned no endpoints")
        return endpoints[0]

    async def generate(self, model: str, prompt: str, options: dict) -> str:
        # Build inference request
        req = InferenceRequest(
            messages=[Message(role="user", content=prompt)],
            model=model or None,
            temperature=options.get("temperature"),
            max_tokens=options.get("num_predict"),
            stream=True,
        )

        endpoint = self.endpoint_selector(self.agent_role)
        output_chunks = []

        if is_airframe_debug():
            self._logger.debug(
                "airframe_llm_provider_generate",
                agent_role=self.agent_role,
                endpoint=endpoint.name,
                base_url=endpoint.base_url,
            )

        async for event in self.client.stream_infer(endpoint, req):
            if event.type == StreamEventType.TOKEN:
                output_chunks.append(event.content or "")
            elif event.type == StreamEventType.MESSAGE:
                output_chunks.append(event.content or "")
            elif event.type == StreamEventType.ERROR:
                raise event.error or RuntimeError("Airframe inference error")
            elif event.type == StreamEventType.DONE:
                break

        return "".join(output_chunks)


def create_airframe_registry_from_env() -> StaticRegistry:
    base_url = os.getenv("LLAMASERVER_HOST", "http://localhost:8080")
    api_type = os.getenv("LLAMASERVER_API_TYPE", "native")
    endpoint = EndpointSpec(
        name="default-llama",
        base_url=base_url,
        backend_kind=BackendKind.LLAMA_SERVER,
        api_type=api_type,
    )
    return StaticRegistry([endpoint])


def create_airframe_llm_factory(registry: StaticRegistry) -> Callable[[str], AirframeLLMProvider]:
    client = AirframeClient(registry)

    def factory(agent_role: str) -> AirframeLLMProvider:
        return AirframeLLMProvider(client=client, registry=registry, agent_role=agent_role)

    return factory
