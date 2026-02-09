"""Database implementations owned by this capability.

Capabilities own the actual database — schemas, concrete persistence,
what to store. Airframe provides protocol-based abstractions only.
"""

from jeeves_capability_hello_world.database.postgres.config import register_postgres_backend

__all__ = ["register_postgres_backend"]
