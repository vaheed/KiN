from __future__

import logging
from contextlib import contextmanager
from typing import Iterator

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

from .config import Settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool = None
        self.redis = None

    def open(self) -> None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        from redis import Redis

        self.pool = ConnectionPool(
            conninfo=self.settings.database_url,
            min_size=self.settings.db_pool_min,
            max_size=self.settings.db_pool_max,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=False,
        )
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        self.pool.open(waiting=True)
        self.redis.ping()
        self._ensure_schema()
        logger.info("database and redis connections ready")

    def close(self) -> None:
        if self.redis is not None:
            self.redis.close()
        if self.pool is not None:
            self.pool.close()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        if self.pool is None:
            raise RuntimeError("database is not started")
        with self.pool.connection() as conn:
            yield conn

    def _ensure_schema(self) -> None:
        with self.connection() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY,
                    memory_type TEXT NOT NULL CHECK (memory_type IN ('semantic', 'episodic')),
                    content TEXT NOT NULL,
                    embedding vector(%s),
                    importance DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    expires_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """ % self.settings.embedding_dimensions
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type_created ON memories(memory_type, created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id UUID PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active','paused','completed','cancelled')),
                    priority INTEGER NOT NULL DEFAULT 50 CHECK (priority >= 0 AND priority <= 100),
                    context JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_status_priority ON goals(status, priority DESC)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id UUID PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    session_id TEXT,
                    goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
                    summary TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(event_type, created_at DESC)")
