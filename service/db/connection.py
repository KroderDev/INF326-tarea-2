import os
import re
from typing import Any, Dict, List, Optional, Tuple

import asyncpg


class AsyncDatabase:
    """Async DB connector backed by asyncpg Pool.

    - Lazily initializes a shared Pool
    - Exposes helpers to prepare SQL with positional parameters
    """

    def __init__(
        self,
        name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        min_size: int = 1,
        max_size: int = 10,
    ) -> None:
        self.name = name or os.getenv("DB_NAME", "messages_service")
        self.user = user or os.getenv("DB_USER", "root")
        self.password = password or os.getenv("DB_PASSWORD", "secret")
        self.host = host or os.getenv("DB_HOST", "database")
        self.port = int(port or os.getenv("DB_PORT", "5432"))
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None

    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.name}"
        )

    async def get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn(),
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=30,
            )
        return self._pool

    @staticmethod
    def prepare(sql: str, params: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Convert ":pN" named params to asyncpg "$N" positional params.

        Preserves the order of first appearance in the SQL string.
        """
        order: List[str] = []
        mapping: Dict[str, int] = {}

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)  # e.g., p1
            if key not in mapping:
                mapping[key] = len(order) + 1
                order.append(key)
            return f"${mapping[key]}"

        new_sql = re.sub(r":(p\d+)\b", repl, sql)
        values: List[Any] = [params.get(k) for k in order]
        return new_sql, values


_adb = AsyncDatabase()


async def get_pool() -> asyncpg.Pool:
    return await _adb.get_pool()


def prepare(sql: str, params: Dict[str, Any]) -> Tuple[str, List[Any]]:
    return AsyncDatabase.prepare(sql, params)
