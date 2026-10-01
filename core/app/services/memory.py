from __future__ import annotations

import json
from typing import Any

from ..config import Settings
from ..repositories import MemoryRepository
from ..schemas import MemoryCreate, MemoryRecord, MemorySearchRequest, MemorySearchResult
from .bifrost import BifrostClient


class MemoryService:
    def __init__(self, settings: Settings, repo: MemoryRepository, bifrost: BifrostClient, redis_client):
        self.settings = settings
        self.repo = repo
        self.bifrost = bifrost
        self.redis = redis_client

    def create(self, item: MemoryCreate) -> MemoryRecord:
        embedding = self.bifrost.embed(item.content)
        return MemoryRecord.model_validate(self.repo.create(item, embedding))

    def search(self, request: MemorySearchRequest) -> list[MemorySearchResult]:
        embedding = self.bifrost.embed(request.query)
        rows = self.repo.semantic_search(embedding, request.limit, request.min_similarity)
        return [MemorySearchResult.model_validate(row) for row in rows]

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
        self.redis.setex(self._key(session_id), self.settings.working_memory_ttl_seconds, json.dumps(trimmed, default=str))

    @staticmethod
    def _key(session_id: str) -> str:
        return f"kin:working:{session_id}"
