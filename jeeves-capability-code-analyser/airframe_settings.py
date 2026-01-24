from __future__ import annotations

import os


_TRUE = {"1", "true", "yes"}
_FALSE = {"0", "false", "no"}


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    lowered = val.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    return default


def is_airframe_enabled() -> bool:
    return _env_bool("AIRFRAME_ENABLED", True)


def is_airframe_strict() -> bool:
    return _env_bool("AIRFRAME_STRICT", False)


def is_airframe_debug() -> bool:
    return _env_bool("AIRFRAME_DEBUG", False)
