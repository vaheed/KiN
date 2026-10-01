from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Settings
from ..schemas import MemoryCreate, MemoryRecord, MemorySearchRequest, MemorySearchResult


class MemoryService:
    """KiN memory facade backed by Mem0 OSS.

    Mem0 owns durable semantic/episodic memory and its consolidation logic.
    Redis remains the working-memory store, while KiN PostgreSQL tables remain
    responsible for goals and the append-only event/audit history.
    """

    def __init__(self, settings: Settings, redis_client):
        self.settings = settings
        self.redis = redis_client
        self._memory = None
        self._memory_lock = threading.Lock()

    def _mem0(self):
        if self._memory is not None:
            return self._memory

        with self._memory_lock:
            if self._memory is None:
                from mem0 import Memory

                history_path = Path(self.settings.memory_history_db_path)
                history_path.parent.mkdir(parents=True, exist_ok=True)

                bifrost_base_url = f"{self.settings.bifrost_url.rstrip('/')}/v1"
                bifrost_api_key = self.settings.bifrost_api_key or "kin-internal"

                config = {
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": self.settings.memory_llm_model,
                            "api_key": bifrost_api_key,
                            "openai_base_url": bifrost_base_url,
                            "temperature": 0.1,
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": self.settings.embedding_model,
                            "api_key": bifrost_api_key,
                            "openai_base_url": bifrost_base_url,
                            "embedding_dims": self.settings.embedding_dimensions,
                        },
                    },
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "dbname": self.settings.db_name,
                            "collection_name": self.settings.memory_collection,
                            "embedding_model_dims": self.settings.embedding_dimensions,
                            "user": self.settings.db_user,
                            "password": self.settings.db_password,
                            "host": self.settings.db_host,
                            "port": self.settings.db_port,
                            "diskann": False,
                            "hnsw": True,
                            "minconn": 1,
                            "maxconn": 5,
                            "sslmode": None,
                        },
                    },
                    "history_db_path": str(history_path),
                    "version": "v1.1",
                    "custom_instructions": (
                        "Only retain stable, reusable information that helps future work. "
                        "Prefer user preferences, durable project facts, recurring infrastructure "
                        "facts, decisions, constraints, and lessons learned. Never retain secrets, "
                        "tokens, passwords, raw credentials, or transient tool output."
                    ),
                }

                self._memory = Memory.from_config(config)

        return self._memory

    def close(self) -> None:
        memory = self._memory
        if memory is not None:
            close = getattr(memory, "close", None)
            if callable(close):
                close()
            self._memory = None

    def create(self, item: MemoryCreate, session_id: str | None = None) -> MemoryRecord:
        """Create an explicit memory without an extra extraction pass.

        Explicit API writes are already curated by the caller. The metadata is
        namespaced so Mem0 can preserve KiN's compatibility fields without
        coupling the application to Mem0's internal payload schema.
        """
        metadata = dict(item.metadata)
        metadata.update(
            {
                "kin_memory_type": item.memory_type.value,
                "kin_importance": item.importance,
                "kin_tags": list(item.tags),
                "kin_source": "api",
            }
        )
        if item.expires_at:
            metadata["kin_expires_at"] = item.expires_at.isoformat()

        result = self._mem0().add(
            item.content,
            user_id=self.settings.memory_user_id,
            agent_id=self.settings.memory_agent_id,
            run_id=session_id,
            metadata=metadata,
            infer=False,
        )
        created = (result.get("results") or [{}])[0]
        memory_id = created.get("id")
        if not memory_id:
            raise RuntimeError("Mem0 did not return a memory id")

        stored = self._mem0().get(memory_id)
        if not stored:
            raise RuntimeError(f"Mem0 memory {memory_id} could not be retrieved after creation")
        return self._record(stored, similarity=None)

    def remember_directive(
        self,
        content: str,
        *,
        session_id: str | None,
        memory_type: str,
        importance: float,
        reason: str,
        goal_id: str | None,
        decision_event_id: str,
    ) -> list[dict[str, Any]]:
        """Let Mem0 infer, consolidate, and update a curated decision memory."""
        metadata = {
            "kin_memory_type": memory_type,
            "kin_importance": importance,
            "kin_source": "decision",
            "kin_reason": reason,
            "kin_goal_id": goal_id,
            "kin_decision_event_id": decision_event_id,
        }
        result = self._mem0().add(
            content,
            user_id=self.settings.memory_user_id,
            agent_id=self.settings.memory_agent_id,
            run_id=session_id,
            metadata=metadata,
            infer=True,
        )
        return list(result.get("results") or [])

    def search(self, request: MemorySearchRequest) -> list[MemorySearchResult]:
        raw = self._mem0().search(
            request.query,
            filters={
                "user_id": self.settings.memory_user_id,
                "agent_id": self.settings.memory_agent_id,
            },
            top_k=request.limit,
            threshold=request.min_similarity,
        )
        results: list[MemorySearchResult] = []
        now = datetime.now(timezone.utc)
        for item in raw.get("results") or []:
            record = self._record(item, similarity=item.get("score"))
            if record.expires_at is not None and record.expires_at <= now:
                continue
            results.append(MemorySearchResult(**record.model_dump(), similarity=float(item.get("score") or 0.0)))
        return results

    def get_working(self, session_id: str) -> dict[str, Any]:
        raw = self.redis.get(self._key(session_id))
        if not raw:
            return {"session_id": session_id, "state": {}}
        return {"session_id": session_id, "state": json.loads(raw)}

    def update_working(self, session_id: str, state: dict[str, Any]) -> None:
        trimmed = state
        if "recent_inputs" in trimmed and len(trimmed["recent_inputs"]) > self.settings.session_max_context_items:
            trimmed = dict(trimmed)
            trimmed["recent_inputs"] = trimmed["recent_inputs"][
                -self.settings.session_max_context_items :
            ]
        self.redis.setex(
            self._key(session_id),
            self.settings.working_memory_ttl_seconds,
            json.dumps(trimmed, default=str),
        )

    @staticmethod
    def _key(session_id: str) -> str:
        return f"kin:working:{session_id}"

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            result = value
        else:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result

    @classmethod
    def _record(cls, item: dict[str, Any], similarity: float | None) -> MemoryRecord:
        metadata = dict(item.get("metadata") or {})
        raw_type = metadata.get("kin_memory_type", "semantic")
        try:
            importance = float(metadata.get("kin_importance", 0.5))
        except (TypeError, ValueError):
            importance = 0.5
        tags = metadata.get("kin_tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]

        expires_at = cls._parse_datetime(metadata.get("kin_expires_at"))
        created_at = cls._parse_datetime(item.get("created_at")) or datetime.now(timezone.utc)
        updated_at = cls._parse_datetime(item.get("updated_at")) or created_at

        return MemoryRecord(
            id=item["id"],
            memory_type=raw_type if raw_type in {"semantic", "episodic"} else "semantic",
            content=item.get("memory") or item.get("data") or "",
            importance=max(0.0, min(1.0, importance)),
            tags=[str(tag) for tag in tags],
            metadata=metadata,
            expires_at=expires_at,
            created_at=created_at,
            updated_at=updated_at,
        )
