from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .endpoints import EndpointSpec, HealthState


class HealthProbe(ABC):
    @abstractmethod
    async def check(self, endpoint: EndpointSpec) -> HealthState:
        ...


class HttpHealthProbe(HealthProbe):
    """
    Basic placeholder; extend with real probing later.
    """
    async def check(self, endpoint: EndpointSpec) -> HealthState:
        return HealthState(status="unknown", detail="not implemented")
