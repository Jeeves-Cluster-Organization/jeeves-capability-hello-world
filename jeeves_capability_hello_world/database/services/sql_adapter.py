"""
SQL database adapter for memory operations.

Capability-owned: table names, type mappings, and domain behavior
are defined here. Airframe provides only DatabaseClientProtocol.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from jeeves_capability_hello_world._logging import get_component_logger
from jeeves_infra.protocols import LoggerProtocol, DatabaseClientProtocol


def _convert_uuids_to_strings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert UUID objects to strings in a dictionary."""
    return {k: str(v) if isinstance(v, UUID) else v for k, v in data.items()}


class SQLAdapter:
    """Handles SQL database operations for memory.

    Capability-owned: table names and type-to-table mappings
    are defined here, not in airframe.
    """

    # Capability defines type-to-table mappings
    TYPE_TO_TABLE = {
        'fact': 'knowledge_facts',
        'message': 'messages',
    }

    # ID column per table
    TABLE_ID_COLUMN = {
        'knowledge_facts': 'fact_id',
        'messages': 'message_id',
    }

    def __init__(self, db_client: DatabaseClientProtocol, logger: Optional[LoggerProtocol] = None):
        """
        Initialize SQL adapter.

        Args:
            db_client: Database client instance
            logger: Optional logger instance (ADR-001 DI)
        """
        self.db = db_client
        self._logger = get_component_logger("sql_adapter", logger)

    def _get_table(self, item_type: str) -> str:
        """Get table name for item type, or raise."""
        table = self.TYPE_TO_TABLE.get(item_type)
        if not table:
            valid = ", ".join(self.TYPE_TO_TABLE.keys())
            raise ValueError(f"Invalid item type: {item_type}. Valid types: {valid}")
        return table

    def _get_id_column(self, table: str) -> str:
        """Get ID column for table."""
        return self.TABLE_ID_COLUMN.get(table, 'id')

    # ============================================================
    # WRITE OPERATIONS
    # ============================================================

    async def write_fact(self, user_id: str, data: Dict[str, Any]) -> str:
        """Write to knowledge_facts table."""
        fact_id = data.get('fact_id') or str(uuid4())
        domain = data.get('domain', 'preferences')
        key = data.get('key', '')
        value = data.get('value', '')
        confidence = data.get('confidence', 1.0)

        query = """
            INSERT INTO knowledge_facts (fact_id, user_id, domain, key, value, confidence, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, domain, key) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                last_updated = excluded.last_updated
        """

        params = (
            fact_id, user_id, domain, key, value,
            confidence, datetime.now(timezone.utc)
        )

        try:
            await self.db.execute(query, params)
            self._logger.info("fact_written", fact_id=fact_id, domain=domain, key=key)
            return fact_id
        except Exception as e:
            self._logger.error("fact_write_failed", error=str(e), domain=domain, key=key)
            raise

    async def write_message(self, session_id: str, data: Dict[str, Any]) -> str:
        """Write to messages table."""
        message_id = str(uuid4())
        message_data = {
            "message_id": message_id,
            "session_id": session_id,
            "role": data.get('role', 'user'),
            "content": data.get('content', ''),
            "created_at": datetime.now(timezone.utc),
        }

        try:
            await self.db.insert("messages", message_data)
            self._logger.info("message_written", message_id=message_id, session_id=session_id)
            return message_id
        except Exception as e:
            self._logger.error("message_write_failed", error=str(e), session_id=session_id)
            raise

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def read_by_id(self, item_id: str, item_type: str) -> Optional[Dict[str, Any]]:
        """Read single item by ID."""
        table = self._get_table(item_type)
        id_column = self._get_id_column(table)

        try:
            if table == 'messages':
                query = f"SELECT * FROM {table} WHERE {id_column} = ?"
                result = await self.db.fetch_one(query, (int(item_id),))
            else:
                query = f"SELECT * FROM {table} WHERE {id_column} = ?"
                result = await self.db.fetch_one(query, (item_id,))

            if result:
                self._logger.debug("item_read", item_id=item_id, item_type=item_type)
                return _convert_uuids_to_strings(dict(result))
            else:
                self._logger.debug("item_not_found", item_id=item_id, item_type=item_type)
                return None

        except Exception as e:
            self._logger.error("read_by_id_failed", error=str(e), item_id=item_id)
            raise

    async def read_by_filter(
        self,
        user_id: str,
        item_type: str,
        filters: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query items with filters."""
        table = self._get_table(item_type)

        # Build WHERE clause
        where_clauses = ["user_id = ?"] if table != 'messages' else []
        params = [user_id] if table != 'messages' else []

        for key, value in filters.items():
            if value is not None:
                where_clauses.append(f"{key} = ?")
                params.append(value)

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        order_column = "last_updated" if table == 'knowledge_facts' else "created_at"

        query = f"""
            SELECT * FROM {table}
            WHERE {where_str}
            ORDER BY {order_column} DESC
            LIMIT ?
        """
        params.append(limit)

        try:
            results = await self.db.fetch_all(query, tuple(params))
            items = [_convert_uuids_to_strings(dict(row)) for row in results]
            self._logger.debug("items_read", user_id=user_id, item_type=item_type, count=len(items))
            return items
        except Exception as e:
            self._logger.error("read_by_filter_failed", error=str(e), item_type=item_type)
            raise

    # ============================================================
    # UPDATE OPERATIONS
    # ============================================================

    async def update_item(self, item_id: str, item_type: str, updates: Dict[str, Any]) -> bool:
        """Update item fields."""
        table = self._get_table(item_type)
        id_column = self._get_id_column(table)

        set_clauses = []
        params = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)

        # Add timestamp update
        if table == 'messages':
            set_clauses.append("edited_at = ?")
        else:
            set_clauses.append("last_updated = ?")
        params.append(datetime.now(timezone.utc))

        set_str = ", ".join(set_clauses)

        try:
            query = f"UPDATE {table} SET {set_str} WHERE {id_column} = ?"
            params.append(item_id)

            await self.db.execute(query, tuple(params))
            self._logger.info("item_updated", item_id=item_id, item_type=item_type)
            return True

        except Exception as e:
            self._logger.error("update_failed", error=str(e), item_id=item_id)
            raise

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete_item(self, item_id: str, item_type: str, soft: bool = True) -> bool:
        """Delete item (soft or hard)."""
        table = self._get_table(item_type)
        id_column = self._get_id_column(table)

        soft_delete_tables = ['messages']

        try:
            query_id = int(item_id) if table == 'messages' else item_id

            if soft and table in soft_delete_tables:
                query = f"UPDATE {table} SET deleted_at = ? WHERE {id_column} = ?"
                await self.db.execute(query, (datetime.now(timezone.utc), query_id))
            else:
                query = f"DELETE FROM {table} WHERE {id_column} = ?"
                await self.db.execute(query, (query_id,))

            self._logger.info("item_deleted", item_id=item_id, item_type=item_type, soft=soft)
            return True

        except Exception as e:
            self._logger.error("delete_failed", error=str(e), item_id=item_id)
            raise
