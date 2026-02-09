"""PostgreSQL backend registration for capability layer.

Registers PostgreSQLClient as the 'postgres' database backend.
Called during capability startup (register_capability flow).
"""

from typing import Any, Dict

from jeeves_infra.database.registry import register_backend


def postgres_config_builder(settings: Any, logger: Any) -> Dict[str, Any]:
    """Build PostgreSQL client configuration from settings.

    Reads generic db_* fields from Settings and builds
    the postgres-specific connection config.
    """
    database_url = (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )
    return {
        "database_url": database_url,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
        "logger": logger,
    }


# pgvector dimension (capability-owned, not in airframe settings)
PGVECTOR_DIMENSION = 384


def register_postgres_backend() -> None:
    """Register PostgreSQL as a database backend.

    Owns the config builder that translates generic db_* settings
    into PostgreSQL-specific connection parameters.
    """
    from jeeves_capability_hello_world.database.postgres.client import PostgreSQLClient

    register_backend("postgres", PostgreSQLClient, postgres_config_builder)
