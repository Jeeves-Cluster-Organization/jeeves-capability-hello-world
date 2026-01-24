import asyncio

import pytest

from airframe.endpoints import EndpointSpec, BackendKind
from airframe.registry import StaticRegistry


@pytest.mark.asyncio
async def test_static_registry_watch_once():
    ep = EndpointSpec(
        name="local",
        base_url="http://localhost:8080",
        backend_kind=BackendKind.LLAMA_SERVER,
    )
    registry = StaticRegistry([ep])

    called = asyncio.Event()

    async def cb(snapshot):
        assert snapshot[0].name == "local"
        called.set()

    handle = registry.watch(cb)
    await asyncio.wait_for(called.wait(), timeout=1.0)
    handle.cancel()
