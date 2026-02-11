"""SQLite database client for hello-world capability.

Implements DatabaseClientProtocol using aiosqlite.
Promoted from jeeves-airframe/tests/fixtures/sqlite_client.py with production hardening.
"""

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

DEFAULT_DB_PATH = "./data/hello_world.db"


class SQLiteClient:
    """SQLite database client satisfying DatabaseClientProtocol."""

    def __init__(self, database_path: Optional[str] = None, **kwargs):
        self.database_path = database_path or os.getenv(
            "JEEVES_SQLITE_PATH", DEFAULT_DB_PATH
        )
        self._db: Optional[aiosqlite.Connection] = None
        self._in_transaction = False

    @property
    def backend(self) -> str:
        return "sqlite"

    @property
    def is_connected(self) -> bool:
        return self._db is not None

    async def connect(self) -> None:
        if self._db is not None:
            return  # idempotent
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute("PRAGMA journal_mode = WAL")

    async def disconnect(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def execute(self, query: str, params=None) -> None:
        q, p = self._convert_params(query, params)
        await self._db.execute(q, p)
        if not self._in_transaction:
            await self._db.commit()

    async def fetch_one(self, query: str, params=None) -> Optional[Dict[str, Any]]:
        q, p = self._convert_params(query, params)
        cursor = await self._db.execute(q, p)
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetch_all(self, query: str, params=None) -> List[Dict[str, Any]]:
        q, p = self._convert_params(query, params)
        cursor = await self._db.execute(q, p)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def insert(self, table: str, data: Dict[str, Any]) -> None:
        cols = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        await self._db.execute(query, data)
        if not self._in_transaction:
            await self._db.commit()

    async def update(self, table: str, data: Dict[str, Any], where_clause: str, where_params=None) -> int:
        set_clause = ", ".join(f"{k} = :_set_{k}" for k in data.keys())
        params = {f"_set_{k}": v for k, v in data.items()}

        if where_params and isinstance(where_params, (list, tuple)):
            idx = [0]
            def _replacer(_m):
                name = f"_w{idx[0]}"
                idx[0] += 1
                return f":{name}"
            named_where = re.sub(r'\?', _replacer, where_clause)
            for i, val in enumerate(where_params):
                params[f"_w{i}"] = val
        else:
            named_where = where_clause

        query = f"UPDATE {table} SET {set_clause} WHERE {named_where}"
        cursor = await self._db.execute(query, params)
        if not self._in_transaction:
            await self._db.commit()
        return cursor.rowcount

    async def upsert(self, table: str, data: Dict[str, Any], key_columns: List[str]) -> None:
        cols = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        update_cols = [k for k in data.keys() if k not in key_columns]
        set_clause = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        if set_clause:
            query += f" ON CONFLICT ({', '.join(key_columns)}) DO UPDATE SET {set_clause}"
        await self._db.execute(query, data)
        if not self._in_transaction:
            await self._db.commit()

    async def initialize_schema(self, schema_path: str) -> None:
        sql = Path(schema_path).read_text(encoding="utf-8")
        await self._db.executescript(sql)

    @asynccontextmanager
    async def transaction(self):
        await self._db.execute("BEGIN")
        self._in_transaction = True
        try:
            yield self
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise
        finally:
            self._in_transaction = False

    # -- internals --

    def _convert_params(self, query, params):
        if params is None:
            return query, []
        if isinstance(params, dict):
            return query, params
        return query, list(params)
