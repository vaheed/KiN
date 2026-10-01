from __future__ import annotations

from uuid import uuid4

from .db import Database
from .schemas import EventCreate, GoalCreate


def _jsonb(value):
    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL operations") from exc
    return Jsonb(value)


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
