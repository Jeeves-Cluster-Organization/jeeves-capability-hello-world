"""Capability-local serialization utilities for datetime, JSON, and UUID handling."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from uuid import UUID


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse a datetime value from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    return None


class JSONEncoderWithUUID(json.JSONEncoder):
    """JSON encoder that handles UUID and datetime objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def to_json(data: Any) -> str:
    """Convert Python object to JSON string with UUID/datetime support."""
    return json.dumps(data, cls=JSONEncoderWithUUID)


def from_json(json_str: Optional[Union[str, Dict, list]]) -> Any:
    """Convert JSON string to Python object, passing through dicts/lists."""
    if json_str is None:
        return None
    if isinstance(json_str, (dict, list)):
        return json_str
    return json.loads(json_str)
