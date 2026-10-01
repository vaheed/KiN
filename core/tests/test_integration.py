from __future__ import annotations

import os

import pytest

from app.config import Settings
from app.db import Database


pytestmark = pytest.mark.integration


def test_postgres_and_redis_roundtrip() -> None:
    if os.getenv("KIN_RUN_INTEGRATION") != "1":
        pytest.skip("set KIN_RUN_INTEGRATION=1 to run integration tests")

    settings = Settings(env="test")
    db = Database(settings)
    db.open()
    try:
        with db.connection() as conn:
            assert conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
            assert conn.execute("SELECT extname FROM pg_extension WHERE extname='vector'").fetchone() is not None
        key = "kin:test:integration"
        db.redis.set(key, "ok", ex=30)
        assert db.redis.get(key) == "ok"
        db.redis.delete(key)
    finally:
        db.close()
