"""Mock settings for testing.

Constitutional Reference:
    - Agent-specific LLM settings are now in capability registry
    - Settings only contains generic infrastructure config
    - See: avionics/capability_registry.py
"""

from typing import Optional


class MockSettings:
    """Mock settings implementing SettingsProtocol for testing.

    Provides sensible defaults for infrastructure settings.
    Agent-specific configs should be registered with capability registry.
    """

    def __init__(
        self,
        *,
        default_model: str = "mock-model",
        default_temperature: Optional[float] = 0.3,
        disable_temperature: bool = True,
        llm_provider: str = "mock",
        llm_timeout: int = 30,
        llm_max_retries: int = 3,
        llamaserver_host: str = "http://localhost:8080",
        llamaserver_api_type: str = "native",
    ):
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._disable_temperature = disable_temperature
        self._llm_provider = llm_provider
        self._llm_timeout = llm_timeout
        self._llm_max_retries = llm_max_retries
        self._llamaserver_host = llamaserver_host
        self._llamaserver_api_type = llamaserver_api_type

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def default_temperature(self) -> Optional[float]:
        return self._default_temperature

    @property
    def disable_temperature(self) -> bool:
        return self._disable_temperature

    @property
    def llm_provider(self) -> str:
        return self._llm_provider

    @property
    def llm_timeout(self) -> int:
        return self._llm_timeout

    @property
    def llm_max_retries(self) -> int:
        return self._llm_max_retries

    @property
    def llamaserver_host(self) -> str:
        return self._llamaserver_host

    @property
    def llamaserver_api_type(self) -> str:
        return self._llamaserver_api_type
