from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Iterable, List, Optional

from .endpoints import EndpointSpec, HealthState


class WatchHandle:
    def __init__(self, task: Optional[asyncio.Task] = None):
        self._task = task

    def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()


class EndpointRegistry(ABC):
    @abstractmethod
    def list_endpoints(self) -> List[EndpointSpec]:
        ...

    @abstractmethod
    def get_health(self, name: str) -> Optional[HealthState]:
        ...

    @abstractmethod
    def watch(
        self, callback: Callable[[List[EndpointSpec]], Awaitable[None]]
    ) -> WatchHandle:
        """
        Callback receives the full snapshot when changes occur.
        """
        ...


class StaticRegistry(EndpointRegistry):
    def __init__(self, endpoints: Iterable[EndpointSpec]):
        self._endpoints = list(endpoints)
        self._health = {e.name: HealthState(status="unknown") for e in self._endpoints}

    def list_endpoints(self) -> List[EndpointSpec]:
        return list(self._endpoints)

    def get_health(self, name: str) -> Optional[HealthState]:
        return self._health.get(name)

    def watch(
        self, callback: Callable[[List[EndpointSpec]], Awaitable[None]]
    ) -> WatchHandle:
        async def fire_once():
            await callback(self.list_endpoints())

        task = asyncio.create_task(fire_once())
        return WatchHandle(task)
