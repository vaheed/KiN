from __future__ import annotations

from app.schemas import MemoryCreate, MemorySearchRequest
from app.services.memory import MemoryService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value
        self.ttls[key] = ttl


class FakeBifrost:
    def embed(self, text: str):
        return [float(len(text)), 1.0]


class FakeRepo:
    def __init__(self) -> None:
        self.created = []
        self.searched = []

    def create(self, item, embedding):
        self.created.append((item, embedding))
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "memory_type": item.memory_type.value,
            "content": item.content,
            "importance": item.importance,
            "tags": item.tags,
            "metadata": item.metadata,
            "expires_at": item.expires_at,
            "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-01T00:00:00Z",
        }

    def semantic_search(self, embedding, limit, min_similarity):
        self.searched.append((embedding, limit, min_similarity))
        return []


def test_working_memory_roundtrip(settings) -> None:
    redis = FakeRedis()
    service = MemoryService(settings, FakeRepo(), FakeBifrost(), redis)
    service.update_working("session-1", {"hello": "world"})
    assert service.get_working("session-1")["state"] == {"hello": "world"}
    assert redis.ttls["kin:working:session-1"] == settings.working_memory_ttl_seconds


def test_memory_create_embeds_before_persistence(settings) -> None:
    repo = FakeRepo()
    service = MemoryService(settings, repo, FakeBifrost(), FakeRedis())
    record = service.create(MemoryCreate(content="remember this", importance=0.8))
    assert record.content == "remember this"
    assert repo.created[0][1] == [13.0, 1.0]


def test_memory_search_embeds_and_passes_limits(settings) -> None:
    repo = FakeRepo()
    service = MemoryService(settings, repo, FakeBifrost(), FakeRedis())
    result = service.search(MemorySearchRequest(query="find", limit=4, min_similarity=0.2))
    assert result == []
    assert repo.searched == [([4.0, 1.0], 4, 0.2)]
