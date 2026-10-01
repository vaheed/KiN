from __future__ import annotations

from uuid import UUID, uuid4

from .db import Database
from .schemas import EventCreate, GoalCreate, MemoryCreate


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(v), ".10g") for v in values) + "]"


def _jsonb(value):
    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL operations") from exc
    return Jsonb(value)


class MemoryRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, item: MemoryCreate, embedding: list[float]) -> dict:
        memory_id = uuid4()
        with self.db.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO memories
                    (id, memory_type, content, embedding, importance, tags, metadata, expires_at)
                VALUES
                    (%s, %s, %s, %s::vector, %s, %s, %s, %s)
                RETURNING id, memory_type, content, importance, tags, metadata, expires_at, created_at, updated_at
                """,
                (
                    memory_id,
                    item.memory_type.value,
                    item.content,
                    _vector_literal(embedding),
                    item.importance,
                    _jsonb(item.tags),
                    _jsonb(item.metadata),
                    item.expires_at,
                ),
            ).fetchone()
        return row

    def semantic_search(self, embedding: list[float], limit: int, min_similarity: float) -> list[dict]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, memory_type, content, importance, tags, metadata, expires_at, created_at, updated_at,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM memories
                WHERE embedding IS NOT NULL
                  AND (expires_at IS NULL OR expires_at > now())
                  AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (_vector_literal(embedding), _vector_literal(embedding), min_similarity, _vector_literal(embedding), limit),
            ).fetchall()
        return rows


class GoalRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, item: GoalCreate) -> dict:
        goal_id = uuid4()
        with self.db.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO goals (id, title, description, status, priority, context)
                VALUES (%s, %s, %s, 'active', %s, %s)
                RETURNING id, title, description, status, priority, context, created_at, updated_at
                """,
                (goal_id, item.title, item.description, item.priority, _jsonb(item.context)),
            ).fetchone()
        return row

    def list(self) -> list[dict]:
        with self.db.connection() as conn:
            return conn.execute(
                "SELECT id, title, description, status, priority, context, created_at, updated_at FROM goals ORDER BY priority DESC, created_at DESC"
            ).fetchall()


class EventRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, item: EventCreate) -> dict:
        event_id = uuid4()
        with self.db.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO events (id, event_type, session_id, goal_id, summary, payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, event_type, session_id, goal_id, summary, payload, created_at
                """,
                (event_id, item.event_type, item.session_id, item.goal_id, item.summary, _jsonb(item.payload)),
            ).fetchone()
        return row

    def list(self, limit: int = 100) -> list[dict]:
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT id, event_type, session_id, goal_id, summary, payload, created_at
                FROM events ORDER BY created_at DESC LIMIT %s
                """,
                (limit,),
            ).fetchall()
