"""PostgreSQL backend registration for capability layer.

Registers PostgreSQLClient as the 'postgres' database backend.
Called during capability startup (register_capability flow).
"""

from jeeves_infra.database.registry import register_backend, postgres_config_builder


def register_postgres_backend() -> None:
    """Register PostgreSQL as a database backend.

    Uses the config builder from airframe's registry module
    and the PostgreSQLClient from this capability's postgres package.
    """
    from jeeves_capability_hello_world.database.postgres.client import PostgreSQLClient

    register_backend("postgres", PostgreSQLClient, postgres_config_builder)
